# Adapted from pico-LCD-1.8.py provided by WaveShare in https://www.waveshare.com/wiki/Pico-LCD-1.8#Examples
import framebuf
import gc
from machine import Pin, SPI, PWM


class LCD_1inch8(framebuf.FrameBuffer):
    def __init__(self, brightness=1, freq=10_000_000, BLpin=13, DCpin=8, RSTpin=12, MOSIpin=11, SCKpin=10, CSpin=9):
        self.width = 160
        self.height = 128
        
        self.BLpwm = PWM(Pin(BLpin))
        self.BLpwm.freq(1000)
        self.brightness = brightness
        
        self.cs = Pin(CSpin, Pin.OUT)
        self.rst = Pin(RSTpin, Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1, freq, polarity=0, phase=0, sck=Pin(SCKpin), mosi=Pin(MOSIpin), miso=None)
        self.dc = Pin(DCpin,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width * 2)
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)
        self.init_display()
        
        self.WHITE = 0xFFFF
        self.BLACK = 0x0000
        self.RED   = self.color(255, 0, 0)
        self.GREEN = self.color(0, 255, 0)
        self.BLUE  = self.color(0, 0, 255)
    
    @property
    def brightness(self):
        return self._brightness
    @brightness.setter
    def brightness(self, value):
        value = min(1, max(0, value)) # Float between 0 and 1
        self._brightness = value
        import math
        self.BLpwm.duty_u16(int(value**2.2*65535)) # max 65535, quadratic relation makes brightness feel more linear
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf: bytearray | int | list[int]):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        if not isinstance(buf, bytearray):
            buf = bytearray([buf] if isinstance(buf, int) else list(buf))
        self.spi.write(buf)
        self.cs(1)

    def init_display(self):
        self.rst(1)
        self.rst(0)
        self.rst(1)
        
        self.write_cmd(0x36)
        self.write_data(0x70)
        
        self.write_cmd(0x3A)
        self.write_data(0x05)

        #ST7735R Frame Rate
        self.write_cmd(0xB1)
        self.write_data([0x01, 0x2C, 0x2D])

        self.write_cmd(0xB2)
        self.write_data([0x01, 0x2C, 0x2D])

        self.write_cmd(0xB3)
        self.write_data([0x01, 0x2C, 0x2D])
        self.write_data([0x01, 0x2C, 0x2D])

        self.write_cmd(0xB4) #Column inversion
        self.write_data(0x07)

        #ST7735R Power Sequence
        self.write_cmd(0xC0)
        self.write_data([0xA2, 0x02, 0x84])
        self.write_cmd(0xC1)
        self.write_data(0xC5)

        self.write_cmd(0xC2)
        self.write_data([0x0A, 0x00])

        self.write_cmd(0xC3)
        self.write_data([0x8A, 0x2A])
        self.write_cmd(0xC4)
        self.write_data([0x8A, 0xEE])

        self.write_cmd(0xC5) #VCOM
        self.write_data(0x0E)

        #ST7735R Gamma Sequence
        self.write_cmd(0xe0)
        self.write_data([0x0f, 0x1a, 0x0f, 0x18, 0x2f, 0x28, 0x20, 0x22, 0x1f, 0x1b, 0x23, 0x37, 0x00, 0x07, 0x02, 0x10])

        self.write_cmd(0xe1)
        self.write_data([0x0f, 0x1b, 0x0f, 0x17, 0x33, 0x2c, 0x29, 0x2e, 0x30, 0x30, 0x39, 0x3f, 0x00, 0x07, 0x03, 0x10])

        self.write_cmd(0xF0) #Enable test command
        self.write_data(0x01)

        self.write_cmd(0xF6) #Disable ram power save mode
        self.write_data(0x00)

        #sleep out
        self.write_cmd(0x11)

        #Turn on the LCD display
        self.write_cmd(0x29)

    def show(self):
        self.write_cmd(0x2A)
        self.write_data([0x00, 0x01, 0x00, 0xA0])
        
        self.write_cmd(0x2B)
        self.write_data([0x00, 0x02, 0x00, 0x81])
        
        self.write_cmd(0x2C)
        self.write_data(self.buffer)
    
    def color(self, R, G, B):
        """ Converts 8-bit red, green and blue values (0-255) to 16 bit hex value in 565 format. """
        return (((G&0b00011100)<<3) +((B&0b11111000)>>3)<<8) + (R&0b11111000)+((G&0b11100000)>>5)
    
    def RGB(self, color565):
        R = (color565 >> 3 & 0b11111) << 3
        G = ((color565 >> 13 & 0b111) + ((color565 & 0b111) << 3)) << 2
        B = (color565 >> 8 & 0b11111) << 3
        return (R, G, B)
    
    # Callback function to update the LCD buffer
    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            r = (color >> 16) & 0xFF
            g = (color >> 8) & 0xFF
            b = color & 0xFF
            self.pixel(x, y, self.color(r, g, b))
    
    def show_image_BMP(self, x, y, file_handle): # Takes a file object, not a path!
        from bmp_file_reader import BMPFileReader # Only import when necessary
        reader = BMPFileReader(file_handle)
        for row_i in range(0, reader.get_height()):
            for col_i, color in enumerate(reader.get_row(row_i)):
                self.set_pixel(x + col_i, y + row_i, (color.red << 16 | color.green << 8 | color.blue))
        del BMPFileReader
        gc.collect()
    
    def show_image_PNG(self, x, y, file_handle): # Takes a file object or path.
        from PNGdecoder import png # Only import when necessary
        png(file_handle, callback=self.set_pixel, fastalpha=False).render(x, y)
        del png
        gc.collect()
    
    def show_image_JPG(self, x, y, file_handle): # Takes a file object or path.
        from JPEGdecoder import jpeg # Only import when necessary
        jpeg(file_handle, callback=self.set_pixel).render(x, y)
        del jpeg
        gc.collect()
        

if __name__ == "__main__":
    LCD = LCD_1inch8(freq=200_000)
    #color BRG
    LCD.fill(LCD.WHITE)
 
    LCD.show()
    
    LCD.fill_rect(0,0,160,20,LCD.RED)
    LCD.rect(0,0,160,20,LCD.RED)
    LCD.text("Raspberry Pi Pico",2,8,LCD.WHITE)
    
    LCD.fill_rect(0,20,160,20,LCD.BLUE)
    LCD.rect(0,20,160,20,LCD.BLUE)
    LCD.text("PicoGo",2,28,LCD.WHITE)
    
    LCD.fill_rect(0,40,160,20,LCD.GREEN)
    LCD.rect(0,40,160,20,LCD.GREEN)
    LCD.text("Pico-LCD-1.8",2,48,LCD.WHITE)
    
    LCD.fill_rect(0,60,160,10,0X07FF)
    LCD.rect(0,60,160,10,0X07FF)
    LCD.fill_rect(0,70,160,10,0xF81F)
    LCD.rect(0,70,160,10,0xF81F)
    LCD.fill_rect(0,80,160,10,0x7FFF)
    LCD.rect(0,80,160,10,0x7FFF)
    LCD.fill_rect(0,90,160,10,0xFFE0)
    LCD.rect(0,90,160,10,0xFFE0)
    LCD.fill_rect(0,100,160,10,0XBC40)
    LCD.rect(0,100,160,10,0XBC40)
    LCD.fill_rect(0,110,160,10,0XFC07)
    LCD.rect(0,110,160,10,0XFC07)
    LCD.fill_rect(0,120,160,10,0X8430)
    LCD.rect(0,120,160,10,0X8430)
    
    LCD.show()

    # Show the content on the display
    LCD.brightness = 1
    LCD.show()
