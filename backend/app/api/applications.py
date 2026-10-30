"""查询候选人、岗位申请和申请详情。"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from ..db import get_db
from ..entities import Application, Candidate, Interview, InterviewTranscript, Event, Resume
from ..services.recruitment import STAGES
from .serializers import app_data, candidate_data, nice_date, transcript_data

router=APIRouter()

@router.get('/applications')
def applications(q:str='',stage:str='',db:Session=Depends(get_db)):
    rows=db.scalars(select(Application).order_by(desc(Application.updated_at))).all()
    out=[app_data(a,db) for a in rows]
    if q: out=[a for a in out if q.lower() in (a['candidate_name']+a['position']+a['id']).lower()]
    if stage: out=[a for a in out if a['stage']==stage]
    return out[:300]

@router.get('/candidates')
def candidates(db:Session=Depends(get_db)):
    return [candidate_data(c) for c in db.scalars(select(Candidate).order_by(desc(Candidate.created_at)).limit(300)).all()]

@router.get('/applications/{app_id}')
def application_detail(app_id:str,db:Session=Depends(get_db)):
    """汇总候选人、共享简历、各轮最新逐字稿和招聘事件。"""
    app=db.get(Application,app_id)
    if not app: raise HTTPException(404,'申请记录不存在')
    c=db.get(Candidate,app.candidate_id)
    interviews=db.scalars(select(Interview).where(Interview.application_id==app_id).order_by(Interview.round_no)).all()
    transcripts=db.scalars(select(InterviewTranscript).where(InterviewTranscript.interview_id.in_([i.id for i in interviews])).order_by(desc(InterviewTranscript.created_at),desc(InterviewTranscript.id))).all() if interviews else []
    latest_transcripts={}
    for transcript in transcripts:
        latest_transcripts.setdefault(transcript.interview_id, transcript)
    events=db.scalars(select(Event).where(Event.application_id==app_id).order_by(desc(Event.created_at))).all()
    resumes=db.scalars(select(Resume).where(Resume.candidate_id==c.id).order_by(desc(Resume.uploaded_at))).all()
    return {'application':app_data(app,db),'candidate':candidate_data(c),
            'resumes':[{'id':r.id,'filename':r.filename,'uploaded_at':nice_date(r.uploaded_at),'text':r.extracted_text} for r in resumes],
            'interviews':[{'id':i.id,'round_no':i.round_no,'interviewer':i.interviewer,'scheduled_at':i.scheduled_at,
                           'status':i.status,'result':i.result,'evaluation':i.evaluation,
                           'transcript':transcript_data(latest_transcripts[i.id],db) if i.id in latest_transcripts else None} for i in interviews],
            'events':[{'id':e.id,'type':e.event_type,'old_stage':STAGES.get(e.old_stage,e.old_stage),
                       'new_stage':STAGES.get(e.new_stage,e.new_stage),'data':json.loads(e.data),
                       'created_at':nice_date(e.created_at),'operator':e.operator} for e in events]}
