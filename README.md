# Agora

**Learn by discussing.** Agora is a method for learning from books, talks, and articles with an AI partner, without handing it your thinking.

Each session starts with a **hook**: a small, catchy exercise where you commit to a guess or a choice before you know the answer. Then you **discuss** the idea behind the source, not just the source itself, until the discussion reaches a real conclusion. Facts come easily, with citations. The judging is yours. At the end you write what you now believe, in your own words, and Agora keeps a record of your positions, how they changed, and the new ideas you had along the way. Over time that record reads like your own book discussion.

```
Resume → Spark → Debrief → Read → Discuss → Converge → Synthesize → Close
```

## How it's built

Agora is a way of reading and thinking first, and software second.

- **The core** is plain text and works with any tool:
  - [`method/`](method/): how a session runs, how hooks are made, how discussion works
  - [`formats/`](formats/): how records are kept (plain markdown and YAML in a repo you own)
- **Surfaces** run the core in different places: a Claude skill, a custom GPT, an AGENTS.md for coding agents, and later voice and diagrams. See [`surfaces/`](surfaces/).

Surfaces are generated from the core by `scripts/build-surfaces.sh`, so they never drift from it.

## Try it

1. Install a surface: see [`surfaces/README.md`](surfaces/README.md).
2. Create your own records repo from [`templates/learner-repo/`](templates/learner-repo/). Keep it private; it's your thinking.
3. Say: *"Start an Agora session on chapter 9 of 《AI未来已来》"* (or any source).

An example spine and hooks are in [`examples/ai-future-is-now/`](examples/ai-future-is-now/).

## What it isn't

- Not a quiz or flashcard app.
- Not a summarizer: it never writes your notes for you.
- Not a book distributor: no source text lives in this repo or in your records beyond short cited excerpts.

## Status

v0: the method, the formats, and three text surfaces. Design, roadmap, and open decisions: [`DESIGN.md`](DESIGN.md). Evals: [`evals/`](evals/).

## License

[MIT](LICENSE)
