# Milestone 2 LLM Conversation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect CodePilot chat and run modes to a Kimi-compatible LLM conversation agent with session logging and local diagnostics.

**Architecture:** Add `llm.py` for OpenAI-compatible HTTP calls, `agent.py` for conversation history, `session.py` for JSONL events, and `diagnostics.py` for safe config inspection. CLI and interaction layers should depend on the agent through a small `respond()` protocol.

**Tech Stack:** Python 3.10 compatible standard library, optional `httpx`, `certifi`, pytest, JSONL sessions.

---

## File Structure

- Create: `src/codepilot/llm.py`
- Create: `src/codepilot/agent.py`
- Create: `src/codepilot/session.py`
- Create: `src/codepilot/diagnostics.py`
- Modify: `src/codepilot/config.py`
- Modify: `src/codepilot/cli.py`
- Modify: `src/codepilot/interaction.py`
- Modify: `README.md`
- Test: `tests/test_llm.py`
- Test: `tests/test_agent.py`
- Test: `tests/test_session.py`
- Test: `tests/test_diagnostics.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_interaction.py`
- Test: `tests/test_config.py`

### Task 1: Kimi Config Defaults

**Files:**

- Modify: `src/codepilot/config.py`
- Test: `tests/test_config.py`

- [x] **Step 1: Write failing config tests**

```python
def test_load_config_returns_defaults_when_config_is_missing(tmp_path):
    config = load_config(tmp_path)
    assert config.default_model == "kimi-k3"
    assert config.api_base_url == "https://api.kimi.com/coding/v1"
    assert config.api_key_env == "MOONSHOT_API_KEY"
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_config.py -q
```

Expected: failure while defaults still point to the previous provider values.

- [x] **Step 3: Implement config fields**

Add `api_key_env` to `CodePilotConfig`, set the defaults to Kimi Coding, and render `api_key_env` into generated config files.

- [x] **Step 4: Verify config tests pass**

```bash
python3 -m pytest tests/test_config.py -q
```

Expected: config tests pass.

### Task 2: LLM Provider

**Files:**

- Create: `src/codepilot/llm.py`
- Test: `tests/test_llm.py`

- [x] **Step 1: Write failing provider tests**

```python
def test_openai_compatible_llm_posts_to_moonshot_chat_completions():
    llm = OpenAICompatibleLLM(config=DEFAULT_CONFIG, env={"MOONSHOT_API_KEY": "test-api-key"}, transport=fake_transport)
    content = llm.chat([ChatMessage(role="user", content="你好")])
    assert content == "你好，我是 Kimi。"
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_llm.py -q
```

Expected: failure because `codepilot.llm` does not exist.

- [x] **Step 3: Implement provider**

Implement `ChatMessage`, `OpenAICompatibleLLM`, `MissingAPIKeyError`, `LLMRequestError`, `LLMAuthenticationError`, `resolve_api_key()`, and response content extraction.

- [x] **Step 4: Verify provider tests pass**

```bash
python3 -m pytest tests/test_llm.py -q
```

Expected: provider tests pass.

### Task 3: SSL Fallback Handling

**Files:**

- Modify: `src/codepilot/llm.py`
- Modify: `pyproject.toml`
- Test: `tests/test_llm.py`

- [x] **Step 1: Write failing SSL context test**

```python
def test_urllib_transport_uses_explicit_ssl_context(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    _urllib_transport("https://api.kimi.com/coding/v1/chat/completions", headers, payload, 60)
    assert captured["context"] is not None
```

- [x] **Step 2: Run test to verify it fails**

```bash
python3 -m pytest tests/test_llm.py::test_urllib_transport_uses_explicit_ssl_context -q
```

Expected: failure because `urlopen()` is not called with `context`.

- [x] **Step 3: Implement SSL context creation**

Use `CODEPILOT_CA_BUNDLE`, then `SSL_CERT_FILE`, then `certifi.where()`, then Python default SSL context.

- [x] **Step 4: Verify SSL behavior**

