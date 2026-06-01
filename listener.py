"""Step 1: Capture voice input and convert speech to text."""

from dataclasses import dataclass
import json
import os

import speech_recognition as sr

import config


@dataclass
class ListenResult:
    """Recognized speech plus raw audio for voice identification."""

    text: str | None
    audio: sr.AudioData | None = None


class VoiceListener:
    """Listens to the microphone and returns recognized text."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._vosk_model = None

        if config.RECOGNITION_ENGINE == "vosk":
            self._load_vosk_model()

    def _load_vosk_model(self) -> None:
        import vosk

        model_path = config.VOSK_MODEL_PATH
        if not os.path.isdir(model_path):
            raise FileNotFoundError(
                f"Vosk model not found at '{model_path}'. "
                "Run: python setup_vosk.py"
            )
        vosk.SetLogLevel(-1)
        self._vosk_model = vosk.Model(model_path)
        print(f"Offline recognition enabled (Vosk: {model_path})")

    def calibrate(self) -> None:
        """Adjust for ambient noise. Run once at startup."""
        print("Calibrating microphone for ambient noise...")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(
                source, duration=config.AMBIENT_NOISE_DURATION
            )
        engine = config.RECOGNITION_ENGINE
        print(f"Calibration complete. Engine: {engine}. Ready to listen.\n")

    def listen(self) -> ListenResult:
        """
        Listen for a spoken phrase and return text plus audio.
        Audio is kept for Guardian voice identification.
        """
        print("Listening...")
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=config.LISTEN_TIMEOUT,
                    phrase_time_limit=config.PHRASE_TIME_LIMIT,
                )
        except sr.WaitTimeoutError:
            print("No speech detected.")
            return ListenResult(None, None)

        print("Processing speech...")
        try:
            text = self._transcribe(audio)
            if text:
                print(f"Heard: {text}")
            return ListenResult(text or None, audio)
        except sr.UnknownValueError:
            print("Could not understand audio.")
            return ListenResult(None, audio)
        except sr.RequestError as exc:
            print(f"Speech recognition service error: {exc}")
            return ListenResult(None, audio)
        except OSError as exc:
            print(f"Recognition error: {exc}")
            return ListenResult(None, None)

    def _transcribe(self, audio: sr.AudioData) -> str:
        if config.RECOGNITION_ENGINE == "vosk":
            return self._transcribe_vosk(audio)
        return self.recognizer.recognize_google(audio)

    def _transcribe_vosk(self, audio: sr.AudioData) -> str:
        import vosk

        rec = vosk.KaldiRecognizer(self._vosk_model, 16000)
        wav = audio.get_wav_data(convert_rate=16000, convert_width=2)
        rec.AcceptWaveform(wav)
        result = json.loads(rec.Result())
        return result.get("text", "").strip()
