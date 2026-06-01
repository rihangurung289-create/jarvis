"""Security guardian: identify speakers, log usage, flag weird behavior."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import config
from audit import ActivityRecord, AuditStore, IncidentRecord, UserProfile, utc_now_iso
from parser import Command, CommandType
import voiceprint

if TYPE_CHECKING:
    import speech_recognition as sr

UNKNOWN_USER_ID = "unknown"
UNKNOWN_DISPLAY_NAME = "Unknown user"

SENSITIVE_COMMANDS = frozenset(
    {
        CommandType.SHUTDOWN,
        CommandType.RESTART,
        CommandType.SLEEP,
    }
)


@dataclass
class Identification:
    user_id: str
    display_name: str
    confidence: float
    distance: float


@dataclass
class GuardianVerdict:
    identification: Identification
    incidents: list[str]
    blocked: bool
    block_reason: str = ""


class SecurityGuardian:
    """Tracks who uses Jarvis and reacts to suspicious patterns."""

    def __init__(self) -> None:
        self.store = AuditStore(config.GUARDIAN_DATA_DIR)
        self._event_times: list[float] = []
        self._unknown_streak = 0
        self._last_identification: Identification | None = None

    def identify(self, audio: sr.AudioData | None) -> Identification:
        if not config.ENABLE_GUARDIAN or audio is None:
            return Identification(UNKNOWN_USER_ID, UNKNOWN_DISPLAY_NAME, 0.0, 999.0)

        users = self.store.list_users()
        if not users:
            return Identification(UNKNOWN_USER_ID, UNKNOWN_DISPLAY_NAME, 0.0, 999.0)

        sample = voiceprint.fingerprint(audio)
        best: UserProfile | None = None
        best_distance = float("inf")

        for profile in users:
            dist = voiceprint.distance(sample, profile.fingerprint)
            if dist < best_distance:
                best_distance = dist
                best = profile

        threshold = config.GUARDIAN_MATCH_THRESHOLD
        if best is None or best_distance > threshold:
            return Identification(
                UNKNOWN_USER_ID,
                UNKNOWN_DISPLAY_NAME,
                voiceprint.match_score(best_distance, threshold),
                best_distance,
            )

        confidence = voiceprint.match_score(best_distance, threshold)
        return Identification(best.user_id, best.display_name, confidence, best_distance)

    def merge_identifications(self, *ids: Identification) -> Identification:
        known = [i for i in ids if i.user_id != UNKNOWN_USER_ID]
        if not known:
            return ids[0] if ids else Identification(UNKNOWN_USER_ID, UNKNOWN_DISPLAY_NAME, 0.0, 999.0)
        return max(known, key=lambda i: i.confidence)

    def evaluate(
        self,
        identification: Identification,
        command: Command,
        raw_text: str,
    ) -> GuardianVerdict:
        if not config.ENABLE_GUARDIAN:
            return GuardianVerdict(identification, [], False)

        incidents: list[str] = []
        now = datetime.now(timezone.utc)
        hour = now.hour

        if identification.user_id == UNKNOWN_USER_ID:
            incidents.append("unknown_user")
            self._unknown_streak += 1
        else:
            self._unknown_streak = 0

        if (
            identification.user_id != UNKNOWN_USER_ID
            and identification.confidence < config.GUARDIAN_LOW_CONFIDENCE
        ):
            incidents.append("low_confidence_voice_match")

        if command.type in SENSITIVE_COMMANDS:
            if identification.user_id == UNKNOWN_USER_ID:
                incidents.append("sensitive_command_by_unknown")
            elif identification.confidence < config.GUARDIAN_LOW_CONFIDENCE:
                incidents.append("sensitive_command_low_confidence")

        if command.type == CommandType.UNKNOWN:
            if self._unknown_streak >= config.GUARDIAN_UNKNOWN_COMMAND_STREAK:
                incidents.append("repeated_unrecognized_commands")

        if self._is_off_hours(hour):
            incidents.append("off_hours_usage")

        self._event_times.append(now.timestamp())
        window = config.GUARDIAN_RATE_WINDOW_SECONDS
        self._event_times = [t for t in self._event_times if now.timestamp() - t <= window]
        if len(self._event_times) > config.GUARDIAN_MAX_COMMANDS_PER_WINDOW:
            incidents.append("high_command_rate")

        blocked = False
        block_reason = ""
        if incidents and self._should_block(command, incidents, identification):
            blocked = True
            block_reason = self._block_message(incidents)

        return GuardianVerdict(identification, incidents, blocked, block_reason)

    def record_interaction(
        self,
        identification: Identification,
        command: Command,
        raw_text: str,
        result: str,
        verdict: GuardianVerdict,
    ) -> None:
        if not config.ENABLE_GUARDIAN:
            return

        self._last_identification = identification
        incidents = verdict.incidents
        event = "blocked" if verdict.blocked else "command"

        self.store.append_activity(
            ActivityRecord(
                timestamp=utc_now_iso(),
                user_id=identification.user_id,
                display_name=identification.display_name,
                confidence=round(identification.confidence, 3),
                event=event,
                command_type=command.type.name,
                raw_text=raw_text,
                result=result,
                incidents=incidents,
            )
        )

        if incidents:
            self.store.append_incident(
                IncidentRecord(
                    timestamp=utc_now_iso(),
                    user_id=identification.user_id,
                    display_name=identification.display_name,
                    confidence=round(identification.confidence, 3),
                    reasons=incidents,
                    command_type=command.type.name,
                    raw_text=raw_text,
                    blocked=verdict.blocked,
                )
            )
            self._print_incident(identification, incidents, verdict.blocked, raw_text)

    def enroll_user(self, display_name: str, audio_samples: list[sr.AudioData]) -> str:
        name = display_name.strip()
        if not name:
            return "I need a name to enroll. Try: enroll user Alex."

        prints = [voiceprint.fingerprint(a) for a in audio_samples if a is not None]
        if not prints:
            return "I could not capture your voice. Please try enrolling again."

        user_id = self._slugify(name)
        existing = self.store.get_user(user_id)
        merged = voiceprint.average_fingerprints(
            [existing.fingerprint, *prints] if existing else prints
        )
        profile = UserProfile(
            user_id=user_id,
            display_name=name,
            fingerprint=merged,
            enrolled_at=existing.enrolled_at if existing else utc_now_iso(),
            sample_count=(existing.sample_count if existing else 0) + len(prints),
        )
        self.store.save_user(profile)
        return f"Enrolled {name}. Jarvis will recognize your voice on future wakes."

    def who_am_i_message(self) -> str:
        if self._last_identification:
            ident = self._last_identification
            if ident.user_id == UNKNOWN_USER_ID:
                return "I do not recognize your voice yet. Say enroll user and your name to register."
            pct = int(ident.confidence * 100)
            return f"You sound like {ident.display_name}, about {pct} percent confident."
        users = self.store.list_users()
        if not users:
            return "No enrolled users yet. Say enroll user and your name to set up voice recognition."
        names = ", ".join(u.display_name for u in users)
        return f"Enrolled users: {names}. Wake me up and I will try to identify you."

    @staticmethod
    def _slugify(name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        return slug or "user"

    def _should_block(
        self,
        command: Command,
        incidents: list[str],
        identification: Identification,
    ) -> bool:
        if not config.GUARDIAN_BLOCK_RISKY_COMMANDS:
            return False
        if command.type not in SENSITIVE_COMMANDS:
            return False

        blocking_reasons = {
            "sensitive_command_by_unknown",
            "sensitive_command_low_confidence",
            "high_command_rate",
        }
        return any(reason in blocking_reasons for reason in incidents)

    def _is_off_hours(self, hour: int) -> bool:
        if not config.GUARDIAN_OFF_HOURS_ENABLED:
            return False
        start = config.GUARDIAN_OFF_HOURS_START
        end = config.GUARDIAN_OFF_HOURS_END
        if start < end:
            return start <= hour < end
        return hour >= start or hour < end

    @staticmethod
    def _block_message(incidents: list[str]) -> str:
        if "sensitive_command_by_unknown" in incidents:
            return (
                "Blocked shutdown and power commands for an unrecognized voice. "
                "Enroll your voice first with enroll user and your name."
            )
        if "sensitive_command_low_confidence" in incidents:
            return "Blocked risky command because voice match confidence was too low."
        if "high_command_rate" in incidents:
            return "Blocked risky command due to unusually rapid requests."
        return "Blocked command for security reasons."

    @staticmethod
    def _print_incident(
        identification: Identification,
        incidents: list[str],
        blocked: bool,
        raw_text: str,
    ) -> None:
        flag = "BLOCKED" if blocked else "FLAGGED"
        print(
            f"\n[Guardian {flag}] user={identification.display_name} "
            f"confidence={identification.confidence:.2f} "
            f"reasons={','.join(incidents)} text={raw_text!r}\n"
        )
