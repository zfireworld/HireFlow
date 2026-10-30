"""统一判断模型模式和运行时使用的模型名称。"""
from pydantic import ValidationError
from ..config import AI_MODE, MODEL_API_KEY, MODEL_NAME, MODEL_BASE_URL
from ..schemas.ai import AIConfig


def is_demo(config: AIConfig | None = None) -> bool:
    mode = config.mode if config else 'server'
    return mode == 'demo' or mode == 'server' and (AI_MODE == 'demo' or AI_MODE == 'auto' and not MODEL_API_KEY)


def require_model(config: AIConfig | None = None) -> None:
    if (config is None or config.mode == 'server') and AI_MODE == 'qwen' and not MODEL_API_KEY:
        raise RuntimeError('服务器模型配置缺少 API Key，请检查 .env')
    if config is None or config.mode == 'server':
        try:
            AIConfig(mode='custom',model=MODEL_NAME,base_url=MODEL_BASE_URL,api_key=MODEL_API_KEY or None)
        except ValidationError as exc:
            raise RuntimeError('服务器模型配置无效，请检查 .env 中的模型名称、接口地址和密钥') from exc


def model_name(config: AIConfig | None = None) -> str:
    if is_demo(config): return 'demo'
    return config.model if config and config.mode == 'custom' else MODEL_NAME
