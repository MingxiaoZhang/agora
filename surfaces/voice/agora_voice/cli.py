"""Command-line entry point: `agora-voice`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agora-voice", description="Run Agora sessions by voice.")
    sub = parser.add_subparsers(dest="command", required=True)

    def repo_arg(p):
        p.add_argument("--learner-repo", type=Path, default=Path("."), metavar="DIR")

    p = sub.add_parser("setup", help="Create or update the ElevenLabs tools and agent. Safe to re-run.")
    repo_arg(p)

    p = sub.add_parser("talk", help="Run a session.")
    repo_arg(p)
    p.add_argument("--source", help="Source slug under sources/. Optional if there is only one.")
    p.add_argument("--unit", help="Unit id. Default: the first unit in progress, else the first not started.")
    p.add_argument("--minutes", type=int)
    p.add_argument("--text", action="store_true", help="Text only: type instead of speaking.")

    p = sub.add_parser("ingest", help="Turn a finished session into a session note and record drafts.")
    p.add_argument("--from-fixture", type=Path, metavar="DIR", required=True,
                   help="Read events.jsonl and conversation.json from DIR instead of the API.")
    repo_arg(p)
    return parser


def default_source(learner_repo: Path) -> str:
    sources = sorted(p.parent.name for p in (learner_repo / "sources").glob("*/spine.yaml"))
    if len(sources) != 1:
        raise SystemExit(f"Pass --source; found {', '.join(sources) or 'no sources'}.")
    return sources[0]


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "setup":
        from .provision import ProvisionError, setup
        try:
            result = setup(config.load(args.learner_repo))
        except ProvisionError as e:
            print(e, file=sys.stderr)
            return 1
        print("\n".join(result.changes) if result.changes else "Already up to date; nothing changed.")
        print(f"Agent: {result.agent_id}  (saved to {config.load(args.learner_repo).path})")
        print("Reminder: set the conversation retention period in the ElevenLabs dashboard.")
    elif args.command == "talk":
        from . import context, talk
        if not args.text:
            print("Voice mode comes in Phase 3; use --text for now.", file=sys.stderr)
            return 1
        try:
            log = talk.run_text(args.learner_repo, args.source or default_source(args.learner_repo),
                                args.unit, args.minutes)
        except (context.ContextError, RuntimeError) as e:
            print(e, file=sys.stderr)
            return 1
        tools = [e.tool for e in log if e.tool not in ("session_start", "conversation")]
        print(f"\nConversation: {log.conversation_id}\nEvent log: {log.path}\nTools called: {', '.join(tools) or 'none'}")
    elif args.command == "ingest":
        d = args.from_fixture
        r, written = ingest.ingest_files(d / "events.jsonl", d / "conversation.json", args.learner_repo)
        print(ingest.summary(r, written, args.learner_repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
