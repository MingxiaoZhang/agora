# Voice (ElevenLabs)

Spoken Agora sessions, built on ElevenLabs' voice agents (ElevenAgents) with hosted Claude.

- [`DESIGN.md`](DESIGN.md): low-level design (option 1, a local CLI)
- [`PLAN.md`](PLAN.md): phased implementation plan
- [`SMOKE-TEST.md`](SMOKE-TEST.md): **start here.** Phase 0, a hand-run spoken session with no code

**Status:** Phase 0 is done: the smoke test passed (results in [`SMOKE-TEST.md`](SMOKE-TEST.md#results)). Phases 1 and 2 are built, and the voice path is in place: `setup` provisions the agents, `talk --web` runs a spoken session on ElevenLabs' talk page, `talk --text` runs a typed one, and each ends with draft records in your learner repo.

Rules that apply to any spoken session live in `method/session.md` under "Spoken sessions", not here. This folder holds only what's specific to ElevenLabs.

| Path | What |
|---|---|
| `agent/` | Hand-written prompt pieces (header, tools, smoke variant, session context) |
| `generated/` | Built prompts. Do not edit; rebuild |
| `scripts/fill-prompt.py` | Fills session variables, for pasting into the dashboard |
| `smoke/` | Variables for the smoke-test session. `smoke/out/` is gitignored |
| `agora_voice/` | The `agora-voice` CLI: session context, event log, reconcile, render, ingest |
| `tests/` | Offline tests, with a fixture session and golden output in `tests/fixtures/` |

## Install

The `agora-voice` CLI needs Python 3.10 or later.

```bash
cd surfaces/voice
pip install -e ".[dev]"
pytest -q
```

Try the offline ingest on the fixture session, against a scratch copy of the template learner repo:

```bash
cp -r ../../templates/learner-repo /tmp/my-reading
mkdir -p /tmp/my-reading/sources/ai-future-is-now
cp ../../examples/ai-future-is-now/spine.yaml /tmp/my-reading/sources/ai-future-is-now/
agora-voice ingest --from-fixture tests/fixtures/ch09-session --learner-repo /tmp/my-reading
```

Commands that call ElevenLabs read the API key from `ELEVENLABS_API_KEY`; it is never written to a file. Per-learner settings, such as the agent id, live in `.agora/voice.toml` in the learner repo. Add `.agora/voice-sessions/` to the learner repo's `.gitignore`: event logs are scratch, not records.

## Run a session

Set up the agents once (safe to re-run; it writes their ids to `.agora/voice.toml`):

```bash
agora-voice setup --learner-repo ~/my-reading
```

**By voice**, on ElevenLabs' talk page in your browser:

```bash
agora-voice talk --web --learner-repo ~/my-reading --unit transformation
```

This opens the page with the session filled in. Allow the microphone and press call. At the synthesis step, type into the page's text box. When you've ended the call, press Enter in the terminal: the conversation is fetched and draft records are written into your learner repo. Review them with `git diff`, then commit. If you skip that step, run `agora-voice ingest` later.

**By typing**, in the terminal (records are captured live by the agent's tools):

```bash
agora-voice talk --text --learner-repo ~/my-reading --unit transformation
```

Type to reply; `/quit` ends the session, and the drafts are written straight after.

To change the model, edit `llm` or `backup_llm` in `.agora/voice.toml` and run `setup` again. After editing anything in `agent/` or `method/`, run `scripts/build-surfaces.sh` first, since `setup` refuses a stale prompt. The unit you talk about needs an unused prepared hook in its spine.
