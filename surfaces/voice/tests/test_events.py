import pytest

from agora_voice.tools import EventLog


def test_new_log_records_session_and_conversation(tmp_path):
    log = EventLog.new(tmp_path, source="s", unit="u")
    assert log.path.parent == tmp_path / ".agora" / "voice-sessions"
    log.append("record_hook", format="predict-and-commit", headline="安全的部分")
    log.set_conversation_id("conv_1")
    log.append("record_commitment", learner_quote="sixty percent")

    events = log.events()
    assert [e.tool for e in events] == ["session_start", "record_hook", "conversation", "record_commitment"]
    assert events[1].params["headline"] == "安全的部分"
    assert events[1].conversation_id is None
    assert events[3].conversation_id == "conv_1"
    assert events[0].t.endswith("Z")
    assert log.session == {"source": "s", "unit": "u"}
    assert log.conversation_id == "conv_1"


def test_missing_file_is_empty(tmp_path):
    log = EventLog(tmp_path / "none.jsonl")
    assert log.events() == [] and log.session == {} and log.conversation_id is None


def test_truncated_last_line_is_skipped(tmp_path):
    log = EventLog(tmp_path / "events.jsonl")
    log.append("record_hook", format="x")
    with log.path.open("a", encoding="utf-8") as f:
        f.write('{"t": "2026-10-20T00:00:00Z", "tool": "record_comm')
    assert [e.tool for e in log.events()] == ["record_hook"]


def test_corrupt_middle_line_raises(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"tool": "a"}\nnot json\n{"tool": "b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=":2:"):
        EventLog(path).events()
