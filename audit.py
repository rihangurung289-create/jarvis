"""Persistent storage for users, activity, and security incidents."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class UserProfile:
    user_id: str
    display_name: str
    fingerprint: list[float]
    enrolled_at: str
    sample_count: int = 1


@dataclass
class ActivityRecord:
    timestamp: str
    user_id: str
    display_name: str
    confidence: float
    event: str
    command_type: str
    raw_text: str
    result: str
    incidents: list[str]


@dataclass
class IncidentRecord:
    timestamp: str
    user_id: str
    display_name: str
    confidence: float
    reasons: list[str]
    command_type: str
    raw_text: str
    blocked: bool


class AuditStore:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self.users_path = os.path.join(data_dir, "users.json")
        self.activity_path = os.path.join(data_dir, "activity.jsonl")
        self.incidents_path = os.path.join(data_dir, "incidents.jsonl")
        os.makedirs(data_dir, exist_ok=True)
        self._users = self._load_users()

    def list_users(self) -> list[UserProfile]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> UserProfile | None:
        return self._users.get(user_id)

    def save_user(self, profile: UserProfile) -> None:
        self._users[profile.user_id] = profile
        payload = {
            uid: {
                "user_id": p.user_id,
                "display_name": p.display_name,
                "fingerprint": p.fingerprint,
                "enrolled_at": p.enrolled_at,
                "sample_count": p.sample_count,
            }
            for uid, p in self._users.items()
        }
        with open(self.users_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def append_activity(self, record: ActivityRecord) -> None:
        self._append_jsonl(self.activity_path, asdict(record))

    def append_incident(self, record: IncidentRecord) -> None:
        self._append_jsonl(self.incidents_path, asdict(record))

    def read_recent_activity(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_recent_jsonl(self.activity_path, limit)

    def read_recent_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._read_recent_jsonl(self.incidents_path, limit)

    def _load_users(self) -> dict[str, UserProfile]:
        if not os.path.isfile(self.users_path):
            return {}
        with open(self.users_path, encoding="utf-8") as f:
            raw = json.load(f)
        users: dict[str, UserProfile] = {}
        for uid, data in raw.items():
            users[uid] = UserProfile(
                user_id=data["user_id"],
                display_name=data["display_name"],
                fingerprint=data["fingerprint"],
                enrolled_at=data["enrolled_at"],
                sample_count=data.get("sample_count", 1),
            )
        return users

    @staticmethod
    def _append_jsonl(path: str, row: dict[str, Any]) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    @staticmethod
    def _read_recent_jsonl(path: str, limit: int) -> list[dict[str, Any]]:
        if not os.path.isfile(path):
            return []
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        rows: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows
