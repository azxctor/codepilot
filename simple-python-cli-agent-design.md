# Python 本地 Agent CLI 简易实现方案

## 1. 背景与目标

目标是实现一个类似 Claude Code 的简易版终端工具，暂定命令名为 `codepilot`。它运行在本地 terminal 中，核心使用方式是交互式对话：用户描述一个开发目标，Agent 通过多轮沟通、上下文读取、任务拆解、工具调用、确认执行和验证反馈来持续推进任务。

第一版不追求完整 IDE Agent 能力，而是先做一个最小可用的交互式本地 Agent CLI：

- 能在当前目录理解项目结构。
- 能通过多轮对话推进一个开发任务。
- 能维护当前任务计划、步骤状态和会话历史。
- 能调用 LLM API。
- 能使用受控工具读取文件、搜索文件、写入文件、执行 shell 命令。
- 对文件写入和 shell 执行默认要求用户确认。
- 能在每个阶段给出下一步计划、执行结果和验证建议。

## 2. 非目标

第一版暂不实现以下能力：

- 长期后台 daemon。
- 多 Agent 协作。
- 自动提交 Git commit。
- 自动安装依赖或运行破坏性命令。
- 全量代码索引和向量数据库。
- 类 IDE 的复杂 diff UI。
- 远程任务执行。
- 无确认的全自动代码修改。

这些能力可以作为后续版本扩展，MVP 阶段先把交互式任务推进链路做清楚，保持架构清晰、权限边界可控。

## 3. 技术栈

建议使用 Python 实现：

- Python 3.11+
- `typer`：CLI 命令入口。
- `rich`：终端输出、状态展示、确认提示、Markdown 渲染。
- `pydantic`：配置、工具参数、LLM 消息结构校验。
- `httpx`：调用 LLM API。
- `prompt_toolkit`：交互式 chat 输入、历史记录、快捷键、多行输入。
- `pytest`：单元测试和工具测试。

可选补充：

- `python-dotenv`：读取 `.env`。
- `tomli` / `tomllib`：读取 `pyproject.toml` 或本地配置。
- `pathspec`：识别 `.gitignore`，避免扫描无关文件。

## 4. CLI 使用方式

MVP 以交互式会话为主，`run` 只是快捷入口。

```bash
codepilot init
codepilot
codepilot chat
codepilot chat --resume latest
codepilot run "总结这个项目"
```

### `codepilot`

默认进入交互式任务会话，等价于 `codepilot chat`。推荐把它作为主要入口。

用户可以直接输入目标：

```text
> 帮我给这个项目加一个基础 CLI 入口
```

Agent 应该先理解目标，再根据情况读取文件、提出计划、询问确认、执行修改、运行验证，并持续汇报任务进度。

### `codepilot init`

在当前目录创建本地配置文件，例如：

```text
.codepilot/
  config.toml
  sessions/
```

配置内容包括：

- 默认模型。
- LLM API base URL。
- 是否允许 shell tool。
- 是否允许文件写入。
- 单次上下文最大文件数量。
- 默认忽略路径。

### `codepilot chat`

进入多轮交互模式，保留当前会话历史。适合连续推进一个开发任务。

交互中支持普通自然语言，也支持少量 slash commands：

```text
/status        查看当前任务状态
/plan          查看或刷新当前计划
/diff          查看本轮建议修改摘要
/approve       批准当前等待确认的操作
/reject        拒绝当前等待确认的操作
/resume        恢复最近会话
/clear         清空当前对话上下文
/exit          退出
```

最早的交互壳可以先实现 `/status`、`/plan`、`/exit`。第一版完成前应补齐 `/approve`、`/reject` 和 `chat --resume latest`；`/diff`、`/clear` 可以放到后续增强。

### `codepilot run "<task>"`

执行一个快捷任务，内部仍复用交互式 Agent Loop。它适合低风险、只读或短任务：

- 总结项目。
- 找入口文件。
- 解释某段代码。
- 生成修改建议。

