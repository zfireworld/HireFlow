"""候选人、岗位、申请、简历和面试相关数据库实体。"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .common import uid, now

class Candidate(Base):
    """候选人基础资料；同一候选人可对应多个岗位申请。"""
    __tablename__ = 'candidates'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education: Mapped[str | None] = mapped_column(String(120), nullable=True)
    skills: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Position(Base):
    """招聘岗位，岗位名称唯一。"""
    __tablename__ = 'positions'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String(120), unique=True)
    department: Mapped[str] = mapped_column(String(100), default='研发部')

class Application(Base):
    """候选人对某个岗位的申请，保存当前阶段和编辑版本。"""
    __tablename__ = 'applications'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey('candidates.id'), index=True)
    position_id: Mapped[str] = mapped_column(ForeignKey('positions.id'), index=True)
    stage: Mapped[str] = mapped_column(String(40), default='SCREENING')
    round_no: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str] = mapped_column(String(100), default='hr-demo')
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (Index('ix_application_candidate_position', 'candidate_id', 'position_id'),)

class Resume(Base):
    """简历原始文件路径及提取出的文字；关联按候选人保存。"""
    __tablename__ = 'resume_files'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    candidate_id: Mapped[str | None] = mapped_column(ForeignKey('candidates.id'), nullable=True)
    filename: Mapped[str] = mapped_column(String(250))
    file_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    extracted_text: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Interview(Base):
    """某个申请的一轮面试，同一申请的轮次不可重复。"""
    __tablename__ = 'interviews'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'), index=True)
    round_no: Mapped[int] = mapped_column(Integer)
    interviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scheduled_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='SCHEDULED')
    evaluation: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str] = mapped_column(String(20), default='PENDING')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('application_id', 'round_no', name='uq_interview_round'),)

class InterviewTranscript(Base):
    """一次全文上传及生成结果；同一面试可以保留多个版本。"""
    __tablename__ = 'interview_transcripts'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    interview_id: Mapped[str] = mapped_column(ForeignKey('interviews.id'), index=True)
    filename: Mapped[str] = mapped_column(String(250))
    transcript_text: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
