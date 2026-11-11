import json

import yaml

from agora_voice import context, ingest
from agora_voice.reconcile import reconcile
from agora_voice.render import render
from agora_voice.tools import EventLog
from conftest import SOURCE

NOTE = """---
date: 2026-10-21
source: ai-future-is-now
unit: transformation
length: 25
surface: voice-elevenlabs
status: {status}
stopped_at: synthesize
---

## Hook
- Format: forced dilemma
- Headline: "A team made contract review 40% faster. Success or failure? You have ninety seconds."

## Commitment
- choice: "At first thought, it's definitely a success." (confidence 80)

## Converge
- Core idea: Speed alone proves nothing. <!-- REVIEW: extracted -->

## Synthesis
_Not written._
"""


def write_note(repo, status="incomplete", name="2026-10-21.md"):
    d = repo / "sources" / SOURCE / "sessions"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(NOTE.format(status=status), encoding="utf-8")
    (repo / "learner" / "positions.yaml").write_text(
        "- id: pos-0001\n  topic: what counts as success\n  current: it depends on cost\n  history:\n"
        "    - {date: 2026-10-21, view: x, origin: {source: ai-future-is-now, unit: transformation, session: 2026-10-21}}\n",
        encoding="utf-8")


def test_continues_the_interrupted_unit_by_default(learner_repo):
    write_note(learner_repo)
    s = context.build(learner_repo, SOURCE)            # no unit given: picks the interrupted one
    assert (s.unit, s.resume_from, s.continues, s.hook_headline) == ("transformation", "synthesize", "2026-10-21", "")
    v = s.variables
    assert "stopped before your synthesis" in v["opening_line"]
    assert v["hook_activity"] == context.HOOK_ALREADY_DONE   # the used hook isn't a blocker
    assert v["hook_debrief_angle"].startswith("What did the learner assume")
    brief = v["resume_brief"]
    assert "the synthesize step never happened" in brief
    assert 'Commitment: choice: "At first thought' in brief
    assert "what counts as success, as it ended: it depends on cost." in brief
    assert "Core idea: Speed alone proves nothing." in brief and "REVIEW" not in brief
    assert "critique it" not in brief                       # nothing was written after the call
    assert context.words(brief) <= context.RESUME_WORDS


def test_fresh_or_complete_sessions_dont_resume(learner_repo):
    write_note(learner_repo)
    s = context.build(learner_repo, SOURCE, "transformation", fresh=True)
    assert s.continues is None and s.variables["resume_brief"] == context.NO_RESUME
    write_note(learner_repo, status="complete")
    assert context.interrupted(learner_repo, SOURCE) is None


def test_only_the_latest_session_on_a_unit_counts(learner_repo):
    write_note(learner_repo)
    write_note(learner_repo, status="complete", name="2026-10-22.md")
    assert context.interrupted(learner_repo, SOURCE, "transformation") is None


def test_a_continued_session_renders_and_completes(learner_repo):
    write_note(learner_repo)
    s = context.build(learner_repo, SOURCE)
    log = EventLog.new(learner_repo, source=s.source, unit=s.unit, hook_headline="", session_minutes=25,
                       date="2026-11-10", mode="text", resume_from=s.resume_from, continues=s.continues)
    log.append("request_synthesis", prompt="Type it", synthesis="Speed counts only if a line moves.", source="in-call")
    conv = {"transcript": [], "analysis": {"data_collection_results": {"hook_headline": {"value": "made up"}}}}
    written = render(learner_repo, reconcile(log, conv), "2026-11-10")
    note = written.session_note.read_text(encoding="utf-8")
    front = yaml.safe_load(note.split("---")[1])
    assert front["status"] == "complete" and str(front["continues"]) == "2026-10-21" and "stopped_at" not in front
    assert "_Continued from 2026-10-21; the hook was done then._" in note and "made up" not in note
    signals = yaml.safe_load((learner_repo / "learner" / "signals.yaml").read_text(encoding="utf-8"))
    assert signals[-1]["hook_skipped"] is False and signals[-1]["synthesis_written"] is True
    # Once continued and complete, the unit no longer resumes.
    assert context.interrupted(learner_repo, SOURCE) is None
