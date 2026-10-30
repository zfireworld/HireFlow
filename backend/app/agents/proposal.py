"""从聊天内容提取结构化招聘操作，支持规则演示和模型调用。"""
from datetime import datetime
from ..clients.model import complete_json
from ..prompts.proposal import SYSTEM_PROMPT, build_user_prompt
from ..schemas import AIConfig, Proposal
from ..services.demo_parser import demo_parse
from ..services.model_settings import is_demo, require_model
from ..services.model_output import parse_structured_output

def extract_proposal(content: str, resume_text: str = '', application_id: str | None = None,
                     config: AIConfig | None = None) -> Proposal:
    """提取提案；用户明确选择的申请 ID 优先于模型推测。"""
    if is_demo(config):
        return demo_parse(content, resume_text, application_id)
    require_model(config)
    prompt=build_user_prompt(content, resume_text, application_id, datetime.now().strftime('%Y-%m-%d'))
    raw=complete_json(SYSTEM_PROMPT, prompt, timeout=35, config=config)
    p=parse_structured_output(raw,Proposal,'intent',('result','data','proposal'))
    if application_id: p.application_id=application_id
    return p