如果任务需要写文件、执行 shell 或多轮澄清，`run` 应提示用户切换到 `codepilot chat`，或者在当前命令中进入确认流程。

### 交互式任务推进模型

交互式模式不是普通聊天，而是围绕一个开发目标持续推进：

1. 用户提出目标。
2. Agent 读取必要上下文，不直接猜测项目结构。
3. 如果目标不清楚，Agent 只问一个关键澄清问题。
4. 如果目标清楚，Agent 生成 2-5 步短计划。
5. 用户可以确认、修改或打断计划。
6. Agent 一次推进一个步骤。
7. 只读工具可以自动执行。
8. 写文件和执行 shell 前必须等待用户确认。
9. 每个步骤结束后更新状态。
10. 完成后给出修改摘要、验证结果和下一步建议。

这个模型的重点是“对话驱动任务状态”，而不是每次输入都被当作独立问题处理。

## 5. 目录结构

建议项目结构如下：

```text
codepilot/
  pyproject.toml
  README.md
  src/
    codepilot/
      __init__.py
      cli.py
      interaction.py
      agent.py
      task_state.py
      commands.py
      approvals.py
      config.py
      llm.py
      session.py
      workspace.py
      prompts.py
      tools/
        __init__.py
        base.py
        read_file.py
        list_files.py
        search_text.py
        write_file.py
        shell.py
  tests/
    test_workspace.py
    test_tools.py
    test_agent.py
    test_task_state.py
    test_commands.py
```

## 6. 核心架构

整体分为八层：

```text
CLI Layer
  -> Interactive Session Controller
    -> Agent Loop
      -> Task State / Planner
    -> LLM Provider
    -> Tool Registry
      -> Approval Gate
      -> Workspace Tools
      -> Shell Tool
    -> Session Store
```

### CLI Layer

负责解析命令、读取配置、初始化工作目录、展示终端输出。

核心文件：

- `cli.py`

主要职责：

- 注册 `init`、`run`、`chat` 命令。
- 加载 `.codepilot/config.toml`。
- 创建 `InteractiveSession` 和 `Agent` 实例。
- 把用户输入交给交互式会话控制器。
- 展示 Agent 返回的结果、工具调用和确认提示。

### Interactive Session Controller

负责 terminal 中的持续对话体验。

核心文件：

- `interaction.py`
- `commands.py`

主要职责：

- 使用 `prompt_toolkit` 读取用户输入。
- 支持多行输入和历史记录。
- 区分自然语言输入和 slash command。
- 在 Agent 等待确认时接收 `/approve` 或 `/reject`。
- 在每轮后展示任务状态、工具结果和下一步建议。
- 退出前保存 session。

### Agent Loop

负责调度 LLM 和工具，是系统核心。

核心文件：

- `agent.py`

基本循环：

1. 接收用户任务。
2. 判断是否需要更新任务状态或计划。
3. 构造系统提示词、会话历史和工作区上下文。
4. 调用 LLM。
5. 如果 LLM 要调用工具，则先经过权限判断。
6. 对只读工具直接执行。
7. 对写文件和 shell 工具创建 pending approval，等待用户确认。
8. 把工具结果追加到消息历史。
9. 继续调用 LLM，直到得到当前轮回复或等待用户输入。

MVP 可以限制最大循环次数，例如最多 8 次，避免工具调用失控。

### Task State / Planner

负责维护当前任务的结构化状态。

核心文件：

- `task_state.py`

建议维护以下字段：

```python
class TaskState(BaseModel):
    goal: str
    plan: list[PlanStep]
    current_step: int | None = None
    status: Literal["idle", "planning", "running", "waiting_approval", "blocked", "done"]
    pending_approval: PendingApproval | None = None
```

任务状态用于让 Agent 的输出更稳定：

- 用户提出新目标时，先创建或更新 `goal`。
- Agent 需要执行多步任务时，生成 `plan`。
- 每次工具调用后更新当前步骤状态。
- 遇到缺信息、失败或需要用户确认时进入对应状态。
- `/status` 和 `/plan` 直接读取这个结构，而不是重新让模型猜。

