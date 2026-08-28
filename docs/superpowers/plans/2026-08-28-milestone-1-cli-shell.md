# Milestone 1 CLI Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable CodePilot CLI shell with initialization and basic interactive slash commands.

**Architecture:** Keep the first milestone narrow. `cli.py` owns command parsing, `config.py` owns workspace config files, `commands.py` parses slash commands, and `interaction.py` owns the prompt loop. No LLM or tool execution is included in this milestone.

**Tech Stack:** Python 3.10 compatible standard library, optional `prompt_toolkit`, pytest, setuptools package layout.

---

## File Structure

- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/codepilot/__init__.py`
- Create: `src/codepilot/__main__.py`
- Create: `src/codepilot/cli.py`
- Create: `src/codepilot/config.py`
- Create: `src/codepilot/commands.py`
- Create: `src/codepilot/interaction.py`
- Create: `tests/test_config.py`
- Create: `tests/test_commands.py`
- Create: `tests/test_interaction.py`
- Create: `tests/test_cli.py`

### Task 1: Config Initialization

**Files:**

- Create: `src/codepilot/config.py`
- Test: `tests/test_config.py`

- [x] **Step 1: Write failing config tests**

```python
def test_initialize_workspace_config_creates_config_and_sessions(tmp_path):
    config_path = initialize_workspace_config(tmp_path)
    assert config_path == tmp_path / ".codepilot" / "config.toml"
    assert config_path.exists()
    assert (tmp_path / ".codepilot" / "sessions").is_dir()
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_config.py -q
```

Expected: failure because `codepilot.config` does not exist.

- [x] **Step 3: Implement config creation and loading**

Implement `CodePilotConfig`, `DEFAULT_CONFIG`, `initialize_workspace_config()`, and `load_config()` in `src/codepilot/config.py`.

- [x] **Step 4: Verify config tests pass**

Run:

```bash
python3 -m pytest tests/test_config.py -q
```

Expected: config tests pass.

### Task 2: Slash Command Parser

**Files:**

- Create: `src/codepilot/commands.py`
- Test: `tests/test_commands.py`

- [x] **Step 1: Write failing parser tests**

```python
def test_parse_slash_command_recognizes_command_with_args():
    assert parse_slash_command("/status verbose") == SlashCommand(
        name="status",
        args=["verbose"],
    )
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_commands.py -q
```

Expected: failure because `codepilot.commands` does not exist.

- [x] **Step 3: Implement `SlashCommand` and `parse_slash_command()`**

Implement a small dataclass and parser that returns `None` for normal text.

- [x] **Step 4: Verify parser tests pass**

Run:

```bash
python3 -m pytest tests/test_commands.py -q
```

Expected: command parser tests pass.

### Task 3: Interactive Shell

**Files:**

- Create: `src/codepilot/interaction.py`
- Test: `tests/test_interaction.py`

- [x] **Step 1: Write failing interaction tests**

```python
def test_interactive_session_exits_on_exit_command(tmp_path):
    output = FakeOutput()
    session = InteractiveSession(
        workspace=tmp_path,
        input_reader=lambda: "/exit",
        output=output,
    )
    result = session.run()
    assert result.exit_requested is True
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_interaction.py -q
```

Expected: failure because `InteractiveSession` does not exist.

- [x] **Step 3: Implement the prompt loop**

Implement `InteractiveSession.run()`, `PlainOutput`, and `InteractionResult`. Support `/status`, `/plan`, unknown commands, empty input, `EOFError`, and `KeyboardInterrupt`.

- [x] **Step 4: Verify interaction tests pass**

Run:

```bash
python3 -m pytest tests/test_interaction.py -q
```

Expected: interaction tests pass.

### Task 4: CLI Entrypoint

**Files:**

- Create: `src/codepilot/cli.py`
- Create: `src/codepilot/__main__.py`
- Create: `src/codepilot/__init__.py`
- Create: `pyproject.toml`
- Test: `tests/test_cli.py`

- [x] **Step 1: Write failing CLI tests**

```python
def test_run_cli_init_creates_workspace_config(tmp_path):
    output = FakeOutput()
    exit_code = run_cli(["init"], workspace=tmp_path, output=output)
    assert exit_code == 0
    assert (tmp_path / ".codepilot" / "config.toml").exists()
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python3 -m pytest tests/test_cli.py -q
```

Expected: failure because `codepilot.cli` does not exist.

- [x] **Step 3: Implement CLI dispatch**

Implement `build_parser()`, `run_cli()`, and `main()`. Route no command and `chat` to `InteractiveSession`.

- [x] **Step 4: Verify CLI behavior**

Run:

```bash
python3 -m pytest tests/test_cli.py -q
env PYTHONPATH=src python3 -m codepilot --help
```

Expected: CLI tests pass and help output lists `init`, `chat`, and `run`.

### Task 5: Commit Milestone 1

**Files:**

- Commit all files created in this plan.

- [x] **Step 1: Run full verification**

```bash
python3 -m pytest -q
env PYTHONPATH=src python3 -m codepilot --help
```

Expected: all tests pass and CLI help renders.

- [x] **Step 2: Commit**

```bash
git add .gitignore README.md pyproject.toml src tests simple-python-cli-agent-design.md
git commit -m "feat: add initial interactive cli shell"
```

Expected: commit `29cc437` or equivalent milestone commit is created.
