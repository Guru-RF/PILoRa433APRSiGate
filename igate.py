#!/usr/bin/env python3

import asyncio
import time
import socket
import random
import logging
from rfc5424logging import Rfc5424SysLogHandler

from datetime import datetime

import board
import digitalio
import busio
import config
from APRS import APRS
import rfm9x

import contextlib

from gpiozero import LED

# Constants
VERSION = "APRSiGate"
RELEASE = "1.0"
loraTimeout = config.LoRaTimeout

# Logging
logger = logging.getLogger(VERSION + "-" + RELEASE)
logger.setLevel(logging.INFO)

# Create RFC 5424 syslog handler
handler = Rfc5424SysLogHandler(
    address=(config.syslogHost, config.syslogPort),
    hostname='aprs-igate-' + config.call,
    appname=VERSION + "-" + RELEASE,
    procid='-',
    structured_data={
        'meta@12345': {
            'site': config.call,
            'type': 'gateway'
        }
    }
)

logger.addHandler(handler)

# SPI + LoRa setup
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
cs = digitalio.DigitalInOut(board.D7)
reset = digitalio.DigitalInOut(board.D25)
rfm9x = rfm9x.RFM9x(spi, cs, reset, 433.775)
rfm9x.tx_power = 5

# APRS setup
aprs = APRS()
rawauthpacket = f"user {config.call} pass {config.passcode} vers {VERSION} {RELEASE}\n"

# System start
logger.info("System online")

led = LED(19)
pwrled = LED(13)
pwrled.on()

post_queue = asyncio.Queue()

async def tcp_post_worker(writer):
    while True:
        rawdata = await post_queue.get()
        try:
            await tcpPost(writer, rawdata)
        except Exception as e:
            logger.error(f"tcpPost_worker failed: {e}")
        post_queue.task_done()

async def led_blink_pattern():
    pattern = [0.2, 0.15, 0.1, 0.07, 0.05, 0.07, 0.1, 0.15, 0.2]
    for duration in pattern:
        led.on()
        await asyncio.sleep(duration)
        led.off()
        await asyncio.sleep(duration)

def trigger_led_blink():
    asyncio.create_task(led_blink_pattern())

async def connect_aprs():
    while True:
        try:
            reader, writer = await asyncio.open_connection(config.aprs_host, config.aprs_port)

            # Get the underlying socket and enable TCP keepalive
            sock = writer.get_extra_info('socket')
            if sock is not None:
              sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
              sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 300)    # seconds before starting keepalive
              sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 30)    # interval between keepalives
              sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)       # fail after 5 missed probes
            writer.write(rawauthpacket.encode())
            await writer.drain()
            logger.info("Connected to APRS-IS")
            return reader, writer
        except Exception as e:
            logger.error(f"TCP connect failed: {e}")
            raise e

async def iGateAnnounce(writer):
    while True:
        now = datetime.utcnow()
        pos = aprs.makePosition(config.latitude, config.longitude, -1, -1, config.symbol)
        ts = aprs.makeTimestamp("z", now.day, now.hour, now.minute, now.second)
        altitude = "/A={:06d}".format(int(config.altitude * 3.2808399))
        comment = f"{VERSION}.{RELEASE} {config.comment}{altitude}"
        packet = f"{config.call}>APRFGI,TCPIP*:@{ts}{pos}{comment}\n"

        try:
            writer.write(packet.encode())
            await writer.drain()
            logger.info("Sent iGate status")
        except Exception as e:
            logger.error(f"iGateAnnounce send failed: {e}")
            raise e

        await asyncio.sleep(15 * 60)

async def tcpPost(writer, rawdata):
    packet = f"{rawdata}\n"
    try:
        writer.write(packet.encode())
        await writer.drain()
        logger.info(f"Sent packet: {rawdata}")
    except Exception as e:
        logger.error(f"tcpPost failed: {e}")
        raise e

async def loraRunner(writer):
    while True:
        timeout = int(loraTimeout) + random.randint(1, 9)
        logger.info(f"LoRa RX waiting for packet, timeout {timeout}s")
        packet = await rfm9x.areceive( with_header=True, timeout=timeout)

        if packet and packet[:3] == b"<\xff\x01":
            try:
                rawdata = packet[3:].decode("utf-8")
            except Exception as e:
                logger.error(f"Error decoding packet: {e}")
                return
            trigger_led_blink()
            logger.info(f"Received: {rawdata}")
            await post_queue.put(rawdata)  # Queue the packet
        await asyncio.sleep(0)

async def main():
    while True:
        try:
            reader, writer = await connect_aprs()

            # Create tasks
            lora_task = asyncio.create_task(loraRunner(writer))
            announce_task = asyncio.create_task(iGateAnnounce(writer))
            post_worker_task = asyncio.create_task(tcp_post_worker(writer)) 


            # Wait for one to raise
            done, pending = await asyncio.wait(
                [lora_task, announce_task, post_worker_task],
                return_when=asyncio.FIRST_EXCEPTION
            )

            for task in done:
              if task.exception():
                logger.error(f"Task {task.get_coro().__name__} raised: {task.exception()}") 

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

            # Close writer
            writer.close()
            await writer.wait_closed()

            logger.error("Disconnected, retrying...")
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Main loop exception: {e}, retrying ...")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

