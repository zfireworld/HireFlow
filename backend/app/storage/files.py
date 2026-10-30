"""限制文件操作范围，集中处理存储、查找和失败清理。"""
from pathlib import Path


class FileStorage:
    def __init__(self, root: Path):
        self.root=Path(root).resolve()

    def resolve(self, path: Path | str) -> Path:
        candidate=Path(path).resolve()
        if not candidate.is_relative_to(self.root) or candidate==self.root:
            raise ValueError('文件路径不在存储目录内')
        return candidate

    def write(self, filename: str, contents: bytes) -> Path:
        if Path(filename).name != filename:
            raise ValueError('文件名无效')
        path=self.resolve(self.root / filename)
        path.write_bytes(contents)
        return path

    def remove(self, path: Path | str) -> None:
        self.resolve(path).unlink(missing_ok=True)

    def existing(self, path: Path | str) -> Path | None:
        try:
            candidate=self.resolve(path)
        except (ValueError, OSError):
            return None
        return candidate if candidate.is_file() else None
