from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from codepilot.agent import create_default_agent
from codepilot.commands import SlashCommand, parse_slash_command
from codepilot.config import CodePilotConfig, load_config


class Output(Protocol):
    def write(self, message: str) -> None:
        ...


class PlainOutput:
    def write(self, message: str) -> None:
        print(message)


class Agent(Protocol):
    status: str
    plan: str

    def respond(self, message: str) -> str:
        ...


@dataclass(frozen=True)
class InteractionResult:
    exit_requested: bool
    turns: int


class InteractiveSession:
    def __init__(
        self,
        workspace: Path,
        input_reader: Callable[[], str] | None = None,
        output: Output | None = None,
        config: CodePilotConfig | None = None,
        agent: Agent | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.config = config or load_config(self.workspace)
        self.input_reader = input_reader or self._prompt
        self.output = output or PlainOutput()
        self.agent = agent or create_default_agent(self.config, workspace=self.workspace)
        self._turns = 0

    def run(self) -> InteractionResult:
        self.output.write("CodePilot 交互式会话")
        self.output.write("输入 /status 查看状态，/plan 查看计划，/exit 退出。")

        while True:
            try:
                user_input = self.input_reader()
            except (EOFError, KeyboardInterrupt):
                self.output.write("已退出 codepilot")
                return InteractionResult(exit_requested=True, turns=self._turns)

            text = user_input.strip()
            if not text:
                continue

            self._turns += 1
            command = parse_slash_command(text)
            if command is not None:
                if self._handle_command(command):
                    return InteractionResult(exit_requested=True, turns=self._turns)
                continue

            self.output.write(self.agent.respond(text))

    def _handle_command(self, command: SlashCommand) -> bool:
        if command.name == "exit":
            self.output.write("已退出 codepilot")
            return True

        if command.name == "status":
            self.output.write(self.agent.status)
            return False

        if command.name == "plan":
            self.output.write(self.agent.plan)
            return False

        self.output.write(f"未知命令：/{command.name}")
        return False

    def _prompt(self) -> str:
        try:
            from prompt_toolkit import prompt
        except ImportError:
            return input("codepilot> ")

        return prompt("codepilot> ")
