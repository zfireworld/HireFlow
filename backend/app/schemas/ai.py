"""校验请求级模型配置，避免在对象表示中暴露密钥。"""
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, model_validator


class AIConfig(BaseModel):
    """选择服务器配置、规则演示或请求级自定义模型。"""
    mode: Literal['server', 'demo', 'custom'] = 'server'
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=512, repr=False)

    @model_validator(mode='after')
    def validate_custom(self):
        if self.mode == 'custom':
            if not self.model or not self.model.strip():
                raise ValueError('自定义模型名称不能为空')
            parsed = urlparse(self.base_url or '')
            if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError('自定义接口地址必须是有效的 HTTP(S) URL，且不能包含账号密码')
            if parsed.scheme == 'http' and self.api_key and parsed.hostname not in ('localhost', '127.0.0.1'):
                raise ValueError('携带 API Key 的远程接口必须使用 HTTPS')
        return self
