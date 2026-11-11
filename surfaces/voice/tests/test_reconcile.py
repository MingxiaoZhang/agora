from agora_voice.reconcile import best_match, reconcile, token_set_ratio
from agora_voice.tools import EventLog


def test_token_set_ratio():
    assert token_set_ratio("seventy percent", "Okay, I'd say seventy percent.") == 1.0
    assert token_set_ratio("Seventy, PERCENT!", "percent seventy") == 1.0
    assert token_set_ratio("accountability moved", "the weather is nice") < 0.5
    assert token_set_ratio("责任转移了", "我觉得责任转移了") == 1.0
    assert token_set_ratio("", "anything") == 0.0


def test_quote_can_span_two_turns():
    turns = ["And on-call.", "It needs me in particular."]
    assert best_match("on-call needs me in particular", turns).score >= 0.8


def reconciled(session_dir):
    import json
    log = EventLog(session_dir / "events.jsonl")
    conv = json.loads((session_dir / "conversation.json").read_text(encoding="utf-8"))
    return reconcile(log, conv)


def test_exact_quotes_verify(session_dir):
    r = reconciled(session_dir)
    assert all(i.verified for i in r.of("record_commitment"))
    which = next(i for i in r.of("record_position") if i.params["topic"] == "which work AI takes first")
    assert which.verified


def test_paraphrased_quote_is_kept_and_flagged(session_dir):
    r = reconciled(session_dir)
    item = next(i for i in r.of("record_position") if i.params["topic"] == "accountability under automation")
    assert not item.verified
    # The agent's quote stays; the closest real turn is attached, not swapped in.
    assert item.params["learner_quote"].startswith("accountability has moved")
    assert item.closest_turn.startswith("Nowadays, I think AI does almost all")
    assert "Closest thing you said" in item.review_note()


def test_missing_converge_is_filled_from_data_collection(session_dir):
    r = reconciled(session_dir)
    (converge,) = r.of("record_converge")
    assert converge.source == "post-call-extraction" and not converge.verified
    assert converge.params["open_questions"] == [
        "Do organizations pay a premium for accountability?",
        "Is a human who only signs off judging or absorbing blame?",
    ]
    # Tool events win over extraction: no extracted hook or commitment.
    assert all(i.source == "tool" for i in r.of("record_hook") + r.of("record_commitment"))


def test_synthesis_is_the_typed_text(session_dir):
    r = reconciled(session_dir)
    assert r.synthesis.source == "post-call"
    assert r.synthesis.text.startswith("I used to think the hard tasks were safe.")
    assert r.conversation_id == "conv_fixture_ch09"


def test_synthesis_is_never_extracted(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    log.append("session_start", source="s", unit="u")
    conv = {"transcript": [], "analysis": {"data_collection_results": {"synthesis": {"value": "made up"}}}}
    assert reconcile(log, conv).synthesis is None


def test_duplicate_events_count_once(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    log.append("session_start", source="s", unit="u")
    for _ in range(2):
        log.append("record_hook", format="predict-and-commit", headline="h")
    assert len(reconcile(log, {"transcript": []}).of("record_hook")) == 1


def test_stopped_at(tmp_path):
    from agora_voice.reconcile import Reconciled, Item, Synthesis
    r = Reconciled(session={})
    assert r.stopped_at() == "spark"
    r.items.append(Item("record_commitment", {}))
    assert r.stopped_at() == "debrief"
    r.items.append(Item("record_position", {}))
    assert r.stopped_at() == "converge"
    r.items.append(Item("record_converge", {}))
    assert r.stopped_at() == "synthesize"
    r.synthesis = Synthesis("typed after", "post-call")
    assert r.stopped_at() == "synthesize"   # not critiqued
    r.synthesis = Synthesis("typed", "typed-in-call")
    assert r.stopped_at() is None
    # A continued session starts with the earlier phases done.
    assert Reconciled(session={"resume_from": "synthesize"}).stopped_at() == "synthesize"
    assert Reconciled(session={"resume_from": "converge"}, synthesis=Synthesis("x", "in-call")).stopped_at() is None