```bash
python3 -m pytest tests/test_llm.py::test_urllib_transport_uses_explicit_ssl_context -q
```

Expected: SSL context test passes.

### Task 4: Conversation Agent and Session Store

**Files:**

- Create: `src/codepilot/agent.py`
- Create: `src/codepilot/session.py`
- Test: `tests/test_agent.py`
- Test: `tests/test_session.py`

- [x] **Step 1: Write failing agent and session tests**

```python
def test_conversation_agent_sends_user_message_to_llm_and_saves_session(tmp_path):
    agent = ConversationAgent(llm=FakeLLM(), session_store=SessionStore.create(tmp_path / "sessions"))
    response = agent.respond("帮我总结这个项目")
    assert response == "这是模型回复"
```

- [x] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_agent.py tests/test_session.py -q
```

Expected: failure because `agent.py` and `session.py` do not exist.

- [x] **Step 3: Implement agent and session store**

Implement `ConversationAgent.respond()`, process-local history, `SessionStore.create()`, `append()`, and `read_events()`.

- [x] **Step 4: Verify agent and session tests pass**

```bash
python3 -m pytest tests/test_agent.py tests/test_session.py -q
```

Expected: agent and session tests pass.

### Task 5: CLI and Chat Integration

**Files:**

- Modify: `src/codepilot/cli.py`
- Modify: `src/codepilot/interaction.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_interaction.py`

- [x] **Step 1: Write failing integration tests**

```python
def test_run_cli_run_sends_task_to_agent(tmp_path):
    exit_code = run_cli(["run", "总结", "这个项目"], workspace=tmp_path, output=output, agent=agent)
    assert exit_code == 0
    assert agent.messages == ["总结 这个项目"]
```

- [x] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_cli.py tests/test_interaction.py -q
```

Expected: failure while `run` is still a placeholder and chat normal text is not routed to the agent.

- [x] **Step 3: Connect CLI and interaction to the agent**

Update `run_cli()` to create or accept an agent. Update `InteractiveSession` so normal text calls `agent.respond()`.

- [x] **Step 4: Verify CLI integration**

```bash
python3 -m pytest tests/test_cli.py tests/test_interaction.py -q
env PYTHONPATH=src python3 -m codepilot --help
```

Expected: tests pass and `run` help says it sends one task through the conversation agent.

### Task 6: Diagnostics

**Files:**

- Create: `src/codepilot/diagnostics.py`
- Modify: `src/codepilot/cli.py`
- Test: `tests/test_diagnostics.py`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing doctor tests**

```python
def test_run_cli_doctor_reports_masked_api_key_source(tmp_path):
    exit_code = run_cli(["doctor"], workspace=tmp_path, output=output, env={"MOONSHOT_API_KEY": "kimi-test-key-abcdef1234567890"})
    assert exit_code == 0
    assert "active_api_key_env: MOONSHOT_API_KEY" in "\n".join(output.lines)
```

- [x] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_diagnostics.py tests/test_cli.py::test_run_cli_doctor_reports_masked_api_key_source -q
```

Expected: failure because `doctor` is not implemented.

- [x] **Step 3: Implement masked diagnostics**

Implement `build_doctor_report()` and CLI `doctor` routing. Mask secrets as `kimi...7890` style output.

- [x] **Step 4: Verify diagnostics**

```bash
python3 -m pytest tests/test_diagnostics.py tests/test_cli.py -q
env PYTHONPATH=src MOONSHOT_API_KEY='invalid-token' python3 -m codepilot doctor
```

Expected: tests pass and doctor prints only masked key data.

### Task 7: Commit Milestone 2

**Files:**

- Commit all files created or modified in this plan.

- [x] **Step 1: Run full verification**

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
```

Expected: all checks pass.

- [x] **Step 2: Commit**

```bash
git add .gitignore README.md pyproject.toml src tests
git commit -m "feat: add kimi llm conversation support"
```

Expected: commit `6ad0b9d` or equivalent milestone commit is created.
