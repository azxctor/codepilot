# 里程碑 4：受控写入、shell 和确认机制设计

## 目标

在现有交互式 Agent 和只读工具基础上，加入受控写入、受控 shell 执行和每次危险动作确认机制。完成后，CodePilot 可以形成类似 Claude Code 的基础闭环：模型根据任务提出文件修改或命令执行请求，CLI 展示动作预览，用户确认后执行，执行结果再回到 Agent 继续对话。

## 范围

本里程碑包含：

- 统一审批模型：`ApprovalRequest`、`ApprovalDecision`、`ApprovalPolicy`。
- 每次危险动作都询问确认。
- 写入工具 `write_file`。
- 单文件文本替换工具 `patch_file`。
- 受控 shell 工具 `run_shell`。
- shell 命令危险模式拦截。
- shell 执行超时和 stdout/stderr/exit code 捕获。
- 默认 Agent 注册只读工具和需确认工具。
- 会话 JSONL 继续记录 `tool_call` 和 `tool_result`。

本里程碑不包含：

- 自动免确认模式。
- 多文件 unified diff 补丁解析。
- shell 命令白名单配置界面。
- 工作区外命令执行。
- 交互式 shell、后台长驻进程或 TUI 编辑器。
- git 自动提交、自动推送或远程分支管理。
- 恢复历史会话。

## 已确认决策

- 写入、修改和 shell 执行默认每次都要用户确认。
- `allow_write = "ask"` 表示每次写入/修改前确认。
- `allow_write = "never"` 表示直接拒绝写入/修改。
- `allow_shell = "ask"` 表示每次 shell 执行前确认。
- `allow_shell = "never"` 表示直接拒绝 shell 执行。
- 本里程碑不实现 `always`，避免绕开确认机制。
- `run_shell` 只允许非交互、带超时、以工作区为当前目录的命令。
- `run_shell` 在确认前先拦截明显危险命令。

## 架构

Milestone 4 复用 Milestone 3 的 `ToolRegistry` 和 JSON 工具循环，不重写 `ConversationAgent` 的职责边界。Agent 仍然只负责接收模型输出、解析工具请求、调用工具、把工具结果追加回历史，并请求模型给出最终回答。

新增的审批能力放在工具层：

- `src/codepilot/approval.py`：定义审批请求、审批决策和审批策略。
- `src/codepilot/shell.py`：封装 shell 命令校验与执行。
- `src/codepilot/tools/write_file.py`：实现 `write_file`。
- `src/codepilot/tools/patch_file.py`：实现 `patch_file`。
- `src/codepilot/tools/run_shell.py`：实现 `run_shell`。
- `src/codepilot/tools/__init__.py`：新增默认 Agent 工具注册表，同时注册只读工具和需确认工具。

`create_default_agent()` 创建默认 Agent 时注入工作区、审批策略和完整工具注册表。测试中可以注入假的审批策略，避免依赖真实 stdin。

## 审批模型

`ApprovalRequest` 描述一次待确认动作：

- `action`：动作类型，例如 `write_file`、`patch_file`、`run_shell`。
- `target`：目标文件路径或命令。
- `risk`：风险级别，当前使用 `write` 或 `shell`。
- `preview`：用户确认前看到的摘要。

`ApprovalDecision` 描述审批结果：

- `approved`：是否允许执行。
- `reason`：拒绝原因或说明。

`ApprovalPolicy` 根据配置和输入方式做决策：

- `ask`：展示预览并读取用户输入。只有输入 `y` 才执行，其他输入都视为拒绝。
- `never`：不询问，直接拒绝。

拒绝不会抛异常，而是返回 `ToolResult(ok=False, error="用户拒绝执行：...")`。Agent 会把该结果交回 LLM，让模型可以调整方案、解释风险或结束任务。

## 工具协议

模型仍然通过单个 JSON 对象请求工具。

### write_file

```json
{"tool": "write_file", "args": {"path": "notes/demo.md", "content": "# Demo\n", "mode": "create"}}
```

参数：

- `path`：工作区内相对路径。
- `content`：UTF-8 文本内容。
- `mode`：`create` 或 `overwrite`。

行为：

- `create` 遇到已有文件时失败。
- `overwrite` 遇到不存在文件时失败。
- 父目录不存在时失败。
- 执行前展示目标路径、模式和内容预览。

### patch_file

```json
{"tool": "patch_file", "args": {"path": "README.md", "old": "旧文本", "new": "新文本"}}
```

行为：

- 只处理单个文件内的简单文本替换。
- `old` 必须在文件中唯一出现。
- `old` 不存在或出现多次时失败。
- 执行前展示目标路径、替换前后摘要。

### run_shell

```json
{"tool": "run_shell", "args": {"command": "python3 -m pytest -q", "timeout_seconds": 30}}
```

行为：

- 命令在工作区根目录下执行。
- 使用非交互执行方式。
- 默认超时来自 `shell_timeout_seconds`。
- 返回 stdout、stderr 和 exit code。
- exit code 非 0 时返回 `ok=False`，但仍保留输出内容。

## shell 安全策略

`run_shell` 在审批前先执行静态拦截。拦截对象包括：

- `sudo`。
- `rm -rf /`、`rm -rf ~` 等明显破坏性删除。
- `git reset --hard`、`git clean -fd` 等高风险仓库破坏命令。
- `vim`、`vi`、`nano`、`less` 等交互式程序。
- 包含后台运行符号 `&` 的长驻倾向命令。
- 通过 `cd` 跳出工作区后执行的命令。

拦截命令直接返回 `ToolResult(ok=False, error="命令被安全策略拦截：...")`，不会进入用户确认步骤。

## 数据流

1. 用户在 `codepilot chat` 中输入任务。
2. Agent 把用户消息发给 LLM。
3. LLM 返回 JSON 工具请求。
4. Agent 调用 `ToolRegistry.execute()`。
5. 需确认工具构造 `ApprovalRequest`。
6. `ApprovalPolicy` 根据配置和用户输入返回决策。
7. 工具执行或拒绝，并返回 `ToolResult`。
8. Agent 写入 `tool_call` 和 `tool_result` 会话事件。
9. Agent 把工具结果追加回消息历史。
10. LLM 基于执行结果继续回答或请求下一步工具。

## 错误处理

- 所有文件路径必须通过 `Workspace.resolve_path()`，禁止访问工作区外路径。
- `write_file` 参数缺失、模式非法、父目录不存在、文件状态不匹配时失败。
- `patch_file` 参数缺失、文件不存在、匹配次数不是 1 时失败。
- `run_shell` 命令为空、危险命令、超时、启动失败或非 0 退出码时失败。
- 审批拒绝作为工具失败结果返回，不中断 Agent 进程。
- LLM 连续工具调用仍受 `max_tool_iterations` 限制。

## 配置

继续使用已有配置字段：

```toml
allow_write = "ask"
allow_shell = "ask"
shell_timeout_seconds = 30
```

允许值：

- `allow_write`：`ask`、`never`。
- `allow_shell`：`ask`、`never`。

如果配置出现其他值，按更保守的 `never` 处理，并在工具结果中说明配置无效。

## 测试策略

新增或扩展测试：

- `tests/test_approval.py`：覆盖 `ask`、`never`、允许、拒绝、预览输出。
- `tests/test_write_tools.py`：覆盖 `write_file` 的 create/overwrite、`patch_file` 的唯一匹配、拒绝、越界访问。
- `tests/test_shell.py`：覆盖成功命令、非 0 退出码、超时、危险命令拦截、工作目录限制。
- `tests/test_agent.py`：覆盖 Agent 执行需确认工具后继续请求 LLM 返回最终回答。
- `tests/test_cli.py` 和 `tests/test_interaction.py`：覆盖默认 Agent 注册新工具，以及确认输入可以注入测试。

必须执行的验证命令：

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

## 验收标准

- `write_file` 只能在用户确认后创建或覆盖工作区内文件。
- `patch_file` 只能在用户确认后替换工作区内单个文件的唯一匹配文本。
- `run_shell` 只能在用户确认后以工作区为 cwd 执行非交互命令。
- `run_shell` 能返回 stdout、stderr、exit code，并处理超时。
- `run_shell` 会在确认前拦截明显危险命令。
- `allow_write = "never"` 和 `allow_shell = "never"` 能直接拒绝对应操作。
- 用户拒绝审批时，工具返回失败结果，Agent 可以继续对话。
- 默认 Agent 同时拥有只读工具和需确认工具。
- 会话 JSONL 继续记录 `tool_call` 和 `tool_result`。

## 不变量

- 不把 API Key 或其他密钥写入配置、日志或文档。
- 不执行工作区外文件写入。
- 不执行工作区外 shell 命令。
- 不新增自动免确认通道。
- 不把审批逻辑塞进 LLM Provider。
- 不把 shell 执行散落在多个工具里。
