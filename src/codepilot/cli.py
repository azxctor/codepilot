from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence

from codepilot.agent import create_default_agent
from codepilot.config import initialize_workspace_config, load_config
from codepilot.diagnostics import build_doctor_report
from codepilot.interaction import InteractiveSession, Output, PlainOutput


class Agent(Protocol):
    def respond(self, message: str) -> str:
        ...


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codepilot",
        description="Local interactive coding agent CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Create .codepilot/config.toml in the current workspace.")
    subparsers.add_parser("doctor", help="Show local configuration and masked API key diagnostics.")

    chat_parser = subparsers.add_parser("chat", help="Start an interactive CodePilot session.")
    chat_parser.add_argument("--resume", default=None, help="Reserved for a later milestone.")

    run_parser = subparsers.add_parser("run", help="Send one task through the conversation agent.")
    run_parser.add_argument("task", nargs="*", help="Task text.")

    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    workspace: Path | None = None,
    input_reader: Callable[[], str] | None = None,
    output: Output | None = None,
    agent: Agent | None = None,
    env: Mapping[str, str] | None = None,
) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    workspace_path = (workspace or Path.cwd()).resolve()
    out = output or PlainOutput()
    active_env = env if env is not None else os.environ

    parser = build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "init":
        target = initialize_workspace_config(workspace_path)
        out.write(f"初始化完成：{target}")
        return 0

    if args.command == "doctor":
        config = load_config(workspace_path)
        for line in build_doctor_report(config, active_env):
            out.write(line)
        return 0

    if args.command in {None, "chat"}:
        config = load_config(workspace_path)
        session = InteractiveSession(
            workspace=workspace_path,
            input_reader=input_reader,
            output=out,
            config=config,
            agent=agent,
        )
        session.run()
        return 0

    if args.command == "run":
        task = " ".join(args.task).strip()
        if not task:
            out.write('run 需要任务文本，例如：codepilot run "总结这个项目"')
            return 2

        config = load_config(workspace_path)
        active_agent = agent or create_default_agent(config)
        out.write(active_agent.respond(task))
        return 0

    parser.print_help()
    return 1


def main() -> int:
    return run_cli()
