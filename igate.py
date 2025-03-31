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

async def trigger_led_blink():
    try:
        with open("/tmp/ledpipe", "w") as fifo:
            fifo.write("blink\n")
    except Exception as e:
        logger.error(f"LED trigger failed: {e}")

async def connect_aprs():
    while True:
        try:
            reader, writer = await asyncio.open_connection(config.aprs_host, config.aprs_port)
            writer.write(rawauthpacket.encode())
            await writer.drain()
            logger.info("Connected to APRS-IS")
            return reader, writer
        except Exception as e:
            logger.error(f"TCP connect failed: {e}")
            await asyncio.sleep(10)

async def keepaliveLoop(writer):
    while True:
        try:
            # This is a harmless APRS comment packet that won't show up on the map
            packet = f"{config.call}>APRS,TCPIP*:{{KEEPALIVE}}\n"
            writer.write(packet.encode())
            await writer.drain()
            logger.info("Sent keepalive")
        except Exception as e:
            logger.error(f"Keepalive failed: {e}")
            raise e

        await asyncio.sleep(30)  # every 30 seconds

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
        packet = rfm9x.areceive(timeout=timeout)

        if packet and packet[:3] == b"<\xff\x01":
            try:
                rawdata = packet[3:].decode("utf-8")
            except Exception as e:
                logger.error(f"Error decoding packet: {e}")
                return
            await trigger_led_blink()
            logger.info(f"Received: {rawdata}")
            try:
                await tcpPost(writer, rawdata)
            except Exception as e:
                logger.error(f"tcpPost failed packet: {e}")
                raise
        await asyncio.sleep(0)

async def main():
    while True:
        try:
            reader, writer = await connect_aprs()

            # Create tasks
            lora_task = asyncio.create_task(loraRunner(writer))
            announce_task = asyncio.create_task(iGateAnnounce(writer))
            keepalive_task = asyncio.create_task(keepaliveLoop(writer))

            # Wait for one to raise
            done, pending = await asyncio.wait(
                [lora_task, announce_task, keepalive_task],
                return_when=asyncio.FIRST_EXCEPTION
            )

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

