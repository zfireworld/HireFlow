"""定义简历评价和人工确认的请求、结果模型。"""
from typing import Literal
import re
from pydantic import BaseModel, Field, field_validator
from .ai import AIConfig
from .interview import InterviewSummary


class ResumeEvaluation(BaseModel):
    """简历中提取的基础资料及面试官参考意见。"""
    candidate_name: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=120)
    skills: str | None = Field(default=None, max_length=5000)
    work_years: int | None = Field(default=None, ge=0, le=80)
    summary: str = Field(min_length=1, max_length=10000)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @field_validator('skills', mode='before')
    @classmethod
    def normalize_skills(cls, value):
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return '、'.join(item.strip() for item in value if item.strip()) or None
        return value

    @field_validator('summary', mode='before')
    @classmethod
    def normalize_summary(cls, value):
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return '\n'.join(item.strip() for item in value if item.strip())
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator('strengths', 'concerns', 'suggestions', mode='before')
    @classmethod
    def normalize_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value.strip() else []
        return value

    @field_validator('work_years', mode='before')
    @classmethod
    def normalize_years(cls, value):
        if isinstance(value, str):
            match = re.fullmatch(r'\s*(\d+)\s*(?:年)?\s*', value)
            return int(match.group(1)) if match else None
        if isinstance(value, float) and not value.is_integer():
            return None
        return value


class ResumeAssessmentCreate(BaseModel):
    file_id: str = Field(min_length=1)
    application_id: str | None = None
    context: str = Field(default='', max_length=12000)
    ai_config: AIConfig | None = None


class ResumeDecision(BaseModel):
    decision: Literal['PENDING', 'REJECT', 'INTERVIEW']
    application_id: str | None = None
    evaluation: ResumeEvaluation


class InterviewDecision(BaseModel):
    decision: Literal['PENDING', 'REJECT', 'PASS']
    evaluation: InterviewSummary
