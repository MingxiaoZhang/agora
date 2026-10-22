"""Per-learner-repo settings in `.agora/voice.toml` (DESIGN.md §4).

The API key is never stored here; it comes from ELEVENLABS_API_KEY.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

CONFIG_PATH = Path(".agora") / "voice.toml"
API_KEY_ENV = "ELEVENLABS_API_KEY"


@dataclass
class Config:
    learner_repo: Path
    agent_id: str | None = None          # CLI agent, with client tools (talk --text)
    web_agent_id: str | None = None      # web agent, no tools (talk --web, ElevenLabs' talk page)
    voice_id: str | None = None
    llm: str = "claude-sonnet-5-5"
    reasoning_effort: str = "low"
    # If the main model hasn't started replying after `cascade_timeout_seconds`, ElevenLabs
    # hands the turn to the backup. Its own default backups aren't Claude, and in dry runs
    # they wrote the converge and synthesis turns, badly. "" disables the backup.
    backup_llm: str = "claude-haiku-5-5"
    cascade_timeout_seconds: int = 8
    language: str = "en"
    save_transcripts: bool = False
    max_duration_seconds: int = 2400
    tool_ids: dict[str, str] = field(default_factory=dict)

    @property
    def path(self) -> Path:
        return self.learner_repo / CONFIG_PATH


def load(learner_repo: Path) -> Config:
    """Read the config for a learner repo. A missing file gives defaults."""
    learner_repo = Path(learner_repo)
    path = learner_repo / CONFIG_PATH
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    known = {k: data[k] for k in Config.__dataclass_fields__ if k in data and k != "learner_repo"}
    return Config(learner_repo=learner_repo, **known)


def api_key() -> str:
    key = os.environ.get(API_KEY_ENV)
    if not key:
        raise RuntimeError(f"{API_KEY_ENV} is not set.")
    return key


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)  # JSON string escapes are valid TOML


def save(cfg: Config) -> None:
    """Write the config back. `setup` owns `agent_id` and `[tool_ids]`; the rest is kept as loaded."""
    lines = ["# Agora voice settings. No secrets: the API key comes from ELEVENLABS_API_KEY.", ""]
    for name in Config.__dataclass_fields__:
        value = getattr(cfg, name)
        if name in ("learner_repo", "tool_ids") or value is None:
            continue
        lines.append(f"{name} = {_toml_value(value)}")
    if cfg.tool_ids:
        lines += ["", "[tool_ids]"] + [f"{k} = {_toml_value(v)}" for k, v in cfg.tool_ids.items()]
    cfg.path.parent.mkdir(parents=True, exist_ok=True)
    cfg.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
