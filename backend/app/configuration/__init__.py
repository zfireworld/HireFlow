"""集中管理配置文件读取和测试时显式指定的配置路径。"""
from pathlib import Path

_config_path: Path | None = None


def set_config_path(path: Path) -> None:
    """仅在导入应用配置前显式指定配置文件，供隔离测试和工具使用。"""
    global _config_path
    _config_path = Path(path)


def config_path(default: Path) -> Path:
    return _config_path if _config_path is not None else default
