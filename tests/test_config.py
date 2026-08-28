from pathlib import Path

from codepilot.config import DEFAULT_CONFIG, initialize_workspace_config, load_config


def test_initialize_workspace_config_creates_config_and_sessions(tmp_path: Path) -> None:
    config_path = initialize_workspace_config(tmp_path)

    assert config_path == tmp_path / ".codepilot" / "config.toml"
    assert config_path.exists()
    assert (tmp_path / ".codepilot" / "sessions").is_dir()
    assert 'default_model = "gpt-4.1-mini"' in config_path.read_text()


def test_load_config_returns_defaults_when_config_is_missing(tmp_path: Path) -> None:
    config = load_config(tmp_path)

    assert config.default_model == DEFAULT_CONFIG.default_model
    assert config.allow_write == "ask"
    assert config.allow_shell == "ask"
    assert config.max_tool_iterations == 8


def test_load_config_reads_initialized_config(tmp_path: Path) -> None:
    initialize_workspace_config(tmp_path)

    config = load_config(tmp_path)

    assert config.default_model == "gpt-4.1-mini"
    assert config.api_base_url == "https://api.openai.com/v1"
    assert config.sessions_dir == tmp_path / ".codepilot" / "sessions"
