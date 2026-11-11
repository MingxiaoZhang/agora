"""Learner repo → dynamic variables for one session (DESIGN.md §7).

Every limit is enforced by dropping whole items (a claim, a position, a
sentence), never by cutting text mid-sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

BRIEF_WORDS = 500
AUTHOR_CONTEXT_WORDS = 100
LEARNER_CONTEXT_WORDS = 200
POSITIONS_WORDS = 300
RESUME_WORDS = 350
MAX_POSITIONS = 5
RECENT_HOOK_FORMATS = 3
DEFAULT_MINUTES = 25
WRAP_UP_MARGIN_SECS = 300   # start converging this long before the session or the call limit ends

NO_POSITIONS = "None recorded for this book yet."
NO_OPEN_QUESTION = "None. This is the first session on this unit."
NO_LEARNER_CONTEXT = "Nothing shared yet."
NO_RESUME = "None. This is a new session."
HOOK_ALREADY_DONE = "Done in the earlier session. Do not present it again."
# How the opening line names the phase an interrupted session stopped before.
PHASE_WORDS = {"spark": "you committed to the exercise", "debrief": "the debrief", "discuss": "the discussion",
               "converge": "we pulled it together", "synthesize": "your synthesis"}
# The stock line in templates/learner-repo/learner/context.md, which isn't the learner's own words.
TEMPLATE_CONTEXT_HINT = "What I choose to share so hooks can be personal"

_WORD = re.compile(r"[㐀-鿿豈-﫿]|[^\s㐀-鿿豈-﫿]+")
_SENTENCE = re.compile(r"(?<=[.!?。！？])\s+")


class ContextError(Exception):
    """The learner repo can't produce a session: missing spine, unit, or hook."""


def words(text: str) -> int:
    """Word count, counting each CJK character as one word."""
    return len(_WORD.findall(text))


def fit(items: list[str], limit: int, sep: str = " ") -> str:
    """Join items in order, skipping any that would push the total over `limit` words."""
    kept, total = [], 0
    for item in items:
        n = words(item)
        if total + n <= limit:
            kept.append(item)
            total += n
    return sep.join(kept)


def _clean(text: Any) -> str:
    return " ".join(str(text).split()) if text else ""


def _sentence(text: str) -> str:
    text = _clean(text)
    return text if not text or text[-1] in ".!?。！？" else text + "."


@dataclass
class Session:
    variables: dict[str, Any]
    source: str
    unit: str
    hook_headline: str
    resume_from: str | None = None      # phase an interrupted session stopped at
    continues: str | None = None        # date of the session being continued

    def sizes(self) -> dict[str, int]:
        return {k: words(str(v)) for k, v in self.variables.items()}


def load_spine(learner_repo: Path, source: str) -> dict:
    path = Path(learner_repo) / "sources" / source / "spine.yaml"
    if not path.exists():
        raise ContextError(f"No spine at {path}.")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def select_unit(spine: dict, unit_id: str | None) -> dict:
    units = spine.get("units") or []
    if unit_id:
        for unit in units:
            if unit.get("id") == unit_id:
                return unit
        raise ContextError(f"No unit {unit_id!r} in the spine.")
    for status in ("in-progress", "not-started"):
        for unit in units:
            if unit.get("status") == status:
                return unit
    raise ContextError("No unit is in progress or not started; pass --unit.")


def recent_hook_formats(learner_repo: Path, n: int = RECENT_HOOK_FORMATS) -> list[str]:
    signals = _load_list(Path(learner_repo) / "learner" / "signals.yaml")
    signals.sort(key=lambda s: str(s.get("session", "")))
    return [str(s.get("hook_format")) for s in signals[-n:] if s.get("hook_format")]


def select_hook(unit: dict, recent_formats: list[str]) -> dict:
    unused = [h for h in unit.get("hooks") or [] if not h.get("used")]
    if not unused:
        raise ContextError(
            f"Unit {unit.get('id')!r} has no unused prepared hook. Prepare hooks first, in another "
            f"surface (e.g. the Claude skill: \"prepare two hooks for unit {unit.get('id')}\") or by hand."
        )
    fresh = [h for h in unused if h.get("format") not in recent_formats]
    return (fresh or unused)[0]


def unit_brief(unit: dict, source_notes: str = "") -> str:
    items = []
    for i, claim in enumerate(unit.get("claims") or [], 1):
        text = _sentence(claim.get("text") if isinstance(claim, dict) else claim)
        why = claim.get("contestable_because") if isinstance(claim, dict) else None
        items.append(f"Claim {i}: {text}" + (f" Contestable because {_sentence(why)}" if why else ""))
    ideas = [_clean(g) for g in unit.get("general_ideas") or []]
    if ideas:
        items.append("General ideas to steer toward: " + " ".join(ideas))
    for c in unit.get("checkable") or []:
        consensus = c.get("consensus") or "unknown"
        items.append(f"Checkable: {_sentence(c.get('claim'))} Current consensus: {consensus}.")
    for w in unit.get("weaknesses") or []:
        items.append(f"Weakness: {_sentence(w)}")

    note = ""
    if source_notes:
        note = (f"Note on the source: {_sentence(source_notes)} These claims are paraphrased; if the learner "
                "asks what the author actually wrote, send them to the source.")
    return fit(items, BRIEF_WORDS - words(note)) + (" " + note if note else "")


