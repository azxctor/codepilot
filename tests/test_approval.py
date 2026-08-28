from codepilot.approval import ApprovalPolicy, ApprovalRequest


class FakeOutput:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        self.lines.append(message)


def test_approval_policy_ask_allows_when_user_inputs_y() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is True
    assert "需要确认执行动作" in "\n".join(output.lines)
    assert "write_file" in "\n".join(output.lines)


def test_approval_policy_ask_rejects_when_user_inputs_anything_else() -> None:
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="ask",
        input_reader=lambda: "n",
        output=FakeOutput(),
    )

    decision = policy.decide(
        ApprovalRequest(
            action="patch_file",
            target="README.md",
            risk="write",
            preview="替换文本",
        )
    )

    assert decision.approved is False
    assert decision.reason == "用户拒绝执行"


def test_approval_policy_never_rejects_without_prompt() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="never",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is False
    assert decision.reason == "配置禁止 write 动作"
    assert output.lines == []


def test_approval_policy_never_rejects_shell_without_prompt() -> None:
    output = FakeOutput()
    policy = ApprovalPolicy(
        allow_write="ask",
        allow_shell="never",
        input_reader=lambda: "y",
        output=output,
    )

    decision = policy.decide(
        ApprovalRequest(
            action="run_shell",
            target="python3 -m pytest -q",
            risk="shell",
            preview="运行测试",
        )
    )

    assert decision.approved is False
    assert decision.reason == "配置禁止 shell 动作"
    assert output.lines == []


def test_approval_policy_invalid_mode_rejects_conservatively() -> None:
    policy = ApprovalPolicy(
        allow_write="always",
        allow_shell="ask",
        input_reader=lambda: "y",
        output=FakeOutput(),
    )

    decision = policy.decide(
        ApprovalRequest(
            action="write_file",
            target="README.md",
            risk="write",
            preview="写入 README.md",
        )
    )

    assert decision.approved is False
    assert "配置值无效" in decision.reason
