from pathlib import Path

from codepilot.approval import ApprovalDecision, ApprovalRequest
from codepilot.tools.patch_file import PatchFileTool
from codepilot.tools.write_file import WriteFileTool
from codepilot.workspace import Workspace


class FakeApprovalPolicy:
    def __init__(self, approved: bool = True) -> None:
        self.approved = approved
        self.requests: list[ApprovalRequest] = []

    def decide(self, request: ApprovalRequest) -> ApprovalDecision:
        self.requests.append(request)
        if self.approved:
            return ApprovalDecision(True, "允许")
        return ApprovalDecision(False, "用户拒绝执行")


def test_write_file_create_writes_after_approval(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy()
    tool = WriteFileTool(Workspace(tmp_path), approval)

    result = tool.run({"path": "notes.md", "content": "hello\n", "mode": "create"})

    assert result.ok is True
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "hello\n"
    assert approval.requests[0].action == "write_file"
    assert approval.requests[0].risk == "write"


def test_write_file_create_rejects_existing_file(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("old\n", encoding="utf-8")
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "notes.md", "content": "new\n", "mode": "create"})

    assert result.ok is False
    assert "文件已存在" in result.error
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "old\n"


def test_write_file_overwrite_updates_existing_file_after_approval(tmp_path: Path) -> None:
    target = tmp_path / "notes.md"
    target.write_text("old\n", encoding="utf-8")
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "notes.md", "content": "new\n", "mode": "overwrite"})

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "new\n"


def test_write_file_overwrite_rejects_missing_file(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "missing.md", "content": "new\n", "mode": "overwrite"})

    assert result.ok is False
    assert "文件不存在" in result.error


def test_write_file_rejects_missing_parent_directory(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "missing/notes.md", "content": "new\n", "mode": "create"})

    assert result.ok is False
    assert "父目录不存在" in result.error


def test_write_file_rejects_when_approval_denies(tmp_path: Path) -> None:
    approval = FakeApprovalPolicy(approved=False)
    tool = WriteFileTool(Workspace(tmp_path), approval)

    result = tool.run({"path": "notes.md", "content": "hello\n", "mode": "create"})

    assert result.ok is False
    assert "用户拒绝执行" in result.error
    assert not (tmp_path / "notes.md").exists()


def test_patch_file_replaces_unique_text_after_approval(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "beta", "new": "gamma"})

    assert result.ok is True
    assert target.read_text(encoding="utf-8") == "alpha\ngamma\n"


def test_patch_file_rejects_multiple_matches(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("same\nsame\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "same", "new": "next"})

    assert result.ok is False
    assert "匹配次数必须为 1" in result.error
    assert target.read_text(encoding="utf-8") == "same\nsame\n"


def test_patch_file_rejects_missing_old_text(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("alpha\n", encoding="utf-8")
    tool = PatchFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "README.md", "old": "missing", "new": "next"})

    assert result.ok is False
    assert "匹配次数必须为 1，实际为 0" in result.error
    assert target.read_text(encoding="utf-8") == "alpha\n"


def test_write_file_rejects_parent_escape(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path), FakeApprovalPolicy())

    result = tool.run({"path": "../outside.txt", "content": "bad", "mode": "create"})

    assert result.ok is False
    assert "路径越界" in result.error
