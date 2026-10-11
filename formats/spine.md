# Spine

A spine gives a source the structure sessions follow, the way chapters give a book its shape. It lives at `sources/<source-slug>/spine.yaml`.

A spine is the partner's private agenda, written down so it carries across sessions. The learner can read it, but sessions don't announce it.

## Schema

```yaml
source:
  title: string
  author: string
  kind: book | talk | video | podcast | articles | course | topic
  published: YYYY or YYYY-MM-DD
  language: string            # e.g. zh, en
  author_context: string      # incentives, affiliations, known critiques
  notes: string               # e.g. "built from a distilled skill repo, not the full text"

order: source | idea          # follow the source's order, or regroup by general idea

units:
  - id: string                # e.g. ch09
    title: string
    location: string          # chapter / pages / timestamps
    status: not-started | in-progress | done | skipped
    claims:
      - text: string          # paraphrased, not quoted
        contestable_because: string
    general_ideas:
      - string                # phrased without the source's vocabulary
    checkable:
      - claim: string
        consensus: holds | contested | superseded | unknown
        checked: YYYY-MM-DD
        sources: [url]
    weaknesses:
      - string
```

Every field except `id`, `title`, and `general_ideas` is optional. A spine can start as a list of unit titles and fill in as sessions happen.

See [`../examples/ai-future-is-now/spine.yaml`](../examples/ai-future-is-now/spine.yaml).
