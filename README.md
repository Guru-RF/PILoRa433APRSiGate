# PiLoRa 433 APRS iGate

A lightweight APRS iGate built for Raspberry Pi using a LoRa module (433 MHz) and Python. Designed to connect to APRS-IS and forward LoRa-received packets with proper filtering and timing. 

---

##  Features

- LoRa (433.775 MHz) reception using Guru-RF RX-only LoRa HAT
- We added a high quality SAW filter it Improves selectivity, filtering out out-of-band signals and reducing interference and Enhances sensitivity, by lowering the noise floor and preventing strong adjacent signals from desensitizing the receiver.
- APRS-IS TCP gateway support
- Syslog over RFC5424 with custom hostname/appname
- GPIO-based LED activity indicator (blinks on packet receive)
- Structured, reconnect-safe asyncio code
- Easy install and systemd integration

---

## Hardware Requirements

- Raspberry Pi Zero 2 W (or compatible Pi)
- Guru-RF RX-only LoRa 433 MHz HAT (coming soon!)

---

## Installation

Clone the repository:

```bash
sudo apt -y install git
git clone https://github.com/Guru-RF/PILoRa433APRSiGate.git
cd PILoRa433APRSiGate
```

Make the installer executable and run it:

```bash
chmod +x install.sh
./install.sh
```

> This will:
> - Install Python dependencies
> - Copy files to `/opt/PiAPRSiGate`
> - Set systemd service: `PiAPRSiGate.service`

---

## Configuration

Edit `/opt/PiAPRSiGate/config.py` to match your callsign, location, APRS passcode, etc.

```python
# config.py

call = "ON6URE-5"
passcode = "12345"  # https://apps.magicbug.co.uk/passcode/
latitude = 51.150000
longitude = 2.770000
altitude = 10  # in meters
symbol = "/R"  # Antenna symbol
comment = "PiLoRa iGate"

aprs_host = "rotate.aprs2.net"
aprs_port = 14580

syslogHost = "your.syslog.server"
syslogPort = 514
LoRaTimeout = 900
```

---

## 🔌 Systemd Services

Start manually: (first time you need to reboot to activate the SPI on the PI!)

```bash
sudo systemctl start PiAPRSiGate
```

Enable on boot:

```bash
sudo systemctl enable PiAPRSiGate
```

Check status:

```bash
sudo systemctl status PiAPRSiGate
```

---

## Files & Structure

```
.
├── igate.py           # Main iGate logic 
├── APRS.py            # APRS utility class
├── config.py          # Your callsign, location, and settings
├── rfm9x.py           # LoRa driver 
├── dependencies.sh    # Installs required Python packages
├── install.sh         # Installer for the system
├── README.md          # This file
```

---

## Credits

Built by [RF.Guru](https://rf.guru) for experimental APRS use with LoRa on Raspberry Pi.

---

## License

MIT License – use it, fork it, improve it!
