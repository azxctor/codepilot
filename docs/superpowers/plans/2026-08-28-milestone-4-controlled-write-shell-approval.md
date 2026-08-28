# 里程碑 4：受控写入、shell 和确认机制实现计划

> **面向自动化执行者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪状态。

**目标：** 在现有 Agent 工具循环上加入受控写入、受控 shell 执行和每次危险动作确认机制。

**架构：** 复用 Milestone 3 的 `ToolRegistry` 和 JSON 工具协议。新增 `approval.py` 统一审批模型，新增 `shell.py` 封装命令校验和执行，新增三个需确认工具：`write_file`、`patch_file`、`run_shell`。Agent 仍只负责调用工具和回传结果，不直接承担审批逻辑。

**技术栈：** Python 3.10 标准库、`dataclasses`、`pathlib`、`subprocess`、`shlex`、pytest。

---

## 文件结构

- 创建：`src/codepilot/approval.py`，负责审批请求、审批结果和审批策略。
- 创建：`src/codepilot/shell.py`，负责 shell 命令静态拦截、执行、超时和结果格式化。
- 创建：`src/codepilot/tools/write_file.py`，实现 `write_file` 工具。
- 创建：`src/codepilot/tools/patch_file.py`，实现 `patch_file` 工具。
- 创建：`src/codepilot/tools/run_shell.py`，实现 `run_shell` 工具。
- 修改：`src/codepilot/tools/__init__.py`，新增完整默认工具注册表。
- 修改：`src/codepilot/agent.py`，更新默认系统提示和 `create_default_agent()` 注入审批策略。
- 修改：`src/codepilot/interaction.py`，让交互会话可以注入审批输入。
- 修改：`src/codepilot/cli.py`，让 `run` 和 `chat` 使用带确认能力的默认 Agent。
- 修改：`README.md`，记录 Milestone 4 的本地使用方式和安全限制。
- 测试：`tests/test_approval.py`。
- 测试：`tests/test_write_tools.py`。
- 测试：`tests/test_shell.py`。
- 测试：`tests/test_agent.py`。
- 测试：`tests/test_cli.py`。
- 测试：`tests/test_interaction.py`。

### 任务 1：审批模型和策略

**文件：**

- 创建：`src/codepilot/approval.py`
- 测试：`tests/test_approval.py`

- [ ] **步骤 1：编写失败的审批测试**

在 `tests/test_approval.py` 中新增：

```python
from codepilot.approval import ApprovalPolicy, ApprovalRequest


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


def test_approval_policy_ask_allows_when_user_inputs_y() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is True
    assert "需要确认执行动作" in "\n".join(output.lines)
    assert "write_file" in "\n".join(output.lines)


def test_approval_policy_ask_rejects_when_user_inputs_anything_else() -> None:
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="ask",
        input_reader=lambda: "n",
        output=FakeOutput(),
    )

    decision = policy.decide(
        ApprovalRequest(
            action="patch_file",
            target="README.md",
            risk="write",
            preview="替换文本",
        )
    )

    assert decision.approved is False
    assert decision.reason == "用户拒绝执行"


def test_approval_policy_never_rejects_without_prompt() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="never",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is False
    assert decision.reason == "配置禁止 write 动作"
    assert output.lines == []


def test_approval_policy_never_rejects_shell_without_prompt() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="never",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="run_shell",
            target="python3 -m pytest -q",
            risk="shell",
            preview="运行测试",
        )
    )

    assert decision.approved is False
    assert decision.reason == "配置禁止 shell 动作"
    assert output.lines == []


def test_approval_policy_invalid_mode_rejects_conservatively() -> None:
    policy = ApprovalPolicy(
        allow_write="always",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=FakeOutput(),
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is False
    assert "配置值无效" in decision.reason
```

