from machine import Pin, SoftI2C

from utils import schedule


class SegmentDisplay:
    """ Controls the '8-Digital LED Segment Display Module V1.0' by DFRobot. """
    def __init__(self, sdapin: int = 4, sclpin: int = 5, brightness: int = 15, blink: int = 0, address: int = 0x70):
        self.i2c = SoftI2C(sda=Pin(sdapin), scl=Pin(sclpin))
        self.address = address # Address of the LED display module. Can be changed by soldering A0 and A1 at back of display.
        self._brightness = self._blink = 0
        self.flashing = False
        self.brightness = brightness # <0: screen off. 0-15: increasing brightness (15=brightest).
        self.blink = blink # 0: continuously on, 1-3: blink increasingly fast (1: 1s on & 1s off, 2: 0.5s, 3: 0.25s)
        self.configure()
        self.char_map = { # Segment order: dot, center, top left, bottom left, bottom, bottom right, top right, top
            'A': 0b01110111, 'C': 0b00111001, 'D': 0b01011110, 'E': 0b01111001, 'F': 0b01110001, 'G': 0b00111101,
            'H': 0b01110110, 'I': 0b00110000, 'J': 0b00001110, 'L': 0b00111000, 'N': 0b00110111, 'O': 0b00111111,
            'P': 0b01110011, 'S': 0b01101101, 'T': 0b01111000, 'U': 0b00111110, 'Z': 0b01011011,
            '0': 0b00111111, '1': 0b00000110, '2': 0b01011011, '3': 0b01001111, '4': 0b01100110,
            '5': 0b01101101, '6': 0b01111101, '7': 0b00000111, '8': 0b01111111, '9': 0b01101111,
            ' ': 0b00000000, '-': 0b01000000, ':': 0b01001000, ')': 0b01001100, "'": 0b00100000, '"': 0b00100010,
            '.': 0b10000000
        }
    
    @property
    def brightness(self):
        if self._brightness < 0: # <0 are special values
            return self._brightness # -1: off, should remain off
        if self.flashing:
            return 15 if self._brightness < 8 else 0
        else:
            return self._brightness
    @brightness.setter
    def brightness(self, b):
        self._brightness = min(15, max(-1, int(b))) # Must be value <16 
        self.configure()
    
    @property
    def blink(self):
        return self._blink
    @blink.setter
    def blink(self, b):
        self._blink = min(3, max(0, int(b))) # Must be value in range 0 to 3
        self.configure()

    def flash(self, state=None):
        self.flashing = not self.flashing if state is None else state
        self.configure()
    
    def send_data(self, data: list):
        self.i2c.writeto(self.address, bytes(data))
    
    def configure(self):
        # System setup (oscillator on)
        self.send_data([0x21])
        # Set blink (81/89: no blink, 83: fast blink, 85: blink, 87: slow blink, other 8X-values: display off)
        self.send_data([0x89 - 2*self.blink] if self.brightness >= 0 else [0x80])
        # Set brightness (E0 - EF: increasing brightness)
        self.send_data([0xE0 + self.brightness])

    def display_message(self, message, offset=0):
        # Map characters to the corresponding data, assuming simple ASCII-to-segment mapping
        data = []
        message = list(message)
        for i, char in enumerate(message):
            if char == '.':
                if i > 0:
                    if message[i-1] != '.': continue
            value = self.char_map.get(char.upper(), 0)  # Default to blank if unknown
            if i < len(message) - 1:
                if message[i+1] == '.' and char != '.':
                    value |= 0b10000000 # Decimal point (add to characters as needed)
            data.append(value)
            data.append(0) # No clue why this is necessary

        data = (data + [0]*16)[:16] # 16 (idk why it's not 8)
        self.send_data([(0x00 + offset) % 0x10] + data)  # 0x00 is the starting register address

if __name__ == "__main__":
    import time
    display = SegmentDisplay()
    for i in range(16):
        display.brightness = i
        display.display_message(f"tESt {i}")
        time.sleep(.5)
        display.flash()
        time.sleep(.5)
        display.flash()
        time.sleep(.5)
