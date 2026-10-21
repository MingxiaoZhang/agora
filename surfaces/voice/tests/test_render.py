import re
import shutil
from pathlib import Path

import yaml

from agora_voice import cli, ingest
from agora_voice.reconcile import Reconciled
from agora_voice.render import Written, mark_hook_used
from conftest import FIXTURES, ROOT, SOURCE

GOLDEN = FIXTURES / "golden"
NOTE = Path("sources") / SOURCE / "sessions" / "2026-10-20.md"


def run(learner_repo, session_dir, positions=True):
    if positions:
        shutil.copy(FIXTURES / "learner-positions" / "positions.yaml", learner_repo / "learner" / "positions.yaml")
    return ingest.ingest_files(session_dir / "events.jsonl", session_dir / "conversation.json", learner_repo)


def test_session_note_matches_golden(learner_repo, session_dir):
    run(learner_repo, session_dir)
    assert (learner_repo / NOTE).read_text(encoding="utf-8") == (GOLDEN / "2026-10-20.md").read_text(encoding="utf-8")


def test_session_note_follows_format(learner_repo, session_dir):
    run(learner_repo, session_dir)
    fmt = (ROOT / "formats" / "session-note.md").read_text(encoding="utf-8")
    template = fmt.split("```markdown", 1)[1].split("```", 1)[0]
    note = (learner_repo / NOTE).read_text(encoding="utf-8")
    heads = lambda text: re.findall(r"^## .+$", text, re.M)
    assert heads(note) == heads(template)
    keys = lambda text: re.findall(r"^(\w+):", text.split("---")[1], re.M)
    assert keys(note) == keys(template)


def test_positions_match_golden(learner_repo, session_dir):
    run(learner_repo, session_dir)
    out = (learner_repo / "learner" / "positions.yaml").read_text(encoding="utf-8")
    assert out == (GOLDEN / "positions.yaml").read_text(encoding="utf-8")


def test_untouched_entries_are_byte_for_byte(learner_repo, session_dir):
    before = (FIXTURES / "learner-positions" / "positions.yaml").read_text(encoding="utf-8")
    run(learner_repo, session_dir)
    after = (learner_repo / "learner" / "positions.yaml").read_text(encoding="utf-8")
    untouched = before[before.index("# A position from another book"):]
    assert untouched in after


def test_history_is_appended_not_overwritten(learner_repo, session_dir):
    run(learner_repo, session_dir)
    positions = yaml.safe_load((learner_repo / "learner" / "positions.yaml").read_text(encoding="utf-8"))
    pos1 = next(p for p in positions if p["id"] == "pos-0001")
    assert [h["view"] for h in pos1["history"]] == [
        "The hardest tasks for AI are the safest.",
        "mostly how hard it is for the AI, but if it goes wrong that's a different story",
    ]
    assert pos1["current"] == pos1["history"][-1]["view"]
    assert [p["id"] for p in positions] == ["pos-0001", "pos-0002", "pos-0003"]


def test_flags_paraphrase_and_extraction(learner_repo, session_dir):
    run(learner_repo, session_dir)
    positions = (learner_repo / "learner" / "positions.yaml").read_text(encoding="utf-8")
    review = [ln for ln in positions.splitlines() if "REVIEW:" in ln]
    assert len(review) == 1 and "Closest thing you said" in review[0]
    questions = (learner_repo / "learner" / "open-questions.md").read_text(encoding="utf-8")
    assert questions.count("REVIEW: extracted after the call") == 2


def test_records_in_an_empty_template(learner_repo, session_dir):
    r, written = run(learner_repo, session_dir, positions=False)
    for name in ("positions", "bets", "signals"):
        data = yaml.safe_load((learner_repo / "learner" / f"{name}.yaml").read_text(encoding="utf-8"))
        assert isinstance(data, list) and data, name
    bets = yaml.safe_load((learner_repo / "learner" / "bets.yaml").read_text(encoding="utf-8"))
    assert bets[0]["prediction"] == "feature development, I'd say seventy percent within three years"
    assert str(bets[0]["origin"]["session"]) == "2026-10-20"
    idea = (learner_repo / "ideas" / "idea-0001.md").read_text(encoding="utf-8")
    front = yaml.safe_load(idea.split("---")[1])
    assert front["title"] == "The on-call relay" and front["status"] == "draft"
    assert "the on-call is basically like a relay there" in idea


def test_second_session_same_day_gets_its_own_note(learner_repo, session_dir):
    run(learner_repo, session_dir)
    _, written = run(learner_repo, session_dir)
    assert written.session_note.name == "2026-10-20-2.md"


def test_marks_prepared_hook_used(learner_repo):
    spine = learner_repo / "sources" / SOURCE / "spine.yaml"
    before = spine.read_text(encoding="utf-8")
    headline = "A team made contract review 40% faster. Success or failure? You have ninety seconds."
    r = Reconciled(session={"source": SOURCE, "unit": "transformation", "hook_headline": headline})
    mark_hook_used(learner_repo, r, "2026-10-21", Written())
    after = spine.read_text(encoding="utf-8")

    unit = next(u for u in yaml.safe_load(after)["units"] if u["id"] == "transformation")
    assert str(unit["hooks"][0]["used"]) == "2026-10-21"
    added = [ln for ln in after.splitlines() if ln not in before.splitlines()]
    assert added == ["        used: 2026-10-21"]
    mark_hook_used(learner_repo, r, "2026-10-22", Written())  # already used: no change
    assert spine.read_text(encoding="utf-8") == after


def test_cli_ingest_from_fixture(learner_repo, session_dir, capsys):
    assert cli.main(["ingest", "--from-fixture", str(session_dir), "--learner-repo", str(learner_repo)]) == 0
    out = capsys.readouterr().out
    assert "To review: 2 item(s)" in out and "Research queued: 1" in out
    assert (learner_repo / NOTE).exists()
