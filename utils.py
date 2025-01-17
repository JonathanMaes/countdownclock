from machine import Timer
import sys
import time


## EXCEPTION HANDLING
def log_exc(e):
    # Only keep most recent logs
    try:
        with open("err.log", "r") as logfile:
            lines = [line for i, line in enumerate(logfile) if i < 300]
    except FileNotFoundError:
        lines = []
    # Add this error to the log
    with open("err.log", "w") as logfile:
        logfile.write(f"{unix_to_iso8601(time.time())}\n")
        sys.print_exception(e, logfile)
        sys.print_exception(e)
        logfile.write("-"*16 + "\n")
        for line in lines: logfile.write(line)

def wrap_timer(func, *args, **kwargs):
    """ Logs any errors that occur, which otherwise get hidden by a Timer. """
    try:
        func(*args, **kwargs)
    except Exception as e:
        log_exc(e)
        raise e

## PRINTING
def wrap_text(text: str, line_length: int = 20): # LCD screen is 20 characters wide
    lines = ['']
    for word in text.split():
        line = f'{lines[-1]} {word}'.strip()
        if len(line) <= line_length:
            lines[-1] = line
        else:
            lines.append(word)
    return '\n'.join(lines)

## TIME(R)
def isdst_CET(unix): # Adapted from https://github.com/micropython/micropython-lib/blob/master/python-stdlib/datetime/test_datetime.py
    if unix is None: return False
    year = time.gmtime(unix)[0]
    if not 2000 <= year < 2100: raise ValueError("isdst() was only implmented for years in range [2000; 2100)")
    day = 31 - (5 * year // 4 + 4) % 7  # last Sunday of March
    beg = time.mktime((year, 3, day, 1, 0, 0, 0, 0))
    day = 31 - (5 * year // 4 + 1) % 7  # last Sunday of October
    end = time.mktime((year, 10, day, 1, 0, 0, 0, 0))
    return beg <= unix < end

def unix_to_iso8601(unix: int) -> str:
    t = time.gmtime(unix)
    return f"{t[0]}-{t[1]:02d}-{t[2]:02d}T{t[3]:02d}:{t[4]:02d}:{t[5]:02d}Z"

def iso8601_to_unix(iso: str) -> int:
    if iso[19] != "Z": raise ValueError("Must receive ISO8601 time in UTC")
    year, month, day, hour, minute, second = int(iso[0:4]), int(iso[5:7]), int(iso[8:10]), int(iso[11:13]), int(iso[14:16]), int(iso[17:19])
    return time.mktime((year, month, day, hour, minute, second, 0, 0)) # Last two zeroes are day of week and day of year, but ignore those

def schedule(t, f, *args, **kwargs): # Run function <f> after <t> seconds
    timer = Timer()
    timer.init(mode=Timer.ONE_SHOT, period=int(t*1000), callback=lambda timer: wrap_timer(f, *args, **kwargs))
