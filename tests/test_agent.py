from codepilot.agent import ConversationAgent
from codepilot.llm import ChatMessage
from codepilot.session import SessionStore
from codepilot.tools.base import ToolResult
from codepilot.tools import ToolRegistry


class FakeLLM:
    def __init__(self, responses: list[str] | None = None) -> None:
        self.calls: list[list[ChatMessage]] = []
        self.responses = responses or ["这是模型回复"]

    def chat(self, messages: list[ChatMessage]) -> str:
        self.calls.append(messages)
        return self.responses.pop(0)


class EchoTool:
    name = "echo"
    description = "Echo input text."

    def run(self, args: dict) -> ToolResult:
        return ToolResult(ok=True, content=f"echo: {args['text']}")


def test_conversation_agent_sends_user_message_to_llm_and_saves_session(tmp_path) -> None:
    llm = FakeLLM()
    store = SessionStore.create(tmp_path / "sessions")
    agent = ConversationAgent(llm=llm, session_store=store)

    response = agent.respond("帮我总结这个项目")

    assert response == "这是模型回复"
    assert llm.calls[0][-1] == ChatMessage(role="user", content="帮我总结这个项目")
    assert agent.history[-2:] == [
        ChatMessage(role="user", content="帮我总结这个项目"),
        ChatMessage(role="assistant", content="这是模型回复"),
    ]
    assert [event["type"] for event in store.read_events()] == [
        "user_message",
        "assistant_message",
    ]


def test_conversation_agent_executes_tool_request_and_returns_final_answer(tmp_path) -> None:
    llm = FakeLLM(
        responses=[
            '{"tool": "echo", "args": {"text": "hello"}}',
            "工具结果是 hello",
        ]
    )
    registry = ToolRegistry()
    registry.register(EchoTool())
    store = SessionStore.create(tmp_path / "sessions")
    agent = ConversationAgent(llm=llm, tool_registry=registry, session_store=store)

    response = agent.respond("调用 echo 工具")

    assert response == "工具结果是 hello"
    assert len(llm.calls) == 2
    assert any(message.content == "工具 echo 返回：\necho: hello" for message in llm.calls[1])
    assert [event["type"] for event in store.read_events()] == [
        "user_message",
        "tool_call",
        "tool_result",
        "assistant_message",
    ]


def test_conversation_agent_stops_when_tool_iterations_exceed_limit(tmp_path) -> None:
    llm = FakeLLM(
        responses=[
            '{"tool": "echo", "args": {"text": "one"}}',
            '{"tool": "echo", "args": {"text": "two"}}',
        ]
    )
    registry = ToolRegistry()
    registry.register(EchoTool())
    agent = ConversationAgent(llm=llm, tool_registry=registry, max_tool_iterations=1)

    response = agent.respond("一直调用工具")

    assert "工具调用超过上限" in response
