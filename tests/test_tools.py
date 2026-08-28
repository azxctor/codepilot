from pathlib import Path

from codepilot.tools import ToolRegistry, default_readonly_registry
from codepilot.workspace import Workspace


def test_default_readonly_registry_executes_list_files(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    registry = default_readonly_registry(Workspace(tmp_path))

    result = registry.execute("list_files", {"path": "."})

    assert result.ok is True
    assert result.content == "README.md"


def test_default_readonly_registry_executes_read_file(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\nbody\n", encoding="utf-8")
    registry = default_readonly_registry(Workspace(tmp_path))

    result = registry.execute("read_file", {"path": "README.md", "start_line": 1, "end_line": 1})

    assert result.ok is True
    assert result.content == "1: # Demo"


def test_default_readonly_registry_executes_search_text(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    registry = default_readonly_registry(Workspace(tmp_path))

    result = registry.execute("search_text", {"query": "Demo"})

    assert result.ok is True
    assert result.content == "README.md:1: # Demo"


def test_tool_registry_reports_unknown_tool(tmp_path: Path) -> None:
    registry = ToolRegistry()

    result = registry.execute("missing_tool", {})

    assert result.ok is False
    assert result.error == "未知工具：missing_tool"