### Approval Gate

负责所有需要用户确认的操作。

核心文件：

- `approvals.py`

需要确认的操作包括：

- 写入新文件。
- 覆盖已有文件。
- 执行 shell 命令。
- 后续可扩展为安装依赖、删除文件、提交 Git 等。

Approval Gate 应记录：

- 操作类型。
- 操作原因。
- 目标路径或命令。
- diff 摘要或命令预览。
- 等待确认的唯一 ID。

用户确认后，Agent 才能继续执行对应工具。

### LLM Provider

负责封装模型调用。

核心文件：

- `llm.py`

建议先实现一个 OpenAI-compatible provider，只要目标服务兼容 `/v1/chat/completions` 即可。

需要支持：

- 普通对话消息。
- tool calling 或类 tool calling JSON 输出。
- 超时。
- 错误重试。
- 流式输出可以放到第二阶段。

### Tool Registry

负责注册和执行工具。

核心文件：

- `tools/base.py`
- `tools/__init__.py`

每个工具都应该有清晰的输入输出结构：

```python
class ToolInput(BaseModel):
    pass

class ToolResult(BaseModel):
    ok: bool
    content: str
    error: str | None = None
```

工具统一通过 registry 调用，Agent 不直接依赖具体工具实现。

### Workspace Context

负责限制所有文件操作都发生在当前项目目录内。

核心文件：

- `workspace.py`

必须保证：

- 不能通过 `../` 访问工作区外文件。
- 默认忽略 `.git`、`.venv`、`node_modules`、大文件、二进制文件。
- 读取文件有大小限制。
- 搜索文件有数量限制。

### Session Store

负责保存交互式任务会话。

核心文件：

- `session.py`

MVP 可以用 JSONL 文件保存：

```text
.codepilot/sessions/2026-08-28T19-30-00.jsonl
```

每行保存一条事件，方便调试和恢复。事件类型包括：

- 用户消息。
- Assistant 回复。
- 工具调用请求。
- 工具执行结果。
- 任务计划更新。
- pending approval 创建。
- 用户批准或拒绝。
- 错误事件。

恢复会话时，需要重建：

- 消息历史。
- 当前任务目标。
- 当前计划。
- 当前步骤状态。
- 是否有等待确认的操作。

## 7. 工具设计

MVP 建议先实现五个工具。

### `list_files`

列出当前工作区文件。

输入：

- `path`
- `max_depth`

输出：

- 文件路径列表。

限制：

- 默认跳过忽略目录。
- 默认最多返回 300 个路径。

### `read_file`

读取指定文本文件。

输入：

- `path`
- `start_line`
- `end_line`

输出：

- 带行号的文本内容。

限制：

- 文件必须在工作区内。
- 单次读取最大字符数，例如 20,000。

### `search_text`

在当前目录搜索文本。

输入：

- `query`
- `glob`
- `max_results`

实现方式：

- 优先调用 Python 自己的文件遍历和正则搜索。
- 后续可以接入 `rg` 提升速度。

### `write_file`

写入或覆盖文件。

输入：

- `path`
- `content`

限制：

- 默认必须用户确认。
- 只能写工作区内文件。
- 如果文件已存在，先展示 diff 摘要。

### `run_shell`

执行 shell 命令。

输入：

- `command`
- `timeout_seconds`

限制：

- 默认必须用户确认。
- 工作目录固定为当前工作区。
- 第一版不允许交互式命令。
- 设置超时，例如 30 秒。
- 对明显危险命令进行拦截，例如 `rm -rf /`、`sudo`、磁盘格式化命令等。

## 8. 权限策略

权限策略应保守设计。

默认规则：

- 读取文件：允许。
- 搜索文件：允许。
- 写入文件：确认后允许。
- 执行 shell：确认后允许。
- 访问工作区外路径：拒绝。
- 执行危险命令：拒绝。

