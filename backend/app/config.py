"""从项目配置文件加载存储、模型和外部同步设置。"""
from pathlib import Path
from .configuration import config_path
from .configuration.files import ConfigFileReader

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_FILE = BACKEND_DIR.parent / '.env'
CONFIG_FILE = config_path(PROJECT_FILE)
values = ConfigFileReader(CONFIG_FILE).read()


def setting(name: str, default: str = '', legacy: str | None = None) -> str:
    value = values.get(name, values.get(legacy, default) if legacy else default)
    return value.strip()


data_dir = setting('DATA_DIR', './data')
if not data_dir:
    raise ValueError('配置文件中的 DATA_DIR 不能为空')
data_path = Path(data_dir)
DATA_DIR = (data_path if data_path.is_absolute() else BACKEND_DIR / data_path).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)
DB_FILE = DATA_DIR / 'hireflow.sqlite3'
CHECKPOINT_FILE = DATA_DIR / 'langgraph.sqlite3'
MODEL_API_KEY = setting('MODEL_API_KEY', legacy='QWEN_API_KEY')
MODEL_NAME = setting('MODEL_NAME', 'qwen-plus', legacy='QWEN_MODEL')
MODEL_BASE_URL = setting('MODEL_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1', legacy='QWEN_BASE_URL')
AI_MODE = setting('AI_MODE', 'auto').lower()
if AI_MODE not in ('auto', 'demo', 'model', 'qwen'):
    raise ValueError('配置文件中的 AI_MODE 仅支持 auto、demo、model 或兼容值 qwen')
HIFLOW_WEBHOOK_URL = setting('HIFLOW_WEBHOOK_URL')
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
