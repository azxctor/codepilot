from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    content: str = ""
    error: str | None = None


class Tool(Protocol):
    name: str
    description: str

    def run(self, args: dict) -> ToolResult:
        ...
