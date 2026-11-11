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


def test_wrap_up_time():
    assert context.wrap_up_secs(25, 2400) == 1200       # five minutes before the session's length
    assert context.wrap_up_secs(60, 2400) == 2100       # or before the call limit, if that's sooner
    assert context.wrap_up_secs(3, 2400) == 120         # never right away


def test_last_question_is_verbatim_without_audio_tags():
    from agora_voice.reconcile import last_question
    conv = {"transcript": [
        {"role": "agent", "message": "Earlier question?"},
        {"role": "user", "message": "answer"},
        {"role": "agent", "message": "[warm] Good point. Two questions stay open. What do you disagree with in that?"},
    ]}
    assert last_question(conv) == "What do you disagree with in that?"
    assert last_question({"transcript": [{"role": "agent", "message": "Take care."}]}) is None


def test_where_it_stopped_feeds_the_next_session(learner_repo):
    log = EventLog.new(learner_repo, source=SOURCE, unit="transformation", session_minutes=25, date="2026-11-10",
                       hook_headline="A team made contract review 40% faster. Success or failure? You have ninety seconds.")
    log.append("record_commitment", kind="choice", summary="success", learner_quote="success")
    conv = {"transcript": [{"role": "user", "message": "success"},
                           {"role": "agent", "message": "[curious] So what number would you point to?"}],
            "analysis": {"data_collection_results": {"progress_summary": {"value": "Revenue as the test; risk unresolved."}}}}
    note = render(learner_repo, reconcile(log, conv), "2026-11-10").session_note.read_text(encoding="utf-8")
    assert "## Where it stopped\n- Stopped at: debrief" in note
    assert '- Left on: "So what number would you point to?"' in note
    assert "Revenue as the test; risk unresolved. <!-- REVIEW:" in note

    brief = context.build(learner_repo, SOURCE).variables["resume_brief"]
    assert "the debrief step never happened" in brief
    assert 'Left on: "So what number would you point to?"' in brief and "REVIEW" not in brief


def test_smoke_prompt_still_fills(tmp_path):
    import subprocess, sys
    from pathlib import Path
    here = Path(__file__).resolve().parents[1]
    vars_file = tmp_path / "vars.json"
    data = json.loads((here / "smoke" / "transformation.vars.json").read_text(encoding="utf-8"))
    data["learner_context"] = "A backend engineer."
    vars_file.write_text(json.dumps(data), encoding="utf-8")
    run = subprocess.run([sys.executable, str(here / "scripts" / "fill-prompt.py"),
                          str(here / "generated" / "agent-prompt.smoke.md"), str(vars_file), "--out", str(tmp_path)],
                         capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    filled = (tmp_path / "system-prompt.md").read_text(encoding="utf-8")
    assert "{{system__call_duration_secs}}" in filled and "{{wrap_up_secs}}" not in filled
