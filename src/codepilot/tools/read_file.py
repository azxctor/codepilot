from __future__ import annotations

from dataclasses import dataclass

from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class ReadFileTool:
    workspace: Workspace
    name: str = "read_file"
    description: str = "Read a UTF-8 text file inside the current workspace."

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        if not path:
            return ToolResult(ok=False, error="read_file 需要 path 参数")

        try:
            content = self.workspace.read_file(
                path=path,
                start_line=args.get("start_line"),
                end_line=args.get("end_line"),
            )
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(ok=True, content=content)
