"""Per-learner-repo settings in `.agora/voice.toml` (DESIGN.md §4).

The API key is never stored here; it comes from ELEVENLABS_API_KEY.
"""

from __future__ import annotations

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
    agent_id: str | None = None
    voice_id: str | None = None
    llm: str = "claude-sonnet-5-5"
    reasoning_effort: str = "low"
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
