"""Step 2: Parse spoken text into structured commands."""

from dataclasses import dataclass
from enum import Enum, auto

import config


class CommandType(Enum):
    OPEN_APP = auto()
    SEARCH_WEB = auto()
    SHUTDOWN = auto()
    RESTART = auto()
    CANCEL_SHUTDOWN = auto()
    SLEEP = auto()
    VOLUME_UP = auto()
    VOLUME_DOWN = auto()
    VOLUME_SET = auto()
    VOLUME_MUTE = auto()
    VOLUME_UNMUTE = auto()
    ENROLL_USER = auto()
    WHO_AM_I = auto()
    EXIT = auto()
    CHAT = auto()
    UNKNOWN = auto()


@dataclass
class Command:
    """A parsed voice command ready for execution."""

    type: CommandType
    target: str = ""  # App name, search query, etc.


class CommandParser:
    """Turns raw speech text into Command objects."""

    def parse(self, text: str) -> Command:
        if not text:
            return Command(type=CommandType.UNKNOWN)

        normalized = text.lower().strip()

        # Optional wake word: "jarvis open notepad" -> "open notepad"
        if normalized.startswith(config.WAKE_WORD):
            normalized = normalized[len(config.WAKE_WORD) :].strip()

        if self._matches(normalized, ("who am i", "who is speaking", "identify me")):
            return Command(type=CommandType.WHO_AM_I)

        enroll_name = self._extract_after(
            normalized,
            ("enroll user", "enroll as", "remember me as", "register as", "register user"),
        )
        if enroll_name is not None:
            return Command(type=CommandType.ENROLL_USER, target=enroll_name)

        if self._matches(normalized, ("exit", "quit", "goodbye")):
            return Command(type=CommandType.EXIT)

        if self._matches(
            normalized,
            ("cancel shutdown", "abort shutdown", "cancel restart", "stop shutdown"),
        ):
            return Command(type=CommandType.CANCEL_SHUTDOWN)

        if self._matches(normalized, ("shut down", "shutdown", "turn off")):
            return Command(type=CommandType.SHUTDOWN)

        if self._matches(normalized, ("restart", "reboot")):
            return Command(type=CommandType.RESTART)

        if self._matches(normalized, ("sleep", "go to sleep")):
            return Command(type=CommandType.SLEEP)

        if self._matches(normalized, ("unmute", "turn on sound")):
            return Command(type=CommandType.VOLUME_UNMUTE)

        if self._matches(normalized, ("mute", "silence")):
            return Command(type=CommandType.VOLUME_MUTE)

        if self._matches(
            normalized, ("volume up", "increase volume", "turn up volume", "louder")
        ):
            return Command(type=CommandType.VOLUME_UP)

        if self._matches(
            normalized, ("volume down", "decrease volume", "turn down volume", "quieter")
        ):
            return Command(type=CommandType.VOLUME_DOWN)

        volume_level = self._parse_volume_level(normalized)
        if volume_level is not None:
            return Command(type=CommandType.VOLUME_SET, target=str(volume_level))

        search_query = self._extract_after(normalized, ("search for", "search the web for", "google"))
        if search_query:
            return Command(type=CommandType.SEARCH_WEB, target=search_query)

        app_name = self._extract_after(normalized, ("open", "launch", "start"))
        if app_name:
            return Command(type=CommandType.OPEN_APP, target=app_name)

        if self._is_conversational(normalized):
            return Command(type=CommandType.CHAT, target=text.strip())

        return Command(type=CommandType.UNKNOWN)

    _CONVERSATIONAL_PHRASES = (
        "what ",
        "what's ",
        "whats ",
        "who ",
        "how ",
        "why ",
        "when ",
        "where ",
        "which ",
        "can you ",
        "could you ",
        "would you ",
        "tell me ",
        "explain ",
        "describe ",
        "do you ",
        "is there ",
        "are there ",
        "help me ",
        "hello",
        "hi ",
        "hey ",
        "good morning",
        "good afternoon",
        "good evening",
        "thanks",
        "thank you",
    )

    @classmethod
    def _is_conversational(cls, text: str) -> bool:
        if text.endswith("?"):
            return True
        return any(
            text == phrase.rstrip() or text.startswith(phrase)
            for phrase in cls._CONVERSATIONAL_PHRASES
        )

    @staticmethod
    def _matches(text: str, phrases: tuple[str, ...]) -> bool:
        return any(text == phrase or text.startswith(phrase + " ") for phrase in phrases)

    @staticmethod
    def _extract_after(text: str, prefixes: tuple[str, ...]) -> str | None:
        for prefix in prefixes:
            if text.startswith(prefix + " "):
                return text[len(prefix) + 1 :].strip()
            if text == prefix:
                return ""
        return None

    @staticmethod
    def _parse_volume_level(text: str) -> int | None:
        """Parse 'set volume to 50', 'volume 50 percent', etc."""
        prefixes = ("set volume to", "volume to", "volume")
        remainder = None
        for prefix in prefixes:
            if text.startswith(prefix + " "):
                remainder = text[len(prefix) + 1 :].strip()
                break
        if remainder is None:
            return None

        remainder = remainder.replace("percent", "").replace("%", "").strip()
        word_map = {
            "zero": 0,
            "ten": 10,
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
            "hundred": 100,
            "max": 100,
            "maximum": 100,
            "half": 50,
        }
        if remainder in word_map:
            return word_map[remainder]

        try:
            level = int(remainder.split()[0])
            return max(0, min(100, level))
        except ValueError:
            return None
