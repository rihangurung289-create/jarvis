"""Wake-word detection helpers."""

import config


def contains_wake_word(text: str) -> bool:
    if not text:
        return False
    return config.WAKE_WORD.lower() in text.lower()


def strip_wake_word(text: str) -> str:
    """Remove the wake word and anything before it; return the command part."""
    if not text:
        return ""
    lower = text.lower()
    wake = config.WAKE_WORD.lower()
    idx = lower.find(wake)
    if idx < 0:
        return text.strip()
    remainder = text[idx + len(wake) :].strip()
    return remainder.lstrip(".,:;!? ")
