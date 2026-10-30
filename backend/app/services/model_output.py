"""统一整理模型输出中的推理块、代码围栏和常见结果包装。"""
import json
import re


def parse_structured_output(raw: str, schema, required_key: str, wrappers: tuple[str, ...]):
    raw=raw.strip()
    raw=re.sub(r'^\s*<think>.*?</think>\s*','',raw,count=1,flags=re.DOTALL)
    fenced=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',raw,flags=re.DOTALL|re.IGNORECASE)
    if fenced: raw=fenced.group(1).strip()
    try:
        parsed=json.loads(raw)
    except json.JSONDecodeError:
        return schema.model_validate_json(raw)
    if isinstance(parsed,dict) and required_key not in parsed:
        wrapped=[parsed[key] for key in wrappers if isinstance(parsed.get(key),dict)]
        if len(wrapped)==1:
            return schema.model_validate({**parsed,**wrapped[0]})
    return schema.model_validate_json(raw)
