"""生成简历参考评价，并兼容常见模型 JSON 输出格式。"""
from ..clients.model import complete_json
from ..prompts.resume import SYSTEM_PROMPT, build_user_prompt
from ..schemas.ai import AIConfig
from ..schemas.assessment import ResumeEvaluation
from ..services.demo_parser import demo_parse
from ..services.model_settings import is_demo, require_model
from ..services.model_output import parse_structured_output


def evaluate_resume(text: str, config: AIConfig | None = None, context: str = '') -> ResumeEvaluation:
    """返回结构化评价；规则演示结果明确标记为非 AI。"""
    if is_demo(config):
        extracted = demo_parse(context, text)
        return ResumeEvaluation(candidate_name=extracted.candidate_name, position=extracted.position,
                                education=extracted.education, skills=extracted.skills,
                                work_years=extracted.work_years,
                                summary='规则演示（非 AI）：已提取明确标注的基本信息，请人工核对简历原文。',
                                suggestions=['结合岗位要求核实候选人相关经历'])
    require_model(config)
    raw = complete_json(SYSTEM_PROMPT, build_user_prompt(text, context), timeout=90, config=config)
    return parse_structured_output(raw,ResumeEvaluation,'summary',('result','data','resume_evaluation'))
