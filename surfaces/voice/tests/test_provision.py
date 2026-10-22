import copy
import itertools
import json
import os

import pytest

from agora_voice import config, provision


class FakeApi:
    """In-memory stand-in for the ElevenLabs API. Like the real one, it adds
    defaults and ids to what it stores, so `contains` has to ignore extras."""

    def __init__(self):
        self.tools, self.agents, self.writes = {}, {}, []
        self.ids = itertools.count(1)

    def get(self, path):
        kind, _, obj_id = path.rpartition("/")
        store = self.tools if "tools" in kind else self.agents
        if obj_id not in store:
            raise KeyError(path)
        return copy.deepcopy(store[obj_id])

    def post(self, path, body):
        self.writes.append(("POST", path))
        if path == "/v1/convai/tools":
            tool_id = f"tool_{next(self.ids)}"
            cfg = dict(body["tool_config"], disable_interruptions=False)
            self.tools[tool_id] = {"id": tool_id, "tool_config": cfg}
            return {"id": tool_id}
        agent_id = f"agent_{next(self.ids)}"
        self.agents[agent_id] = dict(copy.deepcopy(body), agent_id=agent_id, metadata={"created_at_unix_secs": 1})
        return {"agent_id": agent_id}

    def patch(self, path, body):
        self.writes.append(("PATCH", path))
        obj_id = path.rpartition("/")[2]
        if "tools" in path:
            self.tools[obj_id]["tool_config"] = body["tool_config"]
        else:
            self.agents[obj_id] = provision.merge(self.agents[obj_id], body)
        return {}


@pytest.fixture
def cfg(tmp_path):
    return config.load(tmp_path)


def test_creates_tools_and_agent_and_saves_ids(cfg):
    api = FakeApi()
    result = provision.setup(cfg, api)
    assert len(result.tool_ids) == 7 and "queue_research" in result.tool_ids
    assert result.changes[-2:] == ["created agent", "created web agent"]

    saved = config.load(cfg.learner_repo)
    assert saved.agent_id == result.agent_id and saved.tool_ids == result.tool_ids
    assert saved.web_agent_id == result.web_agent_id != result.agent_id

    web = api.agents[result.web_agent_id]
    assert web["name"] == "Agora (web)"
    assert web["conversation_config"]["agent"]["prompt"]["tool_ids"] == []
    assert web["conversation_config"]["agent"]["prompt"]["prompt"] == provision.WEB_PROMPT.read_text(encoding="utf-8")

    agent = api.agents[result.agent_id]
    prompt = agent["conversation_config"]["agent"]["prompt"]
    assert prompt["llm"] == "claude-sonnet-5-5" and prompt["reasoning_effort"] == "low"
    assert prompt["tool_ids"] == list(result.tool_ids.values())
    assert prompt["backup_llm_config"] == {"preference": "override", "order": ["claude-haiku-5-5"]}
    assert prompt["cascade_timeout_seconds"] == 8
    assert prompt["prompt"] == provision.PROMPT.read_text(encoding="utf-8")
    assert agent["conversation_config"]["conversation"]["max_duration_seconds"] == 2400
    assert agent["conversation_config"]["agent"]["first_message"] == "{{opening_line}}"
    assert "synthesis" not in agent["platform_settings"]["data_collection"]
    assert {"positions", "research_questions", "commitment_kind"} <= set(agent["platform_settings"]["data_collection"])


def test_second_run_changes_nothing(cfg):
    api = FakeApi()
    provision.setup(cfg, api)
    writes = len(api.writes)
    result = provision.setup(config.load(cfg.learner_repo), api)
    assert result.changes == [] and len(api.writes) == writes


def test_updates_only_what_changed(cfg, monkeypatch):
    api = FakeApi()
    provision.setup(cfg, api)
    cfg = config.load(cfg.learner_repo)
    cfg.llm = "claude-haiku-5-5"
    assert provision.setup(cfg, api).changes == ["updated agent", "updated web agent"]


def test_recreates_a_tool_deleted_on_elevenlabs(cfg):
    api = FakeApi()
    first = provision.setup(cfg, api)
    del api.tools[first.tool_ids["record_hook"]]
    second = provision.setup(config.load(cfg.learner_repo), api)
    assert second.changes[0] == "created tool record_hook"
    assert "updated agent" in second.changes  # new tool id attached


def test_refuses_stale_prompt(tmp_path, monkeypatch):
    prompt = tmp_path / "agent-prompt.md"
    prompt.write_text("old", encoding="utf-8")
    os.utime(prompt, (0, 0))
    with pytest.raises(provision.ProvisionError, match="build-surfaces.sh"):
        provision.check_prompt_fresh(prompt)
    with pytest.raises(provision.ProvisionError, match="missing"):
        provision.check_prompt_fresh(tmp_path / "none.md")


def test_contains():
    assert provision.contains({"a": 1, "b": {"c": [1, 2], "d": 0}}, {"b": {"c": [1, 2]}})
    assert not provision.contains({"a": [1, 2, 3]}, {"a": [1, 2]})
    assert not provision.contains({"a": 1}, {"a": 1, "b": 2})
    assert provision.contains({"t": 0.6000000001}, {"t": 0.6})


def test_agent_files_are_consistent():
    tools = provision.load_json("tools.json")
    names = [t["name"] for t in tools]
    assert names == ["record_hook", "record_commitment", "record_position", "propose_idea",
                     "queue_research", "record_converge", "request_synthesis"]
    prompt = provision.PROMPT.read_text(encoding="utf-8")
    assert all(f"`{n}`" in prompt for n in names)  # voice-tools.md tells the agent about each one
    for t in tools:
        assert set(t["parameters"]["required"]) <= set(t["parameters"]["properties"]), t["name"]
    synth = next(t for t in tools if t["name"] == "request_synthesis")
    assert synth["expects_response"] and synth["response_timeout_secs"] == -1


def test_config_round_trip(tmp_path):
    cfg = config.load(tmp_path)
    cfg.agent_id, cfg.language, cfg.tool_ids = "agent_1", "zh", {"record_hook": "tool_\"1\""}
    config.save(cfg)
    again = config.load(tmp_path)
    assert (again.agent_id, again.language, again.tool_ids) == ("agent_1", "zh", {"record_hook": "tool_\"1\""})
    assert "API key" in cfg.path.read_text(encoding="utf-8")
