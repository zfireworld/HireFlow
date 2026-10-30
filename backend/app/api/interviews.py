"""面试全文上传、总结生成和人工确认接口。"""
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from sqlalchemy import update
from sqlalchemy.orm import Session
from ..agents.interview_summary import summarize_interview
from ..config import MAX_UPLOAD_BYTES
from ..db import get_db
from ..entities import Interview, InterviewTranscript, Application, Candidate, Position
from ..services.documents import read_transcript
from ..schemas.ai import AIConfig
from ..schemas.assessment import InterviewDecision
from ..services.recruitment import confirm_interview_assessment
from ..services.model_settings import model_name
from .serializers import transcript_data

logger=logging.getLogger(__name__)
router=APIRouter()

@router.post('/interviews/{interview_id}/transcripts', status_code=201)
async def upload_interview_transcript(interview_id:str,file:UploadFile=File(...),
                                      ai_mode:str=Form('server'),ai_model:str=Form(''),
                                      ai_base_url:str=Form(''),ai_api_key:str=Form(''),
                                      db:Session=Depends(get_db)):
    """为待进行的面试生成总结；上传本身不会改变面试阶段。"""
    interview=db.get(Interview,interview_id)
    if not interview: raise HTTPException(404,'面试记录不存在')
    app=db.get(Application,interview.application_id)
    if interview.status!='SCHEDULED' or app.stage!=f'ROUND{interview.round_no}_SCHEDULED':
        raise HTTPException(409,'仅待进行的面试可上传面试文字；请先安排该轮面试')
    name=Path(file.filename or 'interview.txt').name[:180]
    ext=Path(name).suffix.lower()
    if ext not in ('.txt','.pdf','.docx'): raise HTTPException(400,'仅支持 TXT、PDF 或 DOCX 面试文字')
    contents=await file.read(MAX_UPLOAD_BYTES+1)
    if len(contents)>MAX_UPLOAD_BYTES: raise HTTPException(413,'文件不得超过5MB')
    if not contents: raise HTTPException(400,'上传文件为空')
    try:
        text=read_transcript(contents,ext)
    except Exception as exc:
        raise HTTPException(422,f'文件无法读取：{str(exc)[:120]}') from exc
    candidate=db.get(Candidate,app.candidate_id)
    position=db.get(Position,app.position_id)
    try:
        config=AIConfig(mode=ai_mode,model=ai_model or None,base_url=ai_base_url or None,api_key=ai_api_key or None)
    except ValidationError as exc:
        raise HTTPException(422,exc.errors(include_input=False)[0]['msg']) from exc
    try:
        summary=await run_in_threadpool(summarize_interview,text,candidate.name,position.title,interview.round_no,config)
    except RuntimeError as exc:
        raise HTTPException(503,str(exc)[:180]) from exc
    except Exception as exc:
        logger.exception('interview summary failed: %s',interview_id)
        raise HTTPException(502,f'面试总结生成失败：{str(exc)[:180]}') from exc
    # 模型运行期间面试状态可能变化，写入前加锁并重新校验。
    db.execute(update(Interview).where(Interview.id==interview_id).values(id=interview_id))
    db.expire_all()
    interview=db.get(Interview,interview_id)
    app=db.get(Application,interview.application_id)
    if interview.status!='SCHEDULED' or app.stage!=f'ROUND{interview.round_no}_SCHEDULED':
        db.rollback()
        raise HTTPException(409,'面试状态已变化，请刷新后查看')
    active_model=model_name(config)
    record=InterviewTranscript(interview_id=interview.id,filename=name,transcript_text=text,
                               summary_json=summary.model_dump_json(),model_name=active_model)
    db.add(record);db.commit()
    return transcript_data(record,db)


@router.post('/interviews/{interview_id}/transcripts/{transcript_id}/decision')
def decide_interview(interview_id:str,transcript_id:str,payload:InterviewDecision,db:Session=Depends(get_db)):
    """保存面试官修订内容，按其选择决定待定、淘汰或推进。"""
    try:
        return confirm_interview_assessment(db,interview_id,transcript_id,payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422,str(exc)) from exc
