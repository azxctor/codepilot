from __future__ import annotations

from dataclasses import dataclass, field

from codepilot.tools.base import Tool, ToolResult
from codepilot.tools.list_files import ListFilesTool
from codepilot.tools.read_file import ReadFileTool
from codepilot.tools.search_text import SearchTextTool
from codepilot.workspace import Workspace


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def execute(self, name: str, args: dict) -> ToolResult:
        tool = self.tools.get(name)
        if tool is None:
            return ToolResult(ok=False, error=f"未知工具：{name}")
        return tool.run(args)

    def describe_tools(self) -> str:
        if not self.tools:
            return "无可用工具。"
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in self.tools.values())


def default_readonly_registry(workspace: Workspace) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ListFilesTool(workspace))
    registry.register(ReadFileTool(workspace))
    registry.register(SearchTextTool(workspace))
    return registry
