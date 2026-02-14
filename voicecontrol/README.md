# Modern Voice Control System

A modernized voice control system for Home IoT using contemporary libraries and best practices.

## Features

- **Modern Wake Word Detection**: Uses Porcupine v3 for accurate wake word detection
- **Voice Activity Detection (VAD)**: Intelligently records until silence is detected using WebRTC VAD
- **Google Cloud Speech-to-Text**: Python-based integration with Google's Speech API
- **Flexible Command Execution**: Supports both MQTT and REST API for device control
- **Audio Feedback**: Plays voice responses when commands are recognized
- **Configurable**: Easy configuration via INI file

## Architecture

```
┌─────────────────────┐
│   Wake Word         │
│   Detection         │
│   (Porcupine)       │
└──────┬──────────────┘
       │ Wake word detected
       ▼
┌─────────────────────┐
│   Audio Feedback    │
│   "Yes" sound       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Audio Recording   │
│   with VAD          │
│   (until silence)   │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Speech-to-Text    │
│   (Google Cloud)    │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   Command           │
│   Processing        │
└──────┬──────────────┘
       │
       ├──────────┬──────────┐
       ▼          ▼          ▼
   ┌──────┐  ┌──────┐  ┌─────────┐
   │ MQTT │  │ REST │  │ Audio   │
   │      │  │ API  │  │ Feedback│
   └──────┘  └──────┘  └─────────┘
```

## Installation

### 1. Install System Dependencies

#### Debian/Ubuntu:
```bash
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio mpg123
```

#### macOS:
```bash
brew install portaudio mpg123
```

### 2. Install Python Dependencies

```bash
cd voicecontrol
pip install -r requirements.txt
```

### 3. Set Up Google Cloud Speech-to-Text

1. Create a Google Cloud project at https://console.cloud.google.com/
2. Enable the Speech-to-Text API
3. Create a service account and download the JSON key file
4. Set the environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
```

Add this to your `.bashrc` or `.zshrc` for persistence:
```bash
echo 'export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"' >> ~/.bashrc
```

### 4. Get Porcupine Access Key

1. Sign up at https://console.picovoice.ai/
2. Get your free access key (includes 3 wake words)
3. (Optional) Create custom wake words using their console

### 5. Configure Audio Device

List available audio devices:
```bash
python voice_control_modern.py --porcupine-key YOUR_KEY --list-devices
```

Note the index of your microphone.

## Configuration

The system uses the existing `conf.ini` file at `/usr/local/bin/home-iot/conf.ini`.

Required configuration options:
```ini
[Main Config]
listen_address = localhost
listen_port = 5000
mqtt_broker = localhost
audio_dir = /home/ina/VoiceCommands/
```

## Usage

### Basic Usage

```bash
python voice_control_modern.py --porcupine-key YOUR_ACCESS_KEY
```

### With Custom Audio Device

```bash
python voice_control_modern.py --porcupine-key YOUR_ACCESS_KEY --device-index 2
```

### With Custom Wake Word

```bash
python voice_control_modern.py \
  --porcupine-key YOUR_ACCESS_KEY \
  --keyword-paths /path/to/custom_wake_word.ppn
```

### As a Service

Create a systemd service file `/etc/systemd/system/voice-control.service`:

```ini
[Unit]
Description=Home IoT Voice Control
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/usr/local/bin/home-iot/voicecontrol
Environment="GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json"
ExecStart=/usr/bin/python3 voice_control_modern.py --porcupine-key YOUR_KEY --device-index 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable voice-control
sudo systemctl start voice-control
```

## Supported Commands

All commands are in Bulgarian:

### Shutters
- **"вдигни щори"** - Open shutters (semi-open)
- **"пусни щори"** - Close shutters

### Lights
- **"светни ламп"** / **"пусни ламп"** - Turn lights on
- **"гаси ламп"** - Turn lights off
- **"мека светлина"** / **"романтика"** / **"намали ламп"** - Soft light mode
- **"усили ламп"** - Bright light mode

### Vacuum Cleaner
- **"пусни прахосмукачка"** - Start vacuum cleaning
- **"при прахосмукачка"** - Send vacuum to dock

## Audio Feedback Files

The system expects audio files in the configured `audio_dir`:

- `Yes1.mp3`, `Yes2.mp3`, `Yes3.mp3` - Wake word acknowledgment
- `CommandAccepted1.mp3`, `CommandAccepted2.mp3` - Command accepted
- `Lights1.mp3` - Lights command feedback
- `UnknownCommand1.mp3`, `UnknownCommand2.mp3`, `UnknownCommand3.mp3`, `UnknownCommand4.mp3` - Unknown command

## Customization

### Adding New Commands

Edit `voice_control_modern.py` and add to the `CommandProcessor.__init__()` method:

```python
self.commands = {
    # Existing commands...
    "your command phrase": self._your_handler,
}
```

Then implement your handler:

```python
def _your_handler(self):
    """Your command implementation"""
    # Option 1: Use MQTT
    self.mqtt_client.publish('your/topic', 'YOUR_MESSAGE')

    # Option 2: Use REST API
    self._call_api("/homeiot/api/v1.0/your/endpoint", {"param": "value"})
```

### Adjusting VAD Sensitivity

In the `VoiceActivityDetector.__init__()`:
- `aggressiveness`: 0-3 (0 = least aggressive, 3 = most aggressive at filtering non-speech)
- Higher values = more likely to classify audio as non-speech

### Adjusting Recording Parameters

In the `AudioRecorder.record_until_silence()` call:
- `max_duration`: Maximum recording time (seconds)
- `silence_duration`: How long to wait in silence before stopping (seconds)

## Troubleshooting

### Audio Device Issues

If you get audio errors:
1. List devices: `python voice_control_modern.py --porcupine-key KEY --list-devices`
2. Test device: `arecord -l` (Linux) or `system_profiler SPAudioDataType` (macOS)
3. Specify device: `--device-index N`

### Google API Errors

If speech recognition fails:
1. Verify credentials: `echo $GOOGLE_APPLICATION_CREDENTIALS`
2. Test API: `gcloud auth application-default print-access-token`
3. Check API is enabled in Google Cloud Console

### MQTT Connection Issues

1. Verify broker is running: `systemctl status mosquitto`
2. Test connection: `mosquitto_sub -h localhost -t '#'`
3. Check broker address in config

### Porcupine License Issues

Free tier includes:
- Up to 3 wake words
- For personal/evaluation use
- Contact Picovoice for commercial licensing

## Comparison with Old System

| Feature | Old System | New System |
|---------|-----------|------------|
| Wake Word | Old Porcupine | Modern Porcupine v3 |
| Speech Recognition | Bash + curl | Python + Google Cloud SDK |
| Recording | Fixed 3 seconds | VAD-based (smart stop) |
| Device Control | Direct CLI calls | API + MQTT |
| Code Language | Bash + Python | Pure Python |
| Error Handling | Basic | Comprehensive |
| Logging | Print statements | Structured logging |
| Configuration | Hardcoded paths | Configurable |

## Performance

- **Wake word detection**: ~10ms latency
- **VAD processing**: Real-time
- **Recording**: Variable (1-10 seconds based on speech)
- **Speech-to-Text**: 1-3 seconds (network dependent)
- **Total response time**: 2-5 seconds from command to action

## License

Apache License 2.0 (inherits from Porcupine components)

## Contributing

When adding features:
1. Follow existing code structure
2. Add logging for debugging
3. Handle errors gracefully
4. Update this README
5. Test with actual hardware

## Credits

- **Porcupine**: Picovoice Inc.
- **WebRTC VAD**: Google
- **Google Cloud Speech**: Google
