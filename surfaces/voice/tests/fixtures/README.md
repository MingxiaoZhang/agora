# Test fixtures

- `ch09-session/`: a hand-made voice session on 《AI未来已来》 ch. 9. `conversation.json` has the shape of `GET /v1/convai/conversations/{id}`; `events.jsonl` is the local event log. It covers exact quotes, a paraphrased quote (`accountability under automation`), a missing `record_converge` call filled from data collection, and a synthesis typed after the call dropped.
- `web-session/conversation.json`: a hand-made session on the web talk page: no tool events, typed synthesis (`source_medium: text`), and positions and research questions in data collection, one of them not something the learner said.
- `golden/`: the expected session note and `positions.yaml` from ingesting `ch09-session/`. If a change to `render.py` is intended, regenerate them with `agora-voice ingest --from-fixture` and review the diff.
- `learner-positions/positions.yaml`: hand-formatted positions, used to check that untouched entries come through byte for byte.

The tests build a learner repo from `templates/learner-repo/` and `examples/ai-future-is-now/spine.yaml`, so those stay the single source.
