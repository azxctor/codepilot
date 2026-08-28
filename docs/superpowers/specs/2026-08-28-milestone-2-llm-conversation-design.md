# 里程碑 2：LLM 交互式对话设计

## 目标

把交互式 CLI 壳连接到兼容 OpenAI 协议的 LLM，使 `codepilot chat` 和 `codepilot run "<task>"` 能把用户消息发送给 Kimi，并持久化对话事件。

## 范围

本里程碑包含：

- 兼容 OpenAI 的 `/chat/completions` 请求。
- 默认 Kimi Coding 端点：`https://api.kimi.com/coding/v1`。
- 默认模型：`kimi-k3`。
- 从 `MOONSHOT_API_KEY` 读取 API Key。
- 兼容旧的 `CODEPILOT_API_KEY` 兜底环境变量。
- JSONL 会话事件存储。
- `codepilot doctor` 掩码诊断。
- Python `urllib` 兜底路径的 SSL CA 处理。

本里程碑不包含工具调用、文件读取、shell 执行、用户审批、流式输出，或恢复历史会话。

## 架构

`src/codepilot/agent.py` 中的 `ConversationAgent` 接收用户文本，并把模型调用委托给 `src/codepilot/llm.py` 中的 `OpenAICompatibleLLM`。Agent 会把用户事件和助手事件追加写入 `src/codepilot/session.py` 中的 `SessionStore`。

LLM Provider 支持两条传输路径。如果安装了 `httpx`，优先使用 `httpx`；否则回退到 `urllib`，并通过 `CODEPILOT_CA_BUNDLE`、`SSL_CERT_FILE` 或 `certifi` 创建显式 SSL 上下文。

## 组件

- `src/codepilot/llm.py`：聊天消息模型、Key 解析、HTTP 传输、错误映射。
- `src/codepilot/agent.py`：对话历史和模型响应编排。
- `src/codepilot/session.py`：JSONL 事件写入与读取。
- `src/codepilot/diagnostics.py`：本地配置与 API Key 掩码报告。
- `src/codepilot/cli.py`：集成 `run` 命令和 `doctor` 命令。
- `src/codepilot/interaction.py`：把自然语言输入路由给 Agent。

## API Key 策略

密钥绝不写入已提交文件。运行时按以下顺序读取有效 Key：

1. 配置项 `api_key_env` 指定的环境变量。
2. `MOONSHOT_API_KEY`。
3. `CODEPILOT_API_KEY`。

发送请求前会处理无效示例值、多余引号和首尾空白。

## 错误处理

- 缺少 API Key 时返回清晰的本地错误。
- API Key 是无效示例值时返回清晰的本地错误。
- HTTP 401 返回认证专用错误。
- 通过显式 CA 上下文缓解 SSL 校验问题。
- 响应结构无效时抛出 `LLMRequestError`。

## 行为

`codepilot run "你好"` 通过与 chat 相同的 `ConversationAgent` 发送单条消息。`codepilot chat` 在当前进程内维护会话历史，并把事件写入 JSONL。

`codepilot doctor` 输出端点、模型、配置的 Key 环境变量、实际命中的 Key 环境变量，以及掩码后的 Key 预览。它绝不会输出完整密钥。

## 测试

测试覆盖：

- `tests/test_llm.py`
- `tests/test_agent.py`
- `tests/test_session.py`
- `tests/test_diagnostics.py`
- `tests/test_cli.py`
- `tests/test_interaction.py`
- `tests/test_config.py`

必须执行的验证命令：

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
env PYTHONPATH=src python3 -m codepilot doctor
```

## 验收标准

- `codepilot run "<task>"` 把文本路由到 `ConversationAgent`。
- `codepilot chat` 把普通文本路由到 `ConversationAgent`。
- LLM 请求目标为 `https://api.kimi.com/coding/v1/chat/completions`。
- 默认从 `MOONSHOT_API_KEY` 读取 API Key。
- 会话 JSONL 包含用户事件和助手事件。
- `doctor` 能报告配置和掩码后的密钥状态。
- 当 Python 默认 CA Store 不完整但 `certifi` 可用时，SSL 路径不再失败。

## 实现证据

已在以下提交中实现：

```text
6ad0b9d feat: add kimi llm conversation support
```