def _load_list(path: Path) -> list:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _position_origin_and_date(pos: dict) -> tuple[str, str]:
    history = pos.get("history") or []
    if not history:
        return "", ""
    last = max(history, key=lambda h: str(h.get("date", "")))
    return str((last.get("origin") or {}).get("source", "")), str(last.get("date", ""))


def recent_positions(learner_repo: Path, source: str) -> str:
    positions = _load_list(Path(learner_repo) / "learner" / "positions.yaml")
    ranked = sorted(
        positions,
        key=lambda p: (_position_origin_and_date(p)[0] == source, _position_origin_and_date(p)[1]),
        reverse=True,
    )
    items = [f"{_clean(p.get('topic'))}: {_sentence(p.get('current'))}" for p in ranked[:MAX_POSITIONS]
             if p.get("topic") and p.get("current")]
    return fit(items, POSITIONS_WORDS) or NO_POSITIONS


def newest_open_question(learner_repo: Path) -> str | None:
    path = Path(learner_repo) / "learner" / "open-questions.md"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("- "):
            text = line[2:]
            # "- 2026-10-10 · ai-future-is-now/ch09 — Who audits ...?"
            return _clean(text.split(" — ", 1)[1] if " — " in text else text)
    return None


def learner_context(learner_repo: Path) -> str:
    path = Path(learner_repo) / "learner" / "context.md"
    if not path.exists():
        return NO_LEARNER_CONTEXT
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
    lines = [ln for ln in text.splitlines()
             if ln.strip() and not ln.lstrip().startswith("#") and TEMPLATE_CONTEXT_HINT not in ln]
    sentences = [s for ln in lines for s in _SENTENCE.split(_clean(ln.lstrip("-* ")))]
    return fit(sentences, LEARNER_CONTEXT_WORDS) or NO_LEARNER_CONTEXT


def speakable_author(author: Any) -> str:
    """Prefer the romanized name in "李开复 (Kai-Fu Lee)", since TTS can't say every script."""
    m = re.search(r"\(([^)]*)\)", str(author or ""))
    return _clean(m.group(1) if m else author)


def spoken_name(src: dict) -> str:
    if src.get("spoken_name"):
        return _clean(src["spoken_name"])
    author = speakable_author(src.get("author"))
    kind = src.get("kind") or "source"
    return f"{author}'s {kind}" if author else f"the {kind}"


@dataclass
class Note:
    path: Path
    front: dict
    sections: dict[str, str]

    @property
    def date(self) -> str:
        return str(self.front.get("date", self.path.stem))


def session_notes(learner_repo: Path, source: str) -> list[Note]:
    """Session notes for a source, oldest first."""
    d = Path(learner_repo) / "sources" / source / "sessions"
    notes = []
    for path in sorted(d.glob("*.md")) if d.exists() else []:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            continue
        _, front, body = text.split("---", 2)
        parts = re.split(r"^## +(.+)$", body, flags=re.M)
        sections = {parts[i].strip(): parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}
        notes.append(Note(path, yaml.safe_load(front) or {}, sections))
    return notes


def interrupted(learner_repo: Path, source: str, unit_id: str | None = None) -> Note | None:
    """The latest session on the unit (or on any unit) if it ended early."""
    latest: dict[str, Note] = {}
    for note in session_notes(learner_repo, source):
        latest[str(note.front.get("unit"))] = note
    candidates = [latest[unit_id]] if unit_id in latest else ([] if unit_id else list(latest.values()))
    candidates = [n for n in candidates if n.front.get("status") == "incomplete" and n.front.get("stopped_at")]
    return max(candidates, key=lambda n: n.path.name) if candidates else None


def _section_text(text: str) -> str:
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
    lines = [ln.strip().lstrip("-* ").strip() for ln in text.splitlines()]
    return " ".join(ln for ln in lines if ln and not (ln.startswith("_") and ln.endswith("_")))


def _headline(note: Note) -> str:
    m = re.search(r'Headline:\s*"?(.+?)"?\s*$', note.sections.get("Hook", ""), re.M)
    return m.group(1) if m else ""


