"""Finished session → draft records (DESIGN.md §10).

Phase 1 has the offline path only: `ingest_files` reads a saved conversation
and event log. Fetching from the API comes in Phase 3.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .reconcile import Reconciled, reconcile
from .render import Written, render
from .tools import EventLog


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
