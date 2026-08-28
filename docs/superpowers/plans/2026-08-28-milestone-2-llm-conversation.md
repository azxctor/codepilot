# 里程碑 2：LLM 交互式对话实现计划

> **面向自动化执行者：** 必需子技能：使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans` 按任务逐项执行本计划。步骤使用 checkbox（`- [ ]`）语法追踪状态。

**目标：** 将 CodePilot 的 chat 和 run 模式连接到兼容 Kimi 的 LLM 对话 Agent，并加入会话日志和本地诊断能力。

**架构：** 新增 `llm.py` 处理兼容 OpenAI 协议的 HTTP 调用，新增 `agent.py` 管理对话历史，新增 `session.py` 写入 JSONL 事件，新增 `diagnostics.py` 做安全配置检查。CLI 和交互层通过小型 `respond()` 协议依赖 Agent。

**技术栈：** 兼容 Python 3.10 的标准库、可选 `httpx`、`certifi`、pytest、JSONL 会话。

---

## 文件结构

- 创建：`src/codepilot/llm.py`
- 创建：`src/codepilot/agent.py`
- 创建：`src/codepilot/session.py`
- 创建：`src/codepilot/diagnostics.py`
- 修改：`src/codepilot/config.py`
- 修改：`src/codepilot/cli.py`
- 修改：`src/codepilot/interaction.py`
- 修改：`README.md`
- 测试：`tests/test_llm.py`
- 测试：`tests/test_agent.py`
- 测试：`tests/test_session.py`
- 测试：`tests/test_diagnostics.py`
- 测试：`tests/test_cli.py`
- 测试：`tests/test_interaction.py`
- 测试：`tests/test_config.py`

### 任务 1：Kimi 配置默认值

**文件：**

- 修改：`src/codepilot/config.py`
- 测试：`tests/test_config.py`

- [x] **步骤 1：编写失败的配置测试**

```python
def test_load_config_returns_defaults_when_config_is_missing(tmp_path):
    config = load_config(tmp_path)
    assert config.default_model == "kimi-k3"
    assert config.api_base_url == "https://api.kimi.com/coding/v1"
    assert config.api_key_env == "MOONSHOT_API_KEY"
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_config.py -q
```

预期：测试失败，因为默认值仍指向旧 Provider。

- [x] **步骤 3：实现配置字段**

给 `CodePilotConfig` 增加 `api_key_env`，将默认值设置为 Kimi Coding，并把 `api_key_env` 写入生成的配置文件。

- [x] **步骤 4：验证配置测试通过**

```bash
python3 -m pytest tests/test_config.py -q
```

预期：配置测试通过。

### 任务 2：LLM Provider

**文件：**

- 创建：`src/codepilot/llm.py`
- 测试：`tests/test_llm.py`

- [x] **步骤 1：编写失败的 Provider 测试**

```python
def test_openai_compatible_llm_posts_to_kimi_chat_completions():
    llm = OpenAICompatibleLLM(
        config=DEFAULT_CONFIG,
        env={"MOONSHOT_API_KEY": "test-api-key"},
        transport=fake_transport,
    )
    content = llm.chat([ChatMessage(role="user", content="你好")])
    assert content == "你好，我是 Kimi。"
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_llm.py -q
```

预期：测试失败，因为 `codepilot.llm` 尚不存在。

- [x] **步骤 3：实现 Provider**

实现 `ChatMessage`、`OpenAICompatibleLLM`、`MissingAPIKeyError`、`LLMRequestError`、`LLMAuthenticationError`、`resolve_api_key()` 和响应内容提取。

- [x] **步骤 4：验证 Provider 测试通过**

```bash
python3 -m pytest tests/test_llm.py -q
```

预期：Provider 测试通过。

### 任务 3：SSL 兜底处理

**文件：**

- 修改：`src/codepilot/llm.py`
- 修改：`pyproject.toml`
- 测试：`tests/test_llm.py`

- [x] **步骤 1：编写失败的 SSL 上下文测试**

```python
def test_urllib_transport_uses_explicit_ssl_context(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    _urllib_transport("https://api.kimi.com/coding/v1/chat/completions", headers, payload, 60)
    assert captured["context"] is not None
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_llm.py::test_urllib_transport_uses_explicit_ssl_context -q
```

预期：测试失败，因为 `urlopen()` 尚未传入 `context`。

- [x] **步骤 3：实现 SSL 上下文创建**

按顺序使用 `CODEPILOT_CA_BUNDLE`、`SSL_CERT_FILE`、`certifi.where()`，最后回退到 Python 默认 SSL 上下文。

- [x] **步骤 4：验证 SSL 行为**

```bash
python3 -m pytest tests/test_llm.py::test_urllib_transport_uses_explicit_ssl_context -q
```

预期：SSL 上下文测试通过。

### 任务 4：对话 Agent 和会话存储

**文件：**

- 创建：`src/codepilot/agent.py`
- 创建：`src/codepilot/session.py`
- 测试：`tests/test_agent.py`
- 测试：`tests/test_session.py`

- [x] **步骤 1：编写失败的 Agent 与会话测试**

```python
def test_conversation_agent_sends_user_message_to_llm_and_saves_session(tmp_path):
    agent = ConversationAgent(
        llm=FakeLLM(),
        session_store=SessionStore.create(tmp_path / "sessions"),
    )
    response = agent.respond("帮我总结这个项目")
    assert response == "这是模型回复"
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_agent.py tests/test_session.py -q
```

预期：测试失败，因为 `agent.py` 和 `session.py` 尚不存在。

- [x] **步骤 3：实现 Agent 和会话存储**

实现 `ConversationAgent.respond()`、进程内历史、`SessionStore.create()`、`append()` 和 `read_events()`。

- [x] **步骤 4：验证 Agent 与会话测试通过**

```bash
python3 -m pytest tests/test_agent.py tests/test_session.py -q
```

预期：Agent 与会话测试通过。

### 任务 5：CLI 与 chat 集成

**文件：**

- 修改：`src/codepilot/cli.py`
- 修改：`src/codepilot/interaction.py`
- 测试：`tests/test_cli.py`
- 测试：`tests/test_interaction.py`

- [x] **步骤 1：编写失败的集成测试**

```python
def test_run_cli_run_sends_task_to_agent(tmp_path):
    exit_code = run_cli(["run", "总结", "这个项目"], workspace=tmp_path, output=output, agent=agent)
    assert exit_code == 0
    assert agent.messages == ["总结 这个项目"]
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_cli.py tests/test_interaction.py -q
```

预期：测试失败，因为 `run` 仍是临时实现，chat 普通文本也尚未路由到 Agent。

- [x] **步骤 3：连接 CLI、交互层和 Agent**

更新 `run_cli()`，允许创建或注入 Agent。更新 `InteractiveSession`，让普通文本调用 `agent.respond()`。

- [x] **步骤 4：验证 CLI 集成**

```bash
python3 -m pytest tests/test_cli.py tests/test_interaction.py -q
env PYTHONPATH=src python3 -m codepilot --help
```

预期：测试通过，`run` 的帮助信息说明它会通过对话 Agent 发送单次任务。

### 任务 6：诊断命令

**文件：**

- 创建：`src/codepilot/diagnostics.py`
- 修改：`src/codepilot/cli.py`
- 测试：`tests/test_diagnostics.py`
- 测试：`tests/test_cli.py`

- [x] **步骤 1：编写失败的 doctor 测试**

```python
def test_run_cli_doctor_reports_masked_api_key_source(tmp_path):
    exit_code = run_cli(
        ["doctor"],
        workspace=tmp_path,
        output=output,
        env={"MOONSHOT_API_KEY": "kimi-test-key"},
    )
    assert exit_code == 0
    assert "active_api_key_env: MOONSHOT_API_KEY" in "\n".join(output.lines)
```

- [x] **步骤 2：运行测试并确认失败**

```bash
python3 -m pytest tests/test_diagnostics.py tests/test_cli.py::test_run_cli_doctor_reports_masked_api_key_source -q
```

预期：测试失败，因为 `doctor` 尚未实现。

- [x] **步骤 3：实现掩码诊断**

实现 `build_doctor_report()` 和 CLI `doctor` 路由。密钥只输出掩码后的预览。

- [x] **步骤 4：验证诊断命令**

```bash
python3 -m pytest tests/test_diagnostics.py tests/test_cli.py -q
env PYTHONPATH=src MOONSHOT_API_KEY='invalid-token' python3 -m codepilot doctor
```

预期：测试通过，`doctor` 只打印掩码后的 Key 信息。

### 任务 7：提交里程碑 2

**文件：**

- 提交本计划创建或修改的全部文件。

- [x] **步骤 1：运行完整验证**

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

预期：全部检查通过。

- [x] **步骤 2：验证本地诊断输出**

```bash
env PYTHONPATH=src python3 -m codepilot doctor
```

预期：命令退出码为 0，并且不打印完整 API Key。

- [x] **步骤 3：提交**

```bash
git add README.md pyproject.toml src tests
git commit -m "feat: add kimi llm conversation support"
```

预期：创建提交 `6ad0b9d` 或等价的里程碑提交。
