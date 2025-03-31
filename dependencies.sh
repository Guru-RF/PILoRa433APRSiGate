#!/bin/bash

sudo apt update && sudo apt upgrade -y

sudo apt install -y python3 python3-pip python3-dev git netcat-traditional python3-gpiozero

sudo rm -f /usr/lib/python3.11/EXTERNALLY-MANAGED

sudo pip3 install Adafruit-Blinka
sudo pip3 install rfc5424-logging-handler

sudo sed -i '/^#\?dtparam=spi=/d' /boot/firmware/config.txt && echo 'dtparam=spi=on' | sudo tee -a /boot/firmware/config.txt

