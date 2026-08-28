from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_IGNORES = {
    ".git",
    ".codepilot",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
}


class WorkspaceAccessError(ValueError):
    pass


@dataclass
class Workspace:
    root: Path
    ignored_names: set[str] = field(default_factory=lambda: set(DEFAULT_IGNORES))
    max_file_chars: int = 20000

    def __post_init__(self) -> None:
        self.root = self.root.resolve()

    def resolve_path(self, path: str | Path = ".") -> Path:
        candidate = (self.root / path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceAccessError(f"路径越界：{path}") from exc
        return candidate

    def list_files(
        self,
        path: str | Path = ".",
        max_depth: int = 4,
        max_results: int = 300,
    ) -> list[str]:
        base = self.resolve_path(path)
        if not base.exists():
            return []
        if base.is_file():
            return [self._relative(base)]

        results: list[str] = []
        self._walk_files(base, base_depth=self._depth(base), max_depth=max_depth, results=results, max_results=max_results)
        return sorted(results)

    def read_file(
        self,
        path: str | Path,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        target = self.resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"文件不存在：{path}")
        if not target.is_file():
            raise IsADirectoryError(f"不是文件：{path}")

        text = target.read_text(encoding="utf-8")
        if len(text) > self.max_file_chars:
            text = text[: self.max_file_chars]

        lines = text.splitlines()
        start = max((start_line or 1), 1)
        end = end_line or len(lines)
        selected = lines[start - 1 : end]
        return "\n".join(f"{line_number}: {line}" for line_number, line in enumerate(selected, start=start))

    def search_text(
        self,
        query: str,
        glob: str = "*",
        max_results: int = 100,
    ) -> list[str]:
        results: list[str] = []
        for file_path in self._iter_search_files(glob):
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if query in line:
                    results.append(f"{self._relative(file_path)}:{line_number}: {line}")
                    if len(results) >= max_results:
                        return results
        return results

    def _walk_files(
        self,
        directory: Path,
        base_depth: int,
        max_depth: int,
        results: list[str],
        max_results: int,
    ) -> None:
        if len(results) >= max_results:
            return
        for child in sorted(directory.iterdir(), key=lambda item: item.name):
            if child.name in self.ignored_names:
                continue
            if child.is_dir():
                if self._depth(child) - base_depth < max_depth:
                    self._walk_files(child, base_depth, max_depth, results, max_results)
                continue
            if child.is_file():
                results.append(self._relative(child))
                if len(results) >= max_results:
                    return

    def _iter_search_files(self, glob: str) -> list[Path]:
        files: list[Path] = []
        for candidate in self.root.rglob(glob):
            if not candidate.is_file():
                continue
            if any(part in self.ignored_names for part in candidate.relative_to(self.root).parts):
                continue
            files.append(candidate)
        return sorted(files, key=lambda item: self._relative(item))

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    @staticmethod
    def _depth(path: Path) -> int:
        return len(path.parts)
