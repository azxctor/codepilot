from __future__ import annotations

from dataclasses import dataclass

from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class ListFilesTool:
    workspace: Workspace
    name: str = "list_files"
    description: str = "List files under the current workspace."

    def run(self, args: dict) -> ToolResult:
        path = args.get("path", ".")
        max_depth = int(args.get("max_depth", 4))
        max_results = int(args.get("max_results", 300))
        try:
            files = self.workspace.list_files(path=path, max_depth=max_depth, max_results=max_results)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(ok=True, content="\n".join(files))
