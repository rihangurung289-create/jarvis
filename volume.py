"""Windows system volume control via pycaw."""

from ctypes import POINTER, cast

import config

AVAILABLE = False
_volume_interface = None

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    AVAILABLE = True
except ImportError:
    pass


def _get_volume_interface():
    global _volume_interface
    if not AVAILABLE:
        raise RuntimeError("Install pycaw and comtypes for volume control.")
    if _volume_interface is not None:
        return _volume_interface

    speakers = AudioUtilities.GetSpeakers()
    interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    return _volume_interface


def get_volume_percent() -> int:
    """Return current master volume as 0–100."""
    volume = _get_volume_interface()
    scalar = volume.GetMasterVolumeLevelScalar()
    return int(round(scalar * 100))


def set_volume_percent(level: int) -> int:
    """Set master volume to 0–100. Returns the level actually applied."""
    level = max(0, min(100, level))
    volume = _get_volume_interface()
    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
    return level


def change_volume(delta_percent: int) -> int:
    """Raise or lower volume by delta. Returns new level."""
    current = get_volume_percent()
    return set_volume_percent(current + delta_percent)


def set_mute(muted: bool) -> bool:
    volume = _get_volume_interface()
    volume.SetMute(1 if muted else 0, None)
    return muted


def is_muted() -> bool:
    volume = _get_volume_interface()
    return bool(volume.GetMute())


def toggle_mute() -> bool:
    return set_mute(not is_muted())
