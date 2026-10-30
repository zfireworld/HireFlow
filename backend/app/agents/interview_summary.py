"""从面试全文生成参考总结，并核对评分所引用的原文。"""
import re
from ..clients.model import complete_json
from ..prompts.interview import SYSTEM_PROMPT, build_user_prompt
from ..schemas import InterviewSummary
from ..schemas.ai import AIConfig
from ..services.demo_summary import summarize_demo
from ..services.model_settings import is_demo, require_model
from ..services.model_output import parse_structured_output

def summarize_interview(text: str, candidate: str, position: str, round_no: int,
                        config: AIConfig | None = None) -> InterviewSummary:
    """使用所选模型或演示规则生成总结，不直接改变招聘阶段。"""
    if is_demo(config):
        return summarize_demo(text)
    require_model(config)
    prompt=build_user_prompt(text, candidate, position, round_no)
    raw = complete_json(SYSTEM_PROMPT, prompt, timeout=90, config=config)
    result = parse_structured_output(raw,InterviewSummary,'summary',('result','data','interview_summary'))
    # 忽略空白差异后核对评分依据；找不到原文时撤销分数。
    source = re.sub(r'\s+', '', text)
    for item in result.scores:
        if item.score is not None and re.sub(r'\s+', '', item.evidence) not in source:
            item.score = None
            item.evidence = ''
            item.reasoning = '未在逐字稿中找到所给依据，请面试官核实后评分。'
    return result