def resume_brief(note: Note, learner_repo: Path, source: str) -> str:
    """What the agent needs to continue an interrupted session, without the transcript."""
    phase = note.front.get("stopped_at")
    items = [f"The last session on this unit ({note.date}) ended early: the {phase} step never happened."]
    if _headline(note):
        items.append(f"Its hook, already done: {_headline(note)}")
    for title in ("Commitment", "Debrief", "Where it stopped"):
        text = _section_text(note.sections.get(title, ""))
        if text:
            items.append(f"{title}: {text}")
    for p in _load_list(Path(learner_repo) / "learner" / "positions.yaml"):
        if any(str((h.get("origin") or {}).get("session")) == note.date and (h.get("origin") or {}).get("source") == source
               for h in p.get("history") or []):
            items.append(f"Their position on {_clean(p.get('topic'))}, as it ended: {_sentence(p.get('current'))}")
    converge = _section_text(note.sections.get("Converge", ""))
    if converge:
        items.append(f"Converge so far: {converge}")
    synthesis = _section_text(note.sections.get("Synthesis", ""))
    if phase == "synthesize" and synthesis:
        items.append(f"They wrote this synthesis after the session; critique it: {synthesis}")
    items.append("Continue from there, following the method's Resume step. Begin your first reply with a "
                 "one-sentence recap of where they had got to, before any question.")
    return fit(items[:-1], RESUME_WORDS - words(items[-1])) + " " + items[-1]


def opening_line(open_question: str | None, unit_title: str, source_name: str) -> str:
    if open_question:
        return f"Hi, I'm Agora; last time you left with a question, {open_question.rstrip('?')}? Has your thinking on it changed?"
    return f"Hi, I'm Agora; today we're starting {unit_title} from {source_name}, with a quick exercise before any reading, ready?"


def resume_opening(note: Note, unit_title: str) -> str:
    phase = PHASE_WORDS.get(note.front.get("stopped_at"), "the end")
    return f"Hi, I'm Agora; last time on {unit_title} we stopped before {phase}. Before we pick it up, has your thinking changed since?"


def wrap_up_secs(minutes: int, max_seconds: int) -> int:
    """When the agent should stop opening threads: five minutes before the session's
    length or the platform's call limit, whichever comes first."""
    return max(120, min(minutes * 60, max_seconds) - WRAP_UP_MARGIN_SECS)


def build(learner_repo: Path, source: str, unit_id: str | None = None, minutes: int | None = None,
          fresh: bool = False, max_seconds: int = 2400) -> Session:
    """Variables for a session. If the unit's last session ended early (or, with no unit
    given, any unit's), continue it rather than start over, unless `fresh`."""
    learner_repo = Path(learner_repo)
    spine = load_spine(learner_repo, source)
    src = spine.get("source") or {}
    note = None if fresh else interrupted(learner_repo, source, unit_id)
    unit = select_unit(spine, str(note.front.get("unit")) if note else unit_id)
    question = newest_open_question(learner_repo)
    name = spoken_name(src)
    if note:
        headline = _headline(note)
        prepared = next((h for h in unit.get("hooks") or [] if _clean(h.get("headline")) == headline), {})
        fmt = re.search(r"Format:\s*(.*)", note.sections.get("Hook", ""))
        hook = {"format": fmt.group(1).strip() if fmt else "", "headline": headline,
                "activity": HOOK_ALREADY_DONE, "debrief_angle": prepared.get("debrief_angle", "")}
    else:
        hook = select_hook(unit, recent_hook_formats(learner_repo))

    variables = {
        "source_spoken_name": name,
        "source_author": speakable_author(src.get("author")),
        "source_published": str(src.get("published", "")),
        "source_author_context": fit(_SENTENCE.split(_clean(src.get("author_context"))), AUTHOR_CONTEXT_WORDS),
        "unit_title": _clean(unit.get("title")),
        "unit_brief": unit_brief(unit, _clean(src.get("notes"))),
        "hook_format": _clean(hook.get("format")),
        "hook_headline": _clean(hook.get("headline")),
        "hook_activity": _clean(hook.get("activity")),
        "hook_debrief_angle": _clean(hook.get("debrief_angle")),
        "learner_context": learner_context(learner_repo),
        "recent_positions": recent_positions(learner_repo, source),
        "open_question": question or NO_OPEN_QUESTION,
        "session_minutes": minutes or DEFAULT_MINUTES,
        "wrap_up_secs": wrap_up_secs(minutes or DEFAULT_MINUTES, max_seconds),
        "opening_line": (resume_opening(note, _clean(unit.get("title"))) if note
                         else opening_line(question, _clean(unit.get("title")), name)),
        "resume_brief": resume_brief(note, learner_repo, source) if note else NO_RESUME,
    }
    if note:
        return Session(variables=variables, source=source, unit=str(unit.get("id")), hook_headline="",
                       resume_from=str(note.front["stopped_at"]), continues=note.date)
    return Session(variables=variables, source=source, unit=str(unit.get("id")),
                   hook_headline=variables["hook_headline"])
