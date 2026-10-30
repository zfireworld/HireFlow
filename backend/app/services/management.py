"""处理人工维护操作，并保留与聊天操作一致的事件和同步记录。"""
import json
from datetime import datetime
from sqlalchemy import select, update
from ..db import SessionLocal
from ..entities import Application, Candidate, Event, Interview, Message, Outbox, Position, now, uid
from ..schemas import Proposal
from .recruitment import STAGES, apply_proposal, validate_proposal


def record_event(db, app, event_type, data, old_stage=None):
    """在调用方事务中添加人工操作消息、招聘事件和待同步任务。"""
    candidate = db.get(Candidate, app.candidate_id)
    position = db.get(Position, app.position_id)
    message = Message(source='web', external_message_id='manual-' + uid(), sender_id='hr-demo',
                      content='表格维护：' + event_type, status='applied', result='{}')
    db.add(message)
    db.flush()
    event = Event(application_id=app.id, message_id=message.id, event_type=event_type,
                  old_stage=old_stage or app.stage, new_stage=app.stage,
                  data=json.dumps(data, ensure_ascii=False), operator='hr-demo')
    db.add(event)
    db.flush()
    payload = {'event_id':event.id, 'at':now().isoformat(timespec='seconds'),
               'candidate_id':candidate.id, 'application_id':app.id, 'position':position.title,
               'event_type':event_type, 'old_stage':STAGES.get(old_stage or app.stage, old_stage or app.stage),
               'new_stage':STAGES.get(app.stage, app.stage), 'round_no':data.get('round_no') or '',
               'decision':data.get('decision', ''), 'operator':'hr-demo'}
    db.add(Outbox(event_id=event.id, payload=json.dumps(payload, ensure_ascii=False)))


def create_application(db, payload):
    """关联或新建候选人和岗位，建立初始筛选阶段的申请。"""
    position = db.get(Position, payload.position_id) if payload.position_id else None
    if not position and not payload.position_id and payload.position_title:
        title = payload.position_title.strip()
        position = db.scalar(select(Position).where(Position.title == title))
        if not position:
            position = Position(title=title)
            db.add(position)
            db.flush()
    if not position:
        raise ValueError('岗位不存在')
    if payload.candidate_id:
        candidate = db.get(Candidate, payload.candidate_id)
        if not candidate:
            raise ValueError('候选人不存在')
    else:
        name = payload.candidate_name.strip()
        if db.scalar(select(Candidate).where(Candidate.name == name)):
            raise ValueError('已有同名候选人，请从已有候选人中选择')
        candidate = Candidate(name=name, education=payload.education, skills=payload.skills, phone=payload.phone, email=payload.email,
                              work_years=payload.work_years)
        db.add(candidate)
        db.flush()
    if db.scalar(select(Application).where(Application.candidate_id == candidate.id,
                                           Application.position_id == position.id)):
        raise ValueError('该候选人已有此岗位申请')
    app = Application(candidate_id=candidate.id, position_id=position.id, owner=payload.owner.strip(), stage='SCREENING')
    db.add(app)
    db.flush()
    record_event(db, app, 'MANUAL_APPLICATION_CREATED', {'candidate_name':candidate.name, 'position':position.title})
    db.commit()
    return app


def edit_application(db, app, payload):
    """使用版本号防止旧表单覆盖资料，并更新同一候选人的关联版本。"""
    claimed = db.execute(update(Application).where(Application.id == app.id, Application.version == payload.version)
                         .values(version=Application.version + 1, updated_at=now()))
    if claimed.rowcount != 1:
        raise ValueError('申请已更新，请刷新后重新编辑')
    db.refresh(app)
    db.execute(update(Application).where(Application.candidate_id == app.candidate_id, Application.id != app.id)
               .values(version=Application.version + 1, updated_at=now()))
    candidate = db.get(Candidate, app.candidate_id)
    candidate.name = payload.name.strip()
    candidate.education = payload.education or None
    candidate.skills = payload.skills or None
    if 'phone' in payload.model_fields_set: candidate.phone = payload.phone or None
    if 'email' in payload.model_fields_set: candidate.email = payload.email or None
    candidate.work_years = payload.work_years
    app.owner = payload.owner.strip()
    record_event(db, app, 'MANUAL_PROFILE_UPDATED', {'candidate_name':candidate.name, 'owner':app.owner})
    db.commit()


def screening_decision(db, app, payload):
    """仅对筛选阶段的申请记录初筛评价和人工决定。"""
    claimed = db.execute(update(Application).where(Application.id == app.id, Application.stage == 'SCREENING')
                         .values(version=Application.version + 1, updated_at=now()))
    if claimed.rowcount != 1:
        raise ValueError('仅简历筛选阶段可进行初筛，请刷新后查看')
    db.refresh(app)
    if payload.decision == 'INTERVIEW': app.stage = 'ROUND1_PENDING'; app.round_no = 1
    elif payload.decision == 'REJECT': app.stage = 'REJECTED'
    record_event(db, app, 'MANUAL_SCREENING', {'evaluation':payload.evaluation.strip(), 'decision':payload.decision}, old_stage='SCREENING')
    db.commit()
    return app


def edit_interview(db, interview, payload):
    """修改面试资料；未完成的面试评价须通过反馈流程提交。"""
    try:
        datetime.strptime(payload.scheduled_at, '%Y-%m-%d %H:%M')
    except ValueError as exc:
        raise ValueError('面试时间必须是 YYYY-MM-DD HH:MM') from exc
    if interview.status != 'COMPLETED' and payload.evaluation:
        raise ValueError('未完成的面试请通过面试反馈记录评价')
    interview.scheduled_at = payload.scheduled_at
    interview.interviewer = payload.interviewer or None
    interview.evaluation = payload.evaluation or None
    app = db.get(Application, interview.application_id)
    app.version += 1
    app.updated_at = now()
    record_event(db, app, 'MANUAL_INTERVIEW_UPDATED', {'round_no':interview.round_no, 'scheduled_at':interview.scheduled_at})
    db.commit()


def interview_action(app_id, payload):
    """将人工安排或反馈转换为提案，复用状态机与事件写入。"""
    proposal = Proposal(intent='INTERVIEW_SCHEDULE' if payload.action == 'schedule' else 'INTERVIEW_FEEDBACK',
                        application_id=app_id, round_no=payload.round_no, scheduled_at=payload.scheduled_at,
                        interviewer=payload.interviewer, evaluation=payload.evaluation, decision=payload.decision)
    return apply_manual_proposal(proposal, payload.action)


def employment_action(app_id, payload):
    """由人工确认 Offer 已接受或候选人已入职。"""
    return apply_manual_proposal(Proposal(intent='STATUS_UPDATE', application_id=app_id,
                                          next_stage=payload.target), payload.target)


def apply_manual_proposal(proposal, action):
    """复用聊天状态机处理人工操作并保留事件记录。"""
    with SessionLocal() as db:
        _, reason = validate_proposal(proposal, db)
        if reason:
            raise ValueError(reason)
        message = Message(source='web', external_message_id='manual-' + uid(), sender_id='hr-demo',
                          content='表格维护：' + action)
        db.add(message)
        db.commit()
        message_id = message.id
    try:
        return apply_proposal(proposal, message_id, 'hr-demo')
    except Exception:
        with SessionLocal() as db:
            message = db.get(Message, message_id)
            message.status = 'failed'
            message.result = json.dumps({'status':'failed', 'error':'人工操作未能执行'}, ensure_ascii=False)
            db.commit()
        raise
