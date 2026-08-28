# 里程碑 3：任务状态和只读工具实现计划

> **面向自动化执行者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪状态。

**目标：** 增加任务状态、安全工作区访问、只读工具和 Agent 工具执行循环，让 CodePilot 可以基于真实本地上下文回答。

**架构：** 引入 `TaskState`、`Workspace` 和 `tools` 包。Agent 解析 JSON 工具请求，通过 `ToolRegistry` 执行工具，把工具结果追加到消息历史中，然后再次请求 LLM 生成最终回答。

**技术栈：** 兼容 Python 3.10 的标准库、`dataclasses`、`pathlib`、pytest。

---

## 文件结构

- 创建：`src/codepilot/task_state.py`
- 创建：`src/codepilot/workspace.py`
- 创建：`src/codepilot/tools/base.py`
- 创建：`src/codepilot/tools/__init__.py`
- 创建：`src/codepilot/tools/list_files.py`
- 创建：`src/codepilot/tools/read_file.py`
- 创建：`src/codepilot/tools/search_text.py`
- 修改：`src/codepilot/agent.py`
- 修改：`src/codepilot/interaction.py`
- 修改：`src/codepilot/cli.py`
- 修改：`README.md`
- 测试：`tests/test_task_state.py`
- 测试：`tests/test_workspace.py`
- 测试：`tests/test_tools.py`
- 测试：`tests/test_agent.py`
- 测试：`tests/test_interaction.py`

### 任务 1：任务状态

**文件：**

- 创建：`src/codepilot/task_state.py`
- 测试：`tests/test_task_state.py`

- [x] **步骤 1：编写失败的任务状态测试**

```python
def test_task_state_starts_goal_with_default_plan():
    state = TaskState()
    state.start_goal("总结这个项目")
    assert state.goal == "总结这个项目"
    assert state.status == "running"
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_task_state.py -q
```

预期：测试失败，因为 `codepilot.task_state` 尚不存在。

- [x] **步骤 3：实现任务状态**

实现 `PlanStep`、`TaskState.start_goal()`、`set_plan()`、`mark_done()`、`render_status()` 和 `render_plan()`。

- [x] **步骤 4：验证任务状态测试通过**

```bash
python3 -m pytest tests/test_task_state.py -q
```

预期：任务状态测试通过。

### 任务 2：工作区安全

**文件：**

- 创建：`src/codepilot/workspace.py`
- 测试：`tests/test_workspace.py`

- [x] **步骤 1：编写失败的工作区测试**

```python
def test_workspace_resolve_path_rejects_parent_escape(tmp_path):
    workspace = Workspace(tmp_path)
    with pytest.raises(WorkspaceAccessError):
        workspace.resolve_path("../outside.txt")
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_workspace.py -q
```

预期：测试失败，因为 `codepilot.workspace` 尚不存在。

- [x] **步骤 3：实现工作区访问**

实现 `Workspace.resolve_path()`、`list_files()`、`read_file()` 和 `search_text()`。强制路径位于工作区根目录内，并忽略常见目录名。

- [x] **步骤 4：验证工作区测试通过**

```bash
python3 -m pytest tests/test_workspace.py -q
```

预期：工作区测试通过。

### 任务 3：只读工具和注册表

**文件：**

- 创建：`src/codepilot/tools/base.py`
- 创建：`src/codepilot/tools/__init__.py`
- 创建：`src/codepilot/tools/list_files.py`
- 创建：`src/codepilot/tools/read_file.py`
- 创建：`src/codepilot/tools/search_text.py`
- 测试：`tests/test_tools.py`

- [x] **步骤 1：编写失败的工具测试**

```python
def test_default_readonly_registry_executes_list_files(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    registry = default_readonly_registry(Workspace(tmp_path))
    result = registry.execute("list_files", {"path": "."})
    assert result.ok is True
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_tools.py -q
```

预期：测试失败，因为 `codepilot.tools` 尚不存在。

