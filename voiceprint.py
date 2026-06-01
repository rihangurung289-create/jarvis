"""Lightweight voice fingerprints for speaker identification (stdlib only)."""

from __future__ import annotations

import audioop
import math
import struct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import speech_recognition as sr

FEATURE_COUNT = 5


def fingerprint(audio: sr.AudioData) -> list[float]:
    """Build a small feature vector from microphone audio."""
    raw = audio.get_raw_data()
    rate = audio.sample_rate
    width = audio.sample_width
    if not raw or width < 1:
        return [0.0] * FEATURE_COUNT

    clip = _center_clip(raw, rate, width, max_seconds=0.75)
    rms = float(audioop.rms(clip, width))
    peak = float(audioop.max(clip, width))
    zcr = _zero_crossing_rate(clip, width)
    pitch = _estimate_pitch_hz(clip, rate, width)
    duration = len(clip) / (rate * width)

    return [
        math.log1p(rms),
        math.log1p(peak),
        zcr,
        pitch,
        min(duration, 10.0),
    ]


def average_fingerprints(prints: list[list[float]]) -> list[float]:
    if not prints:
        return [0.0] * FEATURE_COUNT
    count = len(prints)
    merged = [0.0] * FEATURE_COUNT
    for fp in prints:
        for i, value in enumerate(fp):
            merged[i] += value
    return [value / count for value in merged]


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def match_score(distance_value: float, threshold: float) -> float:
    """0–1 confidence; higher is a better match."""
    if threshold <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - distance_value / threshold))


def _center_clip(raw: bytes, rate: int, width: int, max_seconds: float) -> bytes:
    max_bytes = int(rate * width * max_seconds)
    if len(raw) <= max_bytes:
        return raw
    start = (len(raw) - max_bytes) // 2
    return raw[start : start + max_bytes]


def _zero_crossing_rate(raw: bytes, width: int) -> float:
    if width != 2 or len(raw) < 4:
        return 0.0
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    crossings = sum(
        1
        for i in range(1, len(samples))
        if (samples[i] >= 0) != (samples[i - 1] >= 0)
    )
    return crossings / max(len(samples) - 1, 1)


def _estimate_pitch_hz(raw: bytes, rate: int, width: int) -> float:
    if width != 2 or rate <= 0:
        return 0.0
    samples = struct.unpack(f"<{len(raw) // 2}h", raw)
    if len(samples) < rate // 10:
        return 0.0

    min_lag = max(2, int(rate / 400))
    max_lag = min(len(samples) - 1, int(rate / 80))
    if max_lag <= min_lag:
        return 0.0

    best_corr = 0.0
    best_lag = 0
    for lag in range(min_lag, max_lag):
        corr = 0.0
        limit = len(samples) - lag
        for i in range(0, limit, 4):
            corr += samples[i] * samples[i + lag]
        if corr > best_corr:
            best_corr = corr
            best_lag = lag

    if best_lag <= 0:
        return 0.0
    return float(rate / best_lag)
