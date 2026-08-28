import pytest
import io
import urllib.error
import urllib.request

from codepilot.config import DEFAULT_CONFIG
from codepilot.llm import (
    ChatMessage,
    LLMAuthenticationError,
    MissingAPIKeyError,
    OpenAICompatibleLLM,
    _urllib_transport,
    resolve_api_key,
)


def test_openai_compatible_llm_posts_to_moonshot_chat_completions() -> None:
    seen = {}

    def fake_transport(url, headers, payload, timeout_seconds):
        seen["url"] = url
        seen["headers"] = headers
        seen["payload"] = payload
        seen["timeout_seconds"] = timeout_seconds
        return {"choices": [{"message": {"content": "你好，我是 Kimi。"}}]}

    llm = OpenAICompatibleLLM(
        config=DEFAULT_CONFIG,
        env={"MOONSHOT_API_KEY": "test-api-key"},
        transport=fake_transport,
    )

    content = llm.chat([ChatMessage(role="user", content="你好")])

    assert content == "你好，我是 Kimi。"
    assert seen["url"] == "https://api.kimi.com/coding/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer test-api-key"
    assert seen["payload"]["model"] == "kimi-k3"
    assert seen["payload"]["messages"] == [{"role": "user", "content": "你好"}]
    assert seen["timeout_seconds"] == 60


def test_openai_compatible_llm_requires_api_key_env_var() -> None:
    llm = OpenAICompatibleLLM(config=DEFAULT_CONFIG, env={}, transport=lambda *args: {})

    with pytest.raises(MissingAPIKeyError) as exc_info:
        llm.chat([ChatMessage(role="user", content="你好")])

    assert "MOONSHOT_API_KEY" in str(exc_info.value)


def test_resolve_api_key_prefers_configured_env_var() -> None:
    resolved = resolve_api_key(
        DEFAULT_CONFIG,
        {"MOONSHOT_API_KEY": "  test-moonshot-key  ", "CODEPILOT_API_KEY": "old-key"},
    )

    assert resolved.env_name == "MOONSHOT_API_KEY"
    assert resolved.value == "test-moonshot-key"


def test_resolve_api_key_falls_back_to_legacy_env_var() -> None:
    resolved = resolve_api_key(DEFAULT_CONFIG, {"CODEPILOT_API_KEY": "legacy-key"})

    assert resolved.env_name == "CODEPILOT_API_KEY"
    assert resolved.value == "legacy-key"


def test_resolve_api_key_rejects_placeholder_values() -> None:
    with pytest.raises(MissingAPIKeyError):
        resolve_api_key(DEFAULT_CONFIG, {"MOONSHOT_API_KEY": "<你提供的 Moonshot API key>"})


def test_urllib_transport_uses_explicit_ssl_context(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"ok"}}]}'

    def fake_urlopen(request, timeout, context):
        captured["request"] = request
        captured["timeout"] = timeout
        captured["context"] = context
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    response = _urllib_transport(
        "https://api.kimi.com/coding/v1/chat/completions",
        {"Authorization": "Bearer test-key"},
        {"model": "kimi-k3", "messages": []},
        60,
    )

    assert response == {"choices": [{"message": {"content": "ok"}}]}
    assert captured["timeout"] == 60
    assert captured["context"] is not None


def test_urllib_transport_converts_http_401_to_authentication_error(monkeypatch) -> None:
    def fake_urlopen(request, timeout, context):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":{"message":"Invalid Authentication"}}'),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(LLMAuthenticationError) as exc_info:
        _urllib_transport(
            "https://api.kimi.com/coding/v1/chat/completions",
            {"Authorization": "Bearer invalid-token"},
            {"model": "kimi-k3", "messages": []},
            60,
        )

    message = str(exc_info.value)
    assert "认证失败" in message
    assert "MOONSHOT_API_KEY" in message
