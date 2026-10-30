"""查看并处理需要人工确认的招聘操作。"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, desc, update
from sqlalchemy.orm import Session
from ..db import get_db
from ..entities import Review, Message
from ..schemas import ReviewResolve, Proposal
from ..services.recruitment import apply_proposal, validate_proposal
from ..services.review_checkpoints import resume_review_checkpoint
from .serializers import nice_date

logger=logging.getLogger(__name__)
router=APIRouter()

@router.get('/reviews')
def reviews(db:Session=Depends(get_db)):
    rows=db.scalars(select(Review).order_by(desc(Review.created_at))).all()
    return [{'id':r.id,'message_id':r.message_id,'application_id':r.application_id,
             'reason':r.reason,'proposal':json.loads(r.proposal),'status':r.status,
             'created_at':nice_date(r.created_at)} for r in rows]

@router.post('/reviews/{review_id}/resolve')
def resolve_review(review_id:str,payload:ReviewResolve,request:Request,db:Session=Depends(get_db)):
    """合并人工修正并重新校验，再恢复工作流执行或拒绝操作。"""
    review=db.get(Review,review_id)
    if not review: raise HTTPException(404,'审核任务不存在')
    if review.status!='pending': raise HTTPException(409,'审核任务已处理')
    prop=json.loads(review.proposal)
    for k in ('intent','application_id','candidate_name','position','round_no','scheduled_at','decision','evaluation','interviewer','next_stage'):
        if k=='application_id' and k in payload.model_fields_set:
            prop[k]=payload.application_id
        elif getattr(payload,k) is not None:
            prop[k]=getattr(payload,k)
    try:
        # 以条件更新取得写锁，避免并发批准和拒绝同一审核。
        claimed=db.execute(update(Review).where(Review.id==review_id,Review.status=='pending').values(status='pending'))
        if claimed.rowcount!=1:
            raise HTTPException(409,'审核任务已处理')
        db.refresh(review)
        if payload.action=='approve':
            try:
                proposal=Proposal.model_validate(prop)
            except Exception as exc:
                raise HTTPException(422,str(exc)[:180]) from exc
            _,reason=validate_proposal(proposal,db)
            if reason: raise HTTPException(422,f'修正后仍无法自动执行：{reason}')
            msg=db.get(Message,review.message_id)
            output=apply_proposal(proposal,review.message_id,msg.sender_id,session=db)
            review.status='approved'
        else:
            output={'status':'rejected','detail':'人工拒绝该更新'}
            msg=db.get(Message,review.message_id)
            msg.status='rejected';msg.result=json.dumps(output,ensure_ascii=False)
            review.status='rejected'
        review.reviewer='hr-demo'
        review.proposal=json.dumps(prop,ensure_ascii=False)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception('review resolution failed')
        raise HTTPException(409,f'审核处理失败：{str(exc)[:180]}')
    # 检查点保存在独立数据库，业务记录是权威状态；恢复失败不能撤销已提交的决定。
    try:
        resume_review_checkpoint(request.app.state.graph,review)
    except Exception:
        logger.exception('review checkpoint could not be resumed: %s', review.id)
    return output
