import pytest

from agora_voice import config


def test_missing_file_gives_defaults(tmp_path):
    cfg = config.load(tmp_path)
    assert cfg.agent_id is None
    assert cfg.max_duration_seconds == 2400
    assert cfg.path == tmp_path / ".agora" / "voice.toml"


def test_reads_file(tmp_path):
    (tmp_path / ".agora").mkdir()
    (tmp_path / ".agora" / "voice.toml").write_text(
        'agent_id = "agent_123"\nlanguage = "zh"\nunknown = 1\n\n[tool_ids]\nrecord_hook = "tool_1"\n',
        encoding="utf-8",
    )
    cfg = config.load(tmp_path)
    assert (cfg.agent_id, cfg.language, cfg.tool_ids) == ("agent_123", "zh", {"record_hook": "tool_1"})


def test_api_key_from_env(monkeypatch):
    monkeypatch.delenv(config.API_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError):
        config.api_key()
    monkeypatch.setenv(config.API_KEY_ENV, "k")
    assert config.api_key() == "k"
