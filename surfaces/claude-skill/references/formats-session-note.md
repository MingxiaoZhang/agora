<!-- Generated from formats/session-note.md by scripts/build-surfaces.sh. Do not edit. -->

# Session note

One note per session at `sources/<source-slug>/sessions/YYYY-MM-DD.md`. It records what happened in each phase, not a full transcript.

## Format

```markdown
---
date: YYYY-MM-DD
source: <slug>
unit: <id>
length: 10 | 25 | open
surface: string            # e.g. claude-skill, chatgpt, voice
status: complete | incomplete
stopped_at: spark | debrief | discuss | converge | synthesize   # only when incomplete
continues: YYYY-MM-DD       # only when this session continued an incomplete one
---

## Hook
- Format: predict-and-commit
- Headline: "..."
- Rejected candidates: "..." (reason), "..." (reason)

## Commitment
What the learner committed to, in their words.

## Debrief
The assumption that surfaced, and the tension named.

## Discussion
- The general idea pursued
- Key turns: where the learner's view moved or hardened
- Research done, with sources

## Converge
- Core idea:
- Provisional conclusion:
- Still open:

## Synthesis
The learner's own two or three sentences, verbatim.

## Records updated
- positions: pos-0001 (moved)
- bets: bet-0002
- ideas: idea-0001 (proposed, accepted)
- open question carried out:
```

Sections may be empty when a phase was skipped. The `Synthesis` section is the learner's text only.

A session is `complete` once the learner's synthesis was written and critiqued. Otherwise it is `incomplete`, and `stopped_at` names the first phase that didn't happen: no commitment to the hook (`spark`), no assumption surfaced (`debrief`), no position taken (`discuss`), no core idea stated (`converge`), or no critiqued synthesis (`synthesize`). A synthesis written after the session ended counts as `synthesize`, since it wasn't critiqued. Read is optional and never blocks completion. The next session on that unit continues an incomplete one (see `../method/session.md`, Resume).
