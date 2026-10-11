# Agora — Design

Active learning with agents: a hook sparks interest, a discussion goes deep, research keeps it accurate and current, and the learner ends up with a book-like record of what they now think.

## 1. Goals and non-goals

**Goals**
1. **Spark interest.** Every session opens with a hook: catchy, even clickbait-style, but truthful and paid off in the same session.
2. **Easy to take in, effortful to judge.** Facts, background, and current consensus are cheap: ask and get a cited answer. Positions, predictions, and syntheses are the learner's work. The tool protects the second kind of effort, not the first.
3. **Book-shaped knowledge.** The learner follows a structure (a "spine") the way a book has chapters, rather than an unbounded chat. The end product reads like a book discussion: chapters, arguments, the learner's positions, and how they changed.
4. **Accurate and current.** Claims are checked against sources, and each one carries a consensus status (holds / contested / superseded since publication).
5. **New ideas become tracked artifacts.** When a discussion produces an original idea, it is captured as an idea card, versioned, and linked back to where it came from.

**Non-goals**
- Not a quiz or flashcard app. Spaced recall may appear later as a minor feature.
- Not a summarizer. The tool never produces the learner's notes for them.
- Not a book distributor. No book text ships in the repo; the learner supplies their own copy or works from public sources.

## 2. Lessons from the first trial (design constraints)

| Problem seen | Constraint |
|---|---|
| Hook asked for 8 items; unfocused | Hooks ask for 1–2 items. Depth over breadth. |
| Questions felt forced by the book's framework | The book is a launchpad. Each tension is stated as a general idea without the book's vocabulary, and discussion follows that idea anywhere. |
| Discussion circled the same point | Convergence rule: after ~6 turns or repeated questions, state the core idea, research the foundational "why," and give a provisional conclusion plus open questions. |
| Analogies stood in for the unstated core idea | Foundational questions trigger real research (literature, law, history) with citations. |
| Agent quizzed instead of discussing | Agent holds stances, concedes only to arguments, and does not end every turn with a question. |

## 3. Architecture

```
            ┌──────────────────────────────────────────────┐
            │                Session Engine                 │
            │  Spark → Debrief → Read → Discuss → Synthesize│
            └───┬──────────┬──────────┬──────────┬─────────┘
                │          │          │          │
         ┌──────▼───┐ ┌────▼─────┐ ┌──▼───────┐ ┌▼──────────┐
         │  Spine   │ │  Hook    │ │ Research │ │  Learner  │
         │ Builder  │ │  Engine  │ │ & Consen-│ │   Model   │
         │          │ │ (+gate)  │ │ sus      │ │           │
         └──────┬───┘ └──────────┘ └────┬─────┘ └─────┬─────┘
                │                       │             │
            ┌───▼───────────────────────▼─────────────▼───┐
            │      Knowledge Store (markdown + YAML, git)  │
            └───────────────────────┬─────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │ Artifact Builder │ → the learner's "book"
                           └─────────────────┘
```

The boxes above are **roles**, not programs. Any of them can be played by a prompt, a skill file, a script, a person, or a dedicated service.

### 3.1 Core vs. surfaces

Agora is a way of reading and thinking first, and software second. So the project separates:

**The core** (stable, implementation-free):
1. **The method**: session flow, hook rules, discussion moves, convergence rule, synthesis rules. Written as plain prose that a human tutor could follow.
2. **The record format**: what a spine, a position, a bet, an idea card, and a session note contain. Plain markdown + YAML, readable by people and any model.
3. **Quality bars**: what makes a hook, a discussion, or a conclusion good (section 7), so any implementation can be judged the same way.

**Surfaces** (swappable, built around the core):

| Surface | Example implementations |
|---|---|
| Conversation | Skill docs imported into Claude or ChatGPT; AGENTS.md in a coding agent; a custom app |
| Voice | Live audio chat with the same method; transcripts saved as session notes |
| Visuals | AI-generated diagrams of a chapter's argument or the learner's position map |
| Research | The model's built-in web search; a dedicated research tool |
| Record keeping | Hand-edited files; a folder the agent writes to; an MCP server; a sync to Notion or Obsidian |
| The "book" | A markdown file; a static site; a PDF |

**Rule:** a surface may add convenience, but must not change the method or the record format. If voice mode needs a different hook style, that's a change to the core method, made deliberately.

### 3.2 Simplest implementation first

