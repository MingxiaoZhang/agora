# Voice surface (ElevenLabs) — low-level design, option 1

**Goal:** run Agora sessions as spoken conversation, with as little software as possible, to answer one question: does the method still work by voice? Everything here is disposable if the answer is no.

**Scope:** a local CLI. No web app, no hosted server, no webhooks. The learner talks through their laptop's mic and speakers, and the CLI turns each call into records in their learner repo.

## 1. Overview

```
 learner repo ──► agora-voice talk ──► ElevenLabs agent (STT → Claude → TTS)
 (spine, positions,   │   dynamic variables         │
  open questions)     │                             │ client tool calls
                      │◄────────────────────────────┘ (commitments, ideas, synthesis…)
                      │ writes events.jsonl locally
                      ▼
               agora-voice ingest ──► GET conversation (transcript + data collection)
                      │
                      ▼
          draft session note + record changes in learner repo  ──► learner reviews (git diff)
```

Three commands:

| Command | Does |
|---|---|
| `agora-voice setup` | Creates or updates the ElevenLabs agent and its tools from config in this repo. Idempotent. |
| `agora-voice talk` | Builds session context from the learner repo, runs the call with mic/speaker, logs tool events. |
| `agora-voice ingest` | Fetches the finished conversation, reconciles it with the local event log, and writes draft records. |

`talk` runs `ingest` automatically when the call ends; `ingest` also works standalone for re-runs.

## 2. Platform pieces used

All from ElevenAgents. Field names below are from the API reference as of 2026-10; verify against current docs when implementing.

| Need | ElevenLabs feature |
|---|---|
| Voice loop | Agent: STT + LLM + TTS + turn-taking |
| Model | Natively hosted Claude (Sonnet- or Haiku-class for latency; low `reasoning_effort`) |
| Method | Agent system prompt: `conversation_config.agent.prompt.prompt` |
| Per-session context | Dynamic variables: `{{name}}` in prompt / first message, passed via `ConversationInitiationData(dynamic_variables=...)` |
| Structured capture during the call | Client tools (`type: client`), handled in the local Python process |
| Ending the call | System tool `end_call` |
| Post-call extraction (fallback) | `platform_settings.data_collection` fields (map of id → `{type, description}`) |
| Fetching results | `GET /v1/convai/conversations/{conversation_id}` |
| Local audio | Python SDK `Conversation` + `DefaultAudioInterface` (`elevenlabs[pyaudio]`) |

Not used in option 1: overrides (dynamic variables cover it and need no security toggles), knowledge base/RAG, webhooks, custom LLM.

## 3. Package layout

```
surfaces/voice/
├── DESIGN.md                 # this file
├── README.md
├── agent/
│   ├── agent.template.json   # agent config, minus prompt and tool ids
│   ├── tools.json            # client tool definitions
│   ├── data-collection.json  # post-call extraction fields
│   ├── voice-header.md       # hand-written: personality, tone, goal, guardrails
│   ├── voice-tools.md        # hand-written: when to call each client tool (CLI)
│   ├── voice-smoke.md        # hand-written: no-tools variant (Phase 0 smoke test)
│   └── session-context.md    # hand-written: the {{variables}} block
├── generated/
│   ├── agent-prompt.md       # built: header + tools + method + context
│   └── agent-prompt.smoke.md # built: header + smoke + method + context
├── scripts/
│   └── fill-prompt.py        # fills variables for pasting into the dashboard
├── smoke/
│   └── transformation.vars.json  # Phase 0 session variables
└── agora_voice/              # Python package
    ├── cli.py                # argparse entry: setup | talk | ingest
    ├── config.py             # env + .agora/voice.toml
    ├── provision.py          # create/update tools and agent
    ├── context.py            # learner repo → dynamic variables
    ├── tools.py              # client tool handlers + event log
    ├── talk.py               # run the conversation
    ├── ingest.py             # fetch, reconcile, write drafts
    ├── reconcile.py          # verbatim checks against the transcript
    └── render.py             # session note + record diffs (formats/)
```

Dependencies: `elevenlabs[pyaudio]`, `pyyaml`. Python 3.11+. On Linux, `portaudio19-dev`; on macOS, `brew install portaudio`.

## 4. Configuration

**Secrets:** `ELEVENLABS_API_KEY` in the environment only. Never written to either repo.

