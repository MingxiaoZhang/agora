# Surfaces

A surface is one way of running the method: a skill imported into Claude, a custom GPT, a coding agent's AGENTS.md, and later voice or diagram tools.

**Rule:** a surface may add convenience, but must not change the method (`../method/`) or the record format (`../formats/`). Each surface has a short hand-written adapter file saying how *that* environment reads and writes records. Everything else is copied from the core by:

```bash
./scripts/build-surfaces.sh
```

Run it after any change to `method/` or `formats/`, and commit the result. Never edit generated files directly.

| Surface | Status | Install |
|---|---|---|
| [`claude-skill/`](claude-skill/) | v0 | Zip the folder and upload it in Claude (Settings → Capabilities → Skills), or copy it to `~/.claude/skills/agora/` for Claude Code |
| [`chatgpt/`](chatgpt/) | v0 | Create a custom GPT: paste `instructions.md`, upload the files in `knowledge/` |
| [`agents-md/`](agents-md/) | v0 | Copy `AGENTS.md` into your learner repo, for Codex, Cursor, and other agents that read it |
| [`voice/`](voice/) | planned | — |
| [`diagrams/`](diagrams/) | planned | — |
| `mcp-server/` | only if needed | — |

Install paths in the UI may change; check the vendor's current docs.
