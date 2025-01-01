import requests
import sys
import time
from machine import Timer

from lcd import LCD_1inch8
from ll2 import LL2Sync, unix_to_iso8601
from segmentdisplay import SegmentDisplay


class CountdownClock:
    def __init__(self, brightness: float = None, SegmentDisplay_kwargs: dict = None, LCD_kwargs: dict = None):
        self.LL2 = LL2Sync()
        if SegmentDisplay_kwargs is None: SegmentDisplay_kwargs = {}
        if LCD_kwargs is None: LCD_kwargs = {}
        if brightness is not None:
            SegmentDisplay_kwargs["brightness"] = brightness*16 - 1
            LCD_kwargs["brightness"] = brightness
        self.segmentdisplay = SegmentDisplay(**SegmentDisplay_kwargs)
        self.LCDdisplay = LCD_1inch8(**LCD_kwargs)
        self.LCD_last_update = 0 # Seconds since epoch.

        self.show()
        self.timer_display = Timer()
        self.timer_display.init(freq=1, mode=Timer.PERIODIC, callback=lambda timer: self.show())

    def show(self): # Runs every second
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
            if dt[1] == 0 and dt[2] == 0: self.segmentdisplay.flash()
            self.segmentdisplay.display_message(("t-" + tstr)[-10:])
        else: # T+
            self.segmentdisplay.display_message(("  " + tstr)[-10:])
        
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
                    flag = requests.get(f"https://raw.githubusercontent.com/yammadev/flag-icons/bd4bcf4f4829002cd10416029e05ba89a7554af4/png/{country.upper()}.png").content
                    self.LCDdisplay.show_image_PNG(0, 0, flag)
                except Exception:
                    flag_shown = False
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
            status_id = 2
            colors = {
                1: self.LCDdisplay.GREEN, # Go for launch
                5: self.LCDdisplay.color(0, 0, 128), # Hold
                6: self.LCDdisplay.WHITE, # In flight
                9: self.LCDdisplay.GREEN, # Payload deployed
                3: self.LCDdisplay.GREEN, # Launch successful
                4: self.LCDdisplay.RED, # Launch failure
                7: self.LCDdisplay.color(255, 80, 0), # Launch partial failure
            } # 2: TBD, 8: TBC
            col = colors.get(status_id, self.LCDdisplay.BLACK)
            anticol = col ^ 0xFFFF # Inverse color
            status_height = 16
            self.LCDdisplay.fill_rect(0, self.LCDdisplay.height - status_height, self.LCDdisplay.width, status_height, colors.get(status_id, self.LCDdisplay.BLACK))
            self.LCDdisplay.hline(0, self.LCDdisplay.height - status_height - 1, self.LCDdisplay.width, self.LCDdisplay.WHITE)
            self.LCDdisplay.text(status_text, c - len(status_text)*4, self.LCDdisplay.height - 8 - int(status_height/2 - 4), anticol)

            self.LCDdisplay.show()

def wrap_text(text: str, line_length: int = 20): # Screen is 20 characters wide
    lines = ['']
    for word in text.split():
        line = f'{lines[-1]} {word}'.strip()
        if len(line) <= line_length:
            lines[-1] = line
        else:
            lines.append(word)
    return '\n'.join(lines)


if __name__ == "__main__":
    try:
        display = CountdownClock(brightness=1)
    except KeyboardInterrupt:
        exit()
    except Exception as e:
        with open("err.log", "w") as logfile:
            logfile.write(f"{unix_to_iso8601(time.time())}\n")
            sys.print_exception(e, file=logfile)
