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
    source: str = "tool"                # tool | session | post-call-extraction
    verified: bool = True
    score: float | None = None
    closest_turn: str | None = None

    @property
    def quote(self) -> str | None:
        return self.params.get("learner_quote")

    def review_note(self) -> str | None:
        """Why the learner should check this item, or None if it checked out."""
        if self.verified:
            return None
        if self.source == "post-call-extraction" and not self.quote:
            return "extracted after the call, not recorded during it; check it against what you said."
        if self.closest_turn:
            return f"the quote doesn't match the transcript (score {self.score:.2f}). Closest thing you said: \"{self.closest_turn}\""
        return "the quote doesn't match anything you said in the transcript."


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
        result.items.append(_check(Item(event.tool, params), turns, threshold))

    _fallback(result, turns, threshold)
    if result.synthesis is None:
        text = typed_synthesis(conversation)
        if text:
            result.synthesis = Synthesis(text, "typed-in-call")
    return result


def _check(item: Item, turns: list[str], threshold: float) -> Item:
    """Verbatim check of the item's learner_quote against what the learner said."""
    if item.quote:
        match = best_match(item.quote, turns)
        item.score = round(match.score, 3)
        item.verified = match.score >= threshold
        if not item.verified:
            item.closest_turn = match.turn or None
    return item


SYNTHESIS_ASK = "text box"  # the web prompt asks for the synthesis "in the text box"


def typed_synthesis(conversation: dict) -> str | None:
    """The synthesis typed on the web talk page: the typed reply to the agent's
    last request for it, which the transcript marks with `source_medium: text`.
    Without such a request, the learner's last run of typed messages."""
    turns = [t for t in conversation.get("transcript") or [] if t.get("message")]
    asks = [i for i, t in enumerate(turns) if t.get("role") == "agent" and SYNTHESIS_ASK in t["message"].lower()]
    run: list[str] = []
    for t in turns[asks[-1] + 1:] if asks else turns:
        if t.get("role") != "user":
            if asks and run:
                break  # the agent's critique follows the synthesis
            continue
        if t.get("source_medium") == "text":
            run.append(t["message"].strip())
        elif asks and run:
            break
        else:
            run = []
    return "\n".join(run) or None


def _positions(value: Any) -> list[dict[str, str]]:
    """Parse "topic ## words ## change || ..." from data collection."""
    out = []
    for entry in str(value or "").split("||"):
        parts = [p.strip() for p in entry.split("##")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            change = parts[2].lower() if len(parts) > 2 and parts[2].lower() in ("new", "moved", "hardened") else "new"
            out.append({"topic": parts[0], "view": parts[1], "why": "", "learner_quote": parts[1], "change": change})
    return out


def _fallback(result: Reconciled, turns: list[str], threshold: float) -> None:
    """Fill record types that have no tool event from post-call data collection.
    Items that carry the learner's words get the same verbatim check as tool
    quotes; the rest are always marked for review."""
    data = result.data

    def extracted(tool: str, params: dict[str, Any]) -> None:
        item = Item(tool, params, source="post-call-extraction", verified=False)
        result.items.append(_check(item, turns, threshold))

    if not result.of("record_hook"):
        if result.session.get("hook_headline"):
            # The hook was prepared and passed in, so the session log already knows it.
            result.items.append(Item("record_hook", {"format": result.session.get("hook_format") or data.get("hook_format", ""),
                                                     "headline": result.session["hook_headline"]}, source="session"))
        elif data.get("hook_format") or data.get("hook_headline"):
            extracted("record_hook", {"format": data.get("hook_format", ""), "headline": data.get("hook_headline", "")})
    if not result.of("record_commitment") and data.get("commitment"):
        params = {"kind": data.get("commitment_kind") or "position", "summary": data["commitment"],
                  "learner_quote": data["commitment"]}
        confidence = data.get("commitment_confidence")
        if confidence not in (None, ""):
            params["confidence"] = int(confidence) if float(confidence).is_integer() else confidence
        extracted("record_commitment", params)
    if not result.of("record_position"):
        for params in _positions(data.get("positions")):
            extracted("record_position", params)
    if not result.of("queue_research"):
        for q in _split_questions(data.get("research_questions")):
            extracted("queue_research", {"question": q, "why_it_matters": ""})
    if not result.of("record_converge") and (data.get("core_idea") or data.get("conclusion")):
        extracted("record_converge", {"core_idea": data.get("core_idea", ""),
                                      "conclusion": data.get("conclusion", ""),
                                      "open_questions": _split_questions(data.get("open_questions"))})
