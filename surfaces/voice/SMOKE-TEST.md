# Voice smoke test (Phase 0)

One real spoken session, set up by hand in the ElevenLabs dashboard, with no Agora code involved. It answers the only question that matters before building anything: **is a spoken Agora session any good?**

You need an ElevenLabs account, Python 3, and about an hour: 15 minutes of setup, a 25-minute session, and 10 minutes for notes. Use headphones so the agent doesn't hear itself.

## 1. Build and fill the prompt

```bash
./scripts/build-surfaces.sh
```

Open `surfaces/voice/smoke/transformation.vars.json` and replace the `EDIT ME` text in `learner_context` with a sentence or two about your role and what you want from the book. Then:

```bash
python3 surfaces/voice/scripts/fill-prompt.py \
  surfaces/voice/generated/agent-prompt.smoke.md \
  surfaces/voice/smoke/transformation.vars.json \
  --out surfaces/voice/smoke/out
```

This writes `smoke/out/system-prompt.md` and `smoke/out/first-message.txt`. The `out/` folder is gitignored, since it contains your learner context.

The session is the "Why AI transformations fail" unit, opening with the "40% faster contract review" hook. It's a unit we haven't discussed yet, so the test isn't contaminated by our earlier conversation.

## 2. Create the agent

Agents live in the ElevenAgents product, not ElevenCreative: switch products from the sidebar, or go to https://elevenlabs.io/app/agents. Create a new blank agent. Setting names below may differ slightly in the current UI.

| Setting | Value |
|---|---|
| Name | Agora (smoke) |
| System prompt | Paste all of `smoke/out/system-prompt.md`, the filled copy. If you paste `generated/agent-prompt.smoke.md` instead, every `{{variable}}` arrives blank unless it has a placeholder value in the agent's dynamic-variables settings, and the agent says the session details didn't load |
| First message | Paste `first-message.txt` |
| LLM | A Claude Sonnet-class model, lowest reasoning effort |
| Language | English |
| Voice | Anything calm and conversational |
| Text normalization | ElevenLabs' normalizer, if offered (so numbers are spoken correctly) |
| Max conversation duration | 40 minutes (2400 seconds). The default is 10 minutes, which cuts a 25-minute session off mid-discussion |
| Silence / turn timeout | As long as allowed, since writing the synthesis takes a minute of silence |
| Conversation retention | Short; this transcript is your thinking |

Then **save** the agent. The talk page and the API use the saved agent, not an unsaved draft.

Don't edit the prompt in the dashboard. If something needs changing, change `surfaces/voice/agent/` or `method/` in the repo, rebuild, re-fill and re-paste, so fixes don't get lost in the dashboard.

## 3. Run the session

Start a conversation from the agent's test button or its talk-to page. Do the session for real: commit to an answer on the hook, argue, and write your synthesis on paper or in a notes app when asked, then read it out.

Watch for:
- **Read-back.** Does it repeat your commitment and wait for a yes before revealing anything?
- **The hook.** Does it deliver the hook as written, without hinting at the theme?
- **Turn length.** Mostly one to three sentences? Any monologues?
- **Leaks.** Does it ever recite the unit brief?
- **Converge.** Does it reach a conclusion after about six exchanges, or keep asking questions?
- **Honesty.** When it doesn't know a fact, does it say so instead of inventing one?
- **Latency.** Are pauses before its replies noticeable? The prompt is about 3,800 tokens, roughly twice ElevenLabs' guideline.
- **Hearing.** Does it mishear you, especially names or numbers?

## 4. Write it up

Copy this into `surfaces/voice/smoke/NOTES.md`, fill it in, and commit it.

```markdown
# Smoke test notes — <date>

Model: <name>   Voice: <name>   Duration: <minutes>

Overall, compared with a good text session: worse / same / better
Would I do a second voice session by choice? yes / no

| Check | Result | Notes |
|---|---|---|
| Hook delivered as written | ✓ / ✗ | |
| Read-back before reveal | ✓ / ✗ | |
| Short turns | ✓ / ✗ | |
| No brief leaks | ✓ / ✗ | |
| Converged with a conclusion | ✓ / ✗ | |
| Honest about unknowns | ✓ / ✗ | |
| Latency acceptable | ✓ / ✗ | |
| Speech recognition accurate | ✓ / ✗ | |

The best moment:
The worst moment:
What I'd change first:
```

## 5. Decide

- **Continue to Phase 1** if the session was at least close to a good text session, and the problems look fixable through the prompt (wording, turn length, timing).
- **Iterate on Phase 0** if the problems are in the prompt itself. Change the files in `surfaces/voice/agent/`, rebuild, and run another session.
- **Stop** if spoken discussion is clearly worse in a way no prompt change can fix: it's too shallow, too slow, or too awkward to think aloud. In that case, voice waits until there's a different design.

If latency is the main problem, the first thing to try is trimming the prompt. The candidates are the session intro paragraph and the moves table, either shortened or moved into the unit brief.

## Results

**2026-10-20, ch. 9.** This run used the first Phase 0 prompt (from the `phase-0-voice-prompt` branch, since merged): the whole method including `hooks.md`, with the prepared "two tasks" hook and the other session details passed as nine variables. Claude Sonnet 5.5, reasoning effort low, ElevenAgents dashboard.
- **Hook:** landed, and led into a real debrief. The partner split "how hard for AI" from "who answers when it goes wrong", which is the tension the hook was built on.
- **Discussion:** under way when the call ended. It stopped at exactly 600 seconds: the agent's default maximum conversation duration, not a token limit. Hence the 40-minute setting above.
- **Friction:** setting up the agent by hand (prompt, variables, model, fillers, saving) was the most inconvenient part.
- **Decision:** continue to Phase 1. Nothing so far suggests voice is worse than text in a way prompt changes can't fix.
