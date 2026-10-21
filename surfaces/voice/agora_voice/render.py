"""Reconciled session → draft records in the learner repo (DESIGN.md §10, formats/).

YAML files are edited as text: new entries are appended, and an existing
position only gains a history item and a new `current`/`status`. Untouched
entries are left byte for byte, so `git diff` shows only what this session
added. Fields that belong to the learner hold `learner_quote`; the agent's
summary goes in a comment next to it. Anything unverified gets a `REVIEW:`
comment (`# REVIEW:` in YAML, `<!-- REVIEW: -->` in markdown).

Nothing here commits. The learner reviews and commits.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .reconcile import Item, Reconciled

SURFACE = "voice-elevenlabs"


@dataclass
class Written:
    session_note: Path | None = None
    updated: list[str] = field(default_factory=list)   # e.g. "positions: pos-0002 (moved)"
    files: list[Path] = field(default_factory=list)


class _Flow(dict):
    """A mapping written inline, like `origin: {source: x, unit: y, session: 2026-10-20}`."""


class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)  # indent nested lists, as formats/ does


_Dumper.add_representer(_Flow, lambda d, data: d.represent_mapping("tag:yaml.org,2002:map", data, flow_style=True))


def _dump(value: Any) -> str:
    return yaml.dump(value, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=10_000)


def _day(date: str) -> dt.date:
    return dt.date.fromisoformat(date)


def _yaml_comment(text: str, indent: str = "") -> str:
    return "".join(f"{indent}# {line}\n" for line in text.splitlines())


def _review_yaml(item: Item, indent: str = "") -> str:
    note = item.review_note()
    return _yaml_comment(f"REVIEW: {note}", indent) if note else ""


def _review_md(item: Item) -> str:
    note = item.review_note()
    return f" <!-- REVIEW: {note} -->" if note else ""


def _indent(text: str, prefix: str) -> str:
    return "".join(prefix + line if line.strip() else line for line in text.splitlines(keepends=True))


def _next_id(text: str, prefix: str, extra: list[str] = ()) -> str:
    nums = [int(n) for n in re.findall(rf"\b{prefix}-(\d+)\b", text + " ".join(extra))]
    return f"{prefix}-{max(nums, default=0) + 1:04d}"


def _append_entries(path: Path, entries: str) -> None:
    """Append top-level list entries to a YAML list file, replacing a bare `[]`."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.strip() == "[]":
            lines[i] = entries
            break
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(entries)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def _origin(r: Reconciled, date: str) -> _Flow:
    return _Flow(source=r.session.get("source", ""), unit=r.session.get("unit", ""), session=_day(date))


# --- positions ---------------------------------------------------------------

def _entry_span(lines: list[str], entry_id: str) -> tuple[int, int] | None:
    """Line range of the top-level list entry with this id, excluding trailing blanks and comments."""
    start = next((i for i, ln in enumerate(lines) if re.match(rf"-\s+id:\s*{re.escape(entry_id)}\s*$", ln)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("- ")), len(lines))
    while end > start + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
        end -= 1
    return start, end


def _set_key(lines: list[str], entry_id: str, key: str, value: Any) -> None:
    """Set a top-level key of an entry in place, replacing its old value and any continuation lines."""
    start, end = _entry_span(lines, entry_id)
    new = _indent(_dump({key: value}), "  ")
    for i in range(start + 1, end):
        if lines[i].startswith(f"  {key}:"):
            j = i + 1
            while j < end and (not lines[j].strip() or lines[j].startswith("   ")):
                j += 1
            lines[i:j] = [new]
            return
    lines.insert(start + 1, new)


def _position_status(change: str) -> str:
    return {"moved": "moved", "hardened": "holding", "new": "holding"}.get(change, "unsure")


def render_positions(repo: Path, r: Reconciled, date: str, out: Written) -> None:
    items = r.of("record_position")
    if not items:
        return
    path = repo / "learner" / "positions.yaml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    existing = {str(p.get("topic")): str(p.get("id")) for p in (yaml.safe_load(text) or []) if isinstance(p, dict)}

    for item in items:
        p = item.params
        words = p.get("learner_quote") or p.get("view", "")
        history = {"date": _day(date), "view": words, "why": p.get("why", ""), "origin": _origin(r, date)}
        summary = _yaml_comment(f"Agent's summary: {p.get('view', '')}", "    ") if p.get("view") else ""
        topic = str(p.get("topic", ""))

        if topic in existing:
            pos_id = existing[topic]
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            _set_key(lines, pos_id, "current", words)
            _set_key(lines, pos_id, "status", _position_status(p.get("change", "")))
            start, end = _entry_span(lines, pos_id)
            if not any(lines[i].startswith("  history:") for i in range(start, end)):
                lines.insert(end, "  history:\n")
                end += 1
            lines.insert(end, _review_yaml(item, "    ") + summary + _indent(_dump([history]), "    "))
            path.write_text("".join(lines), encoding="utf-8")
            out.updated.append(f"positions: {pos_id} ({p.get('change') or 'updated'})")
        else:
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            pos_id = _next_id(text, "pos")
            entry = {"id": pos_id, "topic": topic, "current": words,
                     "status": _position_status(p.get("change", "new")), "history": [history]}
            block = _review_yaml(item) + _yaml_comment(f"Agent's summary: {p.get('view', '')}") + _dump([entry])
            _append_entries(path, block)
            existing[topic] = pos_id
            out.updated.append(f"positions: {pos_id} (new)")
    out.files.append(path)


