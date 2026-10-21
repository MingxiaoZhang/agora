# Voice surface — implementation plan

Implements option 1 from [`DESIGN.md`](DESIGN.md) in five phases. Each phase ends with something usable, and a decision about whether to continue.

The order tests the riskiest assumption first: that the method works by voice at all. Code that needs an ElevenLabs account comes after that answer.

| Phase | Deliverable | Needs ElevenLabs | Size |
|---|---|---|---|
| 0 | Voice prompt + a no-code smoke test | Yes (dashboard only) | ~1 evening |
| 1 | Offline core: context, render, reconcile, with tests | No | ~2–3 evenings |
| 2 | `setup` + text-only dry runs | Yes | ~1–2 evenings |
| 3 | `talk` + `ingest` end to end, by voice | Yes | ~2–3 evenings |
| 4 | Three-session trial and a go/no-go on option 2 | Yes | ~1–2 weeks of use |

Sizes are rough, for one person working in spare time.

---

## Phase 0 — Voice prompt and smoke test

**Status:** done. The smoke test passed; see the results in [`SMOKE-TEST.md`](SMOKE-TEST.md#results).

**Why first:** before writing any CLI code, find out whether a spoken session with this method is any good.

**Deliverables**
- `method/session.md`: new "Spoken sessions" subsection (read back commitments, short turns, typed synthesis, honest research deferral).
- `surfaces/voice/agent/voice-header.md`: voice framing plus the session context block with dynamic variables.
- `scripts/build-surfaces.sh`: new target producing `surfaces/voice/generated/agent-prompt.md`.
- `surfaces/voice/SMOKE-TEST.md`: how to paste the prompt into a dashboard agent and start a session from the hosted talk page, passing context with `var_` URL parameters.

**Done when**
- The generated prompt builds cleanly and reads well aloud. Check by having the agent say its first two turns.
- One manual voice session on 《AI未来已来》 ch. 9 runs end to end.
- You've written down three or four notes: did the hook land, did read-back feel natural, did it converge, what grated.

**Decision:** if the spoken session is clearly worse than text in a way prompt changes can't fix, stop here, and voice waits for option 2 or a different design. Otherwise continue.

**Not included:** tools, records, any Python. The smoke test produces no records.

---

## Phase 1 — Offline core

**Why now:** the parts that touch your records carry the most risk to your data, and they can be built and tested without any account.

**Deliverables**
- Package skeleton: `surfaces/voice/agora_voice/` with `cli.py`, `config.py`, a `pyproject.toml`, and a README install section.
- `context.py`: learner repo → dynamic variables, matching `smoke/transformation.vars.json`. Implements unit selection, prepared-hook selection, the size limits, and whole-item truncation.
- `render.py`: event log + transcript → session note and record drafts, following `formats/`.
- `reconcile.py`: fuzzy check of `learner_quote` against user turns, the data-collection fallback, and `# REVIEW:` markers.
- `EventLog`: append-and-flush JSONL writer and reader.
- Fixtures: the example spine (which has prepared hooks), the template learner repo, and a hand-made transcript plus event log covering exact quotes, paraphrased quotes, a missing tool call, and a post-call synthesis.
- Tests with `pytest`, plus a GitHub Actions workflow running them on push.
- A CLI command that works offline: `agora-voice ingest --from-fixture <dir>` renders drafts from fixtures. It's useful for demos and debugging.

**Done when**
- All tests pass in CI.
- `context.py` on the example spine reproduces the hand-written smoke-test variables, apart from `learner_context`.
- Running `ingest --from-fixture` on the example produces a session note that matches `formats/session-note.md` and flags the paraphrased quote.
- Rendered records diff cleanly against a learner repo: no reformatting of untouched entries, and history is appended, never overwritten.

---

## Phase 2 — Provisioning and text dry runs

**Deliverables**
- `agent/agent.template.json`, `agent/tools.json` (7 client tools), and `agent/data-collection.json` (9 fields).
- `provision.py` + `agora-voice setup`: creates or updates the tools and the agent idempotently and writes ids to `.agora/voice.toml`. It refuses to run on a stale generated prompt.
- `agora-voice talk --text`: the same session flow in text-only mode through the SDK, with tool handlers active. `request_synthesis` reads from the terminal.

**Done when**
- Running `setup` twice in a row changes nothing the second time.
- A text dry run on ch. 9 calls `record_hook`, `record_commitment` (after read-back), `record_converge` and `request_synthesis`, in the right order, and the event log has them.
- Open questions 1, 3 and 4 from the design (model ids, the tools endpoint, the data-collection result shape) are answered in `DESIGN.md`.

**Decision:** pick the model. Run the same dry run on two candidate Claude models and choose by turn latency and how well each follows the method.

---

## Phase 3 — Voice end to end

**Deliverables**
- `talk.py` with audio: `DefaultAudioInterface`, a live transcript in the terminal, clean Ctrl+C, and the conversation id captured.
- `request_synthesis` in voice, with the post-call fallback if the call drops.
- `ingest.py` against the live API: polls until processing is done, reconciles, writes drafts, and prints the summary (counts, items to review, research queued, duration).
- `talk` runs `ingest` automatically. `ingest <conversation_id>` re-runs work standalone.
- A README walkthrough from install to first session.

**Done when**
- A full voice session on ch. 9 produces a session note, position updates and an open question in the learner repo, all reviewable with `git diff`.
- Killing the call midway still leaves a usable partial note.
- Open questions 2 and 5 (tool timeout and silence while typing, mixed-language STT) are answered in `DESIGN.md`, with the fallback tuned if needed.

---

## Phase 4 — Trial and decision

**Deliverables**
- Three real voice sessions on 《AI未来已来》 (ch. 9 continued plus two more units), committed to your learner repo.
- A voice eval case for read-back before reveal in `evals/`, plus hand-scored runs of the hooks, sycophancy and convergence suites by voice.
- `surfaces/voice/TRIAL.md`: what worked, what didn't, the numbers below, and the decision.

**Measure**
- Your rating of each session against a comparable text session (worse / same / better).
- Share of recorded items you had to correct in review (target: under 20%).
- How often `request_synthesis` worked in-call versus fell back.
- Median turn latency, if it's noticeable.

**Decision:** one of the following.
- **Go to option 2** (web app): voice is at least as good as text, and the friction is in the terminal, the laptop-only setup or the review step.
- **Iterate on option 1:** the method needs voice-specific changes first.
- **Park voice:** spoken sessions are consistently worse.

---

## Working conventions

- Work happens on feature branches with one pull request per phase. `main` always has a working state.
- `method/` changes land in their own commit, and every surface is regenerated with `build-surfaces.sh` in the same pull request.
- No secrets in either repo. `ELEVENLABS_API_KEY` lives only in the environment.
- When a phase answers one of the design's open questions, update `DESIGN.md` in that phase's pull request.
