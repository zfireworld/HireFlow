"""读取 dotenv 文件，不读取或展开进程环境变量。"""
from pathlib import Path
from dotenv import dotenv_values


class ConfigFileReader:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> dict[str, str]:
        if not self.path.is_file():
            return {}
        values = dotenv_values(self.path, encoding='utf-8', interpolate=False)
        return {key: value for key, value in values.items() if value is not None}