# --- bets, ideas, open questions, signals --------------------------------------

def render_bets(repo: Path, r: Reconciled, date: str, out: Written) -> None:
    bets = [i for i in r.of("record_commitment") if i.params.get("kind") == "bet"]
    if not bets:
        return
    path = repo / "learner" / "bets.yaml"
    for item in bets:
        p = item.params
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        bet_id = _next_id(text, "bet")
        entry = {"id": bet_id, "date": _day(date), "prediction": p.get("learner_quote") or p.get("summary", "")}
        if p.get("confidence") is not None:
            entry["confidence"] = p["confidence"]
        entry.update({"origin": _origin(r, date), "resolves": "on-reveal", "outcome": "", "lesson": ""})
        block = _review_yaml(item) + _yaml_comment(f"Agent's summary: {p.get('summary', '')}") + _dump([entry])
        _append_entries(path, block)
        out.updated.append(f"bets: {bet_id}")
    out.files.append(path)


def render_ideas(repo: Path, r: Reconciled, date: str, out: Written) -> None:
    ideas_dir = repo / "ideas"
    for item in r.of("propose_idea"):
        p = item.params
        existing = [f.stem for f in ideas_dir.glob("idea-*.md")] if ideas_dir.exists() else []
        idea_id = _next_id("", "idea", existing)
        origin = _origin(r, date)
        review = _review_md(item).strip()
        text = (
            "---\n"
            f"id: {idea_id}\n"
            f"{_dump({'title': p.get('title', '')})}"
            "status: draft\n"
            f"created: {date}\n"
            f"origin: {_dump(origin).strip()}\n"
            "related: []\n"
            "---\n\n"
            "## Statement\n"
            f"{p.get('learner_quote') or p.get('statement', '')}"
            + (f"\n{review}" if review else "")
            + f"\n<!-- Agent's summary: {p.get('statement', '')} -->\n\n"
            "## Why I think so\n\n"
            "## Evidence\n\n"
            "## Open questions\n\n"
            "## Log\n"
            f"- {date} — proposed in a voice session.\n"
        )
        ideas_dir.mkdir(parents=True, exist_ok=True)
        path = ideas_dir / f"{idea_id}.md"
        path.write_text(text, encoding="utf-8")
        out.files.append(path)
        out.updated.append(f"ideas: {idea_id} (proposed)")


def render_open_questions(repo: Path, r: Reconciled, date: str, out: Written) -> list[str]:
    questions = [(q, item) for item in r.of("record_converge") for q in item.params.get("open_questions") or []]
    if not questions:
        return []
    path = repo / "learner" / "open-questions.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Open questions\n\n"
    origin = f"{r.session.get('source', '')}/{r.session.get('unit', '')}"
    new = "".join(f"- {date} · {origin} — {q}{_review_md(item)}\n" for q, item in questions)
    lines = text.splitlines(keepends=True)
    first = next((i for i, ln in enumerate(lines) if ln.startswith("- ")), None)
    if first is None:
        text = text.rstrip("\n") + "\n\n" + new
    else:
        lines.insert(first, new)
        text = "".join(lines)
    path.write_text(text, encoding="utf-8")
    out.files.append(path)
    return [q for q, _ in questions]


def render_signals(repo: Path, r: Reconciled, date: str, out: Written) -> None:
    hooks = r.of("record_hook")
    entry = {
        "session": _day(date),
        "source": r.session.get("source", ""),
        "hook_format": hooks[0].params.get("format", "") if hooks else "",
        "hook_skipped": not hooks,
        "hints_used": int(r.data.get("hints_used") or 0),
        "answer_requested_before_attempt": int(r.data.get("answer_requested_before_attempt") or 0),
        "converged": bool(r.of("record_converge")),
        "synthesis_written": r.synthesis is not None,
    }
    path = repo / "learner" / "signals.yaml"
    _append_entries(path, _dump([entry]))
    out.files.append(path)


