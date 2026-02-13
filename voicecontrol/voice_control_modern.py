#!/usr/bin/env python3
"""
Modern Voice Control System for Home IoT
Uses modern libraries for wake word detection, voice activity detection, and speech recognition.
"""

import os
import sys
import time
import wave
import logging
import json
import struct
import random
from pathlib import Path
from typing import Optional, List
import threading

import pyaudio
import requests
import paho.mqtt.client as mqtt
import numpy as np
import base64

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import openwakeword, use fallback if not available
try:
    from openwakeword.model import Model as WakeWordModel
    OPENWAKEWORD_AVAILABLE = True
    logger.info("OpenWakeWord available")
except ImportError:
    OPENWAKEWORD_AVAILABLE = False
    logger.warning("OpenWakeWord not available, using simple volume-based wake word detection")

# Try to import webrtcvad, use fallback if not available
try:
    import webrtcvad
    WEBRTC_AVAILABLE = True
except ImportError:
    WEBRTC_AVAILABLE = False
    logger.warning("webrtcvad not available, using volume-based VAD fallback")


class VoiceControlConfig:
    """Configuration management for voice control system"""

    def __init__(self, config_path: str = "/usr/local/bin/home-iot/conf.ini"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load configuration from INI file"""
        import configparser
        config = configparser.ConfigParser()

        if os.path.exists(self.config_path):
            config.read(self.config_path)
            return dict(config.items("Main Config"))
        else:
            logger.warning(f"Config file not found at {self.config_path}, using defaults")
            return {
                "listen_address": "localhost",
                "listen_port": "5000",
                "mqtt_broker": "localhost",
                "google_api_key": "",
                "audio_dir": "voicecontrol/VoiceCommands/",
                "wakeword_threshold": "0.5"
            }

    def get(self, key: str, default: Optional[str] = None) -> str:
        """Get configuration value"""
        return self.config.get(key, default)


class AudioPlayer:
    """Handles audio feedback playback"""

    def __init__(self, audio_dir: str = "voicecontrol/VoiceCommands/"):
        self.audio_dir = audio_dir
        # Detect available audio player
        self.player = self._detect_audio_player()
        if self.player:
            logger.info(f"Using audio player: {self.player}")
        else:
            logger.warning("No audio player found (tried: mpg123, ffplay, cvlc, paplay)")

    def _detect_audio_player(self):
        """Detect which audio player is available"""
        import subprocess
        players = [
            ("mpg123", ["mpg123", "-q"]),
            ("ffplay", ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]),
            ("cvlc", ["cvlc", "--play-and-exit", "--quiet"]),
            ("paplay", ["paplay"])
        ]

        for name, cmd in players:
            try:
                result = subprocess.run(
                    ["which", name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                if result.returncode == 0:
                    return (name, cmd)
            except:
                continue
        return None

    def play_reply(self, speech_text: str, max_variants: int = 1):
        """Play audio feedback"""
        import subprocess

        if not self.player:
            logger.debug(f"No audio player available, skipping: {speech_text}")
            return

        try:
            # Random selection if multiple variants exist
            variant = random.randint(1, max_variants)
            audio_file = os.path.join(self.audio_dir, f"{speech_text}{variant}.mp3")

            if os.path.exists(audio_file):
                logger.info(f"Playing audio: {audio_file}")
                print(f"🔊 Playing: {os.path.basename(audio_file)}")

                # Use detected audio player
                player_name, player_cmd = self.player
                cmd = player_cmd + [audio_file]

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10
                )
                if result.returncode != 0:
                    logger.warning(f"{player_name} returned error code: {result.returncode}")
            else:
                logger.warning(f"Audio file not found: {audio_file}")
                print(f"⚠️  Audio file not found: {audio_file}")
        except subprocess.TimeoutExpired:
            logger.error(f"Audio playback timeout for {audio_file}")
        except Exception as e:
            logger.error(f"Error playing audio: {e}")


class VoiceActivityDetector:
    """Voice Activity Detection using WebRTC VAD or volume-based fallback"""

    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 3):
        """
        Initialize VAD

        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000)
            aggressiveness: VAD aggressiveness (0-3, 3 is most aggressive)
        """
        self.sample_rate = sample_rate
        self.frame_duration = 30  # ms (10, 20, or 30)
        self.frame_size = int(sample_rate * self.frame_duration / 1000)
        self.use_webrtc = WEBRTC_AVAILABLE

        if self.use_webrtc:
            self.vad = webrtcvad.Vad(aggressiveness)
            logger.info("Using WebRTC VAD")
        else:
            # Volume-based VAD parameters
            # Much lower threshold for normal speech detection during recording
            self.threshold = 100  # RMS threshold for speech detection (lowered for sensitivity)
            logger.info(f"Using volume-based VAD fallback with threshold: {self.threshold}")

    def is_speech(self, frame: bytes) -> bool:
        """Check if frame contains speech"""
        try:
            if self.use_webrtc:
                return self.vad.is_speech(frame, self.sample_rate)
            else:
                # Fallback: volume-based detection
                audio_data = np.frombuffer(frame, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
                is_speech = rms > self.threshold
                # Debug output every ~10 frames to show levels during recording
                if hasattr(self, '_debug_counter'):
                    self._debug_counter += 1
                else:
                    self._debug_counter = 0
                if self._debug_counter % 10 == 0:
                    logger.debug(f"Audio level: {int(rms):4d} {'[SPEECH]' if is_speech else '[silence]'}")
                return is_speech
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False


class SpeechRecognizer:
    """Google Speech-to-Text REST API integration"""

    def __init__(self, api_key: str, language_code: str = "bg-BG"):
        """
        Initialize Google Speech client

        Args:
            api_key: Google API key for Speech-to-Text
            language_code: Language code (default: bg-BG for Bulgarian)
        """
        self.api_key = api_key
        self.language_code = language_code
        self.api_url = f"https://speech.googleapis.com/v1/speech:recognize?key={api_key}"

    def transcribe_audio(self, audio_data: bytes, sample_rate: int = 16000) -> Optional[str]:
        """
        Transcribe audio using Google Speech-to-Text REST API

        Args:
            audio_data: Raw audio bytes (LINEAR16 format)
            sample_rate: Audio sample rate

        Returns:
            Transcribed text or None if recognition failed
        """
        try:
            original_size = len(audio_data)

            # Try to compress audio to FLAC format for much smaller upload
            print(f"💾 Optimizing audio ({original_size:,} bytes)...")
            compressed_data, actual_sample_rate, encoding = self._optimize_audio(audio_data, sample_rate)
            optimized_size = len(compressed_data)
            compression_ratio = (1 - optimized_size / original_size) * 100 if optimized_size < original_size else 0
            if compression_ratio > 0:
                print(f"✓ Optimized to {optimized_size:,} bytes ({compression_ratio:.1f}% smaller)")
            else:
                print(f"✓ Using {optimized_size:,} bytes (no compression)")

            # Encode audio to base64
            audio_base64 = base64.b64encode(compressed_data).decode('utf-8')

            # Prepare request
            request_data = {
                "config": {
                    "encoding": encoding,
                    "sampleRateHertz": actual_sample_rate,
                    "languageCode": self.language_code,
                    "enableAutomaticPunctuation": False
                },
                "audio": {
                    "content": audio_base64
                }
            }

            logger.info(f"Sending {optimized_size:,} bytes to Google Speech-to-Text API...")

            # Make API request with longer timeout
            response = requests.post(
                self.api_url,
                json=request_data,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30  # Increased timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Google API response: {result}")

                if "results" in result and len(result["results"]) > 0:
                    transcript = result["results"][0]["alternatives"][0]["transcript"]
                    logger.info(f"Transcription: {transcript}")
                    return transcript.lower()
                else:
                    logger.warning(f"No transcription results. Full response: {result}")
                    # Check for error in response
                    if "error" in result:
                        logger.error(f"Google API error: {result['error']}")
                    return None
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.Timeout:
            logger.error("Google API timeout - audio file may be too large or network is slow")
            print("❌ Google API timeout - try speaking less or check your network connection")
            return None
        except Exception as e:
            logger.error(f"Speech recognition error: {e}")
            return None

    def _optimize_audio(self, audio_data: bytes, sample_rate: int) -> tuple:
        """
        Optimize audio for transmission - try FLAC, fall back to downsampling or LINEAR16

        Args:
            audio_data: Raw LINEAR16 PCM audio bytes
            sample_rate: Sample rate in Hz

        Returns:
            Tuple of (optimized_audio_bytes, actual_sample_rate, encoding_type)
        """
        # Try FLAC compression first
        flac_data = self._compress_to_flac(audio_data, sample_rate)

        # Check if FLAC worked (different data means it compressed)
        if len(flac_data) < len(audio_data) * 0.9:  # At least 10% compression
            return (flac_data, sample_rate, "FLAC")

        # FLAC didn't work, try downsampling if sample rate is high
        if sample_rate > 16000:
            logger.info(f"Downsampling from {sample_rate} Hz to 16000 Hz")
            downsampled = self._downsample_audio(audio_data, sample_rate, 16000)
            return (downsampled, 16000, "LINEAR16")

        # No optimization possible, send as-is
        return (audio_data, sample_rate, "LINEAR16")

    def _compress_to_flac(self, audio_data: bytes, sample_rate: int) -> bytes:
        """
        Compress raw LINEAR16 audio to FLAC format, or downsample if FLAC not available

        Args:
            audio_data: Raw LINEAR16 PCM audio bytes
            sample_rate: Sample rate in Hz

        Returns:
            FLAC compressed audio bytes (or downsampled LINEAR16)
        """
        import subprocess
        import tempfile
        import shutil

        # Check if flac command is available
        if shutil.which('flac') is None:
            logger.warning("FLAC encoder not installed - install with: sudo apt-get install flac")
            # Fallback: Downsample to 16kHz if higher to reduce size
            if sample_rate > 16000:
                logger.info(f"Downsampling from {sample_rate} Hz to 16000 Hz to reduce size")
                return self._downsample_audio(audio_data, sample_rate, 16000)
            return audio_data

        try:
            # Write raw audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as raw_file:
                raw_file.write(audio_data)
                raw_path = raw_file.name

            # Create temporary FLAC file
            flac_path = raw_path.replace('.raw', '.flac')

            # Use flac command to compress
            cmd = [
                'flac',
                '-f', '-s', '--best',
                '--endian=little',
                '--channels=1',
                '--bps=16',
                f'--sample-rate={sample_rate}',
                '--sign=signed',
                raw_path,
                '-o', flac_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=5
            )

            if result.returncode != 0:
                raise RuntimeError(f"FLAC compression failed: {result.stderr.decode()}")

            # Read compressed FLAC data
            with open(flac_path, 'rb') as flac_file:
                flac_data = flac_file.read()

            # Clean up
            os.unlink(raw_path)
            os.unlink(flac_path)

            return flac_data

        except Exception as e:
            logger.error(f"FLAC compression error: {e}, using original audio")
            # Try cleanup
            try:
                if 'raw_path' in locals():
                    os.unlink(raw_path)
                if 'flac_path' in locals() and os.path.exists(flac_path):
                    os.unlink(flac_path)
            except:
                pass
            return audio_data

    def _downsample_audio(self, audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
        """
        Downsample audio to reduce size

        Args:
            audio_data: Raw LINEAR16 PCM audio
            from_rate: Current sample rate
            to_rate: Target sample rate

        Returns:
            Downsampled audio bytes
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Simple decimation (take every Nth sample)
            decimation_factor = from_rate // to_rate
            downsampled = audio_array[::decimation_factor]

            return downsampled.tobytes()
        except Exception as e:
            logger.error(f"Downsampling failed: {e}")
            return audio_data


