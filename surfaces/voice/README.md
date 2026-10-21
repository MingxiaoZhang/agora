# Voice (ElevenLabs)

Spoken Agora sessions, built on ElevenLabs' voice agents (ElevenAgents) with hosted Claude.

- [`DESIGN.md`](DESIGN.md): low-level design (option 1, a local CLI)
- [`PLAN.md`](PLAN.md): phased implementation plan
- [`SMOKE-TEST.md`](SMOKE-TEST.md): **start here.** Phase 0, a hand-run spoken session with no code

**Status:** Phase 0 is done: the smoke test passed (results in [`SMOKE-TEST.md`](SMOKE-TEST.md#results)). Phase 1, the offline core, is in progress.

Rules that apply to any spoken session live in `method/session.md` under "Spoken sessions", not here. This folder holds only what's specific to ElevenLabs.

| Path | What |
|---|---|
| `agent/` | Hand-written prompt pieces (header, tools, smoke variant, session context) |
| `generated/` | Built prompts. Do not edit; rebuild |
| `scripts/fill-prompt.py` | Fills session variables, for pasting into the dashboard |
| `smoke/` | Variables for the smoke-test session. `smoke/out/` is gitignored |
