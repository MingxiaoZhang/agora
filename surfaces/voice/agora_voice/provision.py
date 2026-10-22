"""Create or update the ElevenLabs tools and agent from this repo (DESIGN.md §5).

Idempotent: each tool and the agent are compared with what's already on
ElevenLabs, and only updated when something differs, so a second run in a
row changes nothing.
"""

from __future__ import annotations

import copy
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import config as config_mod
from .config import Config

SURFACE_DIR = Path(__file__).resolve().parents[1]
AGENT_DIR = SURFACE_DIR / "agent"
PROMPT = SURFACE_DIR / "generated" / "agent-prompt.md"
WEB_PROMPT = SURFACE_DIR / "generated" / "agent-prompt.web.md"
WEB_NAME = "Agora (web)"
REPO_ROOT = SURFACE_DIR.parents[1]
API = "https://api.elevenlabs.io"


class ProvisionError(Exception):
    pass


class Api:
    """Minimal JSON client for the ElevenLabs REST API."""

    def __init__(self, key: str, base: str = API):
        self.key, self.base = key, base

    def request(self, method: str, path: str, body: Any = None) -> Any:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"xi-api-key": self.key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise KeyError(path) from None
            raise ProvisionError(f"{method} {path}: HTTP {e.code}: {e.read().decode(errors='replace')[:500]}") from None
        return json.loads(raw) if raw else None

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, body: Any) -> Any:
        return self.request("POST", path, body)

    def patch(self, path: str, body: Any) -> Any:
        return self.request("PATCH", path, body)


def check_prompt_fresh(*prompts: Path) -> None:
    """Refuse a generated prompt older than anything it's built from."""
    for prompt in prompts or (PROMPT, WEB_PROMPT):
        if not prompt.exists():
            raise ProvisionError(f"{prompt} is missing. Run scripts/build-surfaces.sh.")
        sources = list((REPO_ROOT / "method").glob("*.md")) + list(AGENT_DIR.glob("*.md"))
        newer = [s for s in sources if s.stat().st_mtime > prompt.stat().st_mtime]
        if newer:
            names = ", ".join(str(s.relative_to(REPO_ROOT)) for s in newer)
            raise ProvisionError(f"{prompt.name} is older than {names}. Run scripts/build-surfaces.sh.")


def contains(actual: Any, desired: Any) -> bool:
    """True if everything in `desired` is already in `actual`. Extra keys the
    server adds (defaults, ids, timestamps) don't count as differences."""
    if isinstance(desired, dict):
        return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k, v in desired.items())
    if isinstance(desired, list):
        return (isinstance(actual, list) and len(actual) == len(desired)
                and all(contains(a, d) for a, d in zip(actual, desired)))
    if isinstance(desired, float) or isinstance(actual, float):
        return isinstance(actual, (int, float)) and abs(actual - desired) < 1e-9
    return actual == desired


def merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_json(name: str) -> Any:
    return json.loads((AGENT_DIR / name).read_text(encoding="utf-8"))


def agent_body(cfg: Config, tool_ids: list[str], prompt: str, name: str | None = None) -> dict:
    extra: dict[str, Any] = {
        "conversation_config": {
            "agent": {
                "language": cfg.language,
                "prompt": {"prompt": prompt, "llm": cfg.llm, "reasoning_effort": cfg.reasoning_effort,
                           "tool_ids": tool_ids, "cascade_timeout_seconds": cfg.cascade_timeout_seconds,
                           "backup_llm_config": ({"preference": "override", "order": [cfg.backup_llm]}
                                                 if cfg.backup_llm else {"preference": "disabled"})},
            },
            "conversation": {"max_duration_seconds": cfg.max_duration_seconds},
        },
        "platform_settings": {"data_collection": load_json("data-collection.json")},
    }
    if cfg.voice_id:
        extra["conversation_config"]["tts"] = {"voice_id": cfg.voice_id}
    if name:
        extra["name"] = name
    return merge(load_json("agent.template.json"), extra)


@dataclass
class Result:
    tool_ids: dict[str, str] = field(default_factory=dict)
    agent_id: str = ""
    web_agent_id: str = ""
    changes: list[str] = field(default_factory=list)   # e.g. "created tool record_hook"


def sync_tools(api: Api, cfg: Config, result: Result) -> None:
    for tool in load_json("tools.json"):
        name = tool["name"]
        tool_id = cfg.tool_ids.get(name)
        current = None
        if tool_id:
            try:
                current = api.get(f"/v1/convai/tools/{tool_id}")
            except KeyError:
                current = None  # deleted on ElevenLabs; recreate
        if current is None:
            tool_id = api.post("/v1/convai/tools", {"tool_config": tool})["id"]
            result.changes.append(f"created tool {name}")
        elif not contains(current.get("tool_config"), tool):
            api.patch(f"/v1/convai/tools/{tool_id}", {"tool_config": tool})
            result.changes.append(f"updated tool {name}")
        result.tool_ids[name] = tool_id


def sync_agent(api: Api, agent_id: str | None, body: dict, label: str, result: Result) -> str:
    """Create the agent, or update it if it differs from `body`. Returns its id."""
    current = None
    if agent_id:
        try:
            current = api.get(f"/v1/convai/agents/{agent_id}")
        except KeyError:
            current = None
    if current is None:
        result.changes.append(f"created {label}")
        return api.post("/v1/convai/agents/create", body)["agent_id"]
    if not contains(current, body):
        api.patch(f"/v1/convai/agents/{agent_id}", body)
        result.changes.append(f"updated {label}")
    return agent_id


def sync_agents(api: Api, cfg: Config, result: Result) -> None:
    tool_ids = [result.tool_ids[t["name"]] for t in load_json("tools.json")]
    cli = agent_body(cfg, tool_ids, PROMPT.read_text(encoding="utf-8"))
    result.agent_id = sync_agent(api, cfg.agent_id, cli, "agent", result)
    # The web agent runs on ElevenLabs' talk page, where client tools can't run.
    web = agent_body(cfg, [], WEB_PROMPT.read_text(encoding="utf-8"), WEB_NAME)
    result.web_agent_id = sync_agent(api, cfg.web_agent_id, web, "web agent", result)


def setup(cfg: Config, api: Api | None = None) -> Result:
    check_prompt_fresh()
    api = api or Api(config_mod.api_key())
    result = Result()
    sync_tools(api, cfg, result)
    sync_agents(api, cfg, result)
    cfg.agent_id, cfg.web_agent_id, cfg.tool_ids = result.agent_id, result.web_agent_id, result.tool_ids
    config_mod.save(cfg)
    return result
