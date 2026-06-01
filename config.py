"""Configuration for the Jarvis voice assistant."""

# Speech recognition: "google" (online) or "vosk" (offline, run setup_vosk.py first)
RECOGNITION_ENGINE = "google"
VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"

WAKE_WORD = "jarvis"  # Say this to activate a command (optional filter)
REQUIRE_WAKE_WORD = True  # Only run commands after the wake word is heard
ENABLE_WAKE_UI = True  # Siri-style overlay when Jarvis wakes up

# Wake overlay appearance
UI_WIDTH = 420
UI_HEIGHT = 160
UI_BOTTOM_MARGIN = 90
UI_WINDOW_ALPHA = 0.94
UI_BG_COLOR = "#0a0e14"
UI_ACCENT_COLOR = "#00d4ff"
UI_GLOW_COLOR = "#66e8ff"
UI_TEXT_COLOR = "#e8f4fc"
UI_SUBTEXT_COLOR = "#7a9bb5"

LISTEN_TIMEOUT = 5  # Seconds to wait for speech after opening the mic
PHRASE_TIME_LIMIT = 10  # Max seconds per spoken phrase
AMBIENT_NOISE_DURATION = 1  # Seconds to calibrate mic for background noise

# Volume control (Windows, requires pycaw)
VOLUME_STEP = 10  # Percent change for "volume up" / "volume down"

# Text-to-speech feedback
ENABLE_VOICE_FEEDBACK = True
SPEECH_RATE = 175

# App aliases: spoken name -> Windows executable or path
APP_ALIASES = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "chrome": "chrome",
    "browser": "chrome",
    "file explorer": "explorer",
    "explorer": "explorer",
    "settings": "ms-settings:",
    "terminal": "wt",  # Windows Terminal; falls back to cmd if missing
    "command prompt": "cmd",
}

# Search engine for "search the web for ..."
SEARCH_URL = "https://www.google.com/search?q={query}"

# Guardian — who is using Jarvis + weird-behavior detection
ENABLE_GUARDIAN = True
GUARDIAN_DATA_DIR = "data/guardian"
GUARDIAN_MATCH_THRESHOLD = 2.8  # Lower = stricter voice matching
GUARDIAN_LOW_CONFIDENCE = 0.45
GUARDIAN_BLOCK_RISKY_COMMANDS = True  # Block shutdown/restart/sleep for unknown voices
GUARDIAN_RATE_WINDOW_SECONDS = 60
GUARDIAN_MAX_COMMANDS_PER_WINDOW = 12
GUARDIAN_UNKNOWN_COMMAND_STREAK = 4
GUARDIAN_OFF_HOURS_ENABLED = False
GUARDIAN_OFF_HOURS_START = 23  # 11 PM
GUARDIAN_OFF_HOURS_END = 6  # 6 AM
GUARDIAN_ENROLL_SAMPLES = 2  # Voice clips collected during enrollment
