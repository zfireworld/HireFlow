"""聊天消息、招聘事件和人工审核任务的持久化实体。"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .common import uid, now

class Message(Base):
    """原始消息；来源与外部消息 ID 共同用于去重。"""
    __tablename__ = 'incoming_messages'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    source: Mapped[str] = mapped_column(String(30), default='web')
    external_message_id: Mapped[str] = mapped_column(String(120))
    sender_id: Mapped[str] = mapped_column(String(100), default='hr-demo')
    content: Mapped[str] = mapped_column(Text, default='')
    file_id: Mapped[str | None] = mapped_column(ForeignKey('resume_files.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default='processing')
    result: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (UniqueConstraint('source', 'external_message_id', name='uq_source_message'),)

class Event(Base):
    """记录一次招聘操作的阶段变化和业务数据。"""
    __tablename__ = 'recruitment_events'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(ForeignKey('applications.id'), index=True)
    message_id: Mapped[str] = mapped_column(ForeignKey('incoming_messages.id'))
    event_type: Mapped[str] = mapped_column(String(50))
    old_stage: Mapped[str] = mapped_column(String(40))
    new_stage: Mapped[str] = mapped_column(String(40))
    data: Mapped[str] = mapped_column(Text, default='{}')
    operator: Mapped[str] = mapped_column(String(100), default='hr-demo')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)

class Review(Base):
    """保存需要人工审核的提案及其工作流检查点标识。"""
    __tablename__ = 'review_tasks'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    message_id: Mapped[str] = mapped_column(ForeignKey('incoming_messages.id'), unique=True)
    application_id: Mapped[str | None] = mapped_column(ForeignKey('applications.id'), nullable=True)
    proposal: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    thread_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    reviewer: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
