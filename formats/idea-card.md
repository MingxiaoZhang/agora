# Idea card

An idea card captures something original the learner said: not a restatement of the source, but a claim of their own. One file per idea in `ideas/`.

The partner may *propose* a card when it notices one. The learner accepts, edits, or rejects it. The statement is always in the learner's words.

## Format

```markdown
---
id: idea-0001
title: string
status: draft | developing | written-up | dropped
created: YYYY-MM-DD
origin: {source: <slug>, unit: <id>, session: YYYY-MM-DD}
related: [idea-0002, pos-0001]
---

## Statement
The idea in the learner's words.

## Why I think so
The learner's reasoning.

## Evidence
- Cited findings that support or challenge it, with dates.

## Open questions
- What would have to be true for this to fail?

## Log
- YYYY-MM-DD — how the idea changed, and why.
```

Ideas can grow across sessions and sources. When one is ready, it can be promoted into an essay or blog post; set `status: written-up` and link the piece.
