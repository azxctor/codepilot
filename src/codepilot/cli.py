from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence

from codepilot.config import initialize_workspace_config, load_config
from codepilot.interaction import InteractiveSession, Output, PlainOutput


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codepilot",
        description="Local interactive coding agent CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Create .codepilot/config.toml in the current workspace.")

    chat_parser = subparsers.add_parser("chat", help="Start an interactive CodePilot session.")
    chat_parser.add_argument("--resume", default=None, help="Reserved for a later milestone.")

    run_parser = subparsers.add_parser("run", help="Reserved shortcut command for a later milestone.")
    run_parser.add_argument("task", nargs="*", help="Task text.")

    return parser


def run_cli(
    argv: Sequence[str] | None = None,
    workspace: Path | None = None,
    input_reader: Callable[[], str] | None = None,
    output: Output | None = None,
) -> int:
    args_list = list(argv) if argv is not None else sys.argv[1:]
    workspace_path = (workspace or Path.cwd()).resolve()
    out = output or PlainOutput()

    parser = build_parser()
    try:
        args = parser.parse_args(args_list)
    except SystemExit as exc:
        return int(exc.code)

    if args.command == "init":
        target = initialize_workspace_config(workspace_path)
        out.write(f"初始化完成：{target}")
        return 0

    if args.command in {None, "chat"}:
        config = load_config(workspace_path)
        session = InteractiveSession(
            workspace=workspace_path,
            input_reader=input_reader,
            output=out,
            config=config,
        )
        session.run()
        return 0

    if args.command == "run":
        out.write("run 快捷命令将在后续 Milestone 接入 Agent Loop。请先使用 codepilot chat。")
        return 0

    parser.print_help()
    return 1


def main() -> int:
    return run_cli()
