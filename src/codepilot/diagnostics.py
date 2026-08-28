from __future__ import annotations

import os
from typing import Mapping

from codepilot.config import CodePilotConfig
from codepilot.llm import MissingAPIKeyError, resolve_api_key


def build_doctor_report(config: CodePilotConfig, env: Mapping[str, str] | None = None) -> list[str]:
    active_env = env if env is not None else os.environ
    lines = [
        "CodePilot doctor",
        f"api_base_url: {config.api_base_url}",
        f"default_model: {config.default_model}",
        f"configured_api_key_env: {config.api_key_env}",
    ]
    if config.api_key_env == "CODEPILOT_API_KEY":
        lines.append('migration_hint: set api_key_env to "MOONSHOT_API_KEY" for the official Moonshot env name')

    try:
        resolved = resolve_api_key(config, active_env)
    except MissingAPIKeyError as exc:
        lines.append("active_api_key_env: missing")
        lines.append(f"api_key_status: {exc}")
        return lines

    lines.append(f"active_api_key_env: {resolved.env_name}")
    lines.append(f"api_key_status: present ({_mask_secret(resolved.value)})")
    return lines


def _mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"
