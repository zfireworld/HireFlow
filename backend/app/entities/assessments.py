"""简历评估及面试官确认结果的持久化实体。"""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .common import now, uid


class ResumeAssessment(Base):
    """分别保存生成的参考评价和人工修订后的评价。"""
    __tablename__ = 'resume_assessments'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    resume_id: Mapped[str] = mapped_column(ForeignKey('resume_files.id'), index=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey('applications.id'), nullable=True)
    generated_json: Mapped[str] = mapped_column(Text)
    reviewed_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default='PENDING')
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class InterviewAssessmentDecision(Base):
    """保存一份面试全文对应的人工修订内容和处理结果。"""
    __tablename__ = 'interview_assessment_decisions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    transcript_id: Mapped[str] = mapped_column(ForeignKey('interview_transcripts.id'), index=True)
    reviewed_json: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (UniqueConstraint('transcript_id', name='uq_interview_assessment_transcript'),)
