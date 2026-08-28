from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodePilotConfig:
    default_model: str
    api_base_url: str
    api_key_env: str
    allow_write: str
    allow_shell: str
    max_tool_iterations: int
    max_file_chars: int
    max_search_results: int
    shell_timeout_seconds: int
    sessions_dir: Path


DEFAULT_CONFIG = CodePilotConfig(
    default_model="kimi-k3",
    api_base_url="https://api.kimi.com/coding/v1",
    api_key_env="MOONSHOT_API_KEY",
    allow_write="ask",
    allow_shell="ask",
    max_tool_iterations=8,
    max_file_chars=20000,
    max_search_results=100,
    shell_timeout_seconds=30,
    sessions_dir=Path(".codepilot") / "sessions",
)


def config_dir(workspace: Path) -> Path:
    return workspace / ".codepilot"


def config_path(workspace: Path) -> Path:
    return config_dir(workspace) / "config.toml"


def initialize_workspace_config(workspace: Path) -> Path:
    workspace = workspace.resolve()
    target_dir = config_dir(workspace)
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "sessions").mkdir(parents=True, exist_ok=True)

    target = config_path(workspace)
    if not target.exists():
        target.write_text(_render_config(DEFAULT_CONFIG), encoding="utf-8")
    return target


def load_config(workspace: Path) -> CodePilotConfig:
    workspace = workspace.resolve()
    values: dict[str, Any] = {}
    target = config_path(workspace)
    if target.exists():
        values = _parse_simple_toml(target.read_text(encoding="utf-8"))

    config = replace(
        DEFAULT_CONFIG,
        default_model=str(values.get("default_model", DEFAULT_CONFIG.default_model)),
        api_base_url=str(values.get("api_base_url", DEFAULT_CONFIG.api_base_url)),
        api_key_env=str(values.get("api_key_env", DEFAULT_CONFIG.api_key_env)),
        allow_write=str(values.get("allow_write", DEFAULT_CONFIG.allow_write)),
        allow_shell=str(values.get("allow_shell", DEFAULT_CONFIG.allow_shell)),
        max_tool_iterations=int(values.get("max_tool_iterations", DEFAULT_CONFIG.max_tool_iterations)),
        max_file_chars=int(values.get("max_file_chars", DEFAULT_CONFIG.max_file_chars)),
        max_search_results=int(values.get("max_search_results", DEFAULT_CONFIG.max_search_results)),
        shell_timeout_seconds=int(values.get("shell_timeout_seconds", DEFAULT_CONFIG.shell_timeout_seconds)),
        sessions_dir=workspace / ".codepilot" / "sessions",
    )
    return config


def _render_config(config: CodePilotConfig) -> str:
    return "\n".join(
        [
            '# CodePilot workspace configuration',
            '# Store the actual key in your shell environment, not in this file.',
            f'default_model = "{config.default_model}"',
            f'api_base_url = "{config.api_base_url}"',
            f'api_key_env = "{config.api_key_env}"',
            f'allow_write = "{config.allow_write}"',
            f'allow_shell = "{config.allow_shell}"',
            f"max_tool_iterations = {config.max_tool_iterations}",
            f"max_file_chars = {config.max_file_chars}",
            f"max_search_results = {config.max_search_results}",
            f"shell_timeout_seconds = {config.shell_timeout_seconds}",
            "",
        ]
    )


def _parse_simple_toml(content: str) -> dict[str, str | int | bool]:
    values: dict[str, str | int | bool] = {}
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if value.startswith('"') and value.endswith('"'):
            values[key] = value[1:-1]
        elif value.lower() in {"true", "false"}:
            values[key] = value.lower() == "true"
        else:
            values[key] = int(value)
    return values
