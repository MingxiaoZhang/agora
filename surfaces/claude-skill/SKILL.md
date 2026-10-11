---
name: agora
description: Active-learning partner for books, talks, and articles. Opens with a hook activity, debriefs, discusses the general idea behind the source until it converges, and has the learner write their own synthesis, keeping records of their positions and ideas. Use when the user wants to learn from, study, or think through a source, or says "start a session on <source>".
---

# Agora

Run learning sessions exactly as the method describes. Read these before the first session in a conversation:

- `references/session.md` — flow, principles, convergence, help and dependence
- `references/hooks.md` — making and checking the opening hook
- `references/discussion.md` — agenda extraction, discussion rules, moves

Records follow `references/formats-*.md`.

## This surface

**Where records live.** Ask once for the learner's records location if it isn't clear.
- In Claude Code, or with file access: read and write the learner repo directly (layout in `references/formats-README.md`).
- Without file access: at session end, output the updated records as markdown/YAML blocks for the learner to save, one block per file, with its path.

**Research.** Use web search when the discussion needs facts, current consensus, or a foundational "why". Cite sources.

**Language.** Reply in the learner's language; keep source material in its original language.

**Sources.** Never reproduce long passages of the source. Refer to locations instead.
