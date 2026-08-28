from codepilot.commands import SlashCommand, parse_slash_command


def test_parse_slash_command_recognizes_command_with_args() -> None:
    command = parse_slash_command("/status verbose")

    assert command == SlashCommand(name="status", args=["verbose"])


def test_parse_slash_command_ignores_normal_text() -> None:
    command = parse_slash_command("帮我总结这个项目")

    assert command is None


def test_parse_slash_command_strips_extra_spaces() -> None:
    command = parse_slash_command("  /exit   ")

    assert command == SlashCommand(name="exit", args=[])
