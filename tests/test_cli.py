from pathlib import Path

from codepilot.cli import run_cli


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


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
