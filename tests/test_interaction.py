from codepilot.interaction import InteractiveSession


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


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
    assert any("当前状态：idle" in line for line in output.lines)


def test_interactive_session_handles_regular_text_without_llm(tmp_path) -> None:
    inputs = iter(["帮我总结这个项目", "/exit"])
    output = FakeOutput()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: next(inputs),
        output=output,
    )

    session.run()

    assert any("LLM Agent 尚未接入" in line for line in output.lines)
