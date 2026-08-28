# Milestone 2 LLM Conversation Design

## Goal

Connect the interactive CLI shell to an OpenAI-compatible LLM so that `codepilot chat` and `codepilot run "<task>"` can send user messages to Kimi and persist conversation events.

## Scope

This milestone covers:

- OpenAI-compatible `/chat/completions` requests.
- Default Kimi Coding endpoint: `https://api.kimi.com/coding/v1`.
- Default model: `kimi-k3`.
- API key lookup from `MOONSHOT_API_KEY`.
- Legacy fallback to `CODEPILOT_API_KEY`.
- JSONL session event storage.
- `codepilot doctor` for masked local diagnostics.
- SSL CA handling for Python `urllib` fallback.

This milestone does not implement tool calling, file reads, shell execution, approvals, streaming output, or session resume.

## Architecture

`ConversationAgent` in `src/codepilot/agent.py` receives user text and delegates model calls to `OpenAICompatibleLLM` in `src/codepilot/llm.py`. The agent appends user and assistant events to `SessionStore` in `src/codepilot/session.py`.

The LLM provider supports two transport paths. If `httpx` is installed it is used. If not, the provider falls back to `urllib` and creates an explicit SSL context with `CODEPILOT_CA_BUNDLE`, `SSL_CERT_FILE`, or `certifi`.

## Components

- `src/codepilot/llm.py`: chat message model, key resolution, HTTP transport, error mapping.
- `src/codepilot/agent.py`: conversation history and model response orchestration.
- `src/codepilot/session.py`: JSONL event writer and reader.
- `src/codepilot/diagnostics.py`: local config and masked API key report.
- `src/codepilot/cli.py`: `run` command and `doctor` command integration.
- `src/codepilot/interaction.py`: natural language input routes to the agent.

## API Key Policy

Secrets are never stored in committed files. The active key is read from environment variables in this order:

1. Configured `api_key_env`
2. `MOONSHOT_API_KEY`
3. `CODEPILOT_API_KEY`

Placeholder values, extra quotes, and surrounding whitespace are handled before a request is sent.

## Error Handling

- Missing API key returns a clear local error.
- Placeholder API key returns a clear local error.
- HTTP 401 returns an authentication-specific error.
- SSL verification issues are mitigated by explicit CA context creation.
- Invalid response shape raises `LLMRequestError`.

## Behavior

`codepilot run "你好"` sends a single message through the same `ConversationAgent` used by chat. `codepilot chat` keeps a process-local message history for the current session and writes JSONL events.

`codepilot doctor` prints endpoint, model, configured key env, active key env, and a masked key preview. It never prints the full key.

## Tests

Covered by:

- `tests/test_llm.py`
- `tests/test_agent.py`
- `tests/test_session.py`
- `tests/test_diagnostics.py`
- `tests/test_cli.py`
- `tests/test_interaction.py`
- `tests/test_config.py`

Required verification:

```bash
python3 -m pytest -q
python3 -m compileall -q src tests
git diff --check
env PYTHONPATH=src python3 -m codepilot doctor
```

## Acceptance Criteria

- `codepilot run "<task>"` routes text to `ConversationAgent`.
- `codepilot chat` routes normal text to `ConversationAgent`.
- LLM requests target `https://api.kimi.com/coding/v1/chat/completions`.
- API key lookup uses `MOONSHOT_API_KEY` by default.
- Session JSONL contains user and assistant events.
- `doctor` reports config and masked secret state.
- SSL path no longer fails when Python default CA store is incomplete but `certifi` is available.

## Implementation Evidence

Implemented in commit:

```text
6ad0b9d feat: add kimi llm conversation support
```
