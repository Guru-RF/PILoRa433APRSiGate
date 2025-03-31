#!/bin/bash

APP_NAME="PiAPRSiGate"
INSTALL_DIR="/opt/$APP_NAME"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
LED_SERVICE_FILE="/etc/systemd/system/ledworker.service"
USER=$(whoami)

echo "🚀 Installing $APP_NAME and LED worker as system services..."

# Run dependencies
echo "📦 Installing Python dependencies..."
chmod +x dependencies.sh
./dependencies.sh || { echo "❌ Dependency install failed"; exit 1; }

# Create target directory
echo "📁 Copying files to $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp *.py "$INSTALL_DIR"
sudo chmod +x "$INSTALL_DIR"/*.py
sudo chown -R "$USER:$USER" "$INSTALL_DIR"

# Create systemd service for LED worker
echo "🛠️ Creating LED worker service..."
sudo tee "$LED_SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=LED Worker for PiAPRSiGate
After=network.target
Before=$APP_NAME.service

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/ledworker.py
WorkingDirectory=$INSTALL_DIR
StandardOutput=journal
StandardError=journal
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Create main systemd service for PiAPRSiGate
echo "🛠️ Creating main APRSiGate service..."
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=$APP_NAME Service
After=ledworker.service network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/igate.py
WorkingDirectory=$INSTALL_DIR
StandardOutput=journal
StandardError=journal
Restart=always
User=$USER

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable both services
echo "🔄 Reloading and enabling services..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable ledworker.service
sudo systemctl enable $APP_NAME.service

echo "✅ $APP_NAME and LED worker installed!"
echo "🔁 Reboot to start the aprs igate."
