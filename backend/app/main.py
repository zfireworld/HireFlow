"""后端启动入口：初始化数据库、演示数据、工作流和同步任务。"""
import logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from fastapi import FastAPI
from .config import HIFLOW_WEBHOOK_URL
from .db import Base, engine, SessionLocal
from .entities import Position
from .agents.workflow import create_checkpointer, create_graph
from .services.outbox import process_outbox
from .services.demo_seed import seed_demo_data
from .services.review_checkpoints import recover_review_checkpoints
from .services.model_settings import is_demo
from .api import router

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger('hireflow')

@asynccontextmanager
async def lifespan(app:FastAPI):
    """启动时注册数据和定时任务，关闭时释放检查点连接。"""
    # 导入实体模块后再建表，确保 SQLAlchemy 已注册全部表结构。
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for title in ('Python后端工程师','Java后端工程师','前端工程师','算法工程师','产品经理','数据分析师'):
            if not db.scalar(select(Position).where(Position.title==title)):
                db.add(Position(title=title))
        db.commit()
        seed_demo_data(db)
    # 检查点保存审核中断状态，便于人工审核后继续执行。
    conn,saver=create_checkpointer()
    app.state.graph=create_graph(saver)
    recover_review_checkpoints(app.state.graph)
    scheduler=AsyncIOScheduler(timezone='Asia/Shanghai')
    if HIFLOW_WEBHOOK_URL:
        scheduler.add_job(process_outbox,'interval',seconds=20,max_instances=1,coalesce=True)
        scheduler.start()
    else: logger.info('HiFlow 未配置，同步任务保留在 outbox 中')
    logger.info('AI 模式: %s', '规则演示' if is_demo() else '服务器模型')
    try:
        yield
    finally:
        if scheduler.running: scheduler.shutdown(wait=False)
        conn.close()

app=FastAPI(title='HireFlow AI 招聘流程自动化',version='1.0.0',lifespan=lifespan)
app.include_router(router)

@app.get('/')
def root(): return {'service':'HireFlow AI API','docs':'/docs'}