class CommandProcessor:
    """Process voice commands and execute actions"""

    def __init__(self, config: VoiceControlConfig, audio_player: AudioPlayer):
        self.config = config
        self.audio_player = audio_player
        self.api_base_url = f"http://{config.get('listen_address')}:{config.get('listen_port')}"

        # MQTT setup
        self.mqtt_client = mqtt.Client()
        mqtt_broker = config.get('mqtt_broker', 'localhost')
        try:
            self.mqtt_client.connect(mqtt_broker, 1883, 60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT broker: {mqtt_broker}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")

        # Define command mappings (Bulgarian commands)
        self.commands = {
            # Shutters
            "вдигни щори": self._open_shutters,
            "пусни щори": self._close_shutters,

            # Lights
            "светни ламп": self._lights_on,
            "пусни ламп": self._lights_on,
            "гаси ламп": self._lights_off,
            "мека светлина": self._lights_soft,
            "романтика": self._lights_soft,
            "намали ламп": self._lights_soft,
            "усили ламп": self._lights_bright,

            # Vacuum
            "пусни прахосмукачка": self._vacuum_start,
            "при прахосмукачка": self._vacuum_dock,
        }

    def process_command(self, text: str) -> bool:
        """
        Process transcribed text and execute matching command

        Returns:
            True if command was recognized, False otherwise
        """
        if not text:
            return False

        text = text.lower().strip()
        logger.info(f"Processing command: {text}")

        # Check each command pattern
        for pattern, action in self.commands.items():
            if pattern in text:
                logger.info(f"Command recognized: {pattern}")
                self.audio_player.play_reply("CommandAccepted", 2)
                try:
                    action()
                    return True
                except Exception as e:
                    logger.error(f"Error executing command: {e}")
                    return False

        logger.info("No command recognized")
        self.audio_player.play_reply("UnknownCommand", 4)
        return False

    # Command implementations using API and MQTT

    def _open_shutters(self):
        """Open shutters via MQTT"""
        self.mqtt_client.publish('shutters/command', 'SEMIOPEN')
        logger.info("Sent SEMIOPEN to shutters/command")

    def _close_shutters(self):
        """Close shutters via MQTT"""
        self.mqtt_client.publish('shutters/command', 'CLOSE')
        logger.info("Sent CLOSE to shutters/command")

    def _lights_on(self):
        """Turn lights on via API"""
        self.audio_player.play_reply("Lights", 1)
        self._call_api("/homeiot/api/v1.0/lights", {"state": "ON"})

    def _lights_off(self):
        """Turn lights off via API"""
        self.audio_player.play_reply("Lights", 1)
        self._call_api("/homeiot/api/v1.0/lights", {"state": "OFF"})

    def _lights_soft(self):
        """Set lights to soft mode - would need API enhancement"""
        self.audio_player.play_reply("Lights", 1)
        # This would require API enhancement to support brightness/temperature
        logger.warning("Soft light mode requires API enhancement")
        self._call_api("/homeiot/api/v1.0/lights", {"state": "ON"})

    def _lights_bright(self):
        """Set lights to bright mode - would need API enhancement"""
        self.audio_player.play_reply("Lights", 1)
        logger.warning("Bright light mode requires API enhancement")
        self._call_api("/homeiot/api/v1.0/lights", {"state": "ON"})

    def _vacuum_start(self):
        """Start vacuum via API"""
        self._call_api("/homeiot/api/v1.0/mirobo/clean", method="GET")

    def _vacuum_dock(self):
        """Send vacuum to dock via API"""
        self._call_api("/homeiot/api/v1.0/mirobo/dock", method="GET")

    def _call_api(self, endpoint: str, data: dict = None, method: str = "POST"):
        """Make API call to home-iot server"""
        try:
            url = f"{self.api_base_url}{endpoint}"
            logger.info(f"Calling API: {method} {url}")

            if method == "POST":
                response = requests.post(url, data=data, timeout=10)
            else:
                response = requests.get(url, timeout=10)

            if response.ok:
                logger.info(f"API call successful: {response.json()}")
            else:
                logger.error(f"API call failed: {response.status_code}")
        except Exception as e:
            logger.error(f"API call error: {e}")


class AudioRecorder:
    """Records audio with voice activity detection"""

    def __init__(self, sample_rate: int = 16000, vad_aggressiveness: int = 3, device_index: Optional[int] = None):
        self.device_index = device_index
        self.channels = 1
        self.format = pyaudio.paInt16
        self.chunk_duration = 30  # ms
        self.audio = pyaudio.PyAudio()

        # Auto-detect supported sample rate for the device (same as wake word detector)
        self.sample_rate = self._get_supported_sample_rate()
        self.chunk_size = int(self.sample_rate * self.chunk_duration / 1000)
        logger.info(f"AudioRecorder using sample rate: {self.sample_rate} Hz")

        self.vad = VoiceActivityDetector(self.sample_rate, vad_aggressiveness)

    def _get_supported_sample_rate(self):
        """Find a supported sample rate for the device"""
        # Try common sample rates in order of preference
        rates_to_try = [16000, 48000, 44100, 32000, 22050, 8000]

        for rate in rates_to_try:
            try:
                # Try to check if rate is supported
                if self.device_index is not None:
                    device_info = self.audio.get_device_info_by_index(self.device_index)
                    default_rate = int(device_info.get('defaultSampleRate', 48000))

                    # Try the device's default rate first
                    if default_rate not in rates_to_try:
                        rates_to_try.insert(0, default_rate)

                # Test if we can open a stream with this rate
                test_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=self.device_index,
                    start=False
                )
                test_stream.close()
                return rate
            except Exception:
                continue

        # Fallback to 44100 if nothing works
        logger.warning("Could not detect supported sample rate, defaulting to 44100 Hz")
        return 44100

    def record_until_silence(
        self,
        max_duration: int = 7,
        silence_duration: float = 0.7,
        device_index: Optional[int] = None,
        silence_threshold: int = 700
    ) -> bytes:
        """
        Record audio until silence is detected (simple volume-based approach)

        Args:
            max_duration: Maximum recording duration in seconds
            silence_duration: Duration of silence to stop recording (seconds)
            device_index: Audio input device index
            silence_threshold: RMS volume threshold - audio below this is considered silence

        Returns:
            Raw audio bytes
        """
        logger.info(f"Recording (max {max_duration}s, stop after {silence_duration}s silence below {silence_threshold})...")
        print(f"🎤 Speak now! Recording stops after {silence_duration}s of silence...")

        # Try to open stream with retries (device might be busy)
        stream = None
        for attempt in range(3):
            try:
                stream = self.audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    input_device_index=device_index
                )
                break
            except OSError as e:
                if attempt < 2:
                    logger.warning(f"Device busy, retrying... (attempt {attempt + 1}/3)")
                    time.sleep(0.3)
                else:
                    logger.error(f"Failed to open audio device after 3 attempts: {e}")
                    raise

        if stream is None:
            raise RuntimeError("Failed to open audio stream")

        frames = []
        silent_chunks = 0
        silence_chunks_needed = int(silence_duration * 1000 / self.chunk_duration)
        max_chunks = int(max_duration * 1000 / self.chunk_duration)

        try:
            for i in range(max_chunks):
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(chunk)

                # Calculate volume (RMS)
                audio_data = np.frombuffer(chunk, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

                # Check if silent (below threshold)
                is_silent = rms < silence_threshold

                if is_silent:
                    silent_chunks += 1
                else:
                    silent_chunks = 0  # Reset on any sound

                # Visual feedback every few chunks
                if i % 5 == 0:
                    bar_length = int(min(rms / 50, 40))
                    bar = "█" * bar_length
                    silent_bar = int((silent_chunks / silence_chunks_needed) * 20)
                    silent_progress = "▓" * silent_bar + "░" * (20 - silent_bar)

                    print(f"\r🎤 Vol: {int(rms):4d} [{bar:40s}] | Silence: [{silent_progress}] {silent_chunks}/{silence_chunks_needed}",
                          end="", flush=True)

                # Stop if we've had enough continuous silence
                if silent_chunks >= silence_chunks_needed:
                    print(f"\n✅ {silence_duration}s of silence detected, processing...")
                    logger.info(f"Silence detected ({silent_chunks} chunks), stopping recording")
                    break

        finally:
            stream.stop_stream()
            stream.close()
            print()  # New line after status

        duration = len(frames) * self.chunk_duration / 1000
        logger.info(f"Recorded {duration:.2f} seconds")
        print(f"📼 Recorded {duration:.2f} seconds of audio")
        return b''.join(frames)

    def close(self):
        """Clean up audio resources"""
        self.audio.terminate()


class WakeWordDetector:
    """Wake word detection using OpenWakeWord or simple volume-based detection"""

    def __init__(
        self,
        wakeword_models: Optional[List[str]] = None,
        threshold: float = 0.5,
        device_index: Optional[int] = None,
        volume_threshold: int = 2000,
        show_volume_meter: bool = False,
        force_sample_rate: Optional[int] = None
    ):
        """
        Initialize wake word detector

        Args:
            wakeword_models: List of wake word model names (e.g., ['hey_jarvis', 'alexa'])
                           If None, uses 'alexa' by default
                           Available: 'alexa', 'hey_jarvis', 'hey_mycroft', 'timer'
                           If OpenWakeWord not available, uses simple clap/loud sound detection
            threshold: Detection threshold (0.0 to 1.0, higher = more strict) for ML models
            device_index: Audio input device index
            volume_threshold: RMS volume threshold for simple detection
            show_volume_meter: Show live audio volume meter during wake word detection
            force_sample_rate: Force a specific sample rate (e.g., 16000) instead of auto-detection
        """
        self.device_index = device_index
        self.threshold = threshold
        self.show_volume_meter = show_volume_meter
        self.audio = pyaudio.PyAudio()

        # Auto-detect supported sample rate for the device, or use forced rate
        if force_sample_rate:
            logger.info(f"Attempting to use forced sample rate: {force_sample_rate} Hz")
            # Test if the forced rate is actually supported
            if self._test_sample_rate(force_sample_rate):
                self.sample_rate = force_sample_rate
                logger.info(f"✓ Using forced sample rate: {self.sample_rate} Hz")
            else:
                logger.warning(f"⚠️  Forced sample rate {force_sample_rate} Hz is not supported by your device")
                logger.warning(f"   Falling back to auto-detection...")
                self.sample_rate = self._get_supported_sample_rate()
                logger.info(f"Using auto-detected sample rate: {self.sample_rate} Hz")
        else:
            self.sample_rate = self._get_supported_sample_rate()
            logger.info(f"Using auto-detected sample rate: {self.sample_rate} Hz")

        self.chunk_size = int(self.sample_rate * 0.08)  # 80ms chunks

        self.use_openwakeword = OPENWAKEWORD_AVAILABLE

        if self.use_openwakeword:
            # Initialize OpenWakeWord model
            if wakeword_models is None:
                wakeword_models = ['alexa']

            try:
                # Download models if needed (supports HuggingFace repos)
                # This returns the actual model filenames to use
                actual_model_names = self._ensure_models_downloaded(wakeword_models)

                # Let OpenWakeWord auto-detect inference framework (tflite preferred, onnx fallback)
                self.oww_model = WakeWordModel(
                    wakeword_models=actual_model_names
                )
                logger.info(f"OpenWakeWord initialized with models: {actual_model_names}, threshold: {threshold}")
                logger.info(f"Available wake words: {list(self.oww_model.models.keys())}")

                # Debug: Check model sample rate expectations
                logger.info(f"Model expects sample rate: 16000 Hz (OpenWakeWord default)")
                logger.info(f"Audio device using: {self.sample_rate} Hz")
                if self.sample_rate != 16000:
                    logger.warning(f"⚠️  SAMPLE RATE MISMATCH! Device={self.sample_rate}Hz, Model expects=16000Hz")
                    logger.warning(f"   This will cause very low detection scores!")
                    logger.warning(f"   Audio will need to be resampled to 16000 Hz")
            except Exception as e:
                logger.error(f"Failed to initialize OpenWakeWord: {e}")
                logger.info("Falling back to simple volume-based wake detection")
                self.use_openwakeword = False

        if not self.use_openwakeword:
            # Fallback: Simple volume-based detection
            # Detects 2 claps or loud sounds in quick succession
            logger.info("Using simple volume-based wake detection")
            logger.info("Wake up: Clap twice or make 2 loud sounds within 1 second")
            self.volume_threshold = volume_threshold
            self.clap_history = []
            self.clap_window = 1.0  # seconds

    def _ensure_models_downloaded(self, wakeword_models: List[str]) -> List[str]:
        """
        Ensure wake word models are downloaded from HuggingFace

        Supports two formats:
        - Standard model names: 'alexa', 'hey_jarvis', etc.
        - HuggingFace repo paths: 'username/repo-name' (e.g., 'johnthenerd/openwakeword-hey-glados')

        Args:
            wakeword_models: List of model names or HuggingFace repo paths

        Returns:
            List of actual model names (without .onnx) to use with OpenWakeWord
        """
        try:
            from huggingface_hub import hf_hub_download, list_repo_files
        except ImportError:
            logger.warning("huggingface_hub not installed - cannot auto-download models")
            logger.info("Install with: pip install huggingface_hub")
            return wakeword_models

        import openwakeword
        import shutil

        # Get OpenWakeWord's models directory
        oww_path = os.path.dirname(openwakeword.__file__)
        models_dir = os.path.join(oww_path, 'resources', 'models')
        os.makedirs(models_dir, exist_ok=True)

        # Built-in model mappings (standard names -> HuggingFace repo)
        builtin_models = {
            'alexa': ('davidscripka/openwakeword', 'alexa_v0.1.onnx'),
            'hey_jarvis': ('davidscripka/openwakeword', 'hey_jarvis_v0.1.onnx'),
            'hey_mycroft': ('davidscripka/openwakeword', 'hey_mycroft_v0.1.onnx'),
            'timer': ('davidscripka/openwakeword', 'timer_v0.1.onnx'),
        }

        # Track actual model names to return
        actual_models = []

        for model_spec in wakeword_models:
            # Check if it's a HuggingFace repo path (contains '/') or a standard name
            if '/' in model_spec:
                # Custom HuggingFace model: 'username/repo-name'
                repo_id = model_spec
                model_name = repo_id.split('/')[-1]

                # Query HuggingFace to find actual .tflite or .onnx files in the repo
                # Prefer .tflite as OpenWakeWord works better with it
                try:
                    logger.info(f"🔍 Discovering models in {repo_id}...")
                    all_files = list_repo_files(repo_id=repo_id)
                    tflite_files = [f for f in all_files if f.endswith('.tflite')]
                    onnx_files = [f for f in all_files if f.endswith('.onnx')]

                    # Prefer .tflite over .onnx (better OpenWakeWord support)
                    model_files = tflite_files if tflite_files else onnx_files

                    if not model_files:
                        logger.warning(f"No .tflite or .onnx files found in {repo_id}")
                        print(f"❌ No wake word models found in {model_name}")
                        continue

                    logger.info(f"Found {len(model_files)} model(s): {', '.join(model_files)}")

                    # Download all model files found
                    for filename in model_files:
                        local_path = os.path.join(models_dir, filename)
                        if os.path.exists(local_path):
                            logger.debug(f"Model already exists: {filename}")
                            # For custom models, use full path (OpenWakeWord needs it)
                            actual_models.append(local_path)
                            continue

                        logger.info(f"📥 Downloading {filename}...")
                        print(f"📥 Downloading: {filename}")

                        downloaded_path = hf_hub_download(
                            repo_id=repo_id,
                            filename=filename,
                            cache_dir=None
                        )

                        shutil.copy(downloaded_path, local_path)
                        logger.info(f"✓ Installed: {filename}")
                        print(f"✓ Model ready: {filename}")

                        # For custom models, use full path (OpenWakeWord needs it)
                        actual_models.append(local_path)

                except Exception as e:
                    logger.error(f"Failed to process {repo_id}: {e}")
                    print(f"❌ Failed to download {model_name}: {e}")

            elif model_spec in builtin_models:
                # Built-in model
                repo_id, filename = builtin_models[model_spec]
                model_name = model_spec

                # Check if model already exists
                local_path = os.path.join(models_dir, filename)
                if os.path.exists(local_path):
                    logger.debug(f"Model already exists: {filename}")
                    # Use the standard name for built-in models
                    actual_models.append(model_spec)
                    continue

                # Download from HuggingFace
                try:
                    logger.info(f"📥 Downloading {model_name} model from HuggingFace...")
                    print(f"📥 Downloading wake word model: {model_name}")

                    downloaded_path = hf_hub_download(
                        repo_id=repo_id,
                        filename=filename,
                        cache_dir=None  # Use default cache
                    )

                    # Copy to OpenWakeWord models directory
                    shutil.copy(downloaded_path, local_path)
                    logger.info(f"✓ Downloaded and installed: {filename}")
                    print(f"✓ Model ready: {model_name}")

                    # Track the actual model name
                    actual_models.append(model_spec)

                except Exception as e:
                    logger.error(f"Failed to download {model_spec}: {e}")
                    print(f"❌ Failed to download {model_name}: {e}")
            else:
                logger.warning(f"Unknown model: {model_spec} - trying as filename")
                # Assume it's already a valid model name
                actual_models.append(model_spec)
                continue

        return actual_models

    def _get_supported_sample_rate(self):
        """Find a supported sample rate for the device"""
        # Try common sample rates in order of preference
        rates_to_try = [16000, 48000, 44100, 32000, 22050, 8000]

        for rate in rates_to_try:
            try:
                # Try to check if rate is supported
                if self.device_index is not None:
                    device_info = self.audio.get_device_info_by_index(self.device_index)
                    default_rate = int(device_info.get('defaultSampleRate', 48000))

                    # Try the device's default rate first
                    if default_rate not in rates_to_try:
                        rates_to_try.insert(0, default_rate)

                # Test if we can open a stream with this rate
                test_stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=self.device_index,
                    start=False
                )
                test_stream.close()
                return rate
            except Exception:
                continue

        # Fallback to 44100 if nothing works
        logger.warning("Could not detect supported sample rate, defaulting to 44100 Hz")
        return 44100

    def _resample_audio(self, audio_array: np.ndarray, from_rate: int, to_rate: int) -> np.ndarray:
        """
        Resample audio to target sample rate using simple linear interpolation

        Args:
            audio_array: Input audio as numpy array (int16)
            from_rate: Source sample rate
            to_rate: Target sample rate

        Returns:
            Resampled audio as numpy array (int16)
        """
        if from_rate == to_rate:
            return audio_array

        # Calculate resampling ratio
        duration = len(audio_array) / from_rate
        target_length = int(duration * to_rate)

        # Use numpy's interp for simple linear interpolation
        x_old = np.linspace(0, duration, len(audio_array))
        x_new = np.linspace(0, duration, target_length)

        # Interpolate and convert back to int16
        resampled = np.interp(x_new, x_old, audio_array.astype(np.float32))
        return resampled.astype(np.int16)

    def start_listening(self, callback):
        """
        Start listening for wake word

        Args:
            callback: Function to call when wake word is detected
        """
        if self.use_openwakeword:
            self._listen_openwakeword(callback)
        else:
            self._listen_volume_based(callback)

    def _listen_openwakeword(self, callback):
        """Listen using OpenWakeWord"""
        logger.info("Listening for wake word (OpenWakeWord)...")
        logger.info(f"Detection threshold: {self.threshold} (lower = more sensitive)")
        if self.show_volume_meter:
            print("\n💡 Volume meter enabled - watch the levels to verify mic is working!")
            print(f"   Say the wake word and watch for score changes\n")

        # OpenWakeWord requires 16kHz audio
        model_sample_rate = 16000
        needs_resampling = (self.sample_rate != model_sample_rate)

        if needs_resampling:
            logger.info(f"🔄 Will resample audio: {self.sample_rate}Hz → {model_sample_rate}Hz")

        stream = self.audio.open(
            rate=self.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index
        )

        # Track scores for debugging
        score_log_counter = 0
        max_score_window = 0.0
        volume_display_counter = 0

        try:
            while True:
                # Read audio chunk
                audio_data = stream.read(self.chunk_size, exception_on_overflow=False)

                # Convert to numpy array (int16)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Resample to 16kHz if needed (OpenWakeWord requirement)
                if needs_resampling:
                    audio_array = self._resample_audio(audio_array, self.sample_rate, model_sample_rate)

                # Calculate volume for meter display
                if self.show_volume_meter:
                    rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                    volume_display_counter += 1

                # Get predictions from the model
                prediction = self.oww_model.predict(audio_array)

                # Check if any wake word exceeded threshold
                for wake_word, score in prediction.items():
                    # Track max score for periodic logging
                    if score > max_score_window:
                        max_score_window = score

                    # Show volume meter (every 3 chunks to avoid overwhelming output)
                    if self.show_volume_meter and volume_display_counter >= 3:
                        bar_length = int(min(rms / 100, 40))
                        bar = "█" * bar_length
                        score_bar_length = int(min(score * 40, 40))
                        score_bar = "▓" * score_bar_length + "░" * (40 - score_bar_length)

                        print(f"\r🎤 Vol: {int(rms):5d} [{bar:40s}] | Score: {score:.3f} [{score_bar}] (need {self.threshold:.2f})",
                              end="", flush=True)
                        volume_display_counter = 0

                    # Log scores periodically to help with tuning (every ~2 seconds)
                    score_log_counter += 1
                    if score_log_counter >= 25:  # ~2 seconds at 80ms chunks
                        if max_score_window > 0.01:  # Only log if there's any activity
                            logger.debug(f"Wake word '{wake_word}' max score: {max_score_window:.3f} (threshold: {self.threshold:.3f})")
                        score_log_counter = 0
                        max_score_window = 0.0

                    if score >= self.threshold:
                        if self.show_volume_meter:
                            print()  # New line after meter
                        logger.info(f"✓ Wake word '{wake_word}' detected! (score: {score:.3f} >= threshold: {self.threshold:.3f})")
                        print(f"✓ Wake word detected! (score: {score:.3f})")

                        # Call the callback with the active stream (DON'T close it!)
                        callback(stream)

                        # Reset model state and counters
                        self.oww_model.reset()
                        score_log_counter = 0
                        max_score_window = 0.0
                        volume_display_counter = 0

                        if self.show_volume_meter:
                            print()  # Extra line before resuming meter
                        break  # Break out of the wake word check loop

        except KeyboardInterrupt:
            if self.show_volume_meter:
                print("\n")
            logger.info("Stopping...")
        finally:
            stream.stop_stream()
            stream.close()

    def _listen_volume_based(self, callback):
        """Listen using simple volume-based detection (2 claps)"""
        logger.info("Listening for wake signal (clap twice or make 2 loud sounds)...")
        logger.info(f"Volume threshold: {self.volume_threshold} (clap/loud sound must exceed this)")
        if self.show_volume_meter:
            print(f"\n💡 TIP: Watch the volume levels below. Clap or speak loudly to see what levels you get.")
            print(f"    If claps don't reach {self.volume_threshold}, adjust with --volume-threshold\n")

        stream = self.audio.open(
            rate=self.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=self.chunk_size,
            input_device_index=self.device_index
        )

        last_print_time = time.time()
        try:
            while True:
                # Read audio chunk
                audio_data = stream.read(self.chunk_size, exception_on_overflow=False)

                # Convert to numpy array and calculate RMS
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))

                current_time = time.time()

                # Print volume level every 2 seconds for monitoring (only if show_volume_meter is enabled)
                if self.show_volume_meter and current_time - last_print_time > 2:
                    bar_length = int(min(rms / 100, 50))
                    bar = "█" * bar_length
                    status = "🔊 LOUD!" if rms > self.volume_threshold else ""
                    print(f"\rVolume: {int(rms):5d} {bar:50s} {status}", end="", flush=True)
                    last_print_time = current_time

                # Remove old claps from history
                self.clap_history = [t for t in self.clap_history if current_time - t < self.clap_window]

                # Check if this is a loud sound (clap/snap/etc)
                if rms > self.volume_threshold:
                    # Avoid detecting same clap multiple times
                    if not self.clap_history or (current_time - self.clap_history[-1]) > 0.2:
                        self.clap_history.append(current_time)
                        if self.show_volume_meter:
                            print(f"\n🎵 Loud sound {len(self.clap_history)}/2 detected (level: {int(rms)})")

                    # If we got 2 claps within the window, trigger wake
                    if len(self.clap_history) >= 2:
                        if self.show_volume_meter:
                            print("\n✅ Wake signal detected!")
                        logger.info("Wake signal detected (2 loud sounds)!")
                        self.clap_history = []  # Reset

                        # Call the callback with the active stream (DON'T close it!)
                        callback(stream)

                        # Reset for next wake word detection
                        if self.show_volume_meter:
                            print("\n📊 Listening for wake signal again...")
                        last_print_time = time.time()

        except KeyboardInterrupt:
            print("\n")
            logger.info("Stopping...")
        finally:
            stream.stop_stream()
            stream.close()

    def close(self):
        """Clean up resources"""
        self.audio.terminate()


