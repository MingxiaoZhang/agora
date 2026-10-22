import base64
import json
import urllib.parse
from pathlib import Path

import pytest
import yaml

from agora_voice import cli, config, ingest, talk
from agora_voice.reconcile import reconcile
from agora_voice.tools import EventLog
from conftest import FIXTURES, SOURCE

WEB = FIXTURES / "web-session" / "conversation.json"


def web_log(learner_repo):
    return EventLog.new(learner_repo, source=SOURCE, unit="transformation", session_minutes=25,
                        hook_headline="A team made contract review 40% faster. Success or failure? You have ninety seconds.",
                        date="2026-10-21", mode="web", started=1792656000)


def test_talk_url_carries_variables_as_base64_json():
    url = talk.talk_url("agent_web", {"source_author": "李开复", "session_minutes": 25})
    query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    assert url.startswith("https://elevenlabs.io/app/talk-to?") and query["agent_id"] == ["agent_web"]
    raw = base64.b64decode(query["vars"][0])
    assert raw.isascii()
    assert json.loads(raw) == {"source_author": "李开复", "session_minutes": 25}


def test_web_session_records_come_from_the_transcript(learner_repo):
    r = reconcile(web_log(learner_repo), json.loads(WEB.read_text(encoding="utf-8")))
    assert r.synthesis.source == "typed-in-call"
    assert r.synthesis.text == ("A faster workflow only counts if something in the business changes.\n"
                                "I'm not sure the financial statements are the only test.")
    (commitment,) = r.of("record_commitment")
    assert commitment.params["kind"] == "choice" and commitment.verified  # matches what was said
    moved, invented = r.of("record_position")
    assert moved.params["change"] == "moved" and moved.verified
    assert not invented.verified and "Closest thing you said" in invented.review_note()
    assert r.of("queue_research")[0].params["question"].startswith("How often do AI projects")
    (converge,) = r.of("record_converge")
    assert not converge.verified and "extracted after the call" in converge.review_note()


def test_typed_synthesis_is_the_last_typed_run():
    conv = {"transcript": [
        {"role": "user", "message": "typed early", "source_medium": "text"},
        {"role": "user", "message": "spoken", "source_medium": "audio"},
        {"role": "user", "message": "final one", "source_medium": "text"},
        {"role": "agent", "message": "critique"},
        {"role": "user", "message": "final two", "source_medium": "text"},
    ]}
    from agora_voice.reconcile import typed_synthesis
    assert typed_synthesis(conv) == "final one\nfinal two"  # no request: the last typed run
    assert typed_synthesis({"transcript": [{"role": "user", "message": "hi", "source_medium": "audio"}]}) is None


class Api:
    def __init__(self, statuses=("processing", "done")):
        self.statuses = list(statuses)
        self.conv = json.loads(WEB.read_text(encoding="utf-8"))

    def get(self, path):
        if path.startswith("/v1/convai/conversations?"):
            return {"conversations": [
                {"conversation_id": "conv_old", "start_time_unix_secs": 1700000000},
                {"conversation_id": "conv_fixture_web", "start_time_unix_secs": 1792656010},
            ]}
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return dict(self.conv, status=status)


def test_fetch_polls_until_processed():
    sleeps = []
    conv = ingest.fetch(Api(("in-progress", "processing", "done")), "conv_fixture_web", sleep=sleeps.append)
    assert conv["status"] == "done" and len(sleeps) == 2
    with pytest.raises(ingest.IngestError, match="re-run|Re-run"):
        ingest.fetch(Api(("processing",)), "c", wait=10, sleep=lambda s: None)


def test_latest_conversation_skips_older_calls():
    assert ingest.latest_conversation(Api(), "agent_web", since=1792656000) == "conv_fixture_web"
    assert ingest.latest_conversation(Api(), "agent_web", since=1800000000) is None


def test_ingest_from_api_writes_drafts_once(learner_repo, monkeypatch, capsys):
    cfg = config.load(learner_repo)
    cfg.agent_id, cfg.web_agent_id = "agent_cli", "agent_web"
    config.save(cfg)
    log = web_log(learner_repo)
    monkeypatch.setattr(cli, "_api", lambda: Api(("done",)))

    assert cli.main(["ingest", "--learner-repo", str(learner_repo)]) == 0
    out = capsys.readouterr().out
    assert "Fetching conv_fixture_web" in out and "Research queued: 1" in out
    assert EventLog(log.path).conversation_id == "conv_fixture_web"
    note = (learner_repo / "sources" / SOURCE / "sessions" / "2026-10-21.md").read_text(encoding="utf-8")
    assert "I'm not sure the financial statements are the only test." in note
    positions = yaml.safe_load((learner_repo / "learner" / "positions.yaml").read_text(encoding="utf-8"))
    assert [p["topic"] for p in positions] == ["what counts as AI success", "measuring value"]

    # Again, by id: refused rather than adding the records twice.
    assert cli.main(["ingest", "conv_fixture_web", "--learner-repo", str(learner_repo)]) == 1
    assert "already ingested" in capsys.readouterr().err


def test_talk_web_opens_page_then_ingests(learner_repo, monkeypatch, capsys):
    cfg = config.load(learner_repo)
    cfg.web_agent_id = "agent_web"
    config.save(cfg)
    opened = []
    monkeypatch.setattr(talk, "open_in_browser", lambda url: opened.append(url) or True)
    monkeypatch.setattr("builtins.input", lambda: "")
    monkeypatch.setattr(cli, "ingest_latest", lambda repo, cid: 0)

    assert cli.main(["talk", "--web", "--learner-repo", str(learner_repo), "--unit", "transformation"]) == 0
    assert opened and "agent_id=agent_web" in opened[0]
    (log,) = ingest.session_logs(learner_repo)
    assert log.session["mode"] == "web" and log.session["unit"] == "transformation"


def test_synthesis_is_the_typed_reply_to_the_request():
    from agora_voice.reconcile import typed_synthesis
    # In an all-typed session, only the reply after the last request counts.
    conv = {"transcript": [
        {"role": "user", "message": "chatting", "source_medium": "text"},
        {"role": "agent", "message": "Type what you now believe in the text box, then send it."},
        {"role": "user", "message": "not yet", "source_medium": "text"},
        {"role": "agent", "message": "Okay. Type it in the text box when ready."},
        {"role": "user", "message": "My synthesis.", "source_medium": "text"},
        {"role": "agent", "message": "Critique."},
        {"role": "user", "message": "thanks, bye", "source_medium": "text"},
    ]}
    assert typed_synthesis(conv) == "My synthesis."


def test_hook_comes_from_the_session_log(learner_repo):
    r = reconcile(web_log(learner_repo), json.loads(WEB.read_text(encoding="utf-8")))
    (hook,) = r.of("record_hook")
    assert hook.source == "session" and hook.verified
    assert hook.params["headline"].startswith("A team made contract review 40% faster")
