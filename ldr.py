from machine import ADC
import time


class LDR:
    def __init__(self, pin: int = 27):
        self.ldr = ADC(pin)
    
    def measure(self, dt: float = 1e-2) -> float:
        """ Measures an inverse light level metric over the next `dt` seconds.
            Typical values: dark room >5000, lit room ~2000, no LDR connected ~15000.
        """
        n = val = 0
        t_stop = time.time_ns() + int(dt*1e9)
        while time.time_ns() < t_stop or n == 0:
            val += self.ldr.read_u16()
            n += 1
        return val/n


if __name__ == "__main__":
    ldr = LDR()
    while True:
        print(ldr.measure())
        time.sleep(1)
