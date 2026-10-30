"""恢复已提交审核对应的 LangGraph 检查点。"""
import json
import logging
from langgraph.types import Command
from sqlalchemy import select
from ..db import SessionLocal
from ..entities import Review

logger = logging.getLogger(__name__)


def resume_review_checkpoint(graph, review):
    """仅恢复仍在等待的检查点，业务决定以数据库中的审核状态为准。"""
    thread={'configurable':{'thread_id':review.thread_id}}
    if graph.get_state(thread).next:
        graph.invoke(Command(resume={'approved':review.status=='approved',
                                     'proposal':json.loads(review.proposal)}),config=thread)


def recover_review_checkpoints(graph):
    """启动时重试未能恢复的已处理审核，不阻断应用启动。"""
    with SessionLocal() as db:
        reviews=db.scalars(select(Review).where(Review.status.in_(['approved','rejected']))).all()
        for review in reviews:
            try:
                resume_review_checkpoint(graph,review)
            except Exception:
                logger.exception('审核检查点恢复失败：%s',review.id)
