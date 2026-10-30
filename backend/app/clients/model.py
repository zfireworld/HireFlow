"""封装 OpenAI 兼容模型接口和 JSON 输出兼容处理。"""
from ..config import MODEL_API_KEY, MODEL_BASE_URL, MODEL_NAME
from ..schemas.ai import AIConfig
from openai import APIStatusError


def build_client(timeout: int, config: AIConfig | None = None, *, max_tokens: int | None = None, max_retries: int = 1):
    """为业务提取和连通性测试共用请求级或服务器配置。"""
    from langchain_openai import ChatOpenAI
    custom = config is not None and config.mode == 'custom'
    options = {'model':config.model if custom else MODEL_NAME,
               'api_key':(config.api_key or 'not-needed') if custom else (MODEL_API_KEY or 'not-needed'),
               'base_url':config.base_url if custom else MODEL_BASE_URL,
               'temperature':0, 'timeout':timeout, 'max_retries':max_retries}
    if max_tokens is not None: options['max_tokens'] = max_tokens
    return ChatOpenAI(**options)


def text_content(response) -> str:
    content = response.content
    if isinstance(content, list):
        blocks = [block['text'] for block in content if isinstance(block, dict)
                  and block.get('type') in ('text', 'output_text') and isinstance(block.get('text'), str)]
        if blocks: return ''.join(blocks)
    if not isinstance(content, str): raise RuntimeError('模型输出非文本')
    return content


def complete_json(system_prompt: str, user_prompt: str, timeout: int, config: AIConfig | None = None) -> str:
    """按请求级配置或服务器配置调用模型，并返回文本响应。"""
    from langchain_core.messages import SystemMessage, HumanMessage
    llm = build_client(timeout, config)
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
    # 仅当服务明确不支持 JSON 响应格式时，回退到普通文本请求。
    try:
        response = llm.invoke(messages, response_format={'type':'json_object'})
    except APIStatusError as exc:
        message = str(exc).lower()
        unsupported = any(word in message for word in ('unsupported', 'not supported', 'not support',
                           'unknown', 'unrecognized', 'unexpected', 'invalid', 'extra_forbidden',
                           'extra inputs', 'not implemented', '不支持'))
        if exc.status_code not in (400, 422) or 'response_format' not in message or not unsupported:
            raise
        response = llm.invoke(messages)
    return text_content(response)


def check_connection(config: AIConfig | None = None) -> None:
    """发送短文本请求，确认所选模型可实际生成回复。"""
    from langchain_core.messages import HumanMessage
    response=build_client(45, config, max_tokens=256, max_retries=0).invoke([HumanMessage(content='Reply with OK.')])
    if not text_content(response).strip():
        raise RuntimeError('模型返回空回复')