- [ ] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_approval.py -q
```

预期：失败，错误包含 `ModuleNotFoundError: No module named 'codepilot.approval'`。

- [ ] **步骤 3：实现审批模型**

在 `src/codepilot/approval.py` 中实现：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class ApprovalOutput(Protocol):
    def write(self, message: str) -> None:
        ...


class StdoutApprovalOutput:
    def write(self, message: str) -> None:
        print(message)


@dataclass(frozen=True)
class ApprovalRequest:
    action: str
    target: str
    risk: str
    preview: str


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reason: str = ""


@dataclass
class ApprovalPolicy:
    allow_write: str = "ask"
    allow_shell: str = "ask"
    input_reader: Callable[[], str] | None = None
    output: ApprovalOutput | None = None

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        mode = self._mode_for(request.risk)
        if mode not in {"ask", "never"}:
            return ApprovalDecision(False, f"配置值无效：{request.risk}={mode}")
        if mode == "never":
            return ApprovalDecision(False, f"配置禁止 {request.risk} 动作")

        out = self.output or StdoutApprovalOutput()
        out.write("需要确认执行动作：")
        out.write(f"动作：{request.action}")
        out.write(f"目标：{request.target}")
        out.write(f"风险：{request.risk}")
        out.write("预览：")
        out.write(request.preview)
        out.write("输入 y 执行，其他输入拒绝。")

        reader = self.input_reader or (lambda: input("确认执行？ "))
        answer = reader().strip().lower()
        if answer == "y":
            return ApprovalDecision(True, "用户确认执行")
        return ApprovalDecision(False, "用户拒绝执行")

    def _mode_for(self, risk: str) -> str:
        if risk == "write":
            return self.allow_write
        if risk == "shell":
            return self.allow_shell
        return "never"


def format_rejection(decision: ApprovalDecision, action: str) -> str:
    return f"用户拒绝执行：{action}（{decision.reason}）"
```

- [ ] **步骤 4：验证审批测试通过**

```bash
python3 -m pytest tests/test_approval.py -q
```

预期：`5 passed`。

- [ ] **步骤 5：提交审批模型**

```bash
git add src/codepilot/approval.py tests/test_approval.py
git commit -m "feat: add approval policy"
```

预期：创建只包含审批模型和测试的提交。

### 任务 2：受控写入和单文件替换工具

**文件：**

- 创建：`src/codepilot/tools/write_file.py`
- 创建：`src/codepilot/tools/patch_file.py`
- 测试：`tests/test_write_tools.py`

- [ ] **步骤 1：编写失败的写入工具测试**

在 `tests/test_write_tools.py` 中新增：

```python
from pathlib import Path

from codepilot.approval import ApprovalDecision, ApprovalPolicy, ApprovalRequest
from codepilot.tools.patch_file import PatchFileTool
from codepilot.tools.write_file import WriteFileTool
from codepilot.workspace import Workspace


class FakeApprovalPolicy:
    def __init__(self, approved: bool = True) -> None:
        self.approved = approved
        self.requests: list[ApprovalRequest] = []

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        if self.approved:
            return ApprovalDecision(True, "允许")
        return ApprovalDecision(False, "用户拒绝执行")


def test_write_file_create_writes_after_approval(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy()
    tool = WriteFileTool(Workspace(tmp_path), approval)

    result = tool.run({"path": "notes.md", "content": "hello\n", "mode": "create"})

    assert result.ok is True
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "hello\n"
    assert approval.requests[0].action == "write_file"
    assert approval.requests[0].risk == "write"


def test_write_file_create_rejects_existing_file(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("old\n", encoding="utf-8")
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "notes.md", "content": "new\n", "mode": "create"})

    assert result.ok is False
    assert "文件已存在" in result.error
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "old\n"


def test_write_file_overwrite_updates_existing_file_after_approval(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("old\n", encoding="utf-8")
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "notes.md", "content": "new\n", "mode": "overwrite"})

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_overwrite_rejects_missing_file(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "missing.md", "content": "new\n", "mode": "overwrite"})

    assert result.ok is False
    assert "文件不存在" in result.error


def test_write_file_rejects_missing_parent_directory(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "missing/notes.md", "content": "new\n", "mode": "create"})

    assert result.ok is False
    assert "父目录不存在" in result.error


def test_write_file_rejects_when_approval_denies(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy(approved=False)
    tool = WriteFileTool(Workspace(tmp_path), approval)

    result = tool.run({"path": "notes.md", "content": "hello\n", "mode": "create"})

    assert result.ok is False
    assert "用户拒绝执行" in result.error
    assert not (tmp_path / "notes.md").exists()


def test_patch_file_replaces_unique_text_after_approval(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "beta", "new": "gamma"})

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "alpha\ngamma\n"


def test_patch_file_rejects_multiple_matches(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("same\nsame\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "same", "new": "next"})

    assert result.ok is False
    assert "匹配次数必须为 1" in result.error
    assert target.read_text(encoding="utf-8") == "same\nsame\n"


def test_patch_file_rejects_missing_old_text(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("alpha\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "missing", "new": "next"})

    assert result.ok is False
    assert "匹配次数必须为 1，实际为 0" in result.error
    assert target.read_text(encoding="utf-8") == "alpha\n"


def test_write_file_rejects_parent_escape(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "../outside.txt", "content": "bad", "mode": "create"})

    assert result.ok is False
    assert "路径越界" in result.error
```

