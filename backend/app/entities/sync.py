"""招聘事件同步队列的持久化实体。"""
from datetime import datetime
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from ..db import Base
from .common import uid, now

class Outbox(Base):
    """保存待发送事件、重试次数和下次重试时间。"""
    __tablename__ = 'sync_outbox'
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=uid)
    event_id: Mapped[str] = mapped_column(ForeignKey('recruitment_events.id'), unique=True)
    payload: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime] = mapped_column(DateTime, default=now)
