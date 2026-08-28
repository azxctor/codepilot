from __future__ import annotations

from dataclasses import dataclass

from codepilot.approval import ApprovalPolicy, ApprovalRequest, format_rejection
from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class WriteFileTool:
    workspace: Workspace
    approval_policy: ApprovalPolicy
    name: str = "write_file"
    description: str = "Create or overwrite a UTF-8 text file inside the current workspace after confirmation."

    def run(self, args: dict) -> ToolResult:
        path = args.get("path")
        content = args.get("content")
        mode = args.get("mode", "create")
        if not isinstance(path, str) or not path:
            return ToolResult(ok=False, error="write_file 需要 path 参数")
        if not isinstance(content, str):
            return ToolResult(ok=False, error="write_file 需要 content 字符串参数")
        if mode not in {"create", "overwrite"}:
            return ToolResult(ok=False, error=f"write_file mode 只支持 create 或 overwrite：{mode}")

        try:
            target = self.workspace.resolve_path(path)
            if not target.parent.is_dir():
                parent = target.parent.relative_to(self.workspace.root).as_posix()
                return ToolResult(ok=False, error=f"父目录不存在：{parent}")
            if mode == "create" and target.exists():
                return ToolResult(ok=False, error=f"文件已存在：{path}")
            if mode == "overwrite" and not target.exists():
                return ToolResult(ok=False, error=f"文件不存在，无法覆盖：{path}")

            request = ApprovalRequest(
                action="write_file",
                target=path,
                risk="write",
                preview=f"模式：{mode}\n内容预览：\n{_preview_text(content)}",
            )
            decision = self.approval_policy.decide(request)
            if not decision.approved:
                return ToolResult(ok=False, error=format_rejection(decision, "write_file"))

            target.write_text(content, encoding="utf-8")
            return ToolResult(ok=True, content=f"已写入文件：{path}（{len(content)} 字符）")
        except Exception as exc:
            return ToolResult(ok=False, error=str(exc))


def _preview_text(content: str, max_lines: int = 20, max_chars: int = 2000) -> str:
    clipped = content[:max_chars]
    lines = clipped.splitlines()
    rendered = "\n".join(lines[:max_lines])
    if len(content) > max_chars or len(lines) > max_lines:
        rendered += "\n...（预览已截断）"
    return rendered
