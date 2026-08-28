# Milestone 1 CLI Shell Design

## Goal

Build the first usable CodePilot command-line shell. The milestone creates the Python package skeleton, a `codepilot` executable entrypoint, local workspace initialization, and a minimal interactive prompt loop.

## Scope

This milestone covers:

- `codepilot --help`
- `codepilot init`
- `codepilot`
- `codepilot chat`
- `/status`, `/plan`, and `/exit`
- `.codepilot/config.toml` creation
- `.codepilot/sessions/` directory creation

This milestone does not call an LLM, read project files through tools, write files, execute shell commands, or resume old sessions.

## Architecture

The CLI starts in `src/codepilot/cli.py` and delegates interactive behavior to `src/codepilot/interaction.py`. Configuration creation and loading live in `src/codepilot/config.py`. Slash commands are parsed by `src/codepilot/commands.py`.

The implementation intentionally uses Python standard library `argparse` for the first shell because the local runtime did not have Typer and Rich installed. The package still declares the planned dependencies in `pyproject.toml` so later milestones can adopt them without changing the command surface.

## Components

- `pyproject.toml`: package metadata, console script, pytest config.
- `README.md`: local usage notes.
- `src/codepilot/__main__.py`: enables `python3 -m codepilot`.
- `src/codepilot/cli.py`: command parser and top-level dispatch.
- `src/codepilot/config.py`: workspace config creation and loading.
- `src/codepilot/commands.py`: slash command parsing.
- `src/codepilot/interaction.py`: interactive prompt loop and basic command handling.

## Behavior

`codepilot init` creates:

```text
.codepilot/
  config.toml
  sessions/
```

`codepilot` and `codepilot chat` start an interactive loop. Empty input is ignored. `/status` shows the idle state, `/plan` shows that no task plan exists, and `/exit` exits cleanly. Normal text input reports that the LLM Agent is not yet connected in this milestone.

## Configuration

The generated config stores only non-secret defaults. API keys are never written into `.codepilot/config.toml`.

## Tests

Covered by:

- `tests/test_config.py`
- `tests/test_commands.py`
- `tests/test_interaction.py`
- `tests/test_cli.py`

Required verification:

```bash
python3 -m pytest -q
env PYTHONPATH=src python3 -m codepilot --help
env PYTHONPATH=src python3 -m codepilot chat
```

## Acceptance Criteria

- `codepilot --help` prints available commands.
- `codepilot init` creates `.codepilot/config.toml` and `.codepilot/sessions/`.
- `codepilot` enters the same interactive shell as `codepilot chat`.
- `/exit` exits without an exception.
- `/status` and `/plan` return stable shell output.

## Implementation Evidence

Implemented in commit:

```text
29cc437 feat: add initial interactive cli shell
```
