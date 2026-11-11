# Book preparation — plan

How Agora turns a book into a spine: the units, the questions worth arguing about, and the information around them. Today spines are written by hand (see `examples/ai-future-is-now/spine.yaml`). This plan builds a pipeline that drafts them, checked by machines where possible and by a person where not (see "Trust and review").

## Direction

**Agora is meant for other people, starting small.** It began as a personal learning tool, but the idea is well enough defined to offer to others. The first users are a handful of readers; the first library is a few reviewed public-domain books. Until there's evidence people keep using it, the design stays cheap to run:
- Spines are plain files, separate from learner records, so they can be shared without anyone's thinking coming with them.
- No servers, accounts or catalog interface until the number of users calls for them.

**Signals to invest further:** early users coming back weekly once the novelty has worn off (session notes and `signals.yaml` already record this), the voice trial's go decision (`surfaces/voice/PLAN.md`, Phase 4), and post-session ratings showing that prepared spines are worth arguing over.

## Decisions

1. **Books are prepared once, centrally, and reviewed by a person.** Not by each learner. A spine is the agent's private agenda (judgment targets, hooks, debrief angles), and a learner who reviews it sees the hooks before they're used, which breaks "feel it before being told it" (`method/session.md`). Central preparation also allows quality checks against a gold set, and pays the cost once per book. **A curator never learns from a book they curated:** reviewing a spine spoils it. Curators review books they've already read; the books they learn from are prepared and reviewed by someone else, or reviewed only after their sessions (see "Trust and review").
2. **"Prepare your own book" comes later,** if ever. It would show the learner only what's safe to see (unit boundaries and reading ranges) and rely on automated checks for the rest.
3. **Book text stays local.** The source file and extracted text live in a gitignored working folder and are never committed. Spines hold paraphrased claims, questions and location references only, enforced by a copy check. A simple version runs from Phase 2, when text is first extracted; Phase 5 tunes it.
4. **Any public library starts with public-domain books** (e.g. Mill's *On Liberty*, the Federalist Papers, Darwin, Thoreau): strongly argumentative, centuries of critique to draw on, no rights issues. Publishing spines of in-copyright books deserves a legal check first. The existing 《AI未来已来》 example stays as a test book for the voice trial, not for the gold set (Phase 1).
5. **Preparation runs offline, once per book,** with a strong model that has the full text and web access: Claude Code or a script over the Claude API. It never runs inside a session surface.

## Trust and review

**AI drafts the whole spine; it isn't trusted with all of it.** Some errors can be caught by machines; others can only be judged by a person, and a learner can't catch any of them, since the spine is a private agenda. Experience on the voice surface bears this out: post-call extraction reworded the learner's speech as quotes, filed six positions under "success", and took a unit title for a hook headline. Each looked plausible until checked against the source.

| Part of the spine | Can AI be trusted? | Checked by |
|---|---|---|
| Structure, units, locations | Yes, with checks | Schema validation; mistakes are visible |
| Paraphrased claims | Yes, with checks | A narrow check against the local text: does the cited passage say this? |
| Copying source text | Caught automatically | The copy check |
| Information layer (facts, consensus, events since) | Yes, with checks | Citations must resolve and support the claim |
| Judgment targets | **No: matters of taste** | A person. Models lean toward safe, generic or lookup-able questions, and toward the author's own framing |
| Hooks | **No: they fail quietly** | A person. "Truthful, no invented numbers" is the first thing a punchy headline breaks |
| "Contested" scores | Partly | A person, especially for books with few reviews or non-English ones, where disagreement is easy to invent |

**Review in layers:**
1. **Automatic checks** on every spine: schema, copy check, claims against the local text, citations.
2. **A second model critiques** judgment targets against the five criteria and hooks against `method/hooks.md`, catching the obvious failures cheaply.
3. **A person reviews what can't be checked:** the judgment targets and hooks, a few short items per unit (roughly 15–30 minutes a book), not the whole spine.
4. **Learners rate targets after their session** on a unit, when seeing them can no longer spoil anything (Phase 7). This catches what review missed, and grows with the number of users.
5. **Human review shrinks as measured precision rises.** For example, once a reviewer would keep about 90% of proposed targets across several books, move from reviewing every target to spot-checking samples. The threshold is set from data, not assumed.

**Labels for learners:** each spine says whether it was reviewed by a person or is AI-prepared only, so learners can weigh it. The method already sends learners to the original text when what the author actually said matters (`method/session.md`, principle 9).

**Measured, not assumed:** the gold set (Phase 1) and post-session ratings (Phase 7) are how trust is earned. Automatic signals from records (positions that moved, discussions that converged, hints used, hooks skipped) help rank targets, but are too noisy to count as ground truth.

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

The curator writes the judgment targets for three units of **a book they have already read closely** and won't learn from with Agora, ideally a strongly argumentative public-domain book that can seed the library. Each target uses `prepare/gold/TEMPLATE.md`: the five-criteria reasoning, what a good answer weighs, and shallow answers. This is the quality bar for everything after it, and teaches what a good target looks like. 《AI未来已来》 is not used, since it's being read in the voice trial and writing its targets would spoil those sessions.

**Done when** three units are filled in `prepare/gold/<book>/`.

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

**Done when** a full spine for the gold-set book passes validation and the copy check, the model critique has run on every target and hook, and the curator's review edits fewer than a third of the judgment targets.

### Phase 6 — Use it

Prepare one public-domain book end to end and read it with Agora, by voice and text.

**Done when** several sessions have run on a pipeline-prepared spine, and the curator's notes say whether it was as good as the hand-written one.

### Phase 7 — Post-session review

- After a session on a unit, show the learner that unit's judgment targets and ask: was each worth arguing about, and what did we miss that you actually cared about? Store the answers next to the session note, and pool them per spine.
- Report per book: the share of targets learners found worth arguing about, the targets they added, and how this compares with the reviewer's judgment.
- Feed the ratings into the gold set and into calibrating the model critique.

**Done when** ratings from at least a few learners on one book are pooled, and the precision figure from step 5 of "Trust and review" can be computed from them.

### Later — as use grows

- A public library repo of reviewed public-domain spines, with stable unit ids and versioning so spines can change after someone has started a book.
- "Prepare your own book," with spoiler-safe review.
- Ladder rungs 3–4: learners draft their own judgment targets and compare them with the library spine.
- A legal check before publishing spines of in-copyright books.

## Open questions

1. How to score "contested" for books with few reviews, especially non-English books.
2. Unit boundaries: when a chapter holds two arguments, or an argument spans chapters.
3. Cost and time per book, and which model each stage needs.
4. Which book the gold set uses: one the curator knows well, argumentative, ideally public domain.
5. How many post-session ratings per book are enough to trust a precision figure, and how to weigh a learner who disagrees with the reviewer.
