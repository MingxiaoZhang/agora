"""Command-line entry point: `agora-voice`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import ingest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agora-voice", description="Run Agora sessions by voice.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", help="Turn a finished session into a session note and record drafts.")
    p.add_argument("--from-fixture", type=Path, metavar="DIR", required=True,
                   help="Read events.jsonl and conversation.json from DIR instead of the API.")
    p.add_argument("--learner-repo", type=Path, default=Path("."), metavar="DIR")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        d = args.from_fixture
        r, written = ingest.ingest_files(d / "events.jsonl", d / "conversation.json", args.learner_repo)
        print(ingest.summary(r, written, args.learner_repo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