- [x] **步骤 3：实现工具**

实现 `ToolResult`、`Tool` 协议、`ToolRegistry`、`default_readonly_registry()`、`ListFilesTool`、`ReadFileTool` 和 `SearchTextTool`。

- [x] **步骤 4：验证工具测试通过**

```bash
python3 -m pytest tests/test_tools.py -q
```

预期：工具测试通过。

### 任务 4：Agent 工具循环

**文件：**

- 修改：`src/codepilot/agent.py`
- 测试：`tests/test_agent.py`

- [x] **步骤 1：编写失败的 Agent 工具循环测试**

```python
def test_conversation_agent_executes_tool_request_and_returns_final_answer(tmp_path):
    llm = FakeLLM(responses=['{"tool": "echo", "args": {"text": "hello"}}', "工具结果是 hello"])
    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = ConversationAgent(llm=llm, tool_registry=registry)
    assert agent.respond("调用 echo 工具") == "工具结果是 hello"
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_agent.py -q
```

预期：测试失败，因为 Agent 尚未解析和执行工具请求。

- [x] **步骤 3：实现 JSON 工具协议**

实现 `ToolRequest`、`parse_tool_request()`、`_extract_json_object()`、工具循环执行、会话 `tool_call` 和 `tool_result` 事件，以及 `max_tool_iterations`。

- [x] **步骤 4：验证 Agent 工具循环测试通过**

```bash
python3 -m pytest tests/test_agent.py -q
```

预期：Agent 测试通过。

### 任务 5：动态状态和计划命令

**文件：**

- 修改：`src/codepilot/interaction.py`
- 修改：`src/codepilot/cli.py`
- 测试：`tests/test_interaction.py`

- [x] **步骤 1：编写失败的交互状态测试**

```python
def test_interactive_session_status_reads_agent_task_state(tmp_path):
    inputs = iter(["帮我总结这个项目", "/status", "/plan", "/exit"])
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
        agent=agent,
    )
    session.run()
    assert "当前状态：done；目标：帮我总结这个项目" in output.lines
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_interaction.py -q
```

预期：测试失败，因为 `/status` 和 `/plan` 仍返回静态文本。

- [x] **步骤 3：把状态和计划接入 Agent**

暴露 `ConversationAgent.status` 和 `ConversationAgent.plan`。更新 `InteractiveSession._handle_command()`，让它读取这些属性。创建默认 Agent 时传入工作区。

- [x] **步骤 4：验证交互测试通过**

```bash
python3 -m pytest tests/test_interaction.py -q
```

预期：交互测试通过。

### 任务 6：CLI 和文档

**文件：**

- 修改：`src/codepilot/cli.py`
- 修改：`README.md`

- [x] **步骤 1：确保默认 Agent 拥有只读工具**

更新 `create_default_agent(config, workspace=workspace_path)` 的使用方式，让 CLI 创建的 Agent 获得 `Workspace` 和 `default_readonly_registry()`。

- [x] **步骤 2：记录只读工具能力**

在 README 中说明 `list_files`、`read_file` 和 `search_text` 的 JSON 工具请求支持。

- [x] **步骤 3：验证 CLI 帮助仍正常**

```bash
env PYTHONPATH=src python3 -m codepilot --help
```

预期：CLI 帮助可以正常渲染。

### 任务 7：提交里程碑 3

**文件：**

- 提交本计划创建或修改的全部文件。

- [x] **步骤 1：运行完整验证**

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

预期：全部检查通过。

- [x] **步骤 2：验证本地假工具循环**

```bash
env PYTHONPATH=src python3 -c "from codepilot.agent import ConversationAgent; print('tool loop verified by tests')"
```

预期：命令退出码为 0。

- [x] **步骤 3：提交**

```bash
git add README.md src tests
git commit -m "feat: implement conversation agent with tool execution capabilities and workspace integration"
```

预期：创建提交 `0d8d6f6` 或等价的里程碑提交。
