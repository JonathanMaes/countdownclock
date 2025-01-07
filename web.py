import errno
import json
import network
import ntptime
import time
from machine import Pin

def connect(): # Expects wlan.json to contain {"ssid": ..., "password": ...}
    pico_led = Pin("LED", Pin.OUT)
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        print("WIFI already connected.")
        return
    wlan.active(True)
    with open("wlan.json", "r") as w:
        cred = json.load(w)
        wlan.connect(cred["ssid"], cred["password"]) # WIFI network name and password
    while wlan.isconnected() == False:
        for _ in range(10): # Blink onboard LED while not connected to WLAN
            pico_led.toggle()
            time.sleep(0.2)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    pico_led.on()
    setUTCtime()
    pico_led.off()
    return ip

def setUTCtime():
    try: # Fetch and set the correct UTC time
        ntptime.settime()
    except Exception as e:
        if e.errno != errno.ETIMEDOUT: raise e

if __name__ == "__main__":
    connect()