- [ ] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_write_tools.py -q
```

预期：失败，错误包含 `ModuleNotFoundError`，因为写入工具尚未实现。

- [ ] **步骤 3：实现 `write_file` 工具**

在 `src/codepilot/tools/write_file.py` 中实现：

```python
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
                return ToolResult(ok=False, error=f"父目录不存在：{target.parent.relative_to(self.workspace.root).as_posix()}")
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
```

- [ ] **步骤 4：实现 `patch_file` 工具**

在 `src/codepilot/tools/patch_file.py` 中实现：

```python
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
```

- [ ] **步骤 5：验证写入工具测试通过**

```bash
python3 -m pytest tests/test_write_tools.py -q
```

预期：`10 passed`。

- [ ] **步骤 6：提交写入工具**

```bash
git add src/codepilot/tools/write_file.py src/codepilot/tools/patch_file.py tests/test_write_tools.py
git commit -m "feat: add confirmed write tools"
```

预期：创建只包含写入工具和测试的提交。

### 任务 3：shell 命令校验和执行器

**文件：**

- 创建：`src/codepilot/shell.py`
- 测试：`tests/test_shell.py`

- [ ] **步骤 1：编写失败的 shell 执行器测试**

在 `tests/test_shell.py` 中新增：

```python
from pathlib import Path

from codepilot.shell import run_shell_command, validate_shell_command


def test_validate_shell_command_allows_normal_test_command() -> None:
    assert validate_shell_command("python3 -m pytest -q") is None


def test_validate_shell_command_rejects_sudo() -> None:
    assert "sudo" in validate_shell_command("sudo ls").lower()


def test_validate_shell_command_rejects_git_reset_hard() -> None:
    assert "git reset --hard" in validate_shell_command("git reset --hard").lower()


def test_validate_shell_command_rejects_background_command() -> None:
    assert "后台" in validate_shell_command("python3 -m http.server &")