class VoiceControlSystem:
    """Main voice control system orchestrator"""

    def __init__(
        self,
        config_path: str = "/usr/local/bin/home-iot/conf.ini",
        device_index: Optional[int] = None,
        wakeword_models: Optional[List[str]] = None,
        threshold: Optional[float] = None,
        volume_threshold: int = 2000,
        recording_silence_threshold: int = 200,
        show_volume_meter: bool = False,
        force_sample_rate: Optional[int] = None
    ):
        """
        Initialize voice control system

        Args:
            config_path: Path to configuration file
            device_index: Audio input device index
            wakeword_models: List of wake word model names (default: ['alexa'])
                           Available: 'alexa', 'hey_jarvis', 'hey_mycroft', 'timer'
            threshold: Wake word detection threshold (0.0-1.0) for ML models
                      If None, reads from config file (default: 0.5)
                      Lower values = more sensitive (e.g., 0.3 will trigger more easily)
                      Higher values = less sensitive (e.g., 0.7 requires clearer pronunciation)
            volume_threshold: RMS volume threshold for wake detection (default: 2000)
            recording_silence_threshold: RMS volume threshold for silence during recording (default: 200)
            show_volume_meter: Show live audio volume meter during wake word detection
            force_sample_rate: Force a specific sample rate (e.g., 16000) to avoid resampling
        """
        self.recording_silence_threshold = recording_silence_threshold
        self.device_index = device_index  # Store device index to use for recording
        self.config = VoiceControlConfig(config_path)
        self.audio_player = AudioPlayer(self.config.get('audio_dir', 'voicecontrol/VoiceCommands/'))

        # Get Google API key from config
        google_api_key = self.config.get('google_api_key')
        if not google_api_key:
            raise ValueError("google_api_key not found in config file!")

        # Get threshold from config if not provided as argument
        if threshold is None:
            threshold = float(self.config.get('wakeword_threshold', '0.5'))
            logger.info(f"Using wakeword threshold from config: {threshold}")

        self.speech_recognizer = SpeechRecognizer(google_api_key)
        self.command_processor = CommandProcessor(self.config, self.audio_player)
        self.audio_recorder = AudioRecorder(device_index=device_index)

        self.wake_word_detector = WakeWordDetector(
            wakeword_models=wakeword_models,
            threshold=threshold,
            device_index=device_index,
            volume_threshold=volume_threshold,
            show_volume_meter=show_volume_meter,
            force_sample_rate=force_sample_rate
        )

    def on_wake_word_detected(self, audio_stream):
        """
        Callback when wake word is detected

        Args:
            audio_stream: The active audio stream from wake word detector (stays open!)
        """
        logger.info("Wake word detected - ready for command")

        # Play acknowledgment sound
        self.audio_player.play_reply("Yes", 3)

        # Record command using the SAME stream (don't close/reopen!)
        audio_data = self._record_from_stream(
            audio_stream,
            max_duration=7,
            silence_duration=0.7,
            silence_threshold=self.recording_silence_threshold,
            show_volume_meter=self.wake_word_detector.show_volume_meter
        )

        # Transcribe with the correct sample rate!
        actual_sample_rate = self.wake_word_detector.sample_rate
        logger.info(f"Sending to Google with sample rate: {actual_sample_rate} Hz, language: bg-BG")
        text = self.speech_recognizer.transcribe_audio(audio_data, sample_rate=actual_sample_rate)

        # Process command
        if text:
            self.command_processor.process_command(text)
        else:
            logger.warning("No speech recognized")
            self.audio_player.play_reply("UnknownCommand", 4)

    def _record_from_stream(
        self,
        stream,
        max_duration: int = 10,
        silence_duration: float = 1.0,
        silence_threshold: int = 200,
        show_volume_meter: bool = False
    ) -> bytes:
        """
        Record from an existing stream without closing it

        Args:
            stream: Active PyAudio stream
            max_duration: Maximum recording duration in seconds
            silence_duration: Duration of silence to stop recording
            silence_threshold: RMS volume threshold for silence
            show_volume_meter: Show live volume meter during recording

        Returns:
            Raw audio bytes
        """
        logger.info(f"Recording (max {max_duration}s, stop after {silence_duration}s silence)...")
        if show_volume_meter:
            print(f"Speak now! Calibrating silence threshold...")

        chunk_duration = 30  # ms
        chunk_size = self.wake_word_detector.chunk_size
        sample_rate = self.wake_word_detector.sample_rate

        frames = []
        silent_chunks = 0
        silence_chunks_needed = int(silence_duration * 1000 / chunk_duration)
        max_chunks = int(max_duration * 1000 / chunk_duration)

        # Adaptive silence threshold: measure background noise for first 0.3 seconds
        calibration_chunks = int(0.3 * 1000 / chunk_duration)  # 10 chunks
        calibration_levels = []
        adaptive_threshold = silence_threshold

        try:
            for i in range(max_chunks):
                chunk = stream.read(chunk_size, exception_on_overflow=False)
                frames.append(chunk)

                # Calculate volume (RMS)
                audio_data = np.frombuffer(chunk, dtype=np.int16)
                rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))

                # Calibration phase: collect background noise levels
                if i < calibration_chunks:
                    calibration_levels.append(rms)
                    if i == calibration_chunks - 1:
                        # Calculate adaptive threshold: 2x average background + safety margin
                        avg_background = np.mean(calibration_levels)
                        adaptive_threshold = max(silence_threshold, avg_background * 2.5)
                        logger.info(f"Adaptive silence threshold: {int(adaptive_threshold)} (background: {int(avg_background)})")
                        print(f"\n✓ Silence threshold: {int(adaptive_threshold)} | Speak now, stops after {silence_duration}s silence")
                    continue  # Skip silence detection during calibration

                # Check if silent (below adaptive threshold)
                is_silent = rms < adaptive_threshold

                if is_silent:
                    silent_chunks += 1
                else:
                    silent_chunks = 0  # Reset on any sound

                # Visual feedback every few chunks (only if show_volume_meter is enabled)
                if show_volume_meter and i % 5 == 0:
                    bar_length = int(min(rms / 50, 40))
                    bar = "█" * bar_length
                    silent_bar = int((silent_chunks / silence_chunks_needed) * 20)
                    silent_progress = "▓" * silent_bar + "░" * (20 - silent_bar)
                    status = "🔇" if is_silent else "🗣️"

                    print(f"\r{status} Vol: {int(rms):4d} [{bar:40s}] | Silence: [{silent_progress}] {silent_chunks}/{silence_chunks_needed}",
                          end="", flush=True)

                # Stop if we've had enough continuous silence
                if silent_chunks >= silence_chunks_needed:
                    if show_volume_meter:
                        print(f"\n{silence_duration}s of silence detected, processing...")
                    logger.info(f"Silence detected ({silent_chunks} chunks), stopping recording")
                    break

        except Exception as e:
            logger.error(f"Error during recording: {e}")
            if show_volume_meter:
                print()

        duration = len(frames) * chunk_duration / 1000
        logger.info(f"Recorded {duration:.2f} seconds")
        if show_volume_meter:
            print(f"Recorded {duration:.2f} seconds of audio")
        return b''.join(frames)

    def run(self):
        """Start the voice control system"""
        logger.info("Starting Voice Control System...")
        logger.info(f"API Server: {self.config.get('listen_address')}:{self.config.get('listen_port')}")
        logger.info(f"MQTT Broker: {self.config.get('mqtt_broker')}")

        try:
            self.wake_word_detector.start_listening(self.on_wake_word_detected)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up resources...")
        self.wake_word_detector.close()
        self.audio_recorder.close()
        self.command_processor.mqtt_client.loop_stop()
        self.command_processor.mqtt_client.disconnect()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Modern Voice Control System (using OpenWakeWord - no API key required!)"
    )
    parser.add_argument(
        '--config',
        default='/usr/local/bin/home-iot/conf.ini',
        help='Path to configuration file'
    )
    parser.add_argument(
        '--device-index',
        type=int,
        default=None,
        help='Audio input device index'
    )
    parser.add_argument(
        '--wakewords',
        nargs='+',
        default=None,
        help='Wake word models to use (default: alexa). Available: alexa, hey_jarvis, hey_mycroft, timer'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=None,
        help='Wake word detection threshold (0.0-1.0, default: from config or 0.5). '
             'Lower = more sensitive (e.g., 0.3 triggers easier), '
             'Higher = less sensitive (e.g., 0.7 needs clearer pronunciation). '
             'If not set, reads from wakeword_threshold in config file.'
    )
    parser.add_argument(
        '--volume-threshold',
        type=int,
        default=2000,
        help='RMS volume threshold for simple wake detection (default: 2000). Lower = more sensitive. Watch live levels to tune.'
    )
    parser.add_argument(
        '--recording-silence-threshold',
        type=int,
        default=200,
        help='RMS volume threshold for silence during recording (default: 200). Audio below this is considered silence. Watch live meter to tune.'
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio devices and exit'
    )
    parser.add_argument(
        '--show-volume-meter',
        action='store_true',
        help='Show live audio volume and detection score meter (helps debug mic issues)'
    )
    parser.add_argument(
        '--sample-rate',
        type=int,
        default=None,
        help='Force specific sample rate in Hz (e.g., 16000). Use 16000 to avoid resampling with OpenWakeWord. '
             'If not set, auto-detects best rate for your device.'
    )

    args = parser.parse_args()

    # List audio devices if requested
    if args.list_devices:
        audio = pyaudio.PyAudio()
        print("\nAvailable audio devices:")
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            print(f"  [{i}] {info['name']} (channels: {info['maxInputChannels']})")
        audio.terminate()
        return

    # Start voice control system
    print("\n" + "="*60)
    print("Starting Modern Voice Control System")
    if OPENWAKEWORD_AVAILABLE:
        print("Using OpenWakeWord (no API key required)")
        print(f"Wake words: {args.wakewords or ['alexa']}")
        print(f"Threshold: {args.threshold}")
        print("Say the wake word, then your command!")
    else:
        print("Using Simple Volume-Based Wake Detection")
        print("Wake trigger: Clap twice or make 2 loud sounds within 1 second")
        print(f"Volume threshold: {args.volume_threshold} (adjust with --volume-threshold)")
        print("Then speak your command!")
    print("="*60 + "\n")

    system = VoiceControlSystem(
        config_path=args.config,
        device_index=args.device_index,
        wakeword_models=args.wakewords,
        threshold=args.threshold,
        volume_threshold=args.volume_threshold,
        recording_silence_threshold=args.recording_silence_threshold,
        show_volume_meter=args.show_volume_meter,
        force_sample_rate=args.sample_rate
    )

    system.run()


if __name__ == "__main__":
    main()