配置示例：

```toml
[permissions]
allow_read = true
allow_write = "ask"
allow_shell = "ask"
deny_outside_workspace = true

[limits]
max_tool_iterations = 8
max_file_chars = 20000
max_search_results = 100
shell_timeout_seconds = 30
```

## 9. Agent 提示词策略

系统提示词需要明确告诉模型：

- 你是本地代码助手。
- 你通过多轮对话帮助用户推进开发任务。
- 对复杂任务先形成简短计划，再逐步执行。
- 每次只推进清晰的一小步。
- 不要猜测文件内容，必须通过工具读取。
- 写文件和执行 shell 前要说明原因。
- 需要确认的操作不能假装已经执行。
- 优先做小范围修改。
- 不要访问工作区外路径。
- 工具失败时要解释失败原因。
- 完成修改后，应建议或执行合适的验证。
- 如果目标不清楚，先问一个关键澄清问题。

MVP 可以先使用固定系统提示词，后续再支持项目级 `CODEPILOT.md` 指令文件。

## 10. 数据流

以 `codepilot chat` 中推进一个代码修改任务为例：

1. CLI 启动交互式会话。
2. 用户输入目标，例如“帮我给这个项目加一个基础 CLI 入口”。
3. Interactive Session Controller 把输入交给 Agent。
4. Agent 创建 `TaskState.goal`。
5. Agent 调用 LLM 判断需要读取哪些上下文。
6. LLM 请求调用 `list_files` 和 `read_file`。
7. Agent 执行只读工具，并把结果写入 session。
8. LLM 生成简短计划，例如“检查结构、添加入口、补 README、运行测试”。
9. Agent 更新 `TaskState.plan` 并向用户展示。
10. 用户继续确认或调整计划。
11. Agent 逐步执行计划。
12. 如果需要写文件，Agent 创建 pending approval。
13. CLI 展示 diff 摘要和确认提示。
14. 用户输入 `/approve` 后，Agent 执行 `write_file`。
15. Agent 建议或请求执行验证命令。
16. 用户确认后，Agent 执行 `run_shell`。
17. Agent 根据验证结果更新任务状态。
18. 完成后输出修改摘要、验证结果和剩余风险。

以 `codepilot run "总结这个项目"` 为例：

1. CLI 接收快捷任务。
2. CLI 加载配置和工作区。
3. Agent 生成初始消息。
4. LLM 请求调用 `list_files`。
5. Agent 执行 `list_files`。
6. LLM 根据文件列表请求读取关键文件。
7. Agent 执行 `read_file`。
8. LLM 生成项目总结。
9. CLI 用 Rich 渲染结果。

如果 `run` 过程中遇到需要多轮确认的修改任务：

1. Agent 先说明需要进入交互式确认流程。
2. CLI 可以继续在当前进程内询问确认。
3. 如果任务变复杂，提示用户使用 `codepilot chat --resume latest` 继续。

## 11. 错误处理

需要明确处理以下错误：

- LLM API key 缺失。
- LLM 请求超时。
- 模型返回非法 tool 参数。
- 文件不存在。
- 文件过大。
- 路径越界。
- shell 命令超时。
- 用户拒绝确认。

错误输出应包含：

- 出错位置。
- 简短原因。
- 可操作建议。

例如：

```text
读取失败：README.md 不存在。
建议：先运行 list_files 查看当前目录文件。
```

## 12. 测试策略

MVP 至少覆盖以下测试：

- `Workspace` 能阻止 `../outside.txt`。
- `read_file` 能按行读取。
- `list_files` 能跳过忽略目录。
- `write_file` 默认需要确认。
- `run_shell` 能处理超时。
- `Agent` 在工具调用超过上限时停止。
- `TaskState` 能创建计划、更新步骤状态、标记完成或阻塞。
- slash command parser 能识别 `/status`、`/plan`、`/exit`。
- pending approval 能保存、批准、拒绝并恢复。
- session replay 能恢复最近任务目标和计划。

