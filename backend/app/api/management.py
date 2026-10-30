"""人工维护候选人、简历、初筛和面试记录的接口。"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from ..db import get_db
from ..entities import Application, Candidate, Interview, Position, Resume, now
from ..schemas.management import ApplicationCreate, ApplicationEdit, InterviewAction, InterviewEdit, ScreeningDecision, ManualResume, EmploymentAction
from ..services.management import create_application, edit_application, edit_interview, interview_action, screening_decision, record_event, employment_action
from ..services.resume_files import stage_resume, storage
from .files import prepare_resume_upload
from .serializers import app_data

router = APIRouter(prefix='/management')


@router.post('/applications/{app_id}/screening')
def screen_application(app_id: str, payload: ScreeningDecision, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app: raise HTTPException(404, '申请记录不存在')
    try:
        return app_data(screening_decision(db, app, payload), db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


def attach_resume(db, app, resume):
    """关联候选人并记录事件，与简历记录一同提交。"""
    db.execute(update(Application).where(Application.id == app.id)
               .values(version=Application.version + 1, updated_at=now()))
    db.refresh(app)
    resume.candidate_id = app.candidate_id
    record_event(db, app, 'MANUAL_RESUME_ADDED', {'filename':resume.filename})
    db.commit()
    return {'id':resume.id, 'filename':resume.filename}


@router.post('/applications/{app_id}/resumes', status_code=201)
async def add_resume_file(app_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传并关联简历；任何写入失败时同时回滚记录和文件。"""
    app = db.get(Application, app_id)
    if not app: raise HTTPException(404, '申请记录不存在')
    resume, path = await prepare_resume_upload(file, db)
    try:
        return attach_resume(db, app, resume)
    except Exception:
        db.rollback()
        storage.remove(path)
        raise


@router.post('/applications/{app_id}/resumes/manual', status_code=201)
def add_manual_resume(app_id: str, payload: ManualResume, db: Session = Depends(get_db)):
    """将人工填写的内容保存为可下载的文字简历。"""
    app = db.get(Application, app_id)
    if not app: raise HTTPException(404, '申请记录不存在')
    text = payload.text.strip()
    data = text.encode('utf-8')
    resume, path = stage_resume(db, '人工填写简历.txt', data, text)
    try:
        return attach_resume(db, app, resume)
    except Exception:
        db.rollback()
        storage.remove(path)
        raise


@router.get('/resumes/{resume_id}/download')
def download_resume(resume_id: str, db: Session = Depends(get_db)):
    """仅返回已关联候选人且位于上传目录内的文件。"""
    resume = db.get(Resume, resume_id)
    if not resume or not resume.candidate_id: raise HTTPException(404, '简历不存在')
    path = storage.existing(resume.file_path)
    if path is None:
        raise HTTPException(404, '简历文件不存在')
    return FileResponse(path, filename=resume.filename)


@router.post('/applications', status_code=201)
def add_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    try:
        app = create_application(db, payload)
        return app_data(app, db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.put('/applications/{app_id}')
def update_application(app_id: str, payload: ApplicationEdit, db: Session = Depends(get_db)):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, '申请记录不存在')
    try:
        edit_application(db, app, payload)
        return app_data(app, db)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get('/interviews')
def list_interviews(db: Session = Depends(get_db)):
    interviews = db.scalars(select(Interview).order_by(Interview.created_at.desc()).limit(500)).all()
    result = []
    for interview in interviews:
        app = db.get(Application, interview.application_id)
        candidate = db.get(Candidate, app.candidate_id)
        position = db.get(Position, app.position_id)
        result.append({'id':interview.id, 'application_id':app.id, 'candidate_name':candidate.name,
                       'position':position.title, 'application_stage':app.stage, 'round_no':interview.round_no,
                       'interviewer':interview.interviewer, 'scheduled_at':interview.scheduled_at,
                       'status':interview.status, 'result':interview.result, 'evaluation':interview.evaluation})
    return result


@router.post('/applications/{app_id}/interview-actions')
def apply_interview_action(app_id: str, payload: InterviewAction):
    try:
        return interview_action(app_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/applications/{app_id}/employment-action')
def apply_employment_action(app_id: str, payload: EmploymentAction):
    try:
        return employment_action(app_id, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.put('/interviews/{interview_id}')
def update_interview(interview_id: str, payload: InterviewEdit, db: Session = Depends(get_db)):
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(404, '面试记录不存在')
    try:
        edit_interview(db, interview, payload)
        return {'status':'updated', 'id':interview.id}
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
