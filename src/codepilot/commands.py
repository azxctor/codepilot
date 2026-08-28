from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommand:
    name: str
    args: list[str]


def parse_slash_command(text: str) -> SlashCommand | None:
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None

    parts = stripped[1:].split()
    if not parts:
        return None

    return SlashCommand(name=parts[0], args=parts[1:])
