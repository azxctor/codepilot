from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class ApprovalOutput(Protocol):
    def write(self, message: str) -> None:
        ...


class StdoutApprovalOutput:
    def write(self, message: str) -> None:
        print(message)


@dataclass(frozen=True)
class ApprovalRequest:
    action: str
    target: str
    risk: str
    preview: str


@dataclass(frozen=True)
class ApprovalDecision:
    approved: bool
    reason: str = ""


@dataclass
class ApprovalPolicy:
    allow_write: str = "ask"
    allow_shell: str = "ask"
    input_reader: Callable[[], str] | None = None
    output: ApprovalOutput | None = None

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        mode = self._mode_for(request.risk)
        if mode not in {"ask", "never"}:
            return ApprovalDecision(False, f"配置值无效：{request.risk}={mode}")
        if mode == "never":
            return ApprovalDecision(False, f"配置禁止 {request.risk} 动作")

        out = self.output or StdoutApprovalOutput()
        out.write("需要确认执行动作：")
        out.write(f"动作：{request.action}")
        out.write(f"目标：{request.target}")
        out.write(f"风险：{request.risk}")
        out.write("预览：")
        out.write(request.preview)
        out.write("输入 y 执行，其他输入拒绝。")

        reader = self.input_reader or (lambda: input("确认执行？ "))
        answer = reader().strip().lower()
        if answer == "y":
            return ApprovalDecision(True, "用户确认执行")
        return ApprovalDecision(False, "用户拒绝执行")

    def _mode_for(self, risk: str) -> str:
        if risk == "write":
            return self.allow_write
        if risk == "shell":
            return self.allow_shell
        return "never"


def format_rejection(decision: ApprovalDecision, action: str) -> str:
    return f"用户拒绝执行：{action}（{decision.reason}）"
