"""处理招聘事件的外部同步队列和失败重试。"""
import json
from datetime import timedelta
from sqlalchemy import select
from ..clients.hiflow import send_event
from ..config import HIFLOW_WEBHOOK_URL
from ..db import SessionLocal
from ..entities import Outbox, now

async def process_outbox():
    """逐条发送到 HiFlow，失败后按指数退避安排下次重试。"""
    if not HIFLOW_WEBHOOK_URL: return
    with SessionLocal() as db:
        jobs=db.scalars(select(Outbox).where(Outbox.status!='success', Outbox.next_retry_at<=now()).limit(10)).all()
        for j in jobs:
            try:
                await send_event(json.loads(j.payload), j.event_id)
                j.status='success';j.last_error=None
            except Exception as exc:
                j.status='failed';j.retry_count+=1
                j.last_error=str(exc)[:500]
                j.next_retry_at=now()+timedelta(seconds=min(3600,30*2**min(j.retry_count,7)))
            db.commit()
