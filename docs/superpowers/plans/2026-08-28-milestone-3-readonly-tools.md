# Milestone 3 Read-Only Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add task state, safe workspace access, read-only tools, and Agent tool execution so CodePilot can answer from real local context.

**Architecture:** Introduce `TaskState`, `Workspace`, and a `tools` package. The Agent parses JSON tool requests, executes them through `ToolRegistry`, appends tool results into message history, and asks the LLM for the final answer.

**Tech Stack:** Python 3.10 compatible standard library, dataclasses, pathlib, pytest.

---

## File Structure

- Create: `src/codepilot/task_state.py`
- Create: `src/codepilot/workspace.py`
- Create: `src/codepilot/tools/base.py`
- Create: `src/codepilot/tools/__init__.py`
- Create: `src/codepilot/tools/list_files.py`
- Create: `src/codepilot/tools/read_file.py`
- Create: `src/codepilot/tools/search_text.py`
- Modify: `src/codepilot/agent.py`
- Modify: `src/codepilot/interaction.py`
- Modify: `src/codepilot/cli.py`
- Modify: `README.md`
- Test: `tests/test_task_state.py`
- Test: `tests/test_workspace.py`
- Test: `tests/test_tools.py`
- Test: `tests/test_agent.py`
- Test: `tests/test_interaction.py`

### Task 1: Task State

**Files:**

- Create: `src/codepilot/task_state.py`
- Test: `tests/test_task_state.py`

- [x] **Step 1: Write failing task state tests**

```python
def test_task_state_starts_goal_with_default_plan():
    state = TaskState()
    state.start_goal("总结这个项目")
    assert state.goal == "总结这个项目"
    assert state.status == "running"
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_task_state.py -q
```

Expected: failure because `codepilot.task_state` does not exist.

- [x] **Step 3: Implement task state**

Implement `PlanStep`, `TaskState.start_goal()`, `set_plan()`, `mark_done()`, `render_status()`, and `render_plan()`.

- [x] **Step 4: Verify task state tests pass**

```bash
python3 -m pytest tests/test_task_state.py -q
```

Expected: task state tests pass.

### Task 2: Workspace Safety

**Files:**

- Create: `src/codepilot/workspace.py`
- Test: `tests/test_workspace.py`

- [x] **Step 1: Write failing workspace tests**

```python
def test_workspace_resolve_path_rejects_parent_escape(tmp_path):
    workspace = Workspace(tmp_path)
    with pytest.raises(WorkspaceAccessError):
        workspace.resolve_path("../outside.txt")
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_workspace.py -q
```

Expected: failure because `codepilot.workspace` does not exist.

- [x] **Step 3: Implement workspace access**

Implement `Workspace.resolve_path()`, `list_files()`, `read_file()`, and `search_text()`. Enforce root containment and ignored directory names.

- [x] **Step 4: Verify workspace tests pass**

```bash
python3 -m pytest tests/test_workspace.py -q
```

Expected: workspace tests pass.

### Task 3: Read-Only Tools and Registry

**Files:**

- Create: `src/codepilot/tools/base.py`
- Create: `src/codepilot/tools/__init__.py`
- Create: `src/codepilot/tools/list_files.py`
- Create: `src/codepilot/tools/read_file.py`
- Create: `src/codepilot/tools/search_text.py`
- Test: `tests/test_tools.py`

- [x] **Step 1: Write failing tool tests**

```python
def test_default_readonly_registry_executes_list_files(tmp_path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    registry = default_readonly_registry(Workspace(tmp_path))
    result = registry.execute("list_files", {"path": "."})
    assert result.ok is True
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_tools.py -q
```

Expected: failure because `codepilot.tools` does not exist.

- [x] **Step 3: Implement tools**

Implement `ToolResult`, `Tool` protocol, `ToolRegistry`, `default_readonly_registry()`, `ListFilesTool`, `ReadFileTool`, and `SearchTextTool`.

- [x] **Step 4: Verify tool tests pass**

```bash
python3 -m pytest tests/test_tools.py -q
```

Expected: tool tests pass.

### Task 4: Agent Tool Loop

**Files:**

- Modify: `src/codepilot/agent.py`
- Test: `tests/test_agent.py`

- [x] **Step 1: Write failing Agent tool-loop tests**

```python
def test_conversation_agent_executes_tool_request_and_returns_final_answer(tmp_path):
    llm = FakeLLM(responses=['{"tool": "echo", "args": {"text": "hello"}}', "工具结果是 hello"])
    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = ConversationAgent(llm=llm, tool_registry=registry)
    assert agent.respond("调用 echo 工具") == "工具结果是 hello"
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_agent.py -q
```

Expected: failure because the Agent does not parse or execute tool requests.

- [x] **Step 3: Implement JSON tool protocol**

Implement `ToolRequest`, `parse_tool_request()`, `_extract_json_object()`, tool loop execution, session `tool_call` and `tool_result` events, and `max_tool_iterations`.

- [x] **Step 4: Verify Agent tool-loop tests pass**

```bash
python3 -m pytest tests/test_agent.py -q
```

Expected: Agent tests pass.

### Task 5: Dynamic Status and Plan Commands

**Files:**

- Modify: `src/codepilot/interaction.py`
- Modify: `src/codepilot/cli.py`
- Test: `tests/test_interaction.py`

- [x] **Step 1: Write failing interaction state tests**

```python
def test_interactive_session_status_reads_agent_task_state(tmp_path):
    inputs = iter(["帮我总结这个项目", "/status", "/plan", "/exit"])
    session = InteractiveSession(workspace=tmp_path, input_reader=lambda: next(inputs), output=output, agent=agent)
    session.run()
    assert "当前状态：done；目标：帮我总结这个项目" in output.lines
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_interaction.py -q
```

Expected: failure while `/status` and `/plan` still return static strings.

- [x] **Step 3: Wire status and plan to Agent**

Expose `ConversationAgent.status` and `ConversationAgent.plan`. Update `InteractiveSession._handle_command()` to read those properties. Pass workspace into `create_default_agent()`.

- [x] **Step 4: Verify interaction tests pass**

```bash
python3 -m pytest tests/test_interaction.py -q
```

Expected: interaction tests pass.

### Task 6: CLI and Documentation

**Files:**

- Modify: `src/codepilot/cli.py`
- Modify: `README.md`

- [x] **Step 1: Ensure default Agent has read-only tools**

Update `create_default_agent(config, workspace=workspace_path)` usage so CLI-created agents receive a `Workspace` and `default_readonly_registry()`.

- [x] **Step 2: Document read-only tools**

Add a README line describing the JSON tool request support for `list_files`, `read_file`, and `search_text`.

- [x] **Step 3: Verify CLI help still works**

```bash
env PYTHONPATH=src python3 -m codepilot --help
```

Expected: CLI help renders.

### Task 7: Commit Milestone 3

**Files:**

- Commit all files created or modified in this plan.

- [x] **Step 1: Run full verification**

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

Expected: all checks pass.

- [x] **Step 2: Verify local fake tool loop**

```bash
env PYTHONPATH=src python3 -c "from codepilot.agent import ConversationAgent; print('tool loop verified by tests')"
```

Expected: command exits with code 0.

- [x] **Step 3: Commit**

```bash
git add README.md src tests
git commit -m "feat: implement conversation agent with tool execution capabilities and workspace integration"
```

Expected: commit `0d8d6f6` or equivalent milestone commit is created.