The cheapest working version is **skill docs + a folder of plain files**: import the method into Claude or ChatGPT, let it read and write the record files, and render the "book" by hand or with a small script. Build software only where that version actually hurts (for example, if the hook gate needs a separate judge, or the record gets too big to manage by hand). The MCP server described below is one possible surface, not a requirement.

## 4. Components

### 4.1 Spine Builder
Turns a source into the structure sessions follow.

- **Input:** a book (user's own EPUB/PDF, read locally), a distilled skill repo, a topic, or a reading list.
- **Output:** `spine.yaml`, an ordered list of units. Each unit has:
  - `claims`: contestable central claims, with source locations (page/chapter, never long quotations)
  - `tensions`: what's arguable about them
  - `general_idea`: the question underneath, phrased without the book's vocabulary
  - `checkable`: predictions or facts that can be checked against today
  - `author_context`: incentives, publication date, known critiques
- **Modes:** book-first (keep the author's chapter order) or idea-first (re-order by general idea, possibly merging several books).
- Keeps the "structure a book provides" while letting discussion leave the book.

### 4.2 Hook Engine
Generates and gates the opening activity.

- **Formats:** predict-and-commit, forced dilemma, role-play, rank-and-defend, find-the-flaw, pre-mortem, structural analogy, personal memory.
- **Headline:** curiosity-gap phrasing allowed.
- **Quality gate** (separate model call, returns pass/fail with reasons):
  1. Every claim in the headline is defensible (checked against Research).
  2. The payoff lands this session.
  3. The learner commits to 1–2 things with stakes.
  4. Interesting even if the book didn't exist.
  5. Format not used in the last 3 sessions.
  6. Personal where possible (uses Learner Model context).
- Generate 3 candidates → gate → present the best one. Store rejected hooks for evals.

### 4.3 Session Engine
State machine for one session.

| Phase | Agent does | Learner does |
|---|---|---|
| Resume | Recalls an open question or past position | Says whether it changed |
| Spark | Presents hook | Commits (1–2 items) |
| Debrief | Asks about assumptions; names the tension only after they articulate it | Explains reasoning |
| Read | Points to the passage; optional | Reads alone |
| Discuss | Generalizes early, uses the move repertoire, holds stances, researches when needed | Argues |
| Converge | States the core idea, gives a cited provisional conclusion and open questions | Disagrees or accepts |
| Synthesize | Critiques, never rewrites | Writes 2–3 sentences in their own words |

Behaviors carried over from the skill: commit before reveal, hint ladder / stuck protocol, fading help, convergence rule, no sycophancy. Session length modes: 10 / 25 / open.

### 4.4 Research & Consensus
Makes discussion accurate and current.

- **Triggers:** a foundational "why" question, a checkable claim from the spine, or the learner asking a factual question.
- Searches the web and scholarly sources; prefers primary sources; cites everything.
- Gives each claim a **consensus status**: `holds`, `contested`, `superseded`, `unknown`, with date checked and sources.
- Explains facts directly. Easy information is a feature; there's no Socratic withholding of facts.
- Caches results in the store with dates, so later sessions can re-check stale claims.

### 4.5 Learner Model
What the system knows about the learner, written only from what they said.

- `positions`: claim, reasoning, date, status (holding / moved / unsure), history of changes
- `bets`: predictions made before reveal, with outcomes
- `open_questions`
- `signals`: hints used, answer requests before attempting, skipped syntheses, session cadence
- `context`: role and interests the learner chose to share (used for personalizing hooks)

Drives: Resume, contradiction checks ("last week you held X"), hook personalization, fading help.

### 4.6 Idea Capture
When the learner says something original (not a restatement of the source), the agent proposes an **idea card**; the learner accepts, edits, or rejects it.

```yaml
id: idea-0007
title: Accountability settles where a system's unverifiable assumptions are
statement: <learner's words>
origin: {session: 2026-10-10, spine_unit: ch9, sparked_by: hook-0003}
evidence: [links to research entries]
status: draft | developing | written-up
related: [idea-0003]
```

Ideas can grow across sessions and books, and eventually be promoted to a blog post or essay.

### 4.7 Artifact Builder
Renders the store into the learner's **book discussion**: one volume per source or topic.

- Per chapter: the hook and what the learner committed to, the general idea, the learner's synthesis, positions and how they moved, key cited research, open questions.
- An "Ideas" section collecting idea cards.
- A "Changed my mind" log, the most valuable page.
- Outputs: a static site (mdBook or Astro), a single markdown file, or PDF.
- Content is the learner's own writing plus cited research; the agent supplies structure, not prose.

## 5. Data layout (the learner's repo)

```
my-reading/                       # one repo per learner
├── sources/                      # per source (book, talk, articles)
│   └── ai-future-is-now/
│       ├── spine.yaml
│       ├── sessions/2026-10-10.md
│       └── research/             # cached cited findings, dated
├── learner/                      # per person, across sources
│   ├── positions.yaml
│   ├── bets.yaml
│   ├── open-questions.md
│   ├── signals.yaml
│   └── context.md
├── ideas/idea-0001.md
└── book/                         # rendered artifact
```

Plain files, so the learner can read, edit, and diff them. Git history gives the "how my thinking evolved" view for free.

## 6. Project repo layout

```
agora/
├── method/                 # THE CORE — plain prose, no tool assumptions
│   ├── session.md          # flow, principles, convergence, synthesis
│   ├── hooks.md            # hook rules, formats, quality bar
│   └── discussion.md       # move repertoire, stuck protocol, fading help
├── formats/                # THE CORE — record schemas + examples
│   ├── README.md           # learner repo layout + rules for writers
│   ├── spine.md
│   ├── learner.md          # positions, bets, open questions, signals
│   ├── idea-card.md
│   └── session-note.md
├── surfaces/               # adapters; each is optional and replaceable
│   ├── claude-skill/       # SKILL.md built from method/
│   ├── chatgpt/            # custom-instructions / GPT version
│   ├── agents-md/          # for coding agents
│   ├── voice/              # (later) live audio adapter
│   ├── diagrams/           # (later) diagram prompts/templates
│   └── mcp-server/         # (later, only if needed) record-keeping tools
├── renderer/               # turns records into the learner's "book"
├── evals/
│   ├── hooks/              # rated good/bad hooks
│   ├── sycophancy/         # learner asserts wrong thing; agent must push back
│   ├── convergence/        # long transcripts; must conclude
│   └── grounding/          # citations must support claims
├── examples/
│   └── ai-future-is-now/   # sample spine + hooks built from the distilled skill repo
├── templates/
│   └── learner-repo/       # starter for a learner's own records repo
├── scripts/
│   └── build-surfaces.sh   # regenerates surfaces from method/ + formats/
├── DESIGN.md
└── README.md
```

## 7. Evals
The protocol is the product, so test it like code.

- **Hook quality:** LLM judge + human ratings against the 6 gate criteria; track pass rate and learner "skip" rate.
- **Anti-sycophancy:** scripted learner states a plausible but wrong claim and persists without new arguments; agent must not concede.
- **Convergence:** after N turns of a looping discussion, the agent must state a core idea and conclusion.
- **Grounding:** every research claim's citation must support it.
- **Generalization:** fraction of discussion turns that reach a general idea beyond the book.
- **Learner outcome (later):** delayed recall and transfer — can the learner explain and apply the idea a week later without help?

## 8. Roadmap

| Version | Scope |
|---|---|
| v0 (now) | Write `method/` and `formats/` from the current `SKILL.md`. Ship two surfaces: a Claude skill and a ChatGPT version. Records are hand-kept files. Use it on 《AI未来已来》 and one non-book source. |
| v1 | Whatever hurt most in v0. Likely: a small script to render the "book," and a separate hook-gate prompt. |
| v2 | New surfaces: voice sessions, diagrams of arguments and position maps. |
| v3 | Software only where needed: spine building from EPUB/PDF, an MCP server for records, evals in CI. |
| Later | Multi-book idea graph, delayed recall checks, shared reading groups. |

## 9. Open decisions

1. **Name.** Agora, after the Athenian public square where people met to argue ideas. Check GitHub and npm for conflicts before publishing.
2. **Whether to build software at all, and when.** Decide per pain point after v0. If a server is built, TypeScript fits MCP tooling best.
3. **Book ingestion and copyright.** Local-only ingestion of the learner's own copy; no text in the repo or rendered artifact beyond short cited excerpts.
4. **Where the hook gate runs:** same model vs. separate cheaper judge.
5. **Bilingual support:** sessions in the learner's language with sources in the original (e.g. Chinese book, English discussion).
6. **How much the agent may personalize** from learner context without feeling intrusive.
