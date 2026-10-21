import io
import json
import queue
import threading

import yaml

from agora_voice import config, talk
from agora_voice.tools import EventLog, Handlers
from conftest import SOURCE


def test_handlers_log_and_strip_call_id(tmp_path):
    log = EventLog(tmp_path / "e.jsonl")
    h = Handlers(log, read_synthesis=lambda prompt: "  I now think X.  ").handlers()
    assert json.loads(h["record_commitment"]({"tool_call_id": "c1", "kind": "bet", "learner_quote": "70"})) == {"ok": True}
    result = json.loads(h["request_synthesis"]({"tool_call_id": "c2", "prompt": "Write it"}))
    assert result["synthesis"] == "I now think X." and "Critique this text" in result["next"]
    events = log.events()
    assert events[0].params == {"kind": "bet", "learner_quote": "70"}
    assert events[1].params == {"prompt": "Write it", "synthesis": "I now think X.", "source": "in-call"}


class FakeConversation:
    """Plays a short session: the agent calls tools in reaction to user messages."""

    def __init__(self, handlers, on_agent, on_end, script):
        self.handlers, self.on_agent, self.on_end, self.script = handlers, on_agent, on_end, script
        self.sent, self.done = [], threading.Event()
        self.work = queue.Queue()
        threading.Thread(target=lambda: [job() for job in iter(self.work.get, None)], daemon=True).start()

    def start_session(self):
        self.on_agent("Hi, ready?")

    def send_user_message(self, text):
        # Like the SDK, run tool handlers in order, off the thread that reads the terminal.
        self.sent.append(text)
        calls = self.script.pop(0) if self.script else []
        last = not self.script

        def act():
            for tool, params in calls:
                result = self.handlers[tool](dict(params, tool_call_id="x"))
                if tool == "request_synthesis":
                    self.on_agent(f"You wrote: {json.loads(result)['synthesis']}")
            if last:
                self.end_session()

        self.work.put(act)

    def end_session(self):
        if not self.done.is_set():
            self.done.set()
            self.on_end()

    def wait_for_session_end(self):
        return "conv_fake"


def run(learner_repo, stdin, script):
    cfg = config.load(learner_repo)
    cfg.agent_id = "agent_x"
    config.save(cfg)
    out = io.StringIO()
    convs = []

    def factory(cfg, variables, handlers, uid, on_agent, on_end):
        assert variables["unit_title"] == "Why AI transformations fail"
        convs.append(FakeConversation(handlers, on_agent, lambda: (finished.set(), on_end()), script))
        return convs[0]

    gate, finished = threading.Event(), threading.Event()

    def typed():
        # Lines after a blank-line marker wait until the agent asks for the synthesis, as a person would.
        before, _, after = stdin.partition("|\n")
        yield from io.StringIO(before)
        gate.wait(5)
        yield from io.StringIO(after)
        finished.wait(5)  # a terminal stays open until the session ends

    term = talk.Terminal(typed(), out)
    threading.Thread(target=lambda: (term.synthesis_wanted.wait(5), gate.set()), daemon=True).start()
    log = talk.run_text(learner_repo, SOURCE, "transformation", None, terminal=term, conversation_factory=factory)
    return log, out.getvalue(), convs[0]


def test_text_session_routes_synthesis_lines_to_the_tool(learner_repo):
    script = [
        [("record_hook", {"format": "forced dilemma", "headline": "40%"})],
        [("record_commitment", {"kind": "choice", "summary": "failure", "learner_quote": "failure"}),
         ("request_synthesis", {"prompt": "Type it"})],
    ]
    # The second message triggers the synthesis; the lines after | are the synthesis, ended by a blank line.
    log, out, conv = run(learner_repo, "go\nfailure\n|\nLine one.\nLine two.\n\n", script)
    assert conv.sent == ["go", "failure"]
    assert [e.tool for e in log] == ["session_start", "record_hook", "record_commitment", "request_synthesis", "conversation"]
    assert log.events("request_synthesis")[0].params["synthesis"] == "Line one.\nLine two."
    assert log.conversation_id == "conv_fake"
    assert "You wrote: Line one." in out


def test_missing_synthesis_is_asked_after_the_call(learner_repo):
    log, out, _ = run(learner_repo, "go\n|\nMy synthesis.\n\n", [[("record_hook", {"format": "f", "headline": "h"})]])
    (synth,) = log.events("request_synthesis")
    assert synth.params == {"prompt": "post-call", "synthesis": "My synthesis.", "source": "post-call"}
    assert "ended without a synthesis" in out
    assert log.session["unit"] == "transformation"


def test_strip_fillers():
    phrases = talk.fillers()
    assert "Okay..." in phrases
    assert talk.strip_fillers("Okay... Thanks. Now the debrief.", phrases) == "Thanks. Now the debrief."
    assert talk.strip_fillers("Hmm, let me think about that. Give me a second.", phrases) == ""
    assert talk.strip_fillers("Okay, so you said seventy.", phrases) == "Okay, so you said seventy."
    assert talk.strip_fillers("[warm] Great. [slow] Take care.", phrases) == "Great. Take care."
