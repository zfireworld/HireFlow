"""使用当前请求的配置测试模型是否能够生成回复。"""
import logging
from time import perf_counter
from fastapi import APIRouter, HTTPException
from openai import APIConnectionError, APITimeoutError, AuthenticationError, NotFoundError, RateLimitError
from ..clients import model
from ..schemas.ai import AIConfig
from ..services.model_settings import is_demo, model_name, require_model

router=APIRouter(prefix='/model')
logger=logging.getLogger(__name__)


@router.post('/test')
def test_model_connection(config: AIConfig):
    if is_demo(config):
        raise HTTPException(422,'当前为规则演示模式，请选择服务器模型或自定义模型')
    try:
        require_model(config)
        started=perf_counter()
        model.check_connection(config)
    except APITimeoutError as exc:
        raise HTTPException(504,'模型请求超时，请检查服务状态或稍后重试') from exc
    except APIConnectionError as exc:
        raise HTTPException(502,'无法连接模型服务，请检查接口地址和网络') from exc
    except AuthenticationError as exc:
        raise HTTPException(502,'模型服务认证失败，请检查 API Key') from exc
    except NotFoundError as exc:
        raise HTTPException(502,'模型或接口不存在，请检查模型名称和接口地址') from exc
    except RateLimitError as exc:
        raise HTTPException(503,'模型服务暂时限流，请稍后重试') from exc
    except RuntimeError as exc:
        logger.warning('模型连通性测试失败：%s',type(exc).__name__)
        raise HTTPException(502,'模型配置不完整或未返回有效文本，请检查配置') from exc
    except Exception as exc:
        logger.warning('模型连通性测试失败：%s',type(exc).__name__)
        raise HTTPException(502,'模型服务请求失败，请检查接口、模型名称及服务日志') from exc
    return {'ok':True,'model':model_name(config),'elapsed_ms':round((perf_counter()-started)*1000)}
