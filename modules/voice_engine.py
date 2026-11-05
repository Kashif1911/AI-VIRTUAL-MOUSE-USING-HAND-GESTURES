#!/usr/bin/env python3
"""
Voice Assistant Engine
AI Virtual Mouse Pro

Offline voice recognition using Vosk + SpeechRecognition.
"""

import json
import os
import threading
import time

import speech_recognition as sr
from vosk import Model, KaldiRecognizer


class VoiceEngine:
    """Offline voice recognition engine for AI Virtual Mouse Pro."""

    def __init__(self, model_path=None):

        # ─────────────────────────────────────────────
        # Locate Vosk model
        # ─────────────────────────────────────────────
        if model_path is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )

            model_path = os.path.join(
                project_root,
                "models",
                "vosk-model-small-en-us-0.15"
            )

        self.model_path = model_path

        # Check model folder
        if not os.path.isdir(self.model_path):
            raise FileNotFoundError(
                f"\nVosk model not found:\n"
                f"{self.model_path}\n\n"
                "Make sure the folder "
                "'vosk-model-small-en-us-0.15' "
                "is inside the models folder."
            )

        # ─────────────────────────────────────────────
        # Load Vosk model DIRECTLY
        # ─────────────────────────────────────────────
        print("[VOICE] Loading Vosk model...")
        print(f"[VOICE] Model: {self.model_path}")

        self.vosk_model = Model(self.model_path)

        print("[VOICE] Vosk model loaded successfully.")

        # ─────────────────────────────────────────────
        # SpeechRecognition microphone
        # ─────────────────────────────────────────────
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.running = False
        self.thread = None

        self.last_command = ""
        self.last_command_time = 0.0

        # Prevent duplicate commands
        self.command_cooldown = 1.0

        # Callback executed when a command is recognized
        self.command_callback = None

        print("[VOICE] Voice Engine initialized.")

    # ─────────────────────────────────────────────
    # Microphone calibration
    # ─────────────────────────────────────────────

    def calibrate_microphone(self):
        """Calibrate microphone for ambient noise."""

        print("[VOICE] Calibrating microphone...")
        print("[VOICE] Please remain quiet for a moment.")

        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=1
                )

            print("[VOICE] Microphone calibrated.")

        except Exception as e:
            print(f"[VOICE] Calibration error: {e}")

    # ─────────────────────────────────────────────
    # Recognize one command
    # ─────────────────────────────────────────────

    def listen_once(self):

        try:

            with self.microphone as source:

                print("[VOICE] Listening...")

                audio = self.recognizer.listen(
                    source,
                    timeout=5,
                    phrase_time_limit=5
                )

            # ─────────────────────────────────────────
            # Create Vosk recognizer directly
            # ─────────────────────────────────────────
            sample_rate = audio.sample_rate

            command_grammar = [
                "open chrome",
                "open google",
                "open youtube",
                "take screenshot",
                "capture screen",
                "mute",
                "unmute",
                "volume up",
                "volume down",
                "increase volume",
                "decrease volume",
                "open file explorer",
                "open explorer",
                "close window",
                "close this window",
                "stop",
                "exit",
                "[unk]"
            ]

            vosk_recognizer = KaldiRecognizer(
            self.vosk_model,
            sample_rate,
            json.dumps(command_grammar)
            )

            # Get raw microphone audio
            raw_audio = audio.get_raw_data(
                convert_rate=sample_rate,
                convert_width=2
            )

            # Send audio to Vosk
            vosk_recognizer.AcceptWaveform(raw_audio)

            # Get final recognition result
            result = vosk_recognizer.FinalResult()

            # Parse JSON
            data = json.loads(result)

            text = data.get(
                "text",
                ""
            ).strip().lower()

            if text:
                print(f"[VOICE] Heard: {text}")
            else:
                print("[VOICE] No speech recognized.")

            return text

        except sr.WaitTimeoutError:

            return ""

        except Exception as e:

            print(
                f"[VOICE] Recognition error: {e}"
            )

            return ""

    # ─────────────────────────────────────────────
    # Command processing
    # ─────────────────────────────────────────────

    def process_command(self, command):

        if not command:
            return

        now = time.time()

        # Prevent duplicate commands
        if (
            command == self.last_command
            and now - self.last_command_time
            < self.command_cooldown
        ):
            return

        self.last_command = command
        self.last_command_time = now

        print(
            f"[VOICE] Command: {command}"
        )

        # Send command to main application
        if self.command_callback:

            try:

                self.command_callback(
                    command
                )

            except Exception as e:

                print(
                    f"[VOICE] Command callback error: {e}"
                )

    # ─────────────────────────────────────────────
    # Background listener
    # ─────────────────────────────────────────────

    def _listen_loop(self):

        print(
            "[VOICE] Voice assistant started."
        )

        while self.running:

            command = self.listen_once()

            if command:

                self.process_command(
                    command
                )

    # ─────────────────────────────────────────────
    # Start
    # ─────────────────────────────────────────────

    def start(
        self,
        command_callback=None
    ):

        if self.running:
            return

        self.command_callback = (
            command_callback
        )

        self.running = True

        self.calibrate_microphone()

        self.thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )

        self.thread.start()

        print(
            "[VOICE] Assistant running."
        )

    # ─────────────────────────────────────────────
    # Stop
    # ─────────────────────────────────────────────

    def stop(self):

        self.running = False

        if self.thread:

            self.thread.join(
                timeout=1.0
            )

            self.thread = None

        print(
            "[VOICE] Assistant stopped."
        )