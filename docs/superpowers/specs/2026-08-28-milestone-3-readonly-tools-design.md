# 里程碑 3：任务状态和只读工具设计

## 目标

加入任务状态和只读工作区工具，让 CodePilot 可以通过受控 Agent 循环检查项目文件，而不是在不了解仓库内容的情况下猜测。

## 范围

本里程碑包含：

- 包含目标、计划、当前步骤和状态的 `TaskState`。
- 动态 `/status` 和 `/plan` 输出。
- 工作区路径范围限制。
- 文件列表和搜索时忽略常见目录。
- 只读工具 `list_files`。
- 只读工具 `read_file`。
- 只读工具 `search_text`。
- `ToolRegistry`。
- `ConversationAgent` 解析 JSON 工具请求。
- 会话 JSONL 记录工具结果事件。

本里程碑不包含写入工具、shell 执行、用户审批、流式输出、项目指令文件，或恢复历史会话。

## 架构

`src/codepilot/workspace.py` 中的 `Workspace` 是唯一允许解析本地路径的对象。只读工具依赖 `Workspace`，Agent 只能通过 `ToolRegistry` 执行工具。

Agent 支持一个最小 JSON 工具协议。当模型响应是包含 `tool` 和 `args` 的 JSON 对象时，Agent 执行对应工具，把工具结果追加回对话历史，并再次调用模型。当模型返回普通文本时，该文本被视为最终回答。

## 工具协议

模型需要调用工具时，必须输出单个 JSON 对象：

```json
{"tool": "list_files", "args": {"path": "."}}
```

支持的工具请求示例：

```json
{"tool": "read_file", "args": {"path": "README.md", "start_line": 1, "end_line": 80}}
```

```json
{"tool": "search_text", "args": {"query": "main", "glob": "*.py"}}
```

如果工具调用次数超过 `max_tool_iterations`，Agent 会自动停止。

## 工作区安全

所有文件路径都必须解析到工作区根目录之下。类似 `../outside.txt` 的越界访问会抛出 `WorkspaceAccessError`。默认忽略名称包括：

- `.git`
- `.codepilot`
- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
- `.pytest_cache`

## 任务状态

收到新的用户目标时，`TaskState.start_goal()` 创建一个简短默认计划：

1. 理解用户目标
2. 读取必要项目上下文
3. 基于真实上下文回答

生成最终回答后，`TaskState.mark_done()` 会把计划标记为完成。`/status` 和 `/plan` 从 Agent 的任务状态读取输出。

## 测试

测试覆盖：

- `tests/test_task_state.py`
- `tests/test_workspace.py`
- `tests/test_tools.py`
- `tests/test_agent.py`
- `tests/test_interaction.py`

必须执行的验证命令：

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

## 验收标准

- 工作区拒绝访问项目根目录之外的路径。
- `list_files` 返回项目相对路径，并跳过忽略目录。
- `read_file` 返回带行号的指定范围内容。
- `search_text` 返回项目相对路径和带行号的匹配项。
- `ToolRegistry` 能清晰报告未知工具。
- Agent 可以执行 JSON 工具请求并返回最终回答。
- `/status` 和 `/plan` 展示真实任务状态，而不是静态假数据文本。

## 实现证据

已在以下提交中实现：

```text
0d8d6f6 feat: implement conversation agent with tool execution capabilities and workspace integration
```
