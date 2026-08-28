from pathlib import Path

from codepilot.cli import run_cli


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


class FakeAgent:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def respond(self, message: str) -> str:
        self.messages.append(message)
        return f"reply: {message}"


def test_run_cli_init_creates_workspace_config(tmp_path: Path) -> None:
    output = FakeOutput()

    exit_code = run_cli(["init"], workspace=tmp_path, output=output)

    assert exit_code == 0
    assert (tmp_path / ".codepilot" / "config.toml").exists()
    assert any("初始化完成" in line for line in output.lines)


def test_run_cli_without_command_starts_interactive_session(tmp_path: Path) -> None:
    output = FakeOutput()

    exit_code = run_cli([], workspace=tmp_path, input_reader=lambda: "/exit", output=output)

    assert exit_code == 0
    assert any("CodePilot 交互式会话" in line for line in output.lines)


def test_run_cli_chat_starts_interactive_session(tmp_path: Path) -> None:
    output = FakeOutput()

    exit_code = run_cli(["chat"], workspace=tmp_path, input_reader=lambda: "/exit", output=output)

    assert exit_code == 0
    assert any("CodePilot 交互式会话" in line for line in output.lines)


def test_run_cli_run_sends_task_to_agent(tmp_path: Path) -> None:
    output = FakeOutput()
    agent = FakeAgent()

    exit_code = run_cli(["run", "总结", "这个项目"], workspace=tmp_path, output=output, agent=agent)

    assert exit_code == 0
    assert agent.messages == ["总结 这个项目"]
    assert output.lines[-1] == "reply: 总结 这个项目"


def test_run_cli_run_requires_task_text(tmp_path: Path) -> None:
    output = FakeOutput()

    exit_code = run_cli(["run"], workspace=tmp_path, output=output)

    assert exit_code == 2
    assert output.lines[-1] == "run 需要任务文本，例如：codepilot run \"总结这个项目\""


def test_run_cli_doctor_reports_masked_api_key_source(tmp_path: Path) -> None:
    output = FakeOutput()

    exit_code = run_cli(
        ["doctor"],
        workspace=tmp_path,
        output=output,
        env={"MOONSHOT_API_KEY": "kimi-test-key-abcdef1234567890"},
    )

    rendered = "\n".join(output.lines)
    assert exit_code == 0
    assert "api_base_url: https://api.kimi.com/coding/v1" in rendered
    assert "default_model: kimi-k3" in rendered
    assert "active_api_key_env: MOONSHOT_API_KEY" in rendered
    assert "kimi...7890" in rendered
    assert "abcdef123456" not in rendered
