import errno
import json
import network
import ntptime
import requests
import time
from machine import Pin

from utils import log_exc


def get_credentials(file: str = "wlan.json"):
    """ Load WiFi credentials from a JSON file.
        The JSON file can contain either:
            a single object    {"ssid": "wifi name", "password": "..."}
            a list of objects  [{"ssid": ..., "password": ...}, ...]
    """
    with open(file, "r") as w:
        cred = json.load(w)
    if not isinstance(cred, list):
        cred = [cred]
    return {c["ssid"]: c.get("password", None) for c in cred}


def internet_check():
    """ Check if an internet connection is available by performing a simple HTTP request. """
    try:
        response = requests.get("http://www.google.com")
        response.close()
        return True
    except Exception:
        return False


def connect(threshold_db: int = 100, credfile: str = "wlan.json", timeout: float = 10.) -> str|None:
    """ Connect to the strongest available WiFi network based on signal strength.

        Args:
            threshold_db (int): Signal strength difference threshold in dB to consider switching.
                Default is 100 to prevent switching. A reasonable value to allow switching would be 20,
                but note that switching can cause loops when calling connect() multiple times.
            credfile (str): Path to the JSON file containing WiFi credentials.
            timeout (float): Number of seconds to attempt connecting to each WiFi network.

        Returns:
            str|None: IP if connected to a network, None otherwise.
    """
    pico_led = Pin("LED", Pin.OUT)
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    credentials = get_credentials(credfile)
    available_networks = wlan.scan()
    
    # Put networks that require authentication (bool(x[4])) first, then sort by signal strength (RSSI = x[3]).
    # This way, we first try networks that require passwords which we might have in <credfile>, and only then
    # do we try open networks (because they often don't work as they require some form of login anyway).
    available_networks.sort(key=lambda x: (bool(x[4]), x[3]), reverse=True)
    current_rssi = wlan.status('rssi') if wlan.isconnected() else -100
    print(*[[nw[3], nw[0]] for nw in available_networks], current_rssi, sep="\n")

    for nw in available_networks:
        ssid = nw[0].decode("utf-8")
        rssi = nw[3]
        authmode = nw[4]

        if wlan.isconnected() and rssi <= current_rssi + abs(threshold_db):
            continue # Skip weaker networks if current connection is strong enough

        if authmode == 0: # Open network
            wlan.connect(ssid)
        elif ssid in credentials: # Secured network with known credentials
            wlan.connect(ssid, credentials[ssid])
        else:
            continue

        # Wait for connection
        dt = 0.2
        for j in range(int(timeout/dt)): # Wait up to 10 seconds
            if wlan.isconnected():
                if not internet_check() and authmode == 0:
                    print(f'Connected to {ssid}, but no internet access.')
                    wlan.disconnect()
                    break
                else: # This is mostly for open networks: check if they actually work.
                    ip = wlan.ifconfig()[0]
                    print(f'Connected to {ssid} with IP {ip}')
                    pico_led.on()
                    setUTCtime()
                    pico_led.off()
                    return ip
            pico_led.toggle()
            time.sleep(dt)

    if wlan.isconnected():
        print(f"Already connected to sufficiently strong WIFI network {wlan.config('ssid')}.")
        ip = wlan.ifconfig()[0]
        return ip
    else:
        print("No suitable networks found or connection failed.")
        return None

def setUTCtime():
    try: # Fetch and set the correct UTC time
        ntptime.settime()
    except Exception as e:
        if e.errno != errno.ETIMEDOUT:
            log_exc(e)

if __name__ == "__main__":
    try:
        for _ in range(1000):
            connect()
    except KeyboardInterrupt:
        pass
