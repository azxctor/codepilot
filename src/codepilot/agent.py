from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from codepilot.config import CodePilotConfig
from codepilot.llm import ChatMessage, LLMError, OpenAICompatibleLLM
from codepilot.session import SessionStore


class LLM(Protocol):
    def chat(self, messages: list[ChatMessage]) -> str:
        ...


@dataclass
class ConversationAgent:
    llm: LLM
    session_store: SessionStore | None = None
    history: list[ChatMessage] = field(default_factory=list)

    def respond(self, message: str) -> str:
        user_message = ChatMessage(role="user", content=message)
        self.history.append(user_message)
        if self.session_store is not None:
            self.session_store.append("user_message", {"content": message})

        try:
            content = self.llm.chat(list(self.history))
        except LLMError as exc:
            content = f"LLM 调用失败：{exc}"

        assistant_message = ChatMessage(role="assistant", content=content)
        self.history.append(assistant_message)
        if self.session_store is not None:
            self.session_store.append("assistant_message", {"content": content})

        return content


def create_default_agent(config: CodePilotConfig) -> ConversationAgent:
    session_store = SessionStore.create(config.sessions_dir)
    return ConversationAgent(
        llm=OpenAICompatibleLLM(config=config),
        session_store=session_store,
    )
