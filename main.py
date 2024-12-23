import json
import ntptime
import time

from machine import Timer, Pin
from segmentdisplay import SegmentDisplay
from web import connect, get_ll_data


class CountdownDisplay(SegmentDisplay):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.NETepoch = 0 # Will show on screen as "LOADING.."
        connect()

        self.show()
        self.timer_display = Timer()
        self.timer_display.init(freq=1, mode=Timer.PERIODIC, callback=self.show)

        self.update_NET()
        self.timer_update_NET = Timer()
        self.timer_update_NET.init(period=600000, mode=Timer.PERIODIC, callback=self.update_NET)
    
    def fetch_LL(self, min_t=300):
        try: # Check if we have requested it within the last <min_t> seconds
            with open("llcache.json", "r") as llcache:
                llc = json.load(llcache)
            if llc["lastfetch"] > time.time() - min_t:
                self.response = llc
                return
        except Exception:
            pass

        print("Fetching LL data...")
        response = get_ll_data(t_min=time.time() - 3600)
        d = response.json()
        d["lastfetch"] = time.time()
        self.response = d
        with open("llcache.json", "w") as llcache:
            json.dump(d, llcache)
    
    def update_NET(self, *args, min_t=300, **kwargs):
        self.fetch_LL(min_t=min_t)
        try:
            NET = self.response['results'][0]['net']
            if NET[19] != "Z": raise ValueError("Must receive time in UTC")
            year, month, day, hour, minute, second = int(NET[0:4]), int(NET[5:7]), int(NET[8:10]), int(NET[11:13]), int(NET[14:16]), int(NET[17:19])
            self.NETepoch = time.mktime((year, month, day, hour, minute, second, 0, 0)) # Last two zeroes are day of week and day of year, but ignore those
        except Exception:
            self.NETepoch = -1 # Will display as "API.ISSUE"
        
    def dt(self):
        """ Returns a 4-tuple (sign, H, M, S), where sign is 1 for T-, 0 for T+. """
        t = self.NETepoch - time.time()
        sign = t >= 0
        t = abs(t)
        H = t // 3600
        t -= H*3600
        M = t // 60
        t -= M*60
        return (sign, H, M, t)
    
    def flash(self, dt=0.5):
        def switch(): self.brightness = 16 - self.brightness
        switch()
        schedule(dt, switch)

    def show(self, *args, **kwargs):
        specials = {0: "LOADING..", -1: "API.ISSUE"}
        if self.NETepoch in specials.keys():
            self.display_message(specials[self.NETepoch])
            return
        dt = self.dt()
        tstr = f"{dt[1]:2d}.{dt[2]:02d}.{dt[3]:02d}"
        if dt[1] == 0: # <1h
            tstr = f"{dt[2]:4d}.{dt[3]:02d}"
            if dt[2] == 0: # <1min
                tstr = f"{dt[3]:6d}"
        if dt[0]: # T-
            if dt[1] == 0 and dt[2] == 0: self.flash()
            self.display_message(("t-" + tstr)[-10:])
        else: # T+
            self.display_message(("  " + tstr)[-10:])

def schedule(t, f): # Run function <f> (without arguments) after <t> seconds
    timer = Timer()
    timer.init(mode=Timer.ONE_SHOT, period=int(t*1000), callback=lambda timer: f())


display = CountdownDisplay(brightness=1)
