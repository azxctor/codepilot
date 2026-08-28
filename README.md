# CodePilot

CodePilot is a Python prototype for a local interactive coding agent CLI.

Current milestone:

- `codepilot init` creates a local `.codepilot/config.toml`.
- `codepilot` and `codepilot chat` start an interactive shell.
- `/status`, `/plan`, and `/exit` are available in the shell.

The LLM agent loop, file tools, approvals, and session recovery are planned in later milestones.
