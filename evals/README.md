# Evals

The method is the product, so it gets tested like code. Each suite holds cases that any surface can be run against: a scripted learner (or a human) plays the learner side, and a judge (a model or a person) scores the partner against the criteria.

| Suite | What fails |
|---|---|
| [`hooks/`](hooks/) | A hook that breaks the quality bar in `method/hooks.md` |
| [`sycophancy/`](sycophancy/) | The partner conceding to repetition or enthusiasm instead of arguments |
| [`convergence/`](convergence/) | A long discussion that never states a core idea or conclusion |
| [`grounding/`](grounding/) | A cited claim the source doesn't support |
| Generalization (planned) | A discussion that never leaves the source's framework |
| Learner outcome (later) | The learner can't explain or apply the idea a week later without help |

There's no runner yet. In v0, run cases by hand against a surface and note results in the case file. Add a runner only once the cases stabilize.
