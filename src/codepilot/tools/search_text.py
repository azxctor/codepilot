from __future__ import annotations

from dataclasses import dataclass

from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class SearchTextTool:
    workspace: Workspace
    name: str = "search_text"
    description: str = "Search plain text in UTF-8 files inside the current workspace."

    def run(self, args: dict) -> ToolResult:
        query = args.get("query")
        if not query:
            return ToolResult(ok=False, error="search_text 需要 query 参数")

        glob = args.get("glob", "*")
        max_results = int(args.get("max_results", 100))
        try:
            matches = self.workspace.search_text(query=query, glob=glob, max_results=max_results)
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))
        return ToolResult(ok=True, content="\n".join(matches))
