from __future__ import annotations

from dataclasses import dataclass

from codepilot.approval import ApprovalPolicy, ApprovalRequest, format_rejection
from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class PatchFileTool:
    workspace: Workspace
    approval_policy: ApprovalPolicy
    name: str = "patch_file"
    description: str = "Replace one unique text occurrence in a UTF-8 file inside the current workspace after confirmation."

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        old = args.get("old")
        new = args.get("new")
        if not isinstance(path, str) or not path:
            return ToolResult(ok=False, error="patch_file 需要 path 参数")
        if not isinstance(old, str) or old == "":
            return ToolResult(ok=False, error="patch_file 需要非空 old 字符串参数")
        if not isinstance(new, str):
            return ToolResult(ok=False, error="patch_file 需要 new 字符串参数")

        try:
            target = self.workspace.resolve_path(path)
            if not target.exists():
                return ToolResult(ok=False, error=f"文件不存在：{path}")
            if not target.is_file():
                return ToolResult(ok=False, error=f"不是文件：{path}")

            content = target.read_text(encoding="utf-8")
            matches = content.count(old)
            if matches != 1:
                return ToolResult(ok=False, error=f"匹配次数必须为 1，实际为 {matches}：{path}")

            request = ApprovalRequest(
                action="patch_file",
                target=path,
                risk="write",
                preview=f"替换前：\n{_preview_text(old)}\n替换后：\n{_preview_text(new)}",
            )
            decision = self.approval_policy.decide(request)
            if not decision.approved:
                return ToolResult(ok=False, error=format_rejection(decision, "patch_file"))

            target.write_text(content.replace(old, new, 1), encoding="utf-8")
            return ToolResult(ok=True, content=f"已修改文件：{path}")
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))


def _preview_text(content: str, max_chars: int = 1000) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n...（预览已截断）"
