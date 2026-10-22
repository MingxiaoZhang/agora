import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).parent / "fixtures"
SOURCE = "ai-future-is-now"


@pytest.fixture(autouse=True)
def isolated_user_config(tmp_path, monkeypatch):
    """Keep tests away from the real ~/.config/agora and $AGORA_LEARNER_REPO."""
    from agora_voice import config
    monkeypatch.setattr(config, "USER_CONFIG", tmp_path / "user-config" / "voice.toml")
    monkeypatch.delenv(config.LEARNER_REPO_ENV, raising=False)


@pytest.fixture
def learner_repo(tmp_path):
    """A learner repo built from the template, with the example spine as its one source."""
    repo = tmp_path / "learner-repo"
    shutil.copytree(ROOT / "templates" / "learner-repo", repo)
    (repo / "sources" / SOURCE).mkdir(parents=True)
    shutil.copy(ROOT / "examples" / SOURCE / "spine.yaml", repo / "sources" / SOURCE / "spine.yaml")
    return repo


@pytest.fixture
def session_dir():
    return FIXTURES / "ch09-session"
