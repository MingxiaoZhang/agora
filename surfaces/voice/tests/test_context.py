import json
from pathlib import Path

import pytest

from agora_voice import context
from conftest import SOURCE

SMOKE_VARS = Path(__file__).resolve().parents[1] / "smoke" / "transformation.vars.json"


def test_matches_smoke_test_variables(learner_repo):
    """Same variables as the hand-written smoke-test set. Wording edits made by
    hand there (e.g. "forty percent") are not expected to match."""
    session = context.build(learner_repo, SOURCE, "transformation")
    ref = json.loads(SMOKE_VARS.read_text(encoding="utf-8"))
    assert set(session.variables) == set(ref)
    for key in ("source_spoken_name", "source_author", "source_published", "unit_title",
                "hook_format", "hook_activity", "recent_positions", "open_question", "session_minutes"):
        assert str(session.variables[key]) == str(ref[key]), key
    assert all(isinstance(v, (str, int, float, bool)) for v in session.variables.values())


def test_brief_has_claims_ideas_and_paraphrase_note(learner_repo):
    brief = context.build(learner_repo, SOURCE, "transformation").variables["unit_brief"]
    assert brief.startswith("Claim 1: An AI project only counts")
    assert "When an explanation fits every failure" in brief
    assert brief.endswith("send them to the source.")
    assert context.words(brief) <= context.BRIEF_WORDS


def test_default_unit_needs_an_unused_hook(learner_repo):
    # ch09 is in progress, but its only hook has been used.
    with pytest.raises(context.ContextError, match="prepare two hooks for unit ch09"):
        context.build(learner_repo, SOURCE)


def test_hook_skips_recent_formats():
    unit = {"hooks": [{"format": "forced dilemma", "used": "2026-10-01"},
                      {"format": "predict-and-commit"}, {"format": "find the flaw"}]}
    assert context.select_hook(unit, ["predict-and-commit"])["format"] == "find the flaw"
    assert context.select_hook(unit, ["predict-and-commit", "find the flaw"])["format"] == "predict-and-commit"


def test_fit_drops_whole_items():
    assert context.fit(["one two three", "four five six seven", "eight"], 5) == "one two three eight"
    assert context.words("李开复 wrote 这本书") == 7


def test_learner_state_feeds_resume(learner_repo):
    (learner_repo / "learner" / "context.md").write_text(
        "# About me\n\nWhat I choose to share so hooks can be personal: role, interests.\n\n"
        "I'm a backend engineer. I want to know which parts of my job last.\n", encoding="utf-8")
    (learner_repo / "learner" / "open-questions.md").write_text(
        "# Open questions\n\n- 2026-10-12 · ai-future-is-now/ch09 — Who audits what AI systems did?\n"
        "- 2026-10-10 · ai-future-is-now/ch09 — Older question?\n", encoding="utf-8")
    (learner_repo / "learner" / "positions.yaml").write_text(
        "- id: pos-0001\n  topic: other book topic\n  current: Unrelated.\n  history:\n"
        "    - {date: 2026-10-15, origin: {source: other}}\n"
        "- id: pos-0002\n  topic: accountability\n  current: It moves to whoever signs\n  history:\n"
        "    - {date: 2026-10-01, origin: {source: ai-future-is-now}}\n", encoding="utf-8")

    v = context.build(learner_repo, SOURCE, "transformation", minutes=10).variables
    assert v["learner_context"] == "I'm a backend engineer. I want to know which parts of my job last."
    assert v["open_question"] == "Who audits what AI systems did?"
    assert "Who audits what AI systems did? Has your thinking" in v["opening_line"]
    assert v["recent_positions"] == "accountability: It moves to whoever signs. other book topic: Unrelated."
    assert v["session_minutes"] == 10


def test_template_context_counts_as_nothing_shared(learner_repo):
    assert context.build(learner_repo, SOURCE, "transformation").variables["learner_context"] == "Nothing shared yet."