def test_run_shell_command_returns_stdout_and_exit_code(tmp_path: Path) -> None:
    result = run_shell_command(
        "python3 -c \"print('hello')\"",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == "hello"
    assert result.stderr == ""
    assert result.timed_out is False


def test_run_shell_command_reports_nonzero_exit(tmp_path: Path) -> None:
    result = run_shell_command(
        "python3 -c \"import sys; print('bad'); sys.exit(7)\"",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.exit_code == 7
    assert result.stdout.strip() == "bad"
    assert result.timed_out is False


def test_run_shell_command_uses_workspace_cwd(tmp_path: Path) -> None:
    result = run_shell_command(
        "python3 -c \"from pathlib import Path; print(Path.cwd())\"",
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert result.exit_code == 0
    assert result.stdout.strip() == str(tmp_path)


def test_run_shell_command_reports_timeout(tmp_path: Path) -> None:
    result = run_shell_command(
        "python3 -c \"import time; time.sleep(2)\"",
        cwd=tmp_path,
        timeout_seconds=0.1,
    )

    assert result.exit_code is None
    assert result.timed_out is True
    assert "超时" in result.stderr
```

- [ ] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_shell.py -q
```

预期：失败，错误包含 `ModuleNotFoundError: No module named 'codepilot.shell'`。

- [ ] **步骤 3：实现 shell 执行器**

在 `src/codepilot/shell.py` 中实现：

```python
from __future__ import annotations

import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ShellExecutionResult:
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


def validate_shell_command(command: str) -> str | None:
    normalized = " ".join(command.strip().split())
    lower = normalized.lower()
    if not normalized:
        return "命令不能为空"

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        return f"命令解析失败：{exc}"

    if not parts:
        return "命令不能为空"
    if parts[0] == "sudo":
        return "命令被安全策略拦截：sudo"
    if parts[0] in {"vim", "vi", "nano", "less", "more", "top", "htop"}:
        return f"命令被安全策略拦截：交互式程序 {parts[0]}"
    if re.search(r"(?<!&)&(?!&)", command):
        return "命令被安全策略拦截：后台运行"
    if re.search(r"(^|[;&|])\s*cd\s+(\.\.|/|~)", lower):
        return "命令被安全策略拦截：禁止跳出工作区的 cd"
    if re.search(r"\brm\s+(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r)\s+(/|~|\*)", lower):
        return "命令被安全策略拦截：高风险删除"
    if re.search(r"\bgit\s+reset\s+--hard\b", lower):
        return "命令被安全策略拦截：git reset --hard"
    if re.search(r"\bgit\s+clean\s+-[a-z]*f", lower):
        return "命令被安全策略拦截：git clean -f"
    return None


def run_shell_command(command: str, cwd: Path, timeout_seconds: float) -> ShellExecutionResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return ShellExecutionResult(
            exit_code=None,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\n命令执行超时：{timeout_seconds} 秒",
            timed_out=True,
        )
    except OSError as exc:
        return ShellExecutionResult(
            exit_code=None,
            stdout="",
            stderr=f"命令启动失败：{exc}",
            timed_out=False,
        )

    return ShellExecutionResult(
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        timed_out=False,
    )


def format_shell_result(result: ShellExecutionResult) -> str:
    return "\n".join(
        [
            f"exit_code: {result.exit_code}",
            f"timed_out: {result.timed_out}",
            "stdout:",
            result.stdout,
            "stderr:",
            result.stderr,
        ]
    )
```

- [ ] **步骤 4：验证 shell 执行器测试通过**

```bash
python3 -m pytest tests/test_shell.py -q
```

预期：`8 passed`。

- [ ] **步骤 5：提交 shell 执行器**

```bash
git add src/codepilot/shell.py tests/test_shell.py
git commit -m "feat: add controlled shell runner"
```

预期：创建只包含 shell 执行器和测试的提交。

### 任务 4：`run_shell` 工具和完整工具注册表

**文件：**

- 创建：`src/codepilot/tools/run_shell.py`
- 修改：`src/codepilot/tools/__init__.py`
- 测试：`tests/test_tools.py`
- 测试：`tests/test_shell.py`

- [ ] **步骤 1：编写失败的 `run_shell` 工具测试**

在 `tests/test_shell.py` 中追加：

```python
from codepilot.approval import ApprovalDecision, ApprovalPolicy, ApprovalRequest
from codepilot.tools.run_shell import RunShellTool
from codepilot.workspace import Workspace


class FakeApprovalPolicy:
    def __init__(self, approved: bool = True) -> None:
        self.approved = approved
        self.requests: list[ApprovalRequest] = []

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        if self.approved:
            return ApprovalDecision(True, "允许")
        return ApprovalDecision(False, "用户拒绝执行")


def test_run_shell_tool_executes_after_approval(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy()
    tool = RunShellTool(Workspace(tmp_path), approval, default_timeout_seconds=5)

    result = tool.run({"command": "python3 -c \"print('ok')\""})

    assert result.ok is True
    assert "stdout:" in result.content
    assert "ok" in result.content
    assert approval.requests[0].action == "run_shell"
    assert approval.requests[0].risk == "shell"


def test_run_shell_tool_rejects_dangerous_command_before_approval(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy()
    tool = RunShellTool(Workspace(tmp_path), approval, default_timeout_seconds=5)

    result = tool.run({"command": "sudo ls"})

    assert result.ok is False
    assert "命令被安全策略拦截" in result.error
    assert approval.requests == []


def test_run_shell_tool_respects_never_policy(tmp_path: Path) -> None:
    approval = ApprovalPolicy(allow_write="ask", allow_shell="never")
    tool = RunShellTool(Workspace(tmp_path), approval, default_timeout_seconds=5)

    result = tool.run({"command": "python3 -c \"print('ok')\""})

    assert result.ok is False
    assert "配置禁止 shell 动作" in result.error


def test_run_shell_tool_rejects_when_approval_denies(tmp_path: Path) -> None:
    tool = RunShellTool(Workspace(tmp_path), FakeApprovalPolicy(approved=False), default_timeout_seconds=5)

    result = tool.run({"command": "python3 -c \"print('ok')\""})

    assert result.ok is False
    assert "用户拒绝执行" in result.error


def test_run_shell_tool_returns_false_for_nonzero_exit(tmp_path: Path) -> None:
    tool = RunShellTool(Workspace(tmp_path), FakeApprovalPolicy(), default_timeout_seconds=5)

    result = tool.run({"command": "python3 -c \"import sys; sys.exit(3)\""})

    assert result.ok is False
    assert "exit_code: 3" in result.content
```

在 `tests/test_tools.py` 中追加：

```python
from codepilot.approval import ApprovalPolicy
from codepilot.tools import default_agent_registry


def test_default_agent_registry_includes_readonly_and_confirmed_tools(tmp_path: Path) -> None:
    registry = default_agent_registry(
        Workspace(tmp_path),
        ApprovalPolicy(allow_write="never", allow_shell="never"),
    )

    assert {"list_files", "read_file", "search_text", "write_file", "patch_file", "run_shell"} <= set(registry.tools)
```

- [ ] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_shell.py tests/test_tools.py -q
```

预期：失败，因为 `RunShellTool` 和 `default_agent_registry()` 尚未实现。

- [ ] **步骤 3：实现 `run_shell` 工具**

在 `src/codepilot/tools/run_shell.py` 中实现：

```python
from __future__ import annotations

from dataclasses import dataclass

from codepilot.approval import ApprovalPolicy, ApprovalRequest, format_rejection
from codepilot.shell import format_shell_result, run_shell_command, validate_shell_command
from codepilot.tools.base import ToolResult
from codepilot.workspace import Workspace


@dataclass
class RunShellTool:
    workspace: Workspace
    approval_policy: ApprovalPolicy
    default_timeout_seconds: int
    name: str = "run_shell"
    description: str = "Run a non-interactive shell command in the current workspace after confirmation."

    def run(self, args: dict) -> ToolResult:
        command = args.get("command")
        if not isinstance(command, str) or not command.strip():
            return ToolResult(ok=False, error="run_shell 需要 command 参数")

        timeout_seconds = args.get("timeout_seconds", self.default_timeout_seconds)
        try:
            timeout = float(timeout_seconds)
        except (TypeError, ValueError):
            return ToolResult(ok=False, error=f"timeout_seconds 必须是数字：{timeout_seconds}")
        if timeout <= 0:
            return ToolResult(ok=False, error="timeout_seconds 必须大于 0")

        blocked_reason = validate_shell_command(command)
        if blocked_reason is not None:
            return ToolResult(ok=False, error=blocked_reason)

        request = ApprovalRequest(
            action="run_shell",
            target=command,
            risk="shell",
            preview=f"工作目录：{self.workspace.root}\n命令：{command}\n超时：{timeout} 秒",
        )
        decision = self.approval_policy.decide(request)
        if not decision.approved:
            return ToolResult(ok=False, error=format_rejection(decision, "run_shell"))

        result = run_shell_command(command, cwd=self.workspace.root, timeout_seconds=timeout)
        content = format_shell_result(result)
        if result.timed_out or result.exit_code != 0:
            return ToolResult(ok=False, content=content, error="shell 命令执行失败")
        return ToolResult(ok=True, content=content)
```

- [ ] **步骤 4：实现完整默认注册表**

修改 `src/codepilot/tools/__init__.py`：

```python
from __future__ import annotations

from dataclasses import dataclass, field

from codepilot.approval import ApprovalPolicy
from codepilot.tools.base import Tool, ToolResult
from codepilot.tools.list_files import ListFilesTool
from codepilot.tools.patch_file import PatchFileTool
from codepilot.tools.read_file import ReadFileTool
from codepilot.tools.run_shell import RunShellTool
from codepilot.tools.search_text import SearchTextTool
from codepilot.tools.write_file import WriteFileTool
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


def default_agent_registry(
    workspace: Workspace,
    approval_policy: ApprovalPolicy,
    shell_timeout_seconds: int = 30,
) -> ToolRegistry:
    registry = default_readonly_registry(workspace)
    registry.register(WriteFileTool(workspace, approval_policy))
    registry.register(PatchFileTool(workspace, approval_policy))
    registry.register(RunShellTool(workspace, approval_policy, shell_timeout_seconds))
    return registry
```

- [ ] **步骤 5：验证工具注册表测试通过**

```bash
python3 -m pytest tests/test_shell.py tests/test_tools.py -q
```

预期：shell 和工具注册表测试通过。

- [ ] **步骤 6：提交 `run_shell` 工具**

```bash
git add src/codepilot/tools/__init__.py src/codepilot/tools/run_shell.py tests/test_shell.py tests/test_tools.py
git commit -m "feat: add confirmed shell tool"
```

预期：创建只包含 `run_shell` 工具和注册表集成的提交。

### 任务 5：Agent 默认工具集和确认输入接入

**文件：**

- 修改：`src/codepilot/agent.py`
- 修改：`src/codepilot/interaction.py`
- 修改：`src/codepilot/cli.py`
- 测试：`tests/test_agent.py`
- 测试：`tests/test_interaction.py`

- [ ] **步骤 1：编写失败的 Agent 集成测试**

在 `tests/test_agent.py` 中追加：

```python
from codepilot.approval import ApprovalDecision, ApprovalRequest
from codepilot.session import SessionStore
from codepilot.tools import default_agent_registry
from codepilot.workspace import Workspace


class AllowApprovalPolicy:
    def __init__(self) -> None:
        self.requests: list[ApprovalRequest] = []

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        return ApprovalDecision(True, "允许")


def test_conversation_agent_executes_confirmed_write_tool_and_continues(tmp_path) -> None:
    llm = FakeLLM(
        responses=[
            '{"tool": "write_file", "args": {"path": "notes.md", "content": "hello\\n", "mode": "create"}}',
            "文件已经创建。",
        ]
    )
    approval = AllowApprovalPolicy()
    registry = default_agent_registry(Workspace(tmp_path), approval, shell_timeout_seconds=5)
    store = SessionStore.create(tmp_path / "sessions")
    agent = ConversationAgent(llm=llm, tool_registry=registry, session_store=store)

    response = agent.respond("创建 notes.md")

    assert response == "文件已经创建。"
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "hello\n"
    assert approval.requests[0].action == "write_file"
    assert [event["type"] for event in store.read_events()] == [
        "user_message",
        "tool_call",
        "tool_result",
        "assistant_message",
    ]
```

在 `tests/test_interaction.py` 中追加：

```python
def test_interactive_session_passes_approval_input_to_default_agent(tmp_path, monkeypatch) -> None:
    output = FakeOutput()
    created_agents = []

    def fake_create_default_agent(config, workspace, approval_input_reader=None, approval_output=None):
        created_agents.append(
            {
                "workspace": workspace,
                "approval_input_reader": approval_input_reader,
                "approval_output": approval_output,
            }
        )
        return FakeAgent()

    monkeypatch.setattr(
        "codepilot.interaction.create_default_agent",
        fake_create_default_agent,
    )

    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: "/exit",
        output=output,
    )

    assert session.run().exit_requested is True
    assert created_agents[0]["workspace"] == tmp_path.resolve()
    assert created_agents[0]["approval_input_reader"] is not None
    assert created_agents[0]["approval_output"] is output
```

该交互测试通过 `monkeypatch` 替换默认 Agent 工厂，确保测试不会触发真实 LLM 调用，也不会直接读取真实 stdin。

- [ ] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_agent.py tests/test_interaction.py -q
```

预期：失败，因为默认 Agent 尚未注册需确认工具，交互层也尚未向审批策略注入输入读取器。

- [ ] **步骤 3：更新 Agent 默认系统提示和默认 Agent 构造**

修改 `src/codepilot/agent.py`：

```python
from codepilot.approval import ApprovalOutput, ApprovalPolicy
from codepilot.tools import ToolRegistry, default_agent_registry
```

将系统提示扩展为包含新工具：

```python
DEFAULT_SYSTEM_PROMPT = """你是 CodePilot，一个本地代码助手。
你可以通过工具获取当前工作区上下文，不要猜测文件内容。
只读工具可以直接使用；写入文件、修改文件和执行 shell 命令会在执行前请求用户确认。
如果需要工具，请只输出一个 JSON 对象：
{"tool": "list_files", "args": {"path": "."}}
{"tool": "read_file", "args": {"path": "README.md", "start_line": 1, "end_line": 80}}
{"tool": "search_text", "args": {"query": "main", "glob": "*.py"}}
{"tool": "write_file", "args": {"path": "notes/demo.md", "content": "# Demo\\n", "mode": "create"}}
{"tool": "patch_file", "args": {"path": "README.md", "old": "旧文本", "new": "新文本"}}
{"tool": "run_shell", "args": {"command": "python3 -m pytest -q"}}
拿到工具结果后，再基于真实内容回答用户。"""
```

更新 `create_default_agent()` 签名和实现：

```python
def create_default_agent(
    config: CodePilotConfig,
    workspace: Path | None = None,
    approval_input_reader: Callable[[], str] | None = None,
    approval_output: ApprovalOutput | None = None,
) -> ConversationAgent:
    session_store = SessionStore.create(config.sessions_dir)
    workspace_root = workspace or Path.cwd()
    code_workspace = Workspace(workspace_root, max_file_chars=config.max_file_chars)
    approval_policy = ApprovalPolicy(
        allow_write=config.allow_write,
        allow_shell=config.allow_shell,
        input_reader=approval_input_reader,
        output=approval_output,
    )
    return ConversationAgent(
        llm=OpenAICompatibleLLM(config=config),
        session_store=session_store,
        tool_registry=default_agent_registry(
            code_workspace,
            approval_policy,
            shell_timeout_seconds=config.shell_timeout_seconds,
        ),
        max_tool_iterations=config.max_tool_iterations,
    )
```

- [ ] **步骤 4：更新交互会话注入审批输入**

修改 `src/codepilot/interaction.py` 的 `InteractiveSession.__init__()`，增加 `approval_input_reader` 参数：

```python
def __init__(
    self,
    workspace: Path,
    input_reader: Callable[[], str] | None = None,
    output: Output | None = None,
    config: CodePilotConfig | None = None,
    agent: Agent | None = None,
    approval_input_reader: Callable[[], str] | None = None,
) -> None:
    self.workspace = workspace.resolve()
    self.config = config or load_config(self.workspace)
    self.input_reader = input_reader or self._prompt
    self.output = output or PlainOutput()
    self.agent = agent or create_default_agent(
        self.config,
        workspace=self.workspace,
        approval_input_reader=approval_input_reader or self.input_reader,
        approval_output=self.output,
    )
    self._turns = 0
```

- [ ] **步骤 5：更新 CLI 的默认 Agent 创建**

修改 `src/codepilot/cli.py` 中 `run` 分支：

```python
active_agent = agent or create_default_agent(
    config,
    workspace=workspace_path,
    approval_input_reader=input_reader,
    approval_output=out,
)
```

`chat` 分支不需要额外创建 Agent，`InteractiveSession` 会处理审批输入注入。

- [ ] **步骤 6：验证 Agent 和交互测试通过**

```bash
python3 -m pytest tests/test_agent.py tests/test_interaction.py tests/test_cli.py -q
```

预期：Agent、交互层和 CLI 测试通过。

- [ ] **步骤 7：提交 Agent 集成**

```bash
git add src/codepilot/agent.py src/codepilot/interaction.py src/codepilot/cli.py tests/test_agent.py tests/test_interaction.py tests/test_cli.py
git commit -m "feat: wire confirmed tools into agent"
```

预期：创建只包含 Agent、CLI、交互层接入的提交。

### 任务 6：README 和本地使用说明

**文件：**

- 修改：`README.md`

- [ ] **步骤 1：更新 README 能力说明**

把当前里程碑列表中的工具描述扩展为中文：

```markdown
- 对话 Agent 可以通过 JSON 工具请求执行工作区工具：`list_files`、`read_file`、`search_text`、`write_file`、`patch_file` 和 `run_shell`。
- `write_file`、`patch_file` 和 `run_shell` 执行前都需要用户确认。
- `run_shell` 只在工作区内执行非交互命令，带超时，并会拦截明显危险命令。
```

在配置说明附近增加：

```markdown
受控动作在 `.codepilot/config.toml` 中配置。
```

配置示例：

```toml
allow_write = "ask"
allow_shell = "ask"
shell_timeout_seconds = 30
```

补充说明：

```markdown
如果需要禁用写入或 shell 动作，把对应配置从 `ask` 改为 `never`。
```

- [ ] **步骤 2：运行文档空白检查**

```bash
git diff --check -- README.md
```

预期：无输出，退出码为 0。

- [ ] **步骤 3：提交 README**

```bash
git add README.md
git commit -m "docs: describe confirmed write and shell tools"
```

预期：创建只包含 README 更新的提交。

### 任务 7：完整验证和里程碑收尾

**文件：**

- 校验本里程碑涉及的全部文件。

- [ ] **步骤 1：运行完整测试**

```bash
python3 -m pytest -q
```

预期：全部测试通过，失败数为 0。

- [ ] **步骤 2：运行编译检查**

```bash
python3 -m compileall -q src tests
```

预期：无输出，退出码为 0。

- [ ] **步骤 3：运行 diff 空白检查**

```bash
git diff --check
```

预期：无输出，退出码为 0。

- [ ] **步骤 4：验证工具注册表包含 6 个工具**

```bash
env PYTHONPATH=src python3 -c "from pathlib import Path; from codepilot.approval import ApprovalPolicy; from codepilot.tools import default_agent_registry; from codepilot.workspace import Workspace; r=default_agent_registry(Workspace(Path.cwd()), ApprovalPolicy(allow_write='never', allow_shell='never')); print(sorted(r.tools))"
```

预期：输出包含：

```text
['list_files', 'patch_file', 'read_file', 'run_shell', 'search_text', 'write_file']
```

- [ ] **步骤 5：检查 git 状态**

```bash
git status --short
```

预期：只剩用户明确保留的无关变更，或工作区干净。不得把 `.codepilot/`、`模型配置.txt` 或密钥文件加入提交。

- [ ] **步骤 6：记录最终提交**

```bash
git log --oneline -6
```

预期：能看到本里程碑的分步提交：

```text
feat: add approval policy
feat: add confirmed write tools
feat: add controlled shell runner
feat: add confirmed shell tool
feat: wire confirmed tools into agent
docs: describe confirmed write and shell tools
```