推荐命令：

```bash
pytest
```

## 13. 实现里程碑

### Milestone 1：基础 CLI 和交互壳

- 创建 Python 包结构。
- 实现 `codepilot init`。
- 实现 `codepilot` / `codepilot chat` 入口。
- 实现配置读取。
- 实现 Rich 输出。
- 实现 prompt loop，能读取用户输入和退出。

验收标准：

- 能运行 `codepilot --help`。
- 能在当前目录生成 `.codepilot/config.toml`。
- 能进入交互式会话并用 `/exit` 退出。

### Milestone 2：LLM 交互式对话能力

- 实现 LLM Provider。
- 实现交互式消息循环。
- 保存基础 session 事件。
- 实现 `codepilot run "<task>"` 作为快捷入口。

验收标准：

- 能在 `codepilot chat` 中连续和模型对话。
- 退出后能看到 session 文件。
- `run` 和 `chat` 复用同一个 Agent。

### Milestone 3：任务状态和只读工具

- 实现 `TaskState`。
- 实现 `/status` 和 `/plan`。
- 实现 `list_files`。
- 实现 `read_file`。
- 实现 `search_text`。
- 接入 Agent Loop。

验收标准：

- 用户提出目标后能生成短计划。
- 能展示当前任务状态。
- 能基于真实文件内容回答问题，不凭空猜测。

### Milestone 4：受控写入、shell 和确认机制

- 实现 `write_file`。
- 实现 `run_shell`。
- 实现 pending approval。
- 实现 `/approve` 和 `/reject`。
- 加入路径和命令安全限制。

验收标准：

- 写文件前展示确认。
- 执行 shell 前展示确认。
- 拒绝访问工作区外路径。
- 用户拒绝后不会执行操作，并能继续对话。

### Milestone 5：会话恢复和任务推进体验

- 实现 `codepilot chat --resume latest`。
- 恢复任务目标、计划、步骤状态和 pending approval。
- 每轮输出阶段性进度和下一步建议。
- 支持在任务中途打断、改计划或继续推进。

验收标准：

- 能恢复最近一次任务会话。
- 能从上次中断的步骤继续。
- 能在完成任务后展示修改摘要和验证结果。

## 14. 第一版验收标准

第一版完成后，应能做到：

- `codepilot init` 初始化配置。
- `codepilot` 或 `codepilot chat` 进入交互式任务会话。
- 用户提出开发目标后，Agent 能读取上下文、生成计划并逐步推进。
- `/status` 能查看当前任务状态。
- `/plan` 能查看当前计划。
- `codepilot run "总结这个项目"` 仍能作为快捷只读任务使用。
- 写文件和 shell 执行前必须确认。
- 所有文件操作都被限制在当前工作区内。
- session 能保存并恢复最近任务。
- 有基础单元测试覆盖核心工具、路径限制、任务状态和会话恢复。

## 15. 后续扩展方向

后续可以逐步加入：

- 流式输出。
- 更好的 diff 预览。
- `CODEPILOT.md` 项目指令。
- Git 状态感知。
- 自动测试建议。
- 可插拔工具系统。
- MCP tool 接入。
- 向量索引或符号索引。
- 多模型 provider。

## 16. 推荐最小实现顺序

建议按以下顺序实现，避免一开始做得过重：

1. `typer` CLI 骨架。
2. `prompt_toolkit` 交互式输入循环。
3. 配置文件和工作区边界。
4. LLM Provider。
5. session 事件保存。
6. `TaskState`、`/status`、`/plan`。
7. `list_files`、`read_file`、`search_text`。
8. Agent Loop 和计划生成。
9. `write_file`、`run_shell` 和确认提示。
10. `chat --resume latest`。
11. `run` 快捷命令。
12. 测试与打包。

这个顺序能最快得到一个以交互式任务推进为核心的本地 Agent CLI，同时保留向 Claude Code 类工具演进的空间。
