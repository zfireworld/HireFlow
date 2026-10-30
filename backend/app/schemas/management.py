"""定义人工建档、简历维护、初筛和面试操作的请求模型。"""
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ApplicationCreate(BaseModel):
    candidate_id: str | None = None
    candidate_name: str | None = Field(default=None, max_length=100)
    position_id: str | None = None
    position_title: str | None = Field(default=None, max_length=120)
    education: str | None = Field(default=None, max_length=120)
    skills: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    work_years: int | None = Field(default=None, ge=0, le=80)
    owner: str = Field(default='hr-demo', min_length=1, max_length=100)

    @model_validator(mode='after')
    def check_candidate(self):
        if not self.candidate_id and not (self.candidate_name and self.candidate_name.strip()):
            raise ValueError('请选择已有候选人或填写候选人姓名')
        if not self.position_id and not (self.position_title and self.position_title.strip()):
            raise ValueError('请选择或填写岗位')
        if not self.owner.strip():
            raise ValueError('负责人不能为空')
        return self


class ApplicationEdit(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    education: str | None = Field(default=None, max_length=120)
    skills: str | None = Field(default=None, max_length=5000)
    phone: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    work_years: int | None = Field(default=None, ge=0, le=80)
    owner: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)

    @model_validator(mode='after')
    def check_names(self):
        if not self.name.strip() or not self.owner.strip():
            raise ValueError('候选人姓名和负责人不能为空')
        return self


class InterviewAction(BaseModel):
    action: Literal['schedule', 'feedback']
    round_no: int = Field(ge=1, le=3)
    scheduled_at: str | None = Field(default=None, max_length=40)
    interviewer: str | None = Field(default=None, max_length=100)
    evaluation: str | None = Field(default=None, max_length=5000)
    decision: Literal['PASS', 'REJECT', 'PENDING'] = 'PENDING'


class InterviewEdit(BaseModel):
    interviewer: str | None = Field(default=None, max_length=100)
    scheduled_at: str = Field(min_length=1, max_length=40)
    evaluation: str | None = Field(default=None, max_length=5000)


class ScreeningDecision(BaseModel):
    decision: Literal['PENDING', 'INTERVIEW', 'REJECT']
    evaluation: str = Field(min_length=1, max_length=5000)

    @model_validator(mode='after')
    def check_evaluation(self):
        if not self.evaluation.strip():
            raise ValueError('请填写初筛评价')
        return self


class ManualResume(BaseModel):
    text: str = Field(min_length=1, max_length=100000)

    @model_validator(mode='after')
    def check_text(self):
        if not self.text.strip():
            raise ValueError('请填写简历内容')
        return self


class EmploymentAction(BaseModel):
    target: Literal['OFFER_ACCEPTED', 'HIRED']
