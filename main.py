import gc
import krequests
import time

from machine import Timer

from lcd import LCD_1inch8
from ldr import LDR
from ll2 import LL2Sync
from segmentdisplay import SegmentDisplay
from utils import isdst_CET, log_exc, wrap_text, wrap_timer
from web import connect


class CountdownClock:
    def __init__(self, SegmentDisplay_kwargs: dict = None, LCD_kwargs: dict = None, LDR_kwargs: dict = None, show_CET: bool = False):
        if SegmentDisplay_kwargs is None: SegmentDisplay_kwargs = {}
        if LCD_kwargs is None: LCD_kwargs = {}
        if LDR_kwargs is None: LDR_kwargs = {}
        self.segmentdisplay = SegmentDisplay(**SegmentDisplay_kwargs)
        self.LCDdisplay = LCD_1inch8(**LCD_kwargs)
        self.LCD_last_update = 0 # Seconds since epoch.
        self.LDR = LDR(**LDR_kwargs)
        self.brightness_update(delta=None)
        self.show_CET = show_CET

        self.segmentdisplay.display_message("CONNECT..")
        connect() # LL2 does this as well, but can't hurt to try already
        self.segmentdisplay.display_message("LOADING..")
        self.LL2 = LL2Sync(dev=False)
        self.timer_display = Timer()
        self.timer_display.init(freq=1, mode=Timer.PERIODIC, callback=lambda timer: wrap_timer(self.show))

    def brightness_update(self, delta: float|None = 0.05):
        """ Sets the brightness based on the LDR connected to the system.
            If `delta` is not `None`, this changes the brightness slightly (by `0 < delta < 1`).
            If `delta` is `None`, it just gets set instantly.
        """
        level = self.LDR.measure()
        if delta is None:
            self.brightness = 0.1 if level > 3000 else 1.1
        else:
            self.brightness *= (1 - delta) if level > 3000 else 1/(1 - delta)
            self.brightness = min(1, max(0.1, self.brightness))
        # Set LCD and segment display brightness based on self.brightness
        self.LCDdisplay.brightness = self.brightness
        self.segmentdisplay.brightness = self.brightness*16 - 1

    def show(self): # Runs every second
        gc.collect()
        print(gc.mem_alloc(), gc.mem_free())
        # 7-segment display
        specials = {0: "LOADING..", -1: "API.ISSUE"} # Special values of NETepoch to display
        if self.LL2.NETepoch in specials.keys():
            self.segmentdisplay.display_message(specials[self.LL2.NETepoch])
            return
        dt = self.LL2.dt_tuple
        tstr = f"{dt[1]:2d}.{dt[2]:02d}.{dt[3]:02d}"
        if dt[1] == 0: # <1h
            tstr = f"{dt[2]:4d}.{dt[3]:02d}"
            if dt[2] == 0: # <1min
                tstr = f"{dt[3]:6d}"
        if dt[0]: # T-
            self.segmentdisplay.display_message(("t-" + tstr)[-10:])
        else: # T+
            self.segmentdisplay.display_message(("  " + tstr)[-10:])
        if dt[0] and dt[1] == dt[2] == 0: self.segmentdisplay.flash()
        else: self.segmentdisplay.flash(False)
        
        # LCD display
        if self.LCD_last_update < self.LL2.lastrequesttime: # Only update LCD when LL2 was updated.
            self.LCD_last_update = max(self.LL2.lastrequesttime, time.time())
            l = self.LL2.launches[0] if len(self.LL2.launches) != 0 else {}
            c = int(self.LCDdisplay.width/2) # Center pixel
            
            self.LCDdisplay.fill(self.LCDdisplay.BLACK)
            # Flag
            country = l.get("country")
            flag_shown = country is not None
            if flag_shown:
                try:
                    gc.collect()
                    response = krequests.get(f"https://raw.githubusercontent.com/yammadev/flag-icons/bd4bcf4f4829002cd10416029e05ba89a7554af4/png/{country.upper()}.png", recvsize=2048)[1]
                    self.LCDdisplay.show_image_PNG(0, 0, response)
                except Exception as e:
                    log_exc(e)
                    flag_shown = False
                    connect()
            # Rocket name
            row = 4
            name = wrap_text(l.get("rocket_name", ""), 20 - 3*flag_shown).split("\n")
            for part in name:
                self.LCDdisplay.text(part, c + 12*flag_shown - len(part)*4, row, self.LCDdisplay.WHITE)
                row += 9
            row = max(row, 15) # Flag is 15 pixels high
            self.LCDdisplay.hline(0, row, self.LCDdisplay.width, self.LCDdisplay.WHITE)
            # Payload name
            row += 8
            name = wrap_text(l.get("payload_name", ""), 20).split("\n")
            for part in name:
                self.LCDdisplay.text(part, c - len(part)*4, row, self.LCDdisplay.GREEN)
                row += 9
            # Pad name
            row += 8
            pad = l.get("pad")
            if pad is None: pad = ""
            loc = l.get("pad_location")
            if loc is None: loc = ""
            name = pad + (", " if pad else "") + loc
            for part in wrap_text(name).split("\n"):
                self.LCDdisplay.text(part, c - len(part)*4, row, self.LCDdisplay.color(128, 128, 128))
                row += 9

            # Status
            status = l.get("status", {})
            status_id = status.get("id")
            status_text = status.get("name", "Status Unknown")
            if len(status_text) > 20: status_text = status.get("abbrev")
            colors = {
                1: self.LCDdisplay.GREEN, # Go for launch
                5: self.LCDdisplay.color(0, 0, 128), # Hold
                6: self.LCDdisplay.WHITE, # In flight
                9: self.LCDdisplay.GREEN, # Payload deployed
                3: self.LCDdisplay.GREEN, # Launch successful
                4: self.LCDdisplay.color(160, 0, 0), # Launch failure
                7: self.LCDdisplay.RED, # Launch partial failure
            } # 2: TBD, 8: TBC
            col = colors.get(status_id, self.LCDdisplay.BLACK)
            R, G, B = self.LCDdisplay.RGB(col)
            brightness = 1e-4*(456*R*R + 896*G*G + 174*B*B)**.5 # From https://stackoverflow.com/a/24213274
            anticol = self.LCDdisplay.WHITE if brightness < 0.5 else self.LCDdisplay.BLACK
            status_height = 16
            self.LCDdisplay.fill_rect(0, self.LCDdisplay.height - status_height, self.LCDdisplay.width, status_height, colors.get(status_id, self.LCDdisplay.BLACK))
            self.LCDdisplay.hline(0, self.LCDdisplay.height - status_height - 1, self.LCDdisplay.width, self.LCDdisplay.WHITE)
            self.LCDdisplay.text(status_text, c - len(status_text)*4, self.LCDdisplay.height - 8 - int(status_height/2 - 4), anticol)

            # Launch time
            try:
                dst = isdst_CET(l["net_epoch"])
            except ValueError as e:
                log_exc(e)
                self.show_CET = dst = False
            TZ = ("CEST" if dst else "CET") if self.show_CET else "UTC"
            T = l["net_epoch"] + self.show_CET*(7200 if dst else 3600)
            weekday = (int(T // 86400) + 4) % 7
            hour = int( T // 3600 ) % 24
            minute = int( T // 60 ) % 60
            second = T % 60
            weekdays = ["Zo", "Ma", "Di", "Wo", "Do", "Vr", "Za"]
            time_height = 10
            time_text = f":{second:02d}"*bool(second)
            time_text = f"{weekdays[weekday]}, {hour}:{minute:02d}{time_text} {TZ}"
            self.LCDdisplay.fill_rect(0, self.LCDdisplay.height - status_height - 1 - time_height, self.LCDdisplay.width, time_height, self.LCDdisplay.BLACK)
            self.LCDdisplay.text(time_text, c - len(time_text)*4, self.LCDdisplay.height - status_height - 1 - 8 - int(time_height/2 - 4), self.LCDdisplay.WHITE)

            self.LCDdisplay.show()
        
        ## Light level
        self.brightness_update()


if __name__ == "__main__":
    try:
        display = CountdownClock(show_CET=True)
    except KeyboardInterrupt:
        exit()
    except Exception as e:
        log_exc(e)
