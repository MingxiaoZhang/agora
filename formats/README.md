# Record formats

Agora keeps its records as plain markdown and YAML in a repo the learner owns: one repo per person, with each source as a folder inside it. Any tool or model can read and write these files, and so can the learner, by hand.

## Learner repo layout

```
my-reading/
├── sources/                      # per source: only makes sense in that source's context
│   └── <source-slug>/
│       ├── spine.yaml            # structure the sessions follow      → spine.md
│       ├── sessions/             # one note per session               → session-note.md
│       │   └── 2026-10-10.md
│       └── research/             # cached, dated, cited findings
├── learner/                      # per person: carries across sources
│   ├── positions.yaml            # what I believe and how it changed  → learner.md
│   ├── bets.yaml                 # predictions made before reveal
│   ├── open-questions.md
│   ├── signals.yaml              # hints, skips, cadence
│   └── context.md                # what I've chosen to share about myself
├── ideas/                        # original ideas, one file each      → idea-card.md
│   └── idea-0001.md
└── book/                         # rendered output (generated)
```

A template is in [`../templates/learner-repo/`](../templates/learner-repo/).

## Rules for every writer

1. **Only the learner's words or decisions.** Never record a belief the learner didn't state, or the partner's suggestion as the learner's choice.
2. **Link back.** Every position, bet, and idea links to the source and session it came from.
3. **History over overwrite.** When a position changes, add to its history; don't erase the old view.
4. **No source text.** Short cited excerpts at most. Location references (chapter, page, timestamp) instead of copies.
5. **Dates on everything** that can go stale, especially research.
