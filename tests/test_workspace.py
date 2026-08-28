from pathlib import Path

import pytest

from codepilot.workspace import Workspace, WorkspaceAccessError


def test_workspace_resolve_path_rejects_parent_escape(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)

    with pytest.raises(WorkspaceAccessError):
        workspace.resolve_path("../outside.txt")


def test_workspace_list_files_skips_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref: main\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "x.pyc").write_bytes(b"compiled")
    workspace = Workspace(tmp_path)

    files = workspace.list_files()

    assert files == ["README.md", "src/app.py"]


def test_workspace_read_file_returns_numbered_line_range(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    content = workspace.read_file("sample.py", start_line=2, end_line=3)

    assert content == "2: b = 2\n3: c = 3"


def test_workspace_search_text_returns_numbered_matches(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("main entry\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    matches = workspace.search_text("main", glob="*.py")

    assert matches == ["a.py:1: def main():"]
