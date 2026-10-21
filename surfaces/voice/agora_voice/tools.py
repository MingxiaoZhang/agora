"""Session event log (DESIGN.md §8). Client tool handlers are added in Phase 2.

One JSON object per line at `<learner-repo>/.agora/voice-sessions/<id>.jsonl`:

    {"t": "2026-10-18T06:42:10Z", "tool": "record_commitment", "params": {...}, "conversation_id": null}

Each line is flushed to disk as it is written, so a call that dies midway
keeps every event up to that point. The reader skips a final line cut off
mid-write rather than failing.

Two entries are not agent tool calls: `session_start` (written by `new`, with
the source, unit and hook the session was built from) and `conversation`
(written by `set_conversation_id`).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SESSIONS_DIR = Path(".agora") / "voice-sessions"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Event:
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    t: str = ""
    conversation_id: str | None = None


class EventLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._conversation_id: str | None = None

    @classmethod
    def new(cls, learner_repo: Path, **session: Any) -> "EventLog":
        """Start a log for a new session, recording what it was built from."""
        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        log = cls(Path(learner_repo) / SESSIONS_DIR / f"{session_id}.jsonl")
        log.append("session_start", **session)
        return log

    def append(self, tool: str, **params: Any) -> Event:
        event = Event(tool=tool, params=params, t=_now(), conversation_id=self._conversation_id)
        line = json.dumps(
            {"t": event.t, "tool": event.tool, "params": event.params, "conversation_id": event.conversation_id},
            ensure_ascii=False,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
        return event

    def set_conversation_id(self, conversation_id: str) -> None:
        self._conversation_id = conversation_id
        self.append("conversation", conversation_id=conversation_id)

    def __iter__(self) -> Iterator[Event]:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").split("\n")
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                if i == len(lines) - 1:  # last line, cut off mid-write
                    return
                raise ValueError(f"{self.path}:{i + 1}: not valid JSON")
            yield Event(tool=raw["tool"], params=raw.get("params", {}), t=raw.get("t", ""),
                        conversation_id=raw.get("conversation_id"))

    def events(self, tool: str | None = None) -> list[Event]:
        return [e for e in self if tool is None or e.tool == tool]

    @property
    def session(self) -> dict[str, Any]:
        starts = self.events("session_start")
        return starts[0].params if starts else {}

    @property
    def conversation_id(self) -> str | None:
        ids = [e.params["conversation_id"] for e in self.events("conversation")]
        return ids[-1] if ids else None
