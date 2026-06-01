"""Optional text-to-speech feedback."""

import config


class VoiceSpeaker:
    """Speaks responses aloud using pyttsx3."""

    def __init__(self):
        self._engine = None
        if config.ENABLE_VOICE_FEEDBACK:
            try:
                import pyttsx3

                self._engine = pyttsx3.init()
                self._engine.setProperty("rate", config.SPEECH_RATE)
            except Exception as exc:
                print(f"Voice feedback disabled: {exc}")

    def say(self, text: str) -> None:
        if not self._engine or not text or text == "__EXIT__":
            return
        self._engine.say(text)
        self._engine.runAndWait()