def mark_hook_used(repo: Path, r: Reconciled, date: str, out: Written) -> None:
    """Set `used:` on the prepared hook this session was built from."""
    source, unit, headline = r.session.get("source"), r.session.get("unit"), r.session.get("hook_headline")
    path = repo / "sources" / str(source) / "spine.yaml"
    if not (source and unit and headline and path.exists()):
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    in_unit = False
    for i, line in enumerate(lines):
        m = re.match(r"(\s*)- id:\s*(\S+)", line)
        if m:
            in_unit = m.group(2) == unit
        if not in_unit or not re.match(r"\s*-?\s*headline:", line):
            continue
        value = yaml.safe_load(line.split("headline:", 1)[1]) if line.split("headline:", 1)[1].strip() else ""
        if str(value).strip() != headline:
            continue
        key_indent = len(line) - len(line.lstrip(" -"))
        item_indent = key_indent - 2
        end = i + 1
        while end < len(lines):
            ln = lines[end]
            ind = len(ln) - len(ln.lstrip(" "))
            if ln.strip() and (ind < key_indent or (ind == item_indent and ln.lstrip().startswith("- "))):
                break
            end += 1
        while end > i + 1 and not lines[end - 1].strip():
            end -= 1
        if any(re.match(rf"\s{{{key_indent}}}used:", lines[k]) for k in range(i, end)):
            return
        lines.insert(end, f"{' ' * key_indent}used: {date}\n")
        path.write_text("".join(lines), encoding="utf-8")
        out.files.append(path)
        return


# --- session note ----------------------------------------------------------------

def session_note(r: Reconciled, date: str, updated: list[str], open_question: str | None) -> str:
    s = r.session
    out = [
        "---",
        f"date: {date}",
        f"source: {s.get('source', '')}",
        f"unit: {s.get('unit', '')}",
        f"length: {s.get('session_minutes', 'open')}",
        f"surface: {SURFACE}",
        "---",
        "",
        "## Hook",
    ]
    for item in r.of("record_hook"):
        p = item.params
        out.append(f"- Format: {p.get('format', '')}{_review_md(item)}")
        out.append(f"- Headline: \"{p.get('headline', '')}\"")
        if p.get("rejected"):
            out.append(f"- Rejected candidates: {p['rejected']}")
    if not r.of("record_hook"):
        out.append("_No hook recorded._")

    out += ["", "## Commitment"]
    for item in r.of("record_commitment"):
        p = item.params
        conf = f" (confidence {p['confidence']})" if p.get("confidence") is not None else ""
        out.append(f"- {p.get('kind', 'commitment')}: \"{p.get('learner_quote') or p.get('summary', '')}\"{conf}{_review_md(item)}")
        if p.get("summary"):
            out.append(f"  <!-- Agent's summary: {p['summary']} -->")

    out += ["", "## Debrief", ""]

    out += ["## Discussion"]
    for item in r.of("record_position"):
        p = item.params
        out.append(f"- {p.get('topic', '')} ({p.get('change', '')}): \"{p.get('learner_quote') or p.get('view', '')}\"{_review_md(item)}")
    research = r.of("queue_research")
    if research:
        out.append("- Research to do:")
        for item in research:
            why = f" ({item.params['why_it_matters']})" if item.params.get("why_it_matters") else ""
            out.append(f"  - {item.params.get('question', '')}{why}")

    out += ["", "## Converge"]
    for item in r.of("record_converge"):
        p = item.params
        review = _review_md(item)
        out.append(f"- Core idea: {p.get('core_idea', '')}{review}")
        out.append(f"- Provisional conclusion: {p.get('conclusion', '')}")
        out.append(f"- Still open: {'; '.join(p.get('open_questions') or [])}")

    out += ["", "## Synthesis"]
    if r.synthesis:
        if r.synthesis.source == "post-call":
            out.append("<!-- Written after the call ended, so it wasn't critiqued in the session. -->")
        out.append(r.synthesis.text)
    else:
        out.append("_Not written._")

    out += ["", "## Records updated"]
    out += [f"- {u}" for u in updated]
    out.append(f"- open question carried out: {open_question or ''}")
    return "\n".join(out) + "\n"


def render(repo: Path, r: Reconciled, date: str) -> Written:
    """Write every draft for one session into the learner repo."""
    repo = Path(repo)
    out = Written()
    render_positions(repo, r, date, out)
    render_bets(repo, r, date, out)
    render_ideas(repo, r, date, out)
    questions = render_open_questions(repo, r, date, out)
    render_signals(repo, r, date, out)
    mark_hook_used(repo, r, date, out)

    sessions = repo / "sources" / str(r.session.get("source", "unknown")) / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    path, n = sessions / f"{date}.md", 2
    while path.exists():
        path, n = sessions / f"{date}-{n}.md", n + 1
    path.write_text(session_note(r, date, out.updated, questions[0] if questions else None), encoding="utf-8")
    out.session_note = path
    out.files.insert(0, path)
    return out
