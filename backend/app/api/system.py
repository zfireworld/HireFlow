from datetime import datetime
"""提供健康检查、统计、演示数据和同步任务接口。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from ..config import MODEL_NAME, HIFLOW_WEBHOOK_URL
from ..db import get_db
from ..entities import Position, Application, Review, Outbox, Interview
from ..services.recruitment import STAGES
from ..services.demo_seed import demo_examples
from ..services.model_settings import is_demo

router=APIRouter()

@router.get('/demo/examples')
def examples():
    return demo_examples()

@router.get('/health')
def health():
    demo=is_demo()
    return {'ok':True,'ai_mode':'demo' if demo else 'qwen',
            'model_mode':'demo' if demo else 'model', 'model_name':MODEL_NAME,
            'qwen_model':MODEL_NAME,'sync_configured':bool(HIFLOW_WEBHOOK_URL)}

@router.get('/positions')
def positions(db:Session=Depends(get_db)):
    return [{'id':p.id,'title':p.title,'department':p.department} for p in db.scalars(select(Position).order_by(Position.title)).all()]

@router.get('/stats/overview')
def stats(db:Session=Depends(get_db)):
    apps=db.scalars(select(Application)).all()
    counts={k:0 for k in STAGES}
    for a in apps: counts[a.stage]=counts.get(a.stage,0)+1
    pending_reviews=db.scalar(select(func.count(Review.id)).where(Review.status=='pending')) or 0
    pending_sync=db.scalar(select(func.count(Outbox.id)).where(Outbox.status!='success')) or 0
    interview_count=db.scalar(select(func.count(Interview.id)).where(Interview.status=='COMPLETED')) or 0
    return {'total':len(apps),'interviewing':sum(counts.get(k,0) for k in counts if k.startswith('ROUND')),
            'offer_accepted':counts.get('OFFER_ACCEPTED',0),'hired':counts.get('HIRED',0),
            'pending_reviews':pending_reviews,'pending_sync':pending_sync,'interviews_completed':interview_count,
            'stages':[{'stage':key,'name':STAGES[key],'count':value} for key,value in counts.items()]}

@router.get('/sync/jobs')
def sync_jobs(db:Session=Depends(get_db)):
    rows=db.scalars(select(Outbox).order_by(desc(Outbox.next_retry_at)).limit(100)).all()
    return [{'id':r.id,'event_id':r.event_id,'status':r.status,'retry_count':r.retry_count,
             'last_error':r.last_error} for r in rows]

@router.post('/sync/jobs/{id}/retry')
def sync_retry(id:str,db:Session=Depends(get_db)):
    job=db.get(Outbox,id)
    if not job: raise HTTPException(404,'任务不存在')
    job.status='pending';job.retry_count=0;job.next_retry_at=datetime.utcnow();db.commit()
    return {'status':'pending'}
