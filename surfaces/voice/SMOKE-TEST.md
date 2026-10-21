# Voice smoke test (Phase 0)

A no-code check of whether an Agora session works by voice at all, before any CLI exists. You paste the generated prompt into an ElevenLabs agent in the dashboard and talk to it from the hosted talk page. Nothing is recorded to your learner repo; the output is your notes.

## 1. Build the prompt

```bash
./scripts/build-surfaces.sh
```

This writes `surfaces/voice/generated/agent-prompt.md` (voice header + `method/`). Don't edit it by hand; change `surfaces/voice/agent/voice-header.md` or `method/` and rebuild.

## 2. Create the agent

Agents live in the ElevenAgents product, not ElevenCreative. Switch products from the sidebar, or go to https://elevenlabs.io/app/agents. Create a blank agent, then:

1. **System prompt:** paste the whole of `agent-prompt.md`.
2. **First message:** leave it empty, so the agent waits for you and its opening comes from the prompt. To start, say "Let's begin."
3. **LLM:** pick a Claude model. Note which one; Phase 2 compares two.
4. **Language:** set the main language you'll speak. If you'll mix Chinese and English, add both and note how transcription copes (this is open question 5).
5. **Dynamic variables:** the prompt uses nine. Each needs a placeholder value in the agent's dynamic-variables settings, or the agent sees blanks and says the session details didn't load. Fill them with the ch. 9 values below; they act as defaults, so the long ones never need to go in a URL. Simpler for a one-off test: substitute the values into the prompt text before pasting, and skip variables entirely.
6. **Text input:** if the widget settings offer text input, turn it on. That's how you type the synthesis.
7. **Save.** The talk page and the API use the saved agent, not an unsaved draft.

No tools, knowledge base or data collection. Those come in Phase 2.

### Ch. 9 values

| Variable | Value |
|---|---|
| `source_title` | AI未来已来：CEO、组织、个人的时代红利 |
| `source_author` | 李开复 (Kai-Fu Lee) |
| `unit_title` | Two maps: is my job still safe? / Three directions |
| `unit_location` | Chapter 9 |
| `session_minutes` | 25 |
| `learner_context` | Nothing shared yet. |
| `resume` | First session on this source. |
| `unit_brief` | see below |
| `hook` | see below |

`unit_brief` (from `examples/ai-future-is-now/spine.yaml`):

```text
Claims: (1) Work can be placed on two axes: whether it has a standard right answer, and whether its value depends on a particular person being present and answerable. Contestable: neither axis is measurable. (2) Knowledge work turned out more automatable, and hands-on work less, than people expected a decade ago. Contestable: depends on which tasks and how far ahead. (3) Value gathers where someone must answer for the outcome when things go wrong. Contestable: assumes organizations pay a premium for accountability.
General ideas: Which kinds of work does AI take over first, and why does that differ from intuitions about difficulty? Who is accountable when work is automated? When a human stays in the loop only to sign off, are they judging or absorbing blame?
Weaknesses: the map is a snapshot and an earlier version was wrong; "move toward accountability" assumes orgs reward it; if everyone moves to the same scarce roles the premium may vanish.
Built from a distilled summary, not the full text.
```

`hook` (from `examples/ai-future-is-now/hooks.md`, hook 1):

```text
Headline: "The safest part of your job probably isn't the part you think." Activity: pick the two tasks from your week you'd most hate to lose. For each, give the percent chance AI does it as well as you within 3 years, and say whether it needs you in particular, and why. Debrief toward: were you weighing how hard the task is for AI, or what happens when it goes wrong?
```

## 3. Check the first two turns

Before a full session, start a call, say "Let's begin," and listen to two turns. Check that:

- It doesn't read out markdown, headings or lists.
- Turns are short and end on one question.
- It presents the hook without naming the theme or the answer.

If not, fix `voice-header.md`, rebuild, and paste again.

## 4. Run the session

Open the agent's shareable talk page. To override any variable for a run, add it to the URL with a `var_` prefix, URL-encoded:

```text
https://elevenlabs.io/app/talk-to?agent_id=<AGENT_ID>&var_session_minutes=10&var_learner_context=Product%20manager
```

Any variable you leave out uses its dashboard placeholder. Then run the session end to end: hook, debrief, (skip or do) read, discuss, converge, typed synthesis, spoken close.

## 5. Write your notes

Three or four lines are enough. Keep them for the Phase 0 decision in `PLAN.md`.

- **Hook:** did it land? Did committing out loud feel like a commitment?
- **Read-back:** did it repeat your commitment before revealing? Natural or robotic?
- **Convergence:** did it arrive somewhere, or circle?
- **What grated:** latency, interruptions, turn length, language switching, anything else.
- Model used, session length, and whether typed synthesis worked.

**Decision:** if voice is clearly worse than text in a way prompt changes can't fix, stop and record why. Otherwise go on to Phase 1.

## Results

**2026-10-20, ch. 9.** Claude Sonnet 5.5, reasoning effort low, ElevenAgents dashboard.
- **Hook:** landed, and led into a real debrief. The partner split "how hard for AI" from "who answers when it goes wrong", which is the tension the hook was built on.
- **Discussion:** under way when the call ended. It stopped at exactly 600 seconds: the agent's default maximum conversation duration (10 minutes), not a token limit. A 25-minute session needs this raised to about 40 minutes.
- **Friction:** setting up the agent by hand (prompt, nine variables, model, fillers, saving) was the most inconvenient part.
- **Decision:** continue. Nothing so far suggests voice is worse than text in a way prompt changes can't fix.
