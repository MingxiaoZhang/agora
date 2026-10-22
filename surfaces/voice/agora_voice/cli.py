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
        p.add_argument("--learner-repo", type=Path, metavar="DIR", default=None,
                       help="Your learner repo. Default: $AGORA_LEARNER_REPO, else the one `setup` "
                            "last ran on, else the current folder.")

    p = sub.add_parser("setup", help="Create or update the ElevenLabs tools and agents. Safe to re-run.")
    repo_arg(p)

    p = sub.add_parser("talk", help="Run a session, then save draft records.")
    repo_arg(p)
    p.add_argument("--source", help="Source slug under sources/. Optional if there is only one.")
    p.add_argument("--unit", help="Unit id. Default: the first unit in progress, else the first not started.")
    p.add_argument("--minutes", type=int)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--web", action="store_true", help="Speak on ElevenLabs' talk page in your browser.")
    mode.add_argument("--text", action="store_true", help="Type in the terminal.")

    p = sub.add_parser("ingest", help="Turn a finished session into a session note and record drafts.")
    p.add_argument("session", nargs="?", metavar="SESSION_OR_CONVERSATION",
                   help="A session log name (e.g. 20261022T005152Z) or a conversation id (conv_...). "
                        "Default: the newest session not yet ingested.")
    p.add_argument("--from-fixture", type=Path, metavar="DIR",
                   help="Read events.jsonl and conversation.json from DIR instead of the API.")
    repo_arg(p)
    return parser


def default_source(learner_repo: Path) -> str:
    sources = sorted(p.parent.name for p in (learner_repo / "sources").glob("*/spine.yaml"))
    if len(sources) != 1:
        raise SystemExit(f"Pass --source; found {', '.join(sources) or 'no sources'}.")
    return sources[0]


def _api():
    from .provision import Api
    return Api(config.api_key())


def ingest_latest(learner_repo: Path, session: str | None = None) -> int:
    """Find the session's conversation on ElevenLabs, wait for it to be processed, and render it."""
    conversation_id = session if session and session.startswith("conv_") else None
    log = ingest.find_log(learner_repo, conversation_id, None if conversation_id else session)
    if log is None:
        where = learner_repo.resolve() / ingest.SESSIONS_DIR
        what = f"session {session}" if session else "a session that hasn't been ingested"
        print(f"No log for {what} in {where}. Is --learner-repo right?", file=sys.stderr)
        return 1
    api, cfg = _api(), config.load(learner_repo)
    if not conversation_id:
        conversation_id = log.conversation_id
    if not conversation_id:
        agent = cfg.web_agent_id if log.session.get("mode") == "web" else cfg.agent_id
        conversation_id = ingest.latest_conversation(api, agent, log.session.get("started", 0))
        if not conversation_id:
            print("ElevenLabs has no conversation for this session yet. Once the call has ended, "
                  "run `agora-voice ingest`.", file=sys.stderr)
            return 1
    print(f"Fetching {conversation_id} from ElevenLabs...")
    try:
        conversation = ingest.fetch(api, conversation_id)
        if not log.events("ingested") and not ingest.has_synthesis(log, conversation) and sys.stdin.isatty():
            ask_synthesis(log)
        r, written = ingest.ingest_conversation(learner_repo, log, conversation)
    except ingest.IngestError as e:
        print(e, file=sys.stderr)
        return 1
    print(ingest.summary(r, written, learner_repo))
    return 0


def ask_synthesis(log) -> None:
    """The call ended before the synthesis: ask for it here, as the method requires it written."""
    print("\nThe call ended before your synthesis. Type it now: what you now believe, what moved you, "
          "and what is still unresolved, in two or three sentences. Press Enter on an empty line to finish, "
          "or just Enter to skip.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line.strip():
            break
        lines.append(line)
    if lines:
        log.append("request_synthesis", prompt="post-call", synthesis="\n".join(lines), source="post-call")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.learner_repo is None:
        args.learner_repo = config.default_learner_repo()
    if args.command == "setup":
        from .provision import ProvisionError, setup
        try:
            result = setup(config.load(args.learner_repo))
        except ProvisionError as e:
            print(e, file=sys.stderr)
            return 1
        config.remember_learner_repo(args.learner_repo)
        print("\n".join(result.changes) if result.changes else "Already up to date; nothing changed.")
        print(f"Agents: {result.agent_id} (text), {result.web_agent_id} (web)  "
              f"(saved to {config.load(args.learner_repo).path})")
        print("Reminder: set the conversation retention period in the ElevenLabs dashboard.")
    elif args.command == "talk":
        from . import context, talk
        source = args.source or default_source(args.learner_repo)
        try:
            if args.web:
                log, url = talk.start_web(args.learner_repo, source, args.unit, args.minutes)
                opened = talk.open_in_browser(url)
                print(("Opened the talk page in your browser." if opened else "Open this page in your browser:")
                      + f"\n{url}\n\nAllow the microphone, then press the call button. At the synthesis step, type in "
                      "the page's text box.\nWhen you've ended the call, press Enter here to save the records "
                      "(or press Ctrl+C now and run `agora-voice ingest` later).")
                try:
                    input()
                except (KeyboardInterrupt, EOFError):
                    print(f"\nSession log kept. After the call, run:\n  agora-voice ingest {log.path.stem} "
                          f"--learner-repo {args.learner_repo}")
                    return 0
            else:
                log = talk.run_text(args.learner_repo, source, args.unit, args.minutes)
                print(f"\nConversation: {log.conversation_id}")
        except (context.ContextError, RuntimeError) as e:
            print(e, file=sys.stderr)
            return 1
        return ingest_latest(args.learner_repo, log.conversation_id)
    elif args.command == "ingest":
        if args.from_fixture:
            d = args.from_fixture
            r, written = ingest.ingest_files(d / "events.jsonl", d / "conversation.json", args.learner_repo)
            print(ingest.summary(r, written, args.learner_repo))
        else:
            return ingest_latest(args.learner_repo, args.session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
