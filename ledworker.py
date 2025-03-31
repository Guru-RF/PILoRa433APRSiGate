#!/usr/bin/env python3

import os
import time
from gpiozero import LED

FIFO = "/tmp/ledpipe"
led = LED(19)
LED(13).on()

def blink_pattern():
    pattern = [0.2, 0.15, 0.1, 0.07, 0.05, 0.07, 0.1, 0.15, 0.2]
    for duration in pattern:
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)

# Create FIFO if it doesn't exist
if not os.path.exists(FIFO):
    os.mkfifo(FIFO)

print("LED worker ready, waiting for commands...")
while True:
    with open(FIFO, "r") as fifo:
        for line in fifo:
            cmd = line.strip()
            if cmd == "blink":
                blink_pattern()
