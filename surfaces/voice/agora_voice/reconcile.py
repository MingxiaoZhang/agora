"""Check what the agent recorded against what the learner said (DESIGN.md §10).

1. Verbatim check: each `learner_quote` is fuzzy-matched against the user
   turns of the transcript. Below the threshold it is kept as the agent gave
   it, marked unverified, with the closest real turn attached. The closest
   turn is never swapped in, since it may be a different sentence.
2. Fallback fill: a record type with no tool event is filled from post-call
   data collection, always unverified.
3. Synthesis: only ever the typed text from the event log.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from .tools import EventLog

THRESHOLD = 0.8

_TOKEN = re.compile(r"[㐀-鿿豈-﫿]|[a-z0-9]+(?:'[a-z]+)?")


def tokens(text: str) -> list[str]:
    """Lowercased words; each CJK character is its own token."""
    text = unicodedata.normalize("NFKC", text or "").lower().replace("’", "'")
    return _TOKEN.findall(text)


def token_set_ratio(a: str, b: str) -> float:
    """Similarity in [0, 1] that ignores word order and repeats. A quote
    whose words all appear in a longer turn scores 1.0."""
    ta, tb = set(tokens(a)), set(tokens(b))
    if not ta or not tb:
        return 0.0
    common = " ".join(sorted(ta & tb))
    only_a = " ".join([common] + sorted(ta - tb)).strip()
    only_b = " ".join([common] + sorted(tb - ta)).strip()

    def ratio(x: str, y: str) -> float:
        return SequenceMatcher(None, x, y).ratio()

    return max(ratio(common, only_a), ratio(common, only_b), ratio(only_a, only_b))


@dataclass
class Match:
    score: float
    turn: str


def best_match(quote: str, user_turns: list[str]) -> Match:
    """Closest user turn, also trying adjacent pairs, since a quote can span a turn break."""
    candidates = list(user_turns) + [f"{a} {b}" for a, b in zip(user_turns, user_turns[1:])]
    best = Match(0.0, "")
    for turn in candidates:
        score = token_set_ratio(quote, turn)
        if score > best.score:
            best = Match(score, turn)
    return best


@dataclass
class Item:
    tool: str
    params: dict[str, Any]
    source: str = "tool"                # tool | post-call-extraction
    verified: bool = True
    score: float | None = None
    closest_turn: str | None = None

    @property
    def quote(self) -> str | None:
        return self.params.get("learner_quote")

    def review_note(self) -> str | None:
        """Why the learner should check this item, or None if it checked out."""
        if self.source == "post-call-extraction":
            return "extracted after the call, not recorded during it; check it against what you said."
        if self.verified:
            return None
        if self.closest_turn:
            return f"the agent's quote doesn't match the transcript (score {self.score:.2f}). Closest thing you said: \"{self.closest_turn}\""
        return "the agent's quote doesn't match anything you said in the transcript."


@dataclass
class Synthesis:
    text: str
    source: str                          # in-call | post-call


@dataclass
class Reconciled:
    session: dict[str, Any]
    items: list[Item] = field(default_factory=list)
    synthesis: Synthesis | None = None
    data: dict[str, Any] = field(default_factory=dict)   # data-collection values
    metadata: dict[str, Any] = field(default_factory=dict)
    conversation_id: str | None = None

    def of(self, tool: str) -> list[Item]:
        return [i for i in self.items if i.tool == tool]

    def unverified(self) -> list[Item]:
        return [i for i in self.items if not i.verified]


def user_turns(conversation: dict) -> list[str]:
    return [t.get("message") or "" for t in conversation.get("transcript") or []
            if t.get("role") == "user" and t.get("message")]


def data_collection(conversation: dict) -> dict[str, Any]:
    """Data-collection values by field id. Accepts `{"value": ...}` objects
    or bare values, since the result shape is still open question 4."""
    results = (conversation.get("analysis") or {}).get("data_collection_results") or {}
    out = {}
    for key, result in results.items():
        value = result.get("value") if isinstance(result, dict) else result
        if value not in (None, ""):
            out[key] = value
    return out


def _split_questions(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [q.strip() for q in str(value or "").split("|") if q.strip()]


RECORD_TOOLS = ("record_hook", "record_commitment", "record_position", "propose_idea",
                "queue_research", "record_converge")


def reconcile(log: EventLog, conversation: dict, threshold: float = THRESHOLD) -> Reconciled:
    turns = user_turns(conversation)
    result = Reconciled(
        session=log.session,
        data=data_collection(conversation),
        metadata=conversation.get("metadata") or {},
        conversation_id=conversation.get("conversation_id") or log.conversation_id,
    )

    seen = set()
    for event in log:
        key = (event.tool, json.dumps(event.params, sort_keys=True, ensure_ascii=False))
        if key in seen:  # the agent sometimes records the same thing twice
            continue
        seen.add(key)
        if event.tool == "request_synthesis":
            text = (event.params.get("synthesis") or "").strip()
            if text:
                result.synthesis = Synthesis(text, event.params.get("source", "in-call"))
            continue
        if event.tool not in RECORD_TOOLS:
            continue
        params = dict(event.params)
        if event.tool == "record_converge":
            params["open_questions"] = _split_questions(params.get("open_questions"))
        item = Item(event.tool, params)
        if item.quote:
            match = best_match(item.quote, turns)
            item.score = round(match.score, 3)
            item.verified = match.score >= threshold
            if not item.verified:
                item.closest_turn = match.turn or None
        result.items.append(item)

    _fallback(result)
    return result


def _fallback(result: Reconciled) -> None:
    data = result.data

    def extracted(tool: str, params: dict[str, Any]) -> None:
        result.items.append(Item(tool, params, source="post-call-extraction", verified=False))

    if not result.of("record_hook") and (data.get("hook_format") or data.get("hook_headline")):
        extracted("record_hook", {"format": data.get("hook_format", ""), "headline": data.get("hook_headline", "")})
    if not result.of("record_commitment") and data.get("commitment"):
        extracted("record_commitment", {"kind": "position", "summary": data["commitment"],
                                        "learner_quote": data["commitment"]})
    if not result.of("record_converge") and (data.get("core_idea") or data.get("conclusion")):
        extracted("record_converge", {"core_idea": data.get("core_idea", ""),
                                      "conclusion": data.get("conclusion", ""),
                                      "open_questions": _split_questions(data.get("open_questions"))})
