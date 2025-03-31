# Base config for both iGates and Gateways

# We use papertrail, it also logs unrecoverable errors so we can fix them in future updates
# You can user your own syslog offcourse, it's up2you
syslogHost = "logs4.papertrailapp.com"
syslogPort = 24262
# APRS
call = "URECALL-5"
aprs_host = "belgium.aprs2.net"
aprs_port = 14580
passcode = "12345"  # https://apps.magicbug.co.uk/passcode/
latitude = 51.150000
longitude = 2.770000
altitude = 5  # in meters
comment = "https://rf.guru"
# iGate symbol
symbol = "R&"
