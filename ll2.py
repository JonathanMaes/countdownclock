import errno
import gc
import json
import requests
import time
from machine import Timer

import medea
from web import connect


class LL2Sync:
    def __init__(self, API_throttle: int = 15, keep_seconds: int = 3600, cachefile="llcache.json"):
        connect()
        self.API_throttle = API_throttle # Request at most <API_throttle> requests per hour
        self.keep_seconds = keep_seconds # Launch will be displayed until at most T+<keep_seconds>

        self.queue = []
        self.thresholds = Threshold([180, 60, -60, -180]) # Seconds until launch (<0 is T+) when we will re-fetch data (to detect HOLD HOLD HOLD)
        self._t_min = 0 # Earliest time when we want to know a launch (used in get_upcoming)

        self.cachefile = cachefile
        self.cache_load()
        
        self.timer_tick = Timer()
        self.timer_tick.init(period=10*1000, mode=Timer.PERIODIC, callback=lambda timer: self.tick())
    
    @property
    def t_min(self): # Adjusts _t_min appropriately
        self._t_min = max(self._t_min, time.time() - self.keep_seconds) # At most keep_seconds ago
        if len(self.launches) >= 2: # Check if launch 1 is closer than launch 0
            dt_last = time.time() - self.launches[0]["net_epoch"] # Seconds since launch 0
            dt_next = self.launches[1]["net_epoch"] - time.time() # Seconds until launch 1
            if dt_next < dt_last:
                self._t_min = self.launches[0]["net_epoch"] + 1
        return self._t_min
    
    @property
    def request_dt(self):
        # Two launches within 1 hour only happened twice in 2024. Probably more frequent in the future, but still rare.
        n = max(1, self.API_throttle - len(self.thresholds)) # So allow room for Thresholds to be triggered once per hour
        dt = int(3600/n) + 1
        return min(dt, 600) # Wait at most 10 minutes
    
    def cache_save(self):
        with open(self.cachefile, "w") as llcache:
            json.dump({"launches": self.launches, "lastfetch": self.lastrequesttime}, llcache)
    
    def cache_load(self):
        try:
            with open(self.cachefile, "r") as llcache:
                llc = json.load(llcache)
                self.launches = llc["launches"]
                self.lastrequesttime = llc["lastfetch"]
            for launch in self.launches:
                if not launch.get("detailed", False): # Launch was not yet fetched in detailed mode
                    self.queue_details(launch["id"])
        except (OSError, KeyError): # File not found or invalid
            self.launches = []
            self.lastrequesttime = 0
            self.cache_save() # Should create or overwrite file

    @property
    def NETepoch(self):
        if len(self.launches) == 0: return 0
        # TODO: return -1 if API issue, but somehow have to store that we had an issue then.
        return self.launches[0]["net_epoch"]
    
    @property
    def dt(self):
        return self.NETepoch - time.time()
    
    @property
    def dt_tuple(self):
        """ Returns a 4-tuple (sign, H, M, S), where sign is 1 for T-, 0 for T+. """
        S = abs(self.dt)
        H = S // 3600
        S -= H*3600
        M = S // 60
        S -= M*60
        return (self.dt >= 0, H, M, S)

    def tick(self): # Performs all the checks and requests information when needed. Should be run every few seconds or so.
        gc.collect()
        # HOW ABOUT THIS:
        #   -> Must make sure that we do not empty this queue too rapidly, otherwise threshold requests might fail.
        #        -> Idea: we could keep track of <i>, the number of requests performed, and when it exceeds
        #                 <API_throttle>-5, we do not request anymore unless it is a threshold. When we hit this
        #                 amount, request our quota from the API after every request and update <i> accordingly.
        
        if self.thresholds.pass_check(self.dt): # Threshold passed: should definitely re-fetch NETs
            self.get_upcoming()
        if time.time() - self.lastrequesttime > self.request_dt: # Sufficient time has passed since last request
            if len(self.queue) == 0: # No special requests
                self.get_upcoming()
            else:
                self.queue[0]()
                self.queue.pop(0)
        # Remove launches from before <self.t_min>
        n = len(self.launches)
        self.launches = list(filter(lambda launch: launch["net_epoch"] > self.t_min, self.launches))
        if len(self.launches) < n: # A launch has been removed, so update everything.
            self.get_upcoming()

    def request(self, endpoint) -> medea.LazyRequest | None:
        url = "https://ll.thespacedevs.com/2.3.0/" + endpoint.lstrip("/")
        if self.lastrequesttime > time.time(): return
        self.lastrequesttime = time.time()
        try:
            response = medea.LazyRequest(url, timeout=10.)
            if response.status_code == 429: # Too many requests
                    response_throttle = requests.get("https://ll.thespacedevs.com/2.3.0/api-throttle/") # Just use requests lib, this is a small JSON
                    self.lastrequesttime = time.time() + response_throttle.json()["next_use_secs"]
                    return
            elif response.status_code == 200: return response
            else: return
        except OSError as e:
            if e.errno == errno.EHOSTUNREACH:
                connect() # WIFI connection likely lost
                return self.request(endpoint)
            else:
                raise e
    
    def update_launch_data(self, lazyreq: medea.LazyRequest, detailed: bool = False): # Puts relevant information from an LL2 launch response into self.launches.
        """ When <detailed> is True, the ["detailed"] field of affected launches is set to True, preventing further detailed requests. """
        new = [{}] # List of launches in the response. We will build this up during the JSONgen, and merge with self.launches later.
        
        JSONgen = lazyreq.tokenize()
        path = []
        i = d = 0
        def check_field(*keypath): return path[d:] == list(keypath)

        for tok, val in JSONgen:
            if medea.extendpath(path, tok, val): continue # Not at a key-value pair
            # API either returns a pure launch, or an object like {<request_metadata>, "results": [<launch(es)>]}
            if path[0] == "results": # Response includes some metadata, so ignore that
                i = int(path[1]) # Number of launch we are at in the response (for indexing <new>)
                d = 2 # Offset for indexing (because we have to skip ["results"][i])
                if len(new) <= i: new.append({})

            l = new[i]
            if check_field("id"):
                l["id"] = val
            elif check_field("net"):
                l["net"] = val
                l["net_epoch"] = iso8601_to_unix(l["net"])
            elif check_field("net_precision", "id"):
                l["net_precision_id"] = val # >2: Uncertainty >1h, so probably not interesting to show on clock
            elif path[d] == "status": # Dict with "id", "name", "abbrev" and "description"
                l.setdefault("status", {}) # Setting a dict requires some extra effort
                l["status"][path[d+1]] = val
            elif check_field("image", "thumbnail_url"):
                l["image_thumbnail_url"] = val
            elif check_field("name"):
                split = val.split(" | ") # Failsafe when not using detailed mode
                if len(split) != 2: continue
                l.setdefault("rocket_name", split[0])
                l.setdefault("payload_name", split[1])
            elif check_field("rocket", "configuration", "full_name"):
                l["rocket_name"] = val
            elif check_field("mission", "name"):
                l["payload_name"] = val
            elif check_field("pad", "name"):
                l["pad"] = val
            elif check_field("pad", "location", "name"):
                l["pad_location"] = val
            elif check_field("launch_service_provider", "name"):
                l["lsp"] = val
            elif "country" in path: # Country codes are found in many places. Set country in increasing order of importance.
                priorities = [ # First has highest priority
                    ("rocket", "configuration", "manufacturer", "country", 0, "alpha_2_code"),
                    ("launch_service_provider", "country", 0, "alpha_2_code"),
                    ("mission", "agencies", 0, "country", 0, "alpha_2_code"),
                    ("pad", "country", "alpha_2_code"),
                    ("pad", "agencies", 0, "country", 0, "alpha_2_code")
                ]
                for i, p in enumerate(priorities):
                    if check_field(*p):
                        if l.get("country_importance", 100) > i:
                            l["country"] = val
                            l["country_importance"] = i
                            break

        # Update <self.launches> with <new>
        for launch in new:
            if (ID := launch.get("id")) is None: continue
            launch.pop("country_importance", None)
            
            # Have we requested this ID yet?
            ls = [l for l in self.launches if l["id"] == ID]
            if ls: # Known launch
                l = ls[0]
            else: # New launch: add and fetch details
                l = {"id": ID, "detailed": False}
                self.launches.append(l)
                self.queue_details(ID)
            
            merge(l, launch) # <launch> will overwrite fields in <l>
            
            if detailed: l["detailed"] = True
        
        # Remove launches that are not in the upcoming
        if not detailed: # Only do this when we are making an "upcoming" request
            IDs = [l["id"] for l in new]
            self.launches = list(filter(lambda launch: launch["id"] in IDs, self.launches))
        
        # Sort and save
        self.launches.sort(key=lambda launch: launch["net_epoch"]) # Keep ordered if times would have changed
        self.cache_save()
    
    def get_upcoming(self, n=10):
        t_min = unix_to_iso8601(self.t_min)
        endpoint = f"/launches/upcoming/?limit={n:d}&mode=list&ordering=net&net__gt={t_min}"
        response = self.request(endpoint)
        if response is None: return
        self.update_launch_data(response, detailed=False)
    
    def get_details(self, ID): # Fetches launch <ID> in detailed mode
        endpoint = f"/launches/upcoming/?id={ID}&mode=normal" # TODO: can now change "normal" to "detailed" because memory constraints should be gone
        response = self.request(endpoint)
        if response is None: return
        self.update_launch_data(response, detailed=True)
    
    def queue_details(self, ID):
        self.queue.append(lambda: self.get_details(ID))
        self.queue.append(self.get_upcoming) # After fetching details, make sure to update NETs before next element in queue
            


