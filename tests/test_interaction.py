from codepilot.interaction import InteractiveSession


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


class FakeAgent:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.status = "当前状态：idle"
        self.plan = "当前计划：暂无任务计划"

    def respond(self, message: str) -> str:
        self.messages.append(message)
        self.status = "当前状态：done；目标：帮我总结这个项目"
        self.plan = "当前计划：\n1. [done] 理解用户目标"
        return f"模型回复：{message}"


def test_interactive_session_exits_on_exit_command(tmp_path) -> None:
    output = FakeOutput()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: "/exit",
        output=output,
    )

    result = session.run()

    assert result.exit_requested is True
    assert "已退出 codepilot" in output.lines[-1]


def test_interactive_session_handles_status_command(tmp_path) -> None:
    inputs = iter(["/status", "/exit"])
    output = FakeOutput()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
    )

    result = session.run()

    assert result.exit_requested is True
    assert any(line == "当前状态：idle" for line in output.lines)


def test_interactive_session_status_reads_agent_task_state(tmp_path) -> None:
    inputs = iter(["帮我总结这个项目", "/status", "/plan", "/exit"])
    output = FakeOutput()
    agent = FakeAgent()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
        agent=agent,
    )

    session.run()

    assert "当前状态：done；目标：帮我总结这个项目" in output.lines
    assert "当前计划：\n1. [done] 理解用户目标" in output.lines


def test_interactive_session_handles_regular_text_without_llm(tmp_path) -> None:
    inputs = iter(["帮我总结这个项目", "/exit"])
    output = FakeOutput()
    agent = FakeAgent()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
        agent=agent,
    )

    session.run()

    assert agent.messages == ["帮我总结这个项目"]
    assert any("模型回复：帮我总结这个项目" in line for line in output.lines)