**Learner repo:** `.agora/voice.toml` (committed in the learner's private repo, no secrets):

```toml
agent_id = "agent_..."          # written by setup
voice_id = "..."                # chosen by the learner
llm = "<claude model id from the ElevenLabs model list>"
reasoning_effort = "low"
language = "en"                 # discussion language
save_transcripts = false        # if true, ingest keeps a transcript next to the session note
max_duration_seconds = 2400    # 40 min; the platform default of 600 cuts sessions short

[tool_ids]                      # written by setup
record_commitment = "tool_..."
# ...
```

## 5. Agent provisioning (`setup`)

1. Load `tools.json`. For each tool, create it via the tools API if `tool_ids` lacks it, otherwise update it. Store ids.
2. Load `generated/agent-prompt.md`. Fail if it's stale (older than any file in `method/`); tell the user to run `build-surfaces.sh`.
3. Merge `agent.template.json` with prompt, `llm`, `reasoning_effort`, `voice_id`, `language`, `tool_ids`, `max_duration_seconds`, and `data-collection.json`.
4. If `agent_id` is set, update the agent; otherwise create it and write `agent_id`.
5. Print the agent id and a reminder to set the conversation retention period in the dashboard.

`agent.template.json` essentials:

```json
{
  "name": "Agora",
  "conversation_config": {
    "agent": {
      "first_message": "{{opening_line}}",
      "prompt": { "temperature": 0.6 }
    },
    "conversation": { "max_duration_seconds": 2400 }
  }
}
```

The agent prompt is the same method text every other surface uses. Session specifics arrive only through dynamic variables, so one agent serves every source and session.

## 6. Prompt

`build-surfaces.sh` builds two variants:

```
generated/agent-prompt.md       = voice-header + voice-tools + method + session-context
generated/agent-prompt.smoke.md = voice-header + voice-smoke + method + session-context
method = method/session.md + method/discussion.md, minus "## Agenda extraction",
         with cross-file "(see `x.md`)" pointers removed, headings nested under "# The method"
```

**Prompt budget.** ElevenLabs recommends staying under about 2,000 tokens, since longer prompts add latency. The method alone is about 3,200 tokens, so two things are omitted from the voice prompt, without changing any method text:
- **`method/hooks.md`.** Hooks are prepared ahead of time, pass the quality bar outside the call, and arrive as variables (section 7). This also improves hook quality, since checking three candidates live is too slow for voice.
- **Agenda extraction.** The agenda arrives already extracted, as `unit_brief`.

Measured in Phase 0: about 3,300 tokens for the smoke prompt before variables, and about 3,800 filled. Whether that latency is acceptable is a Phase 0 question. If it isn't, the next cuts are the session intro paragraph and the moves table.

Formats are **not** in the prompt; the agent never writes records. It calls tools, and the CLI writes records.

**Hand-written pieces** (only what's specific to this surface), following ElevenLabs' prompting guide (Personality / Environment / Tone / Goal / Guardrails / Tools sections, critical rules repeated with "This step is important"):
- `voice-header.md`: spoken style, no markdown, numbers in words; the hook is prepared, so deliver it as given; read back before reveal; no web access, so defer research honestly; the read step means either skip or end the call and come back; guardrails (never read the brief aloud, never invent facts, converge after about six exchanges).
- `voice-tools.md`: when to call each client tool (section 8), and what to do if one fails.
- `voice-smoke.md`: no tools; the learner jots down research questions and writes the synthesis on paper, then reads it out.
- `session-context.md`: the variable block, ending with the private unit brief.

The first message is `{{opening_line}}`, set on the agent, not in the prompt.

## 7. Session context (`context.py`)

Input: learner repo path, `--source <slug>`, optional `--unit <id>` (default: first unit with `status: in-progress`, else first `not-started`), optional `--minutes`.

Dynamic variables (all strings; values must be strings, numbers, or booleans):

| Variable | Built from | Limit |
|---|---|---|
| `source_spoken_name` | `spine.yaml: source.spoken_name` (new optional field), else author + kind, e.g. "Kai-Fu Lee's book". TTS can't pronounce every title, especially in other scripts | — |
| `source_author`, `source_published` | `spine.yaml: source` | — |
| `source_author_context` | `spine.yaml: source.author_context` | ~100 words |
| `unit_title` | selected unit | — |
| `unit_brief` | unit `claims`, `general_ideas`, `checkable`, `weaknesses`, rendered as compact prose, ending with a note that it's paraphrased if the spine says so | ~500 words |
| `hook_format`, `hook_headline`, `hook_activity`, `hook_debrief_angle` | first prepared hook on the unit with no `used` date | — |
| `learner_context` | `learner/context.md` | ~200 words |
| `recent_positions` | up to 5 positions whose `origin.source` matches, or that are most recent overall; `topic: current` | ~300 words |
| `open_question` | newest line in `learner/open-questions.md`, or "" | 1 line |
| `session_minutes` | flag or 25 | — |
| `opening_line` | resume question if `open_question` is set, else a one-line greeting naming the unit | 1 sentence |

**Hook selection.** Pick the first unused prepared hook whose format isn't among the last three in `learner/signals.yaml`, falling back to any unused hook. If the unit has none, stop with a message: prepare hooks first, in another surface (e.g. the Claude skill: "prepare two hooks for unit X") or by hand. `ingest` sets `used` on the hook afterwards.

Truncate by dropping whole items, never mid-sentence. Log the final variable sizes in verbose mode. Never include `secret__` variables; none are needed.

## 8. Client tools (`tools.py`)

Every tool appends one JSON line to the session's event log and returns a small acknowledgement. The event log is the primary source of truth for structured data; post-call data collection is the fallback.

**Faithfulness rule:** every tool that records something the learner said takes a `learner_quote` parameter: the learner's own words, as close to verbatim as the agent can manage. `reconcile.py` checks it against the transcript (section 10).

| Tool | Parameters | `expects_response` | Agent calls it when |
|---|---|---|---|
| `record_hook` | `format`, `headline`, `rejected` (string, optional) | false | after presenting the hook |
| `record_commitment` | `kind` (bet / choice / ranking / position), `summary`, `learner_quote`, `confidence` (number, optional) | true → `{"ok": true}` | after the learner commits **and has confirmed the read-back**, before any reveal |
| `record_position` | `topic`, `view`, `why`, `learner_quote`, `change` (new / moved / hardened) | false | when the learner states or changes a position |
| `propose_idea` | `title`, `statement`, `learner_quote` | false | after the learner agrees an idea is theirs and worth keeping |
| `queue_research` | `question`, `why_it_matters` | false | when a fact or consensus question can't be answered reliably |
| `record_converge` | `core_idea`, `conclusion`, `open_questions` | false | at the converge step |
| `request_synthesis` | `prompt` | true, `response_timeout_secs` large | at the synthesize step |

**`request_synthesis`** keeps the written-synthesis rule without a UI. The handler prints the prompt in the terminal and blocks on `input()` (multi-line, ended by an empty line). It returns `{"synthesis": "<typed text>"}` to the agent, which then critiques it aloud, per the method. The typed text also goes into the event log verbatim.
*Risk:* the platform may time out a tool response or end an idle call while the learner types. Mitigation: set the largest allowed `response_timeout_secs`. If the call drops anyway, `talk` notices the session ended without a `synthesis` event and asks for it in the terminal before running `ingest`. In that case the critique is skipped and noted.

**Event log:** `<learner-repo>/.agora/voice-sessions/<local-session-id>.jsonl`, one object per line:

```json
{"t": "2026-10-18T06:42:10Z", "tool": "record_commitment", "params": {...}, "conversation_id": null}
```

`conversation_id` is filled in when known. Writes are append-and-flush, so a crash mid-call loses nothing already logged. The `.agora/voice-sessions/` folder should be gitignored in the learner repo; it is scratch, not records.

## 9. The call (`talk.py`)

```
1. cfg = load_config(); vars = build_context(...)
2. log = EventLog.new()
3. tools = ClientTools(); register each handler, bound to log
4. conv = Conversation(client, cfg.agent_id, requires_auth=True,
         audio_interface=DefaultAudioInterface(), client_tools=tools,
         config=ConversationInitiationData(dynamic_variables=vars),
         callback_agent_response=print_agent, callback_user_transcript=print_user)
5. SIGINT → conv.end_session()
6. conv.start_session(user_id=<stable hash of learner repo path>)
7. conversation_id = conv.wait_for_session_end(); log.set_conversation_id(...)
8. if no synthesis event: prompt in terminal, log it with source="post-call"
9. run ingest(conversation_id, log)
```

The terminal shows a live transcript (both sides), so the learner can see what the system heard. Mis-hearings show up in the moment.

## 10. Ingest and reconcile (`ingest.py`, `reconcile.py`, `render.py`)

**Fetch:** `GET /v1/convai/conversations/{id}`. Poll every 5 s while `status` is `processing`, giving up after 2 minutes. Use `transcript`, `analysis` (data collection results), and `metadata` (duration, cost).

**Reconcile:**
1. **Verbatim check.** For each `learner_quote`, fuzzy-match it (normalized, token-set ratio) against user turns in the transcript. At or above the threshold (start at 0.8; tune), mark `verified`. Below it, mark `unverified` and attach the closest user turn, so the learner can fix it.
2. **Fallback fill.** For each record type with no tool event, use the matching data-collection field if it's non-empty. Mark it `source: post-call-extraction` and always `unverified`.
3. **Synthesis.** Always the typed text from the event log. Never extracted.

**Render (into the learner repo, as drafts):**
- `sources/<slug>/sessions/<date>.md` per `formats/session-note.md`. Sections come from tool events. Research items from `queue_research` go under "Discussion → research to do". The surface is `voice-elevenlabs`.
- `learner/positions.yaml`: new entries, or a new `history` item on a matching `topic`, matched by exact topic, else appended as new.
- `learner/bets.yaml`: commitments with `kind: bet`.
- `ideas/idea-NNNN.md`: one per `propose_idea`, `status: draft`.
- `learner/open-questions.md`: prepend from `record_converge.open_questions`.
- `learner/signals.yaml`: one entry. `hints_used` and `answer_requested_before_attempt` come from data collection; `synthesis_written` and `converged` come from events.
- Optional `<date>.transcript.md` if `save_transcripts = true`.

Every rendered item that is `unverified` gets an inline `# REVIEW:` comment. Ingest never commits. It prints a summary: counts, unverified items, research queued, and call cost. The learner reviews with `git diff` and commits.

**Data-collection fields** (`data-collection.json`, fallback and signals only):

| id | type | description (abridged) |
|---|---|---|
| `hook_format` | string | Hook format used, from the method's list |
| `hook_headline` | string | Headline as spoken |
| `commitment` | string | What the learner committed to, in their words |
| `core_idea` | string | Core idea stated at converge |
| `conclusion` | string | Provisional conclusion |
| `open_questions` | string | Open questions, separated by " | " |
| `hints_used` | integer | Number of hints the agent gave |
| `answer_requested_before_attempt` | integer | Times the learner asked for the answer before trying |
| `converged` | boolean | Whether the agent stated a core idea and conclusion |

## 11. Method changes (in `method/`, not here)

Per the surface rule, these go into `method/session.md` as a "Spoken sessions" subsection, since they'd apply to any voice surface:
1. **Read back commitments.** Repeat the learner's bet or choice and get a yes before revealing anything.
2. **Short turns.** One to three sentences. The converge step may run longer but stays under about 45 seconds of speech.
3. **Synthesis is always typed,** even in a spoken session.
4. **No live research? Defer honestly.** Name the uncertainty, queue the question, and continue.

## 12. Failure modes

| Failure | Handling |
|---|---|
| Agent forgets to call a tool | Data-collection fallback, marked `unverified` |
| Agent paraphrases the learner in a tool call | Verbatim check flags it with the closest real turn |
| STT mishears | Live transcript in the terminal; read-back before reveal; review step |
| Call drops mid-session | Event log already flushed; `ingest` works on partial calls; synthesis asked post-call |
| Analysis not ready | Poll, then exit with a "re-run `agora-voice ingest <id>`" message |
| Mixed-language speech (e.g. Chinese source terms in English discussion) | `language` setting; check STT accuracy in the first trial; if poor, keep source terms out of spoken hooks |
| Runaway cost | `max_duration_seconds`; cost printed after each call |
| Privacy | Retention set in the dashboard; transcripts not saved locally unless opted in; API key only in env |

## 13. Testing

- **Unit tests** (no network): `context.py` on the example spine and template learner repo; `reconcile.py` on a fixture transcript plus event log, covering exact quotes, paraphrased quotes, and missing tool calls; `render.py` output checked against `formats/` with golden files.
- **Text-only dry runs:** text-only mode exists as an override, so a `talk --text` flag can run the same agent in text to iterate on the prompt cheaply. That needs the text-only override enabled in the agent's security settings.
- **Evals:** run `evals/hooks`, `evals/sycophancy`, and `evals/convergence` by voice for the first few sessions, scoring by hand. Add a voice-specific eval for read-back before reveal.
- **Trial:** three real sessions on 《AI未来已来》. Success means the learner rates at least two as being as good as the text sessions, and fewer than 20% of recorded items need correcting in review.

## 14. Open questions to settle while building

1. Exact Claude model ids in the ElevenLabs model list, and which gives acceptable turn latency. *Phase 0:* Claude Sonnet 5.5 (`claude-sonnet-5-5`) at low reasoning effort worked in the smoke test, with no latency complaints. Phase 2 still compares two models.
2. Maximum `response_timeout_secs` for client tools, and whether silence while typing ends the call (affects `request_synthesis`).
3. Whether tools are created via a separate tools endpoint and referenced by `tool_ids` (the agent schema marks inline `tools` as deprecated).
4. Data-collection result shape in the conversation response (value plus rationale).
5. STT quality for mixed English and Chinese terms.

## 15. Build order

1. `context.py` + `render.py` + `reconcile.py` with fixtures (no ElevenLabs needed).
2. Done in Phase 0: voice prompt pieces, `build-surfaces.sh` target, method "Spoken sessions" subsection, prepared hooks.
3. `provision.py`, then a text-only dry run.
4. `talk.py` with audio, then the first real session.
5. Tune from the trial: prompt, thresholds, tool timing.