class Threshold:
    def __init__(self, thresholds: list[float], start_value=0):
        """ Given a list of <thresholds>, calling self.pass_check(value) will check if <value> passes any of
            those thresholds when coming from the <old_value> of the previous self.pass_check(old_value) call
            (most recently passed threshold is disabled until another is passed, so <len(thresholds)> must be > 2).
        """
        self.thresholds = thresholds # List of thresholds where self.check() returns true if passed
        self.value = start_value # Last seen value
        self._last_th_passed = None # Used to make sure we don't activate the same threshold twice in row (is annoying)

    def pass_check(self, value):
        """ Returns True if a threshold was passed/reached when going from <value> to <self.value>. """
        f = lambda threshold: (threshold - value)*(threshold - self.value) <= 0 and self.value != threshold
        thresholds_passed = list(filter(f, self.thresholds))
        self.value = value

        if len(thresholds_passed) == 0: return False # No thresholds passed
        if self._last_th_passed is not None:
            if len(thresholds_passed) == 1:
                if self._last_th_passed == thresholds_passed[0]: # The only passed threshold is the last passed one
                    return False

        # Find the nearest passed threshold and return True
        deltas = [abs(threshold - value) for threshold in self.thresholds]
        nearest_th_i = deltas.index(min(deltas)) # Get argmin of <deltas> without numpy
        self._last_th_passed = nearest_th_i
        return True

    def __len__(self): return len(self.thresholds)


