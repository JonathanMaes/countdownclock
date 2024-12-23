import asyncio
import errno
import json
import network
import ntptime
import requests
import time

from machine import Pin

def connect(): # Expects wlan.json to contain {"ssid": ..., "password": ...}
    pico_led = Pin("LED", Pin.OUT)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    with open("wlan.json", "r") as w:
        cred = json.load(w)
        wlan.connect(cred["ssid"], cred["password"]) # WIFI network name and password
    while wlan.isconnected() == False:
        for _ in range(10): # Blink onboard LED while not connected to WLAN
            pico_led.toggle()
            time.sleep(0.1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    pico_led.on()
    setUTCtime()
    return ip

def setUTCtime():
    try: # Fetch and set the correct UTC time
        ntptime.settime()
    except Exception as e:
        if e.errno != errno.ETIMEDOUT: raise e

def get_ll_data(t_min=0):
    try:
        t = time.gmtime(t_min) # Get launches no longer ago than <t_min>, which is a UNIX UTC timestamp
        s = f"{t[0]}-{t[1]:02d}-{t[2]:02d}T{t[3]:02d}:{t[4]:02d}:{t[5]:02d}Z"
        return requests.get("https://ll.thespacedevs.com/2.3.0/launches/upcoming/?limit=2&mode=list&ordering=net&net__gt=" + s)
    except Exception as e:
        if e.errno == errno.EHOSTUNREACH:
            connect()
            return get_ll_data()
        else:
            raise e
