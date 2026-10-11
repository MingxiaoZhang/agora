<!-- Generated from formats/learner.md by scripts/build-surfaces.sh. Do not edit. -->

# Learner records

These live in `learner/` and belong to the person, not to any one source. Positions from one book can be challenged by the next.

## positions.yaml

What the learner believes, and how that changed.

```yaml
- id: pos-0001
  topic: string                 # general idea, e.g. "accountability under automation"
  current: string               # the learner's words
  status: holding | moved | unsure
  history:
    - date: YYYY-MM-DD
      view: string              # the learner's words at the time
      why: string               # their reasoning
      origin: {source: <slug>, unit: <id>, session: YYYY-MM-DD}
  related: [pos-0003, idea-0001]
```

Add a `history` entry whenever the view changes. Never delete old entries; the "changed my mind" page is built from them.

## bets.yaml

Predictions made before a reveal, so being wrong registers.

```yaml
- id: bet-0001
  date: YYYY-MM-DD
  prediction: string
  confidence: 0-100             # optional
  origin: {source: <slug>, unit: <id>, session: YYYY-MM-DD}
  resolves: YYYY-MM-DD | on-reveal | open
  outcome: string               # filled in later
  lesson: string                # the learner's words about the gap
```

## open-questions.md

A plain list, newest first, each with a date and origin. The partner opens sessions with one of these.

```markdown
- 2026-10-10 · ai-future-is-now/ch09 — Who audits the public record of what AI systems did?
```

## signals.yaml

Session-level data used to fade or increase help. Facts, not judgments about the person.

```yaml
- session: YYYY-MM-DD
  source: <slug>
  hook_format: string
  hook_skipped: bool
  hints_used: int
  answer_requested_before_attempt: int
  converged: bool
  synthesis_written: bool
```

## context.md

What the learner has chosen to share about themselves (role, interests, goals), used to personalize hooks. Written by the learner or with their explicit OK. Nothing sensitive unless they put it there themselves.