def get_safe(d: dict, *args, default=None):
    """ Can be used to get keys from a dictionary that are not guaranteed to exist. """
    s = d
    for arg in args:
        try:
            s = s[arg]
        except Exception:
            return default
    return s

def merge(a, b, path=None, update=True):
    """ From https://stackoverflow.com/a/25270947 """
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            elif isinstance(a[key], list) and isinstance(b[key], list):
                for idx, val in enumerate(b[key]):
                    a[key][idx] = merge(a[key][idx], b[key][idx], path + [str(key), str(idx)], update=update)
            elif update:
                a[key] = b[key]
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a

def unix_to_iso8601(unix):
    t = time.gmtime(unix)
    return f"{t[0]}-{t[1]:02d}-{t[2]:02d}T{t[3]:02d}:{t[4]:02d}:{t[5]:02d}Z"

def iso8601_to_unix(iso):
    if iso[19] != "Z": raise ValueError("Must receive ISO8601 time in UTC")
    year, month, day, hour, minute, second = int(iso[0:4]), int(iso[5:7]), int(iso[8:10]), int(iso[11:13]), int(iso[14:16]), int(iso[17:19])
    return time.mktime((year, month, day, hour, minute, second, 0, 0)) # Last two zeroes are day of week and day of year, but ignore those

if __name__ == "__main__":
    LL2 = LL2Sync()
    if len(LL2.launches):
        LL2.get_details(LL2.launches[0]["id"])
