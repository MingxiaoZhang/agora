"""Run a session (DESIGN.md §9): typed in the terminal (`run_text`), or spoken on
ElevenLabs' talk page in the browser (`start_web`).

The terminal is shared by the conversation and `request_synthesis`, so one
thread reads stdin and `Terminal` routes each line: to the agent normally,
or into the synthesis while the agent is waiting for one.
"""

from __future__ import annotations

import base64
import hashlib
import json
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from datetime import date
from pathlib import Path
from typing import Callable, TextIO

from . import config as config_mod, context
from .provision import load_json
from .tools import EventLog, Handlers

SYNTHESIS_END = "Press enter on an empty line to send."


class Terminal:
    def __init__(self, stdin: TextIO = sys.stdin, out: TextIO = sys.stdout):
        self.lines: queue.Queue[str | None] = queue.Queue()
        self.out = out
        self.synthesis_wanted = threading.Event()
        self.synthesis: queue.Queue[str] = queue.Queue()
        threading.Thread(target=self._read, args=(stdin,), daemon=True).start()

    def _read(self, stdin: TextIO) -> None:
        for line in stdin:
            self.lines.put(line.rstrip("\n"))
        self.lines.put(None)  # end of input

    def get(self, timeout: float | None = None) -> str | None:
        """Next line, or None once input has ended (and every time after). Raises queue.Empty on timeout."""
        line = self.lines.get(timeout=timeout)
        if line is None:
            self.lines.put(None)
        return line

    def say(self, text: str) -> None:
        print(text, file=self.out, flush=True)

    def read_synthesis(self, prompt: str) -> str:
        """Called from the tool handler's thread; blocks until the learner has typed it."""
        self.say(f"\n[Synthesis] {prompt}\n{SYNTHESIS_END}")
        self.synthesis_wanted.set()
        return self.synthesis.get()

    def collect_synthesis(self, first: str) -> None:
        parts = [first] if first.strip() else []
        while True:
            line = self.get()
            if line is None or not line.strip():
                if parts or line is None:
                    break
                continue
            parts.append(line)
        self.synthesis_wanted.clear()
        self.synthesis.put("\n".join(parts))


def fillers() -> list[str]:
    """The agent's soft-timeout fillers. They suit a voice call, but in text they are noise."""
    soft = load_json("agent.template.json")["conversation_config"]["turn"]["soft_timeout_config"]
    return [soft["message"], *soft.get("additional_soft_timeout_messages", [])]


_AUDIO_TAG = re.compile(r"\[[a-z][a-z ]{0,20}\]\s*")


def strip_fillers(text: str, phrases: list[str]) -> str:
    """Make a voice reply readable as text: drop the fillers the platform prepends
    ("Okay... Thanks." -> "Thanks.") and expressive audio tags such as "[warm]"."""
    text = _AUDIO_TAG.sub("", text).strip()
    changed = True
    while changed:
        changed = False
        for phrase in phrases:
            if text.startswith(phrase):
                text, changed = text[len(phrase):].lstrip(), True
    return text


def new_log(learner_repo: Path, session: context.Session, mode: str) -> EventLog:
    return EventLog.new(learner_repo, source=session.source, unit=session.unit, hook_headline=session.hook_headline,
                        hook_format=session.variables["hook_format"],
                        session_minutes=session.variables["session_minutes"], date=date.today().isoformat(),
                        mode=mode, started=int(time.time()))


TALK_PAGE = "https://elevenlabs.io/app/talk-to"


def talk_url(agent_id: str, variables: dict) -> str:
    """The talk page URL with the session variables as base64 JSON in `vars`.
    ASCII-only JSON, so non-Latin text survives the page's base64 decoding."""
    encoded = base64.b64encode(json.dumps(variables, ensure_ascii=True).encode()).decode()
    return f"{TALK_PAGE}?{urllib.parse.urlencode({'agent_id': agent_id, 'vars': encoded})}"


def open_in_browser(url: str) -> bool:
    """Open a URL, preferring the Windows browser when running under WSL."""
    if shutil.which("wslview"):
        return subprocess.run(["wslview", url]).returncode == 0
    if shutil.which("explorer.exe"):
        subprocess.run(["explorer.exe", url])  # returns 1 even when it works
        return True
    return webbrowser.open(url)


def start_web(learner_repo: Path, source: str, unit: str | None, minutes: int | None) -> tuple[EventLog, str]:
    """Log the session's start and return the talk page URL for it."""
    cfg = config_mod.load(learner_repo)
    if not cfg.web_agent_id:
        raise RuntimeError("No web agent yet. Run `agora-voice setup` first.")
    session = context.build(learner_repo, source, unit, minutes)
    return new_log(learner_repo, session, "web"), talk_url(cfg.web_agent_id, session.variables)


def user_id(learner_repo: Path) -> str:
    return hashlib.sha256(str(Path(learner_repo).resolve()).encode()).hexdigest()[:16]


def run_text(learner_repo: Path, source: str, unit: str | None, minutes: int | None,
             terminal: Terminal | None = None, conversation_factory: Callable | None = None) -> EventLog:
    """Run one text-only session and return its event log."""
    cfg = config_mod.load(learner_repo)
    if not cfg.agent_id:
        raise RuntimeError("No agent yet. Run `agora-voice setup` first.")
    session = context.build(learner_repo, source, unit, minutes)
    log = new_log(learner_repo, session, "text")
    term = terminal or Terminal()
    handlers = Handlers(log, term.read_synthesis)
    ended = threading.Event()
    phrases = fillers()

    def show(text: str) -> None:
        text = strip_fillers(text, phrases)
        if text:
            term.say(f"\nAgora: {text}\n")

    conv = (conversation_factory or _sdk_conversation)(
        cfg, session.variables, handlers.handlers(), user_id(learner_repo),
        on_agent=show, on_end=ended.set,
    )
    term.say(f"Text session on {session.unit}. Type to reply; /quit ends the session (the agent never hangs up).")
    conv.start_session()
    try:
        while not ended.is_set():
            try:
                line = term.get(timeout=0.5)
            except queue.Empty:
                continue
            if term.synthesis_wanted.is_set():
                term.collect_synthesis(line or "")
            elif line is None or line.strip() == "/quit":
                break
            elif line.strip():
                conv.send_user_message(line)
    except KeyboardInterrupt:
        pass
    finally:
        if not ended.is_set():
            conv.end_session()
        conversation_id = conv.wait_for_session_end()
    if conversation_id:
        log.set_conversation_id(conversation_id)

    if not handlers.has_synthesis():
        term.say("\nThe session ended without a synthesis. Type it now (two or three sentences). " + SYNTHESIS_END)
        term.synthesis_wanted.set()
        first = term.get()
        if first is not None:
            term.collect_synthesis(first)
            text = term.synthesis.get().strip()
            if text:
                log.append("request_synthesis", prompt="post-call", synthesis=text, source="post-call")
    return log


def _sdk_conversation(cfg, variables, handlers, uid, on_agent, on_end):
    from elevenlabs.client import ElevenLabs
    from elevenlabs.conversational_ai.conversation import ClientTools, Conversation, ConversationInitiationData

    tools = ClientTools()
    for name, handler in handlers.items():
        tools.register(name, handler)
    return Conversation(
        ElevenLabs(api_key=config_mod.api_key()), cfg.agent_id, uid, requires_auth=True,
        audio_interface=None,  # text-only
        config=ConversationInitiationData(dynamic_variables=variables),
        client_tools=tools, callback_agent_response=on_agent, callback_end_session=on_end,
    )
