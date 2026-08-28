# 里程碑 1：基础 CLI 和交互壳设计

## 目标

构建 CodePilot 的第一个可运行命令行壳。该里程碑负责建立 Python 包结构、`codepilot` 可执行入口、本地工作区初始化能力，以及最小可用的交互式提示循环。

## 范围

本里程碑包含：

- `codepilot --help`
- `codepilot init`
- `codepilot`
- `codepilot chat`
- `/status`、`/plan`、`/exit`
- 创建 `.codepilot/config.toml`
- 创建 `.codepilot/sessions/` 目录

本里程碑不包含 LLM 调用、通过工具读取项目文件、写文件、执行 shell 命令，或恢复历史会话。

## 架构

CLI 从 `src/codepilot/cli.py` 启动，并把交互行为委托给 `src/codepilot/interaction.py`。配置创建和加载逻辑放在 `src/codepilot/config.py`。斜杠命令解析由 `src/codepilot/commands.py` 负责。

首个交互壳刻意使用 Python 标准库 `argparse`，因为本地运行环境没有预装 Typer 和 Rich。`pyproject.toml` 仍然声明了后续规划依赖，后续里程碑可以在不改变命令形态的前提下接入它们。

## 组件

- `pyproject.toml`：包元数据、控制台脚本、pytest 配置。
- `README.md`：本地使用说明。
- `src/codepilot/__main__.py`：支持 `python3 -m codepilot`。
- `src/codepilot/cli.py`：命令解析和顶层分发。
- `src/codepilot/config.py`：工作区配置创建和加载。
- `src/codepilot/commands.py`：斜杠命令解析。
- `src/codepilot/interaction.py`：交互式提示循环和基础命令处理。

## 行为

`codepilot init` 创建：

```text
.codepilot/
  config.toml
  sessions/
```

`codepilot` 和 `codepilot chat` 进入同一个交互循环。空输入会被忽略。`/status` 显示空闲状态，`/plan` 显示当前还没有任务计划，`/exit` 干净退出。普通文本输入会提示本里程碑尚未接入 LLM Agent。

## 配置

生成的配置文件只保存非敏感默认值。API Key 不会写入 `.codepilot/config.toml`。

## 测试

测试覆盖：

- `tests/test_config.py`
- `tests/test_commands.py`
- `tests/test_interaction.py`
- `tests/test_cli.py`

必须执行的验证命令：

```bash
python3 -m pytest -q
env PYTHONPATH=src python3 -m codepilot --help
env PYTHONPATH=src python3 -m codepilot chat
```

## 验收标准

- `codepilot --help` 能打印可用命令。
- `codepilot init` 能创建 `.codepilot/config.toml` 和 `.codepilot/sessions/`。
- `codepilot` 能进入与 `codepilot chat` 相同的交互壳。
- `/exit` 能无异常退出。
- `/status` 和 `/plan` 返回稳定的交互壳输出。

## 实现证据

已在以下提交中实现：

```text
29cc437 feat: add initial interactive cli shell
```
