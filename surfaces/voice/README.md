# Voice (ElevenLabs)

Spoken Agora sessions, built on ElevenLabs' voice agents (ElevenAgents) with hosted Claude.

- [`DESIGN.md`](DESIGN.md): low-level design (option 1, a local CLI)
- [`PLAN.md`](PLAN.md): phased implementation plan
- [`SMOKE-TEST.md`](SMOKE-TEST.md): **start here.** Phase 0, a hand-run spoken session with no code

**Status:** Phase 0 is done: the smoke test passed (results in [`SMOKE-TEST.md`](SMOKE-TEST.md#results)). Phase 1, the offline core, is built: `agora-voice ingest --from-fixture` renders draft records from a saved session.

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
