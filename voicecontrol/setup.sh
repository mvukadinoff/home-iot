#!/bin/bash
# Setup script for Modern Voice Control System

set -e

echo "================================"
echo "Voice Control Setup"
echo "================================"
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python $PYTHON_VERSION"

# Check for system dependencies
echo ""
echo "Checking system dependencies..."

if ! command -v portaudio &> /dev/null && ! ldconfig -p | grep -q portaudio; then
    echo "⚠ PortAudio not found. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-pyaudio
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install portaudio
    fi
else
    echo "✓ PortAudio found"
fi

if ! command -v mpg123 &> /dev/null; then
    echo "⚠ mpg123 not found. Installing..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y mpg123
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install mpg123
    fi
else
    echo "✓ mpg123 found"
fi

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

echo ""
echo "✓ Dependencies installed"

# Check for Google Cloud credentials
echo ""
echo "Checking Google Cloud credentials..."
if [ -z "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo "⚠ GOOGLE_APPLICATION_CREDENTIALS not set"
    echo ""
    echo "Please follow these steps:"
    echo "1. Create a Google Cloud project at https://console.cloud.google.com/"
    echo "2. Enable the Speech-to-Text API"
    echo "3. Create a service account and download JSON key"
    echo "4. Run: export GOOGLE_APPLICATION_CREDENTIALS='/path/to/key.json'"
    echo ""
    read -p "Enter path to Google Cloud credentials JSON (or press Enter to skip): " CRED_PATH
    if [ -n "$CRED_PATH" ] && [ -f "$CRED_PATH" ]; then
        echo "export GOOGLE_APPLICATION_CREDENTIALS='$CRED_PATH'" >> ~/.bashrc
        export GOOGLE_APPLICATION_CREDENTIALS="$CRED_PATH"
        echo "✓ Credentials configured"
    else
        echo "⚠ Skipping Google Cloud setup - you'll need to configure this manually"
    fi
else
    echo "✓ Google Cloud credentials configured at: $GOOGLE_APPLICATION_CREDENTIALS"
fi

# Porcupine setup
echo ""
echo "Porcupine Wake Word Detection Setup"
echo "-----------------------------------"
echo "You'll need a Porcupine access key from https://console.picovoice.ai/"
echo "The free tier includes 3 wake words for personal use."
echo ""
read -p "Enter your Porcupine access key (or press Enter to skip): " PORCUPINE_KEY

if [ -n "$PORCUPINE_KEY" ]; then
    # Save to a .env file for convenience
    echo "PORCUPINE_ACCESS_KEY=$PORCUPINE_KEY" > .env
    echo "✓ Porcupine key saved to .env file"
fi

# Audio device setup
echo ""
echo "Audio Device Setup"
echo "------------------"
read -p "Would you like to list available audio devices? (y/n): " LIST_DEVICES

if [[ "$LIST_DEVICES" =~ ^[Yy]$ ]]; then
    if [ -n "$PORCUPINE_KEY" ]; then
        python3 voice_control_modern.py --porcupine-key "$PORCUPINE_KEY" --list-devices
    else
        echo "⚠ Need Porcupine key to list devices. Install dependencies and run:"
        echo "   python3 voice_control_modern.py --porcupine-key YOUR_KEY --list-devices"
    fi
fi

# Systemd service setup
echo ""
echo "Systemd Service Setup"
echo "--------------------"
read -p "Would you like to create a systemd service? (y/n): " CREATE_SERVICE

if [[ "$CREATE_SERVICE" =~ ^[Yy]$ ]]; then
    read -p "Enter your username: " USERNAME
    read -p "Enter audio device index (or press Enter for default): " DEVICE_INDEX

    SERVICE_FILE="/etc/systemd/system/voice-control.service"

    DEVICE_ARG=""
    if [ -n "$DEVICE_INDEX" ]; then
        DEVICE_ARG="--device-index $DEVICE_INDEX"
    fi

    if [ -z "$PORCUPINE_KEY" ]; then
        read -p "Enter Porcupine access key: " PORCUPINE_KEY
    fi

    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Home IoT Voice Control
After=network.target

[Service]
Type=simple
User=$USERNAME
WorkingDirectory=$(pwd)
Environment="GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"
ExecStart=/usr/bin/python3 voice_control_modern.py --porcupine-key $PORCUPINE_KEY $DEVICE_ARG
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo "✓ Service created at $SERVICE_FILE"
    echo ""
    echo "To enable and start the service:"
    echo "  sudo systemctl enable voice-control"
    echo "  sudo systemctl start voice-control"
    echo ""
    echo "To check status:"
    echo "  sudo systemctl status voice-control"
    echo ""
    echo "To view logs:"
    echo "  sudo journalctl -u voice-control -f"
fi

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Make sure your config file exists at /usr/local/bin/home-iot/conf.ini"
echo "2. Ensure audio feedback files are in the configured audio_dir"
echo "3. Test the system: python3 voice_control_modern.py --porcupine-key YOUR_KEY"
echo ""
echo "For more information, see README.md"
echo ""
