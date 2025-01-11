# Countdown clock

This repository contains [MicroPython](https://micropython.org/) source code for a [Raspberry Pico W](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html#picow-technical-specification)-controlled clock counting down to the next launch, leveraging the [LL2 API](https://thespacedevs.com/llapi).

> [!NOTE]  
> This requires access to a WiFi network: create a file `wlan.json` (in the same directory as `main.py`) to store the name and password of your WiFi network(s) in the format `[{"ssid": ..., "password": ...}, ...]`.
