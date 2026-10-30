"""定义招聘提案、聊天消息和人工审核的接口契约。"""
from typing import Literal
from pydantic import BaseModel, Field, field_validator
from .ai import AIConfig

Intent = Literal['RESUME_RECEIVED','HR_EVALUATION','INTERVIEW_SCHEDULE','INTERVIEW_FEEDBACK','STATUS_UPDATE','INFORMATION_QUERY','UNKNOWN']
Decision = Literal['PASS','REJECT','PENDING']

class Proposal(BaseModel):
    """提取出的操作建议，仍需经过状态机校验。"""
    intent: Intent = 'UNKNOWN'
    candidate_name: str | None = None
    application_id: str | None = None
    position: str | None = None
    education: str | None = None
    skills: str | None = None
    work_years: int | None = None
    evaluation: str | None = None
    round_no: int | None = Field(default=None, ge=1, le=3)
    interviewer: str | None = None
    scheduled_at: str | None = None
    decision: Decision = 'PENDING'
    next_stage: str | None = None

    @field_validator('decision', mode='before')
    @classmethod
    def default_missing_decision(cls, value):
        return 'PENDING' if value is None else value

class MessageIn(BaseModel):
    source: Literal['web','wecom'] = 'web'
    external_message_id: str = Field(min_length=3, max_length=120)
    sender_id: str = Field(default='hr-demo', max_length=100)
    content: str = Field(default='', max_length=12000)
    file_id: str | None = None
    application_id: str | None = None
    ai_config: AIConfig | None = None

class ReviewResolve(BaseModel):
    """人工修正提案后提交的审核动作。"""
    action: Literal['approve','reject']
    intent: Intent | None = None
    application_id: str | None = None
    candidate_name: str | None = None
    position: str | None = None
    round_no: int | None = Field(default=None, ge=1, le=3)
    scheduled_at: str | None = None
    decision: Decision | None = None
    evaluation: str | None = None
    interviewer: str | None = None
    next_stage: str | None = None
