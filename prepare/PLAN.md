# Book preparation — plan

How Agora turns a book into a spine: the units, the questions worth arguing about, and the information around them. Today spines are written by hand (see `examples/ai-future-is-now/spine.yaml`). This plan builds a pipeline that drafts them, with a person reviewing every one.

## Direction

**Agora is a personal tool for now.** Everything here is built for one curator (Michael) preparing books for his own reading. The design keeps expansion cheap without building for it:
- Spines are plain files, separate from learner records, so they can be shared later without anyone's thinking coming with them.
- No servers, accounts, catalog interface, or "prepare your own book" flow until there's a reason.

**What would justify expanding:** sustained personal use once the novelty wears off, roughly one or two sessions a week a month from now, without forcing it. The learner repo's session notes and `signals.yaml` already record this. Interest from other people is a second signal.

## Decisions

1. **Books are prepared once, centrally, and reviewed by a person.** Not by each learner. A spine is the agent's private agenda (judgment targets, hooks, debrief angles), and a learner who reviews it sees the hooks before they're used, which breaks "feel it before being told it" (`method/session.md`). Central preparation also allows quality checks against a gold set, and pays the cost once per book. While Agora is personal, the curator and the learner are the same person; that's an accepted tradeoff, softened by preparing a different book than the one being read.
2. **"Prepare your own book" comes later,** if ever. It would show the learner only what's safe to see (unit boundaries and reading ranges) and rely on automated checks for the rest.
3. **Book text stays local.** The source file and extracted text live in a gitignored working folder and are never committed. Spines hold paraphrased claims, questions and location references only, enforced by a copy check (Phase 5).
4. **Any public library starts with public-domain books** (e.g. Mill's *On Liberty*, the Federalist Papers, Darwin, Thoreau): strongly argumentative, centuries of critique to draw on, no rights issues. Publishing spines of in-copyright books deserves a legal check first. The existing 《AI未来已来》 example stays as the personal test book.
5. **Preparation runs offline, once per book,** with a strong model that has the full text and web access: Claude Code or a script over the Claude API. It never runs inside a session surface.

## The two layers

The pipeline's main job is to sort each unit into two layers. These become method and format rules in Phase 0.

- **Judgment targets:** the few decisions a thoughtful reader should reach themselves. Agora protects these and never answers them first.
- **Information layer:** facts, background, evidence, author context, and what has happened since publication. Agora gives these freely, with sources.

**The lookup test** decides which is which: *if the learner looked it up, would the question go away?* If yes, it's information. If no, it's a judgment.

**A good judgment target is:** load-bearing (the argument depends on it), contested (informed people disagree, or the case has a real weak spot), consequential (the answer changes what you'd do or believe), transferable (still a good question outside the book), and not lookup-able. Most units have one to three. Each is recorded with what a good answer has to weigh and the common shallow answers, so the agent can tell a real verdict from a quick one without holding a single correct answer.

**The evidence rule:** when the learner has an idea and asks for evidence, Agora brings evidence on both sides, with sources and the state of the consensus, and the learner gives the verdict. Evidence attaches to the position or idea card it supports.

## Pipeline

```
book (local) → 1 ingest → 2 structure → 3 argument maps → 4 two-layer sort
             → 5 outside context → 6 hooks → 7 spine + checks → human review
```

| Stage | Does | Reuses |
|---|---|---|
| 1 Ingest | EPUB/PDF → chapter text with location markers, in a gitignored working folder | ebooklib or Docling (EPUB); Marker or MinerU (PDF, MinerU for Chinese); pdf-craft (scanned); fallback-per-format design from book-to-skill |
| 2 Structure | Adler-style first pass: kind of book, thesis, outline. Split into units by argument, not chapter length | Adler analytical-reading template, as in cangjie-skill |
| 3 Argument maps | Per unit: main conclusion, premises, support and attack, implicit premises (hidden assumptions). Paraphrased, with locations | Stage design from llm_argumentation (code available) |
| 4 Two-layer sort | Score candidate judgment targets on the five criteria; "load-bearing" from the argument map (premises many conclusions depend on). Extract checkable claims for the information layer | Claimify's select-then-decompose method for checkable claims |
| 5 Outside context | Reviews and critiques (where informed readers disagree feeds "contested"), author incentives, events since publication, consensus labels with dates and sources | — |
| 6 Hooks | Two or three candidates per judgment target, judged against `method/hooks.md` by a separate call | — |
| 7 Spine + checks | Write `spine.yaml`, validate against `formats/`, run the copy check | — |

**Build, not borrow:** judgment-target scoring, the critique pass, the hook gate, the spine writer and the copy check. That's where Agora differs from existing tools, which extract what to apply (frameworks, rules) or what a book says (summaries), not what's worth arguing about.

## Phases

### Phase 0 — Method and formats

- `method/discussion.md`: judgment targets, the lookup test, and the evidence rule.
- `formats/spine.md`: a `judgments` list per unit (question, why it matters, what a good answer weighs, shallow answers, locations) and an information section (checkable claims with consensus label, date, sources; absorbs today's `checkable`).
- Regenerate surfaces. Update the voice unit brief (`context.py`) to include judgment targets.

**Done when** the example spine's `transformation` unit has judgment targets in the new format, and a session on it runs.

### Phase 1 — Gold set, by hand

Michael writes the judgment targets for three units of 《AI未来已来》, using `prepare/gold/TEMPLATE.md`: each target with the five-criteria reasoning, what a good answer weighs, and shallow answers. This is the quality bar for everything after it, and teaches what a good target looks like.

**Done when** three units are filled in `prepare/gold/ai-future-is-now/`.

### Phase 2 — Ingest and structure

- `prepare/` package with an extractor per format and an Adler structure pass.
- Working folder `prepare/work/` (gitignored) for source files and extracted text.

**Done when** 《AI未来已来》 ingests with correct chapter boundaries and locations, and the proposed units are sensible to a human reader.

### Phase 3 — Argument maps and the two-layer sort

- Argument map per unit; candidate judgment targets scored; information-layer claims extracted.
- Eval against the gold set: how many gold targets were found (recall), how many proposed targets the curator would keep (precision), and whether any proposed target fails the lookup test.

**Done when** the pipeline finds at least two of the three gold targets per unit (a starting bar, to tune), and no proposed target is lookup-able.

### Phase 4 — Outside context and research

Critique search, author incentives, events since publication, and consensus labels on checkable claims.

**Done when** each unit's information layer has dated, sourced claims, and contested scores visibly use critique evidence.

### Phase 5 — Hooks, spine writer, checks

Hook generation with the quality gate, `spine.yaml` output validated against `formats/`, and the copy check (reject runs of source text above a threshold, tuned during the phase).

**Done when** a full spine for 《AI未来已来》 passes validation and the copy check, and the curator's review edits fewer than a third of the judgment targets.

### Phase 6 — Use it

Prepare one public-domain book end to end and read it with Agora, by voice and text.

**Done when** several sessions have run on a pipeline-prepared spine, and the curator's notes say whether it was as good as the hand-written one.

### Later — only if expanding

- A public library repo of reviewed public-domain spines, with stable unit ids and versioning so spines can change after someone has started a book.
- "Prepare your own book," with spoiler-safe review.
- Ladder rungs 3–4: learners draft their own judgment targets and compare them with the library spine.
- A legal check before publishing spines of in-copyright books.

## Open questions

1. How to score "contested" for books with few reviews, especially non-English books.
2. Unit boundaries: when a chapter holds two arguments, or an argument spans chapters.
3. Cost and time per book, and which model each stage needs.
4. Whether the curator seeing a book's targets spoils sessions enough to matter while Agora is personal.
