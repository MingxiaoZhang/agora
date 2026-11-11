# Hook trial — nonfiction, 2026-11-11

First run of [`../PROCEDURE.md`](../PROCEDURE.md), done by hand (by Claude, in conversation). Two units:

- 《AI未来已来》 ch. 6–7, from the public distillation (`Grruuu/ai-future-is-now-skill`: `boss-ai-engines`, `living-ontology`), **not the full text**.
- *On Liberty* ch. 2, from the full public-domain text.

Kept hooks are in each spine. Verdicts reference the quality bar in `method/hooks.md` (1 truthful, 2 paid off, 3 felt before told, 4 stakes, 5 small, 6 interesting without the source, 7 not a lookup, 8 fresh, 9 personal).

## 《AI未来已来》 ch. 6–7: enterprise decision core and "boss AI"

### Targets considered

| Target | Claim type | Lookup test | Used |
|---|---|---|---|
| Should leaders get the truth by reading people's raw work records, and what makes that legitimate? | Recommendation | Survives: depends on values and tradeoffs | Yes |
| When an AI gets your organization wrong, is the missing piece information or the connections between facts? | Distinction / cause | Survives: depends on the learner's own case | Yes |
| How should you weigh advice from someone who sells what they recommend? | Author's credibility | Survives | No: covered by "Follow the incentives" in `examples/ai-future-is-now/hooks.md`; fails 8 |

### Candidates

**Target 1: reading raw work records**

| Candidate | Verdict |
|---|---|
| **Scene: CEO deciding whether to roll out the pilot** | **Kept.** Passes all nine and the scene rules. The pilot's early catch makes "as is" tempting, and the consequences make it backfire. Roles are composites. |
| Forced dilemma: "Would you rather your manager see an AI summary of all your commits and meetings, or your weekly status update?" | Passes, and strongly personal for an engineer. Not kept only because it overlaps the scene; a good alternate for a second session on this unit. |
| Predict-and-commit: "What share of employees would change how they work once monitored?" | Rejected: invites an invented number and has no single defensible answer to reveal (fails 1–2). |

**Target 2: information vs relationships**

| Candidate | Verdict |
|---|---|
| **Personal memory: the last time an AI got your work wrong; missing or scattered?** | **Kept.** Personal (9), felt from the learner's own case (3), commits to one answer (4). Headline makes no claim, so 1 is safe. |
| Structural analogy: "A library versus a detective's corkboard: where is a case solved?" | Rejected: the analogy itself announces the book's answer (fails 3). |
| Agree/disagree: "Give an AI all your documents and it will understand your company." | Rejected: too easy to answer with a slogan; little to debrief (fails 4). |

### Notes

- The distillation's caveats (no safeguards, signals gamed once watched, vendor narrative) made better scene material than the book's claims themselves. Preparation should read critiques before writing scenes, which matches pipeline stage 5 running before stage 6.
- Both hooks rest on the distillation's paraphrase. Check against the book before relying on the debrief angles.

## *On Liberty* ch. 2: liberty of thought and discussion

### Targets considered

| Target | Claim type | Lookup test | Used |
|---|---|---|---|
| When, if ever, is it right to suppress a claim you're confident is false and harmful? | Recommendation | Survives | Yes |
| Can you really understand a belief you've never had to defend? | Cause | Survives | Yes |
| Does truth win out on its own, or does it need protection? | Prediction / historical | Survives: the examples are lookups, the verdict isn't | Yes |
| Which movements did Mill say were suppressed before the Reformation? | Fact | Fails: a lookup | No: information layer |

### Candidates

**Target 1: suppressing a false, harmful claim**

| Candidate | Verdict |
|---|---|
| **Scene: content-policy lead and a viral health claim** | **Kept.** A fictional additive avoids making a real-world health claim (1). The moderator's high-dose study builds Mill's partial-truth argument into the scene without naming it (3). Removing it is tempting and backfires. |
| Forced dilemma: "Would you ban a false claim if it caused one death a year?" | Rejected: contrived numbers, abstract, and answerable by slogan (fails 3–4). |
| Agree/disagree: "Some opinions are too dangerous to allow." | Rejected: generic; people answer from their existing politics without new reasoning (fails 4, weak 6). |

**Target 2: understanding a belief you've never defended**

| Candidate | Verdict |
|---|---|
| **Predict-and-commit: predict, then try, arguing against your own belief** | **Kept.** The gap between prediction and result is felt directly (3), and the activity is the learner's own belief (9). |
| Structural analogy: "an immune system never exposed to a virus" | Rejected: leads straight to Mill's conclusion (fails 3). |
| Agree/disagree: "A true belief you can't defend is worth less than one you can." | Rejected: the answer feels obvious, so there's no stake (fails 4). |

**Target 3: does truth win on its own**

| Candidate | Verdict |
|---|---|
| **Predict-and-commit: bet on "the truth always comes out"** | **Kept** as a third hook in a different target. Short, and the survivorship problem gives the debrief somewhere to go. |
| Scene: a 15th-century printer deciding whether to print a banned tract | Not kept: strong, but long for a point the bet makes faster. Candidate for a future history-scene trial. |

## What the trial taught

1. **The claim-type table helped.** Recommendations produced the two scenes; causal claims produced the predict-and-commit hooks. Facts were filtered out by the lookup test before any drafting.
2. **Scenes need the critiques.** Both scenes' best material (gamed signals, the partial-truth study) came from weaknesses and critiques, not the main claims.
3. **Fictional details protect truthfulness.** "Additive X" and a fictional company let the scene have stakes without making real-world claims.
4. **Debrief angles must not leak the answer.** The first draft of the On Liberty target 2 angle named "dead dogma"; it now says not to until the learner describes the gap.
5. **Open question:** scenes run longer by voice than a plain hook. Measure in the next voice session whether one stays within a few minutes.
