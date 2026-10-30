"""接收聊天消息，执行招聘提案或创建人工审核任务。"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..db import get_db
from ..agents.proposal import extract_proposal
from ..entities import Message, Review
from ..schemas import MessageIn, Proposal
from ..services.recruitment import apply_proposal
from .serializers import nice_date

logger=logging.getLogger(__name__)
router=APIRouter()

@router.post('/messages')
def send_message(payload:MessageIn, request:Request, db:Session=Depends(get_db)):
    """以来源和外部消息 ID 去重，并通过工作流校验提案。"""
    if not payload.content.strip() and not payload.file_id: raise HTTPException(400,'请填写消息或上传简历')
    existing=db.scalar(select(Message).where(Message.source==payload.source, Message.external_message_id==payload.external_message_id))
    if existing: return {'status':'duplicate','message_id':existing.id,'original_status':existing.status,'original_result':json.loads(existing.result)}
    if payload.file_id:
        raise HTTPException(422,'简历请通过简历评估提交，并由面试官确认处理')
    resume_text=''
    msg=Message(source=payload.source,external_message_id=payload.external_message_id,
                sender_id=payload.sender_id,content=payload.content,file_id=payload.file_id)
    db.add(msg)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'消息已存在，请刷新列表')
    thread={'configurable':{'thread_id':msg.id}}
    try:
        state={'content':payload.content,'resume_text':resume_text,'application_id':payload.application_id}
        # 自定义模型配置仅用于本次提取，不写入工作流检查点。
        if payload.ai_config is not None:
            state['proposal']=extract_proposal(payload.content,resume_text,payload.application_id,payload.ai_config).model_dump()
        result=request.app.state.graph.invoke(state,config=thread)
        values=request.app.state.graph.get_state(thread).values
        if '__interrupt__' in result:
            p=values.get('proposal',{})
            task=Review(message_id=msg.id,application_id=values.get('resolved_app'),
                        proposal=json.dumps(p,ensure_ascii=False),reason=values.get('reason') or '待审核',thread_id=msg.id)
            db.add(task)
            msg.status='pending_review'
            out={'status':'pending_review','message_id':msg.id,'reason':task.reason,'proposal':p}
            msg.result=json.dumps(out,ensure_ascii=False)
            db.commit()
            return out
        proposal=Proposal.model_validate(values['proposal'])
        output=apply_proposal(proposal,msg.id,payload.sender_id)
        return {'message_id':msg.id,**output}
    except Exception as exc:
        logger.exception('message processing failed: %s', msg.id)
        db.expire_all()
        msg=db.get(Message,msg.id)
        msg.status='failed'
        msg.result=json.dumps({'status':'failed','error':str(exc)[:180]},ensure_ascii=False)
        db.commit()
        raise HTTPException(502, f'处理失败：{str(exc)[:180]}')

@router.get('/messages')
def messages(db:Session=Depends(get_db)):
    rows=db.scalars(select(Message).order_by(Message.created_at.desc()).limit(60)).all()
    return [{'id':m.id,'content':m.content,'status':m.status,'result':json.loads(m.result),
             'file_id':m.file_id,'created_at':nice_date(m.created_at)} for m in rows]
