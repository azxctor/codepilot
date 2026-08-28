# Milestone 3 Read-Only Tools Design

## Goal

Add task state and read-only workspace tools so CodePilot can inspect project files through a controlled Agent loop instead of guessing repository contents.

## Scope

This milestone covers:

- `TaskState` with goal, plan, current step, and status.
- Dynamic `/status` and `/plan` output.
- Workspace path containment.
- Ignored directories for file listing and search.
- `list_files` read-only tool.
- `read_file` read-only tool.
- `search_text` read-only tool.
- `ToolRegistry`.
- JSON tool request parsing in `ConversationAgent`.
- Tool result events in session JSONL.

This milestone does not implement write tools, shell execution, user approvals, streaming, project instruction files, or session resume.

## Architecture

`Workspace` in `src/codepilot/workspace.py` is the only object allowed to resolve local paths. Read-only tools depend on `Workspace`, and `ToolRegistry` is the only execution surface the agent uses.

The Agent supports a minimal JSON tool protocol. When the model response is a JSON object with `tool` and `args`, the Agent runs the tool, appends the result back into history, and calls the model again. When the model returns normal text, that text is treated as the final answer.

## Tool Protocol

The model must output one JSON object when it wants a tool:

```json
{"tool": "list_files", "args": {"path": "."}}
```

Supported tools:

```json
{"tool": "read_file", "args": {"path": "README.md", "start_line": 1, "end_line": 80}}
```

```json
{"tool": "search_text", "args": {"query": "main", "glob": "*.py"}}
```

The Agent automatically stops if tool calls exceed `max_tool_iterations`.

## Workspace Safety

All file paths are resolved under the workspace root. Attempts such as `../outside.txt` raise `WorkspaceAccessError`. Default ignored names include:

- `.git`
- `.codepilot`
- `.venv`
- `venv`
- `node_modules`
- `__pycache__`
- `.pytest_cache`

## Task State

When a new user goal arrives, `TaskState.start_goal()` creates a short default plan:

1. 理解用户目标
2. 读取必要项目上下文
3. 基于真实上下文回答

When the final answer is produced, `TaskState.mark_done()` marks the plan as done. `/status` and `/plan` read from the Agent task state.

## Tests

Covered by:

- `tests/test_task_state.py`
- `tests/test_workspace.py`
- `tests/test_tools.py`
- `tests/test_agent.py`
- `tests/test_interaction.py`

Required verification:

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

## Acceptance Criteria

- Workspace rejects paths outside the project root.
- `list_files` returns project-relative paths and skips ignored directories.
- `read_file` returns numbered line ranges.
- `search_text` returns project-relative numbered matches.
- Tool Registry reports unknown tools cleanly.
- Agent can execute JSON tool requests and return a final answer.
- `/status` and `/plan` show real task state instead of static placeholder text.

## Implementation Evidence

Implemented in commit:

```text
0d8d6f6 feat: implement conversation agent with tool execution capabilities and workspace integration
```
