"""Finished session → draft records (DESIGN.md §10).

`ingest_conversation` fetches a conversation from ElevenLabs and renders it
with its local event log; `ingest_files` does the same from saved files.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from .reconcile import Reconciled, reconcile
from .render import Written, render
from .tools import SESSIONS_DIR, EventLog

POLL_SECONDS = 5
WAIT_SECONDS = 120
UNFINISHED = ("initiated", "in-progress", "processing")


class IngestError(Exception):
    pass


def fetch(api: Any, conversation_id: str, wait: float = WAIT_SECONDS,
          sleep: Callable[[float], None] = time.sleep) -> dict:
    """The finished conversation, polling while ElevenLabs is still processing it."""
    waited = 0.0
    while True:
        conv = api.get(f"/v1/convai/conversations/{conversation_id}")
        if conv.get("status") not in UNFINISHED:
            return conv
        if waited >= wait:
            raise IngestError(f"Conversation {conversation_id} is still {conv.get('status')}. "
                              f"Re-run `agora-voice ingest {conversation_id}` in a minute.")
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS


def latest_conversation(api: Any, agent_id: str, since: float) -> str | None:
    """The newest conversation with this agent that started after `since` (unix seconds)."""
    page = api.get(f"/v1/convai/conversations?agent_id={agent_id}&page_size=10")
    convs = [c for c in page.get("conversations") or [] if c.get("start_time_unix_secs", 0) >= since - 60]
    convs.sort(key=lambda c: c.get("start_time_unix_secs", 0), reverse=True)
    return convs[0]["conversation_id"] if convs else None


def session_logs(learner_repo: Path) -> list[EventLog]:
    """Event logs in the learner repo, newest first."""
    d = Path(learner_repo) / SESSIONS_DIR
    return [EventLog(p) for p in sorted(d.glob("*.jsonl"), reverse=True)] if d.exists() else []


def find_log(learner_repo: Path, conversation_id: str | None, name: str | None = None) -> EventLog | None:
    """The log with this name, or for this conversation, else the newest log not yet tied to one."""
    logs = session_logs(learner_repo)
    if name:
        return next((log for log in logs if log.path.stem == name), None)
    if conversation_id:
        for log in logs:
            if log.conversation_id == conversation_id:
                return log
    return next((log for log in logs if not log.conversation_id), None)


def has_synthesis(log: EventLog, conversation: dict) -> bool:
    from .reconcile import typed_synthesis
    return any(e.params.get("synthesis") for e in log.events("request_synthesis")) or bool(typed_synthesis(conversation))


def ingest_conversation(learner_repo: Path, log: EventLog, conversation: dict) -> tuple[Reconciled, Written]:
    done = log.events("ingested")
    if done:
        raise IngestError(f"This session was already ingested into {done[-1].params.get('session_note')}. "
                          "Running it again would add its records twice.")
    if conversation.get("conversation_id") and log.conversation_id != conversation["conversation_id"]:
        log.set_conversation_id(conversation["conversation_id"])
    r = reconcile(log, conversation)
    written = render(Path(learner_repo), r, session_date(r, log))
    log.append("ingested", session_note=str(written.session_note.relative_to(learner_repo)))
    return r, written


def session_date(r: Reconciled, log: EventLog) -> str:
    if r.session.get("date"):
        return str(r.session["date"])
    start = r.metadata.get("start_time_unix_secs")
    if start:
        return datetime.fromtimestamp(int(start)).date().isoformat()
    first = next(iter(log), None)
    return first.t[:10] if first else datetime.now().date().isoformat()


def ingest_files(events: Path, conversation: Path, learner_repo: Path) -> tuple[Reconciled, Written]:
    log = EventLog(events)
    conv = json.loads(Path(conversation).read_text(encoding="utf-8"))
    r = reconcile(log, conv)
    return r, render(Path(learner_repo), r, session_date(r, log))


def summary(r: Reconciled, written: Written, learner_repo: Path) -> str:
    repo = Path(learner_repo)
    counts = {}
    for item in r.items:
        counts[item.tool] = counts.get(item.tool, 0) + 1
    lines = [f"Session note: {written.session_note.relative_to(repo)}"]
    lines.append("Recorded: " + (", ".join(f"{n} {tool}" for tool, n in counts.items()) or "nothing"))
    lines += [f"  {u}" for u in written.updated]
    unverified = r.unverified()
    lines.append(f"To review: {len(unverified)} item(s) marked REVIEW:")
    for item in unverified:
        lines.append(f"  {item.tool}: {item.review_note()}")
    research = r.of("queue_research")
    lines.append(f"Research queued: {len(research)}")
    lines += [f"  {i.params.get('question', '')}" for i in research]
    if r.synthesis is None:
        lines.append("Synthesis: not written.")
    elif r.synthesis.source == "post-call":
        lines.append("Synthesis: written after the call, not critiqued.")
    duration = r.metadata.get("call_duration_secs")
    if duration:
        lines.append(f"Duration: {int(duration) // 60} min {int(duration) % 60} s")
    lines.append("Nothing is committed. Review with `git diff`, then commit.")
    return "\n".join(lines)
