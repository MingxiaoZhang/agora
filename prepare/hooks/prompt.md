# Prompt: prepare hooks for one unit

Use with any capable model that can read the repo (for example Claude Code in this repo). Replace the bracketed parts.

---

Prepare hooks for unit `[unit id]` of `[path to spine.yaml]`.

Read first:
- `method/hooks.md`: the quality bar, the formats, the scene rules, and "Hooks for nonfiction"
- `prepare/hooks/PROCEDURE.md`: the steps
- `formats/spine.md`: the hook fields
- the unit in the spine, and the source's `author_context`
- `[learner context, if any]`

Then follow the procedure:
1. List the unit's candidate judgment targets. For each, apply the lookup test and name the claim type. Pick one or two targets.
2. For each target, draft three hooks in different formats, chosen from the nonfiction table. Use a scene if the target is about what to do.
3. Gate every candidate against each item of the quality bar (and the scene rules for scenes). Give a one-line verdict per candidate.
4. Keep the best one or two overall.

Output two things:
- **YAML** for the kept hooks, ready to paste under the unit's `hooks:`, with `target`, `format`, `headline`, `activity`, `debrief_angle`, and `scene` for scenes.
- **A trial note** in markdown: the targets considered, every candidate with its verdict, and why the kept ones won.

Rules:
- Claims in headlines must be defensible from the spine or well-established facts. No invented statistics.
- Paraphrase only; never quote the source at length.
- Roles are composites, never real named people, including the author.
- If the spine is built from a distillation rather than the full text, say so in the trial note.
