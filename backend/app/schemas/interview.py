"""定义面试总结和基于原文依据的参考评分。"""
from pydantic import BaseModel, Field, field_validator, model_validator


class InterviewScore(BaseModel):
    """单个能力维度的评分、逐字稿依据和解释。"""
    dimension: str = Field(min_length=1, max_length=100)
    score: float | None = Field(default=None, ge=1, le=5)
    evidence: str = Field(default='', max_length=2000)
    reasoning: str = Field(default='', max_length=2000)

    @field_validator('evidence', 'reasoning', mode='before')
    @classmethod
    def normalize_text(cls, value):
        return '' if value is None else value

    @field_validator('score', mode='before')
    @classmethod
    def normalize_score(cls, value):
        if value is None or isinstance(value, bool): return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if 1 <= number <= 5 else None

    @model_validator(mode='after')
    def require_evidence(self):
        """没有依据时不保留分数，避免展示无来源的评分。"""
        if not self.evidence.strip(): self.score = None
        return self

class InterviewSummary(BaseModel):
    """保存基本信息、候选人表现、建议和各能力维度评分。"""
    candidate_name: str | None = None
    position: str | None = None
    round_no: int | None = Field(default=None, ge=1, le=3)
    interviewer: str | None = None
    interview_time: str | None = None
    duration: str | None = None
    summary: str = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    performance: list[str] = Field(default_factory=list)
    scores: list[InterviewScore] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)

    @field_validator('topics', 'performance', 'strengths', 'concerns', 'follow_ups', 'suggestions', mode='before')
    @classmethod
    def normalize_lists(cls, value):
        if value is None: return []
        if isinstance(value, str): return [value] if value.strip() else []
        return value

    @field_validator('scores', mode='before')
    @classmethod
    def normalize_scores(cls, value):
        return [] if value is None else value
