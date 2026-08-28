# 里程碑 1：基础 CLI 和交互壳实现计划

> **面向自动化执行者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪状态。

**目标：** 构建第一个可运行的 CodePilot CLI 壳，支持工作区初始化和基础交互式斜杠命令。

**架构：** 首个里程碑保持范围克制。`cli.py` 负责命令解析，`config.py` 负责工作区配置文件，`commands.py` 负责解析斜杠命令，`interaction.py` 负责提示循环。本里程碑不接入 LLM，也不执行工具。

**技术栈：** 兼容 Python 3.10 的标准库、可选 `prompt_toolkit`、pytest、setuptools 包布局。

---

## 文件结构

- 创建：`pyproject.toml`
- 创建：`README.md`
- 创建：`src/codepilot/__init__.py`
- 创建：`src/codepilot/__main__.py`
- 创建：`src/codepilot/cli.py`
- 创建：`src/codepilot/config.py`
- 创建：`src/codepilot/commands.py`
- 创建：`src/codepilot/interaction.py`
- 创建：`tests/test_config.py`
- 创建：`tests/test_commands.py`
- 创建：`tests/test_interaction.py`
- 创建：`tests/test_cli.py`

### 任务 1：配置初始化

**文件：**

- 创建：`src/codepilot/config.py`
- 测试：`tests/test_config.py`

- [x] **步骤 1：编写失败的配置测试**

```python
def test_initialize_workspace_config_creates_config_and_sessions(tmp_path):
    config_path = initialize_workspace_config(tmp_path)
    assert config_path == tmp_path / ".codepilot" / "config.toml"
    assert config_path.exists()
    assert (tmp_path / ".codepilot" / "sessions").is_dir()
```

- [x] **步骤 2：运行测试并确认失败**

```bash
PYTHONPATH=src python3 -m pytest tests/test_config.py -q
```

预期：测试失败，因为 `codepilot.config` 尚不存在。

- [x] **步骤 3：实现配置创建和加载**

在 `src/codepilot/config.py` 中实现 `CodePilotConfig`、`DEFAULT_CONFIG`、`initialize_workspace_config()` 和 `load_config()`。

- [x] **步骤 4：验证配置测试通过**

```bash
python3 -m pytest tests/test_config.py -q
```

预期：配置相关测试通过。

### 任务 2：斜杠命令解析器

**文件：**

- 创建：`src/codepilot/commands.py`
- 测试：`tests/test_commands.py`

- [x] **步骤 1：编写失败的解析器测试**

```python
def test_parse_slash_command_recognizes_command_with_args():
    assert parse_slash_command("/status verbose") == SlashCommand(
        name="status",
        args=("verbose",),
    )
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_commands.py -q
```

预期：测试失败，因为命令解析器尚未实现。

- [x] **步骤 3：实现命令解析**

实现 `SlashCommand` 和 `parse_slash_command()`。普通文本返回 `None`，斜杠命令解析为命令名和参数元组。

- [x] **步骤 4：验证命令测试通过**

```bash
python3 -m pytest tests/test_commands.py -q
```

预期：命令解析测试通过。

### 任务 3：交互壳

**文件：**

- 创建：`src/codepilot/interaction.py`
- 测试：`tests/test_interaction.py`

- [x] **步骤 1：编写失败的交互测试**

```python
def test_interactive_session_handles_status_plan_and_exit(tmp_path):
    inputs = iter(["/status", "/plan", "/exit"])
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
    )
    session.run()
    assert "当前状态：idle" in output.lines
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_interaction.py -q
```

预期：测试失败，因为交互会话尚未实现。

- [x] **步骤 3：实现提示循环**

实现 `InteractiveSession.run()`、输出适配器、输入读取器注入，以及 `/status`、`/plan`、`/exit` 的基础处理。

- [x] **步骤 4：验证交互测试通过**

```bash
python3 -m pytest tests/test_interaction.py -q
```

预期：交互测试通过。

### 任务 4：CLI 入口

**文件：**

- 创建：`src/codepilot/cli.py`
- 创建：`src/codepilot/__main__.py`
- 测试：`tests/test_cli.py`

- [x] **步骤 1：编写失败的 CLI 测试**

```python
def test_run_cli_init_creates_workspace_files(tmp_path):
    exit_code = run_cli(["init"], workspace=tmp_path, output=output)
    assert exit_code == 0
    assert (tmp_path / ".codepilot" / "config.toml").exists()
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_cli.py -q
```

预期：测试失败，因为 CLI 尚未实现。

- [x] **步骤 3：实现 CLI 分发**

使用 `argparse` 实现 `run_cli()`、`main()`、`init`、`chat`，并让无子命令时默认进入 chat。

- [x] **步骤 4：验证 CLI 测试通过**

```bash
python3 -m pytest tests/test_cli.py -q
env PYTHONPATH=src python3 -m codepilot --help
```

预期：CLI 测试通过，帮助信息可以正常渲染。

### 任务 5：提交里程碑 1

**文件：**

- 提交本计划创建或修改的所有文件。

- [x] **步骤 1：运行完整验证**

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

预期：全部检查通过。

- [x] **步骤 2：执行本地 CLI 冒烟检查**

```bash
env PYTHONPATH=src python3 -m codepilot --help
```

预期：命令退出码为 0，帮助信息列出 `init` 和 `chat`。

- [x] **步骤 3：提交**

```bash
git add README.md pyproject.toml src tests
git commit -m "feat: add initial interactive cli shell"
```

预期：创建提交 `29cc437` 或等价的里程碑提交。
