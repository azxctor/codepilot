from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from codepilot.config import CodePilotConfig


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


@dataclass(frozen=True)
class ResolvedAPIKey:
    env_name: str
    value: str


class LLMError(RuntimeError):
    pass


class MissingAPIKeyError(LLMError):
    pass


class LLMRequestError(LLMError):
    pass


class LLMAuthenticationError(LLMRequestError):
    pass


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any], int], Mapping[str, Any]]


class OpenAICompatibleLLM:
    def __init__(
        self,
        config: CodePilotConfig,
        env: Mapping[str, str] | None = None,
        transport: Transport | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.config = config
        self.env = env if env is not None else os.environ
        self.transport = transport or _default_transport
        self.timeout_seconds = timeout_seconds

    def chat(self, messages: Sequence[ChatMessage]) -> str:
        api_key = resolve_api_key(self.config, self.env)

        url = f"{self.config.api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key.value}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.default_model,
            "messages": [message.to_dict() for message in messages],
        }
        response = self.transport(url, headers, payload, self.timeout_seconds)
        return _extract_content(response)


def resolve_api_key(config: CodePilotConfig, env: Mapping[str, str]) -> ResolvedAPIKey:
    candidates = _api_key_env_candidates(config)
    for env_name in candidates:
        raw_value = env.get(env_name)
        value = _normalize_api_key(raw_value)
        if not value:
            continue
        if _looks_like_placeholder(value):
            raise MissingAPIKeyError(
                f"{env_name} 看起来还是占位文本，请设置为 Moonshot 控制台生成的真实 API key。"
            )
        return ResolvedAPIKey(env_name=env_name, value=value)

    joined = "、".join(candidates)
    raise MissingAPIKeyError(f"缺少 API key 环境变量：{joined}。请在本地 shell 中设置后重试。")


def _api_key_env_candidates(config: CodePilotConfig) -> list[str]:
    candidates: list[str] = []
    for env_name in [config.api_key_env, "MOONSHOT_API_KEY", "CODEPILOT_API_KEY"]:
        if env_name and env_name not in candidates:
            candidates.append(env_name)
    return candidates


def _normalize_api_key(raw_value: str | None) -> str:
    if raw_value is None:
        return ""

    value = raw_value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1].strip()
    return value


def _looks_like_placeholder(value: str) -> bool:
    lowered = value.lower()
    return (
        "your-api-key" in lowered
        or "your_api_key" in lowered
        or "moonshot api key" in lowered
        or "你的" in value
        or (value.startswith("<") and value.endswith(">"))
    )


def _default_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout_seconds: int,
) -> Mapping[str, Any]:
    try:
        import httpx
    except ImportError:
        return _urllib_transport(url, headers, payload, timeout_seconds)

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(url, headers=dict(headers), json=dict(payload))
            response.raise_for_status()
            return response.json()
    except Exception as exc:
        response = getattr(exc, "response", None)
        if getattr(response, "status_code", None) == 401:
            raise LLMAuthenticationError(_authentication_error_message()) from exc
        raise LLMRequestError(f"LLM 请求失败：{exc}") from exc


def _urllib_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout_seconds: int,
) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
            context=_create_ssl_context(),
        ) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        if exc.code == 401:
            raise LLMAuthenticationError(_authentication_error_message(body)) from exc
        raise LLMRequestError(f"LLM 请求失败：HTTP {exc.code} {body}") from exc
    except Exception as exc:
        raise LLMRequestError(f"LLM 请求失败：{exc}") from exc


def _extract_content(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMRequestError("LLM 响应缺少 choices。")

    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise LLMRequestError("LLM 响应 choices[0] 格式无效。")

    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise LLMRequestError("LLM 响应缺少 message。")

    content = message.get("content")
    if not isinstance(content, str):
        raise LLMRequestError("LLM 响应缺少文本 content。")

    return content


def _create_ssl_context() -> ssl.SSLContext:
    explicit_cafile = os.environ.get("CODEPILOT_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if explicit_cafile:
        return ssl.create_default_context(cafile=explicit_cafile)

    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()

    return ssl.create_default_context(cafile=certifi.where())


def _authentication_error_message(body: str = "") -> str:
    suffix = f" Kimi API 响应：{body}" if body else ""
    return (
        "认证失败：Kimi API 返回 HTTP 401。"
        "请运行 `env PYTHONPATH=src python3 -m codepilot doctor`，确认 active_api_key_env 指向真实有效的 "
        "MOONSHOT_API_KEY，且没有误用占位文本、过期 key、已撤销 key 或多余空白。"
        f"{suffix}"
    )
