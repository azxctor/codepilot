from codepilot.agent import ConversationAgent
from codepilot.llm import ChatMessage
from codepilot.session import SessionStore


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[ChatMessage]] = []

    def chat(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        return "这是模型回复"


def test_conversation_agent_sends_user_message_to_llm_and_saves_session(tmp_path) -> None:
    llm = FakeLLM()
    store = SessionStore.create(tmp_path / "sessions")
    agent = ConversationAgent(llm=llm, session_store=store)

    response = agent.respond("帮我总结这个项目")

    assert response == "这是模型回复"
    assert llm.calls == [[ChatMessage(role="user", content="帮我总结这个项目")]]
    assert agent.history == [
        ChatMessage(role="user", content="帮我总结这个项目"),
        ChatMessage(role="assistant", content="这是模型回复"),
    ]
    assert [event["type"] for event in store.read_events()] == [
        "user_message",
        "assistant_message",
    ]
