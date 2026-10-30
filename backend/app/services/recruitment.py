"""招聘状态机及人工确认后的事务写入。"""
import json
from contextlib import nullcontext
from datetime import datetime
from sqlalchemy import select, func, update
from ..db import SessionLocal
from ..entities import Candidate, Position, Application, Interview, Event, Outbox, Message, Resume, now
from ..schemas import Proposal

STAGES = {
 'SCREENING':'简历筛选','ROUND1_PENDING':'一面待安排','ROUND1_SCHEDULED':'一面待进行','ROUND1_FEEDBACK':'一面待反馈',
 'ROUND2_PENDING':'二面待安排','ROUND2_SCHEDULED':'二面待进行','ROUND2_FEEDBACK':'二面待反馈',
 'ROUND3_PENDING':'三面待安排','ROUND3_SCHEDULED':'三面待进行','ROUND3_FEEDBACK':'三面待反馈',
 'OFFER_PENDING':'Offer待处理','OFFER_ACCEPTED':'Offer已接受','HIRED':'已入职','REJECTED':'已淘汰','WITHDRAWN':'已退出'
}
CLOSED = {'HIRED','REJECTED','WITHDRAWN'}

def get_application(db, proposal: Proposal):
    """按申请 ID 或姓名和岗位定位申请；存在歧义时要求明确指定。"""
    if proposal.application_id:
        app=db.get(Application, proposal.application_id)
        return app, None if app else '指定申请ID不存在'
    if not proposal.candidate_name:
        return None, '缺少候选人姓名或申请ID'
    q = select(Application).join(Candidate, Candidate.id==Application.candidate_id).join(Position,Position.id==Application.position_id).where(Candidate.name==proposal.candidate_name)
    if proposal.position: q=q.where(Position.title==proposal.position.replace(' ',''))
    apps = db.scalars(q).all()
    if len(apps)>1: return None, '同名或多岗位申请，必须指定申请ID'
    if not apps: return None, '候选人申请不存在；请先上传简历建档'
    return apps[0], None

def validate_proposal(p: Proposal, db):
    """只校验业务规则，不写数据库；返回申请 ID 和不可执行原因。"""
    if p.intent=='UNKNOWN': return None, '无法识别招聘操作意图'
    if p.intent=='RESUME_RECEIVED':
        if not p.candidate_name or not p.position: return None, '简历缺少姓名或岗位，请在聊天中补充'
        app, reason = get_application(db,p)
        if p.application_id and reason: return None, reason
        if reason and '候选人申请不存在' not in reason: return None, reason
        if app:
            target_candidate=db.get(Candidate,app.candidate_id)
            target_position=db.get(Position,app.position_id)
            if target_candidate.name!=p.candidate_name or target_position.title!=p.position.replace(' ',''):
                return app.id, '简历信息与所选申请不一致'
            if app.stage in CLOSED: return app.id, '已有同岗位的已结束申请，避免自动覆盖，请人工确认'
        return app.id if app else None, None
    app,reason=get_application(db,p)
    if reason: return None,reason
    if not app: return None,'岗位申请不存在'
    existing_candidate=db.get(Candidate,app.candidate_id)
    existing_position=db.get(Position,app.position_id)
    if p.candidate_name and p.candidate_name != existing_candidate.name: return app.id,'候选人姓名与申请ID不一致'
    if p.position and p.position.replace(' ','') != existing_position.title: return app.id,'岗位与申请ID不一致'
    s=app.stage
    if p.intent=='INFORMATION_QUERY': return app.id,None
    if s in CLOSED: return app.id,'流程已结束，禁止自动修改'
    if p.intent=='HR_EVALUATION':
        return app.id, None if s=='SCREENING' else '仅允许在简历初筛阶段追加HR初评'
    if p.intent=='INTERVIEW_SCHEDULE':
        r=p.round_no
        if r not in (1,2,3): return app.id,'缺少有效面试轮次'
        if not p.scheduled_at: return app.id,'缺少精确的面试日期时间'
        try: datetime.strptime(p.scheduled_at,'%Y-%m-%d %H:%M')
        except (TypeError,ValueError): return app.id,'面试时间必须是 YYYY-MM-DD HH:MM'
        if s not in (f'ROUND{r}_PENDING',f'ROUND{r}_SCHEDULED'): return app.id,f'当前阶段{s}不能安排第{r}轮面试'
        return app.id,None
    if p.intent=='INTERVIEW_FEEDBACK':
        r=p.round_no
        if r not in (1,2,3): return app.id,'缺少有效面试轮次'
        if s not in (f'ROUND{r}_SCHEDULED',f'ROUND{r}_FEEDBACK'): return app.id,'面试反馈轮次与当前状态不一致'
        if not p.evaluation: return app.id,'面试评价不能为空'
        return app.id,None
    if p.intent=='STATUS_UPDATE':
        target=p.next_stage
        if target=='OFFER_ACCEPTED' and s=='OFFER_PENDING': return app.id,None
        if target=='HIRED' and s=='OFFER_ACCEPTED': return app.id,None
        if target=='OFFER_PENDING' and s=='ROUND3_FEEDBACK': return app.id,None
        if target in ('REJECTED','WITHDRAWN'): return app.id,None
        return app.id,'目标阶段或当前流程不满足状态变更规则'
    return app.id,'不支持的操作'

def apply_proposal(p: Proposal, message_id: str, sender: str, *, session=None):
    """在事务内再次校验，并原子写入申请、招聘事件和同步任务。"""
    own_session = session is None
    with (SessionLocal() if own_session else nullcontext(session)) as db:
        # 先取得写锁，再读取状态和检查幂等，避免并发重复处理同一消息。
        db.execute(update(Message).where(Message.id==message_id).values(id=message_id))
        msg = db.get(Message, message_id)
        if not msg: raise ValueError('原始消息不存在')
        existing = db.scalar(select(Event).where(Event.message_id==message_id))
        if existing: return {'status':'applied','event_id':existing.id,'application_id':existing.application_id,'detail':'已处理过该消息'}
        app_id,reason=validate_proposal(p,db)
        if reason: raise ValueError(reason)
        if p.intent=='INFORMATION_QUERY':
            app=db.get(Application,app_id)
            result={'status':'applied','application_id':app.id,'detail':f'当前招聘阶段：{STAGES.get(app.stage,app.stage)}（版本 {app.version}）'}
            msg.status='applied';msg.result=json.dumps(result,ensure_ascii=False)
            if own_session: db.commit()
            return result
        if p.intent=='RESUME_RECEIVED' and app_id is None:
            candidate=Candidate(name=p.candidate_name,education=p.education,skills=p.skills,work_years=p.work_years)
            db.add(candidate); db.flush()
            position=db.scalar(select(Position).where(Position.title==p.position.replace(' ','')))
            if not position:
                position=Position(title=p.position.replace(' ',''));db.add(position);db.flush()
            app=Application(candidate_id=candidate.id,position_id=position.id,stage='SCREENING')
            db.add(app);db.flush()
        else:
            app=db.get(Application, app_id)
            candidate=db.get(Candidate, app.candidate_id)
            if p.intent=='RESUME_RECEIVED':
                candidate.education=candidate.education or p.education
                candidate.skills=candidate.skills or p.skills
                candidate.work_years=candidate.work_years if candidate.work_years is not None else p.work_years
        old=app.stage
        if p.intent=='HR_EVALUATION' and ('建议面试' in (p.evaluation or '') or '进入面试' in (p.evaluation or '')):
            app.stage='ROUND1_PENDING';app.round_no=1
        elif p.intent=='INTERVIEW_SCHEDULE':
            interview=db.scalar(select(Interview).where(Interview.application_id==app.id,Interview.round_no==p.round_no))
            if not interview:
                interview=Interview(application_id=app.id,round_no=p.round_no)
                db.add(interview)
            interview.scheduled_at=p.scheduled_at
            interview.interviewer=p.interviewer
            interview.status='SCHEDULED'
            app.stage=f'ROUND{p.round_no}_SCHEDULED';app.round_no=p.round_no
        elif p.intent=='INTERVIEW_FEEDBACK':
            interview=db.scalar(select(Interview).where(Interview.application_id==app.id,Interview.round_no==p.round_no))
            if not interview: raise ValueError('面试安排记录不存在')
            interview.evaluation=p.evaluation
            interview.result=p.decision
            interview.status='COMPLETED'
            # 如果面试总结此前处于待定，其他反馈入口作出最终决定时同步结论。
            from ..entities import InterviewTranscript, InterviewAssessmentDecision
            latest = db.scalar(select(InterviewTranscript).where(InterviewTranscript.interview_id==interview.id)
                               .order_by(InterviewTranscript.created_at.desc(),InterviewTranscript.id.desc()).limit(1))
            if latest:
                prior = db.scalar(select(InterviewAssessmentDecision).where(InterviewAssessmentDecision.transcript_id==latest.id))
                if prior and prior.status=='DEFERRED' and p.decision in ('PASS','REJECT'):
                    prior.decision=p.decision
                    prior.status='FINAL'
            if p.decision=='PASS':
                app.stage=f'ROUND{p.round_no+1}_PENDING' if p.round_no<3 else 'OFFER_PENDING'
            elif p.decision=='REJECT': app.stage='REJECTED'
            else: app.stage=f'ROUND{p.round_no}_FEEDBACK'
        elif p.intent=='STATUS_UPDATE': app.stage=p.next_stage
        if msg.file_id:
            resume=db.get(Resume,msg.file_id)
            if resume: resume.candidate_id=app.candidate_id
        app.version+=1;app.updated_at=now()
        payload={'intent':p.intent,'candidate_name':candidate.name,'position':db.get(Position,app.position_id).title,
                 'evaluation':p.evaluation,'round_no':p.round_no,'decision':p.decision,
                 'scheduled_at':p.scheduled_at}
        event=Event(application_id=app.id,message_id=message_id,event_type=p.intent,
                    old_stage=old,new_stage=app.stage,data=json.dumps(payload,ensure_ascii=False),operator=sender)
        db.add(event);db.flush()
        sync_data={'event_id':event.id,'at':now().isoformat(timespec='seconds'),
                   'candidate_id':app.candidate_id,'application_id':app.id,'position':payload['position'],
                   'event_type':p.intent,'old_stage':STAGES.get(old,old),
                   'new_stage':STAGES.get(app.stage,app.stage),'round_no':p.round_no or '',
                   'decision':p.decision,'operator':sender}
        db.add(Outbox(event_id=event.id,payload=json.dumps(sync_data,ensure_ascii=False)))
        result={'status':'applied','event_id':event.id,'application_id':app.id,
                'candidate_id':app.candidate_id,'old_stage':old,'new_stage':app.stage,
                'detail':f'{candidate.name}：{STAGES.get(old,old)} → {STAGES.get(app.stage,app.stage)}'}
        msg.status='applied';msg.result=json.dumps(result,ensure_ascii=False)
        if own_session: db.commit()
        return result


def confirm_resume_assessment(db, assessment_id, payload):
    """保存面试官修订的简历评价，并按人工选择更新申请阶段。"""
    from sqlalchemy import update
    from ..entities import ResumeAssessment
    from .management import record_event

    assessment = db.get(ResumeAssessment, assessment_id)
    if not assessment:
        raise ValueError('简历评估不存在')
    prior_status = assessment.status
    # 通过条件更新领取待处理评估，防止重复确认。
    claimed = db.execute(update(ResumeAssessment).where(
        ResumeAssessment.id == assessment_id,
        ResumeAssessment.status.in_(['PENDING', 'DEFERRED'])
    ).values(status='PROCESSING'))
    if claimed.rowcount != 1:
        raise ValueError('简历评估不存在、正在处理或已完成')
    if prior_status == 'DEFERRED' and assessment.application_id and payload.application_id != assessment.application_id:
        raise ValueError('该评估已关联申请，请保留原申请继续处理')
    evaluation = payload.evaluation
    if not (evaluation.candidate_name and evaluation.candidate_name.strip()
            and evaluation.position and evaluation.position.strip() and evaluation.summary.strip()):
        raise ValueError('请填写候选人姓名、岗位和简历评价')
    p = Proposal(intent='RESUME_RECEIVED', candidate_name=evaluation.candidate_name.strip(),
                 position=evaluation.position.strip(), education=evaluation.education,
                 skills=evaluation.skills, work_years=evaluation.work_years,
                 application_id=payload.application_id)
    app_id, reason = validate_proposal(p, db)
    if reason:
        raise ValueError(reason)
    resume = db.get(Resume, assessment.resume_id)
    if resume.candidate_id and (not app_id or db.get(Application, app_id).candidate_id != resume.candidate_id):
        raise ValueError('该简历已关联其他候选人，请使用对应候选人的申请')
    if app_id:
        app = db.get(Application, app_id)
        if app.stage != 'SCREENING':
            raise ValueError('只有简历筛选阶段可以确认简历评估')
        candidate = db.get(Candidate, app.candidate_id)
        if evaluation.education is not None: candidate.education = evaluation.education
        if evaluation.skills is not None: candidate.skills = evaluation.skills
        if evaluation.work_years is not None: candidate.work_years = evaluation.work_years
        # 候选人资料由多个申请共享，其他申请的旧编辑版本也要失效。
        db.execute(update(Application).where(Application.candidate_id == candidate.id, Application.id != app.id)
                   .values(version=Application.version + 1, updated_at=now()))
    else:
        candidate = Candidate(name=p.candidate_name, education=evaluation.education,
                              skills=evaluation.skills, work_years=evaluation.work_years)
        db.add(candidate); db.flush()
        position = db.scalar(select(Position).where(Position.title == p.position.replace(' ','')))
        if not position:
            position = Position(title=p.position.replace(' ','')); db.add(position); db.flush()
        app = Application(candidate_id=candidate.id, position_id=position.id, stage='SCREENING')
        db.add(app); db.flush()
    old_stage = app.stage
    if payload.decision == 'REJECT': app.stage = 'REJECTED'
    elif payload.decision == 'INTERVIEW': app.stage = 'ROUND1_PENDING'; app.round_no = 1
    resume.candidate_id = candidate.id
    app.version += 1; app.updated_at = now()
    assessment.application_id = app.id
    assessment.reviewed_json = evaluation.model_dump_json()
    assessment.decision = payload.decision
    assessment.status = 'DEFERRED' if payload.decision == 'PENDING' else 'FINAL'
    record_event(db, app, 'RESUME_ASSESSMENT_CONFIRMED',
                 {'assessment_id':assessment.id, 'evaluation':evaluation.summary,
                  'decision':payload.decision}, old_stage=old_stage)
    db.commit()
    return {'status':'applied', 'application_id':app.id, 'new_stage':app.stage, 'decision':payload.decision}


def confirm_interview_assessment(db, interview_id, transcript_id, payload):
    """确认最新面试总结，将人工决定、阶段和事件写入同一事务。"""
    from sqlalchemy import update
    from ..entities import InterviewAssessmentDecision, InterviewTranscript
    from .management import record_event

    # 读取决定和当前阶段前先取得 SQLite 写锁，避免并发确认。
    locked = db.execute(update(Interview).where(Interview.id == interview_id).values(id=interview_id))
    if locked.rowcount != 1:
        raise ValueError('面试记录不存在')
    interview = db.get(Interview, interview_id)
    transcript = db.get(InterviewTranscript, transcript_id)
    if not transcript or transcript.interview_id != interview_id:
        raise ValueError('面试逐字稿不存在或不属于该面试')
    # 只能确认最新版本，避免旧逐字稿覆盖新的评估结果。
    latest_id = db.scalar(select(InterviewTranscript.id).where(InterviewTranscript.interview_id == interview_id)
                          .order_by(InterviewTranscript.created_at.desc(), InterviewTranscript.id.desc()).limit(1))
    if latest_id != transcript_id:
        raise ValueError('已有更新的面试逐字稿，请核对最新评估')
    existing = db.scalar(select(InterviewAssessmentDecision).where(InterviewAssessmentDecision.transcript_id == transcript_id))
    if existing and existing.status == 'FINAL':
        raise ValueError('此面试评估已确认完成')
    app = db.get(Application, interview.application_id)
    candidate = db.get(Candidate, app.candidate_id)
    position = db.get(Position, app.position_id)
    evaluation = payload.evaluation
    if not evaluation.summary.strip():
        raise ValueError('请填写面试总结')
    if (evaluation.candidate_name and evaluation.candidate_name.strip() != candidate.name
            or evaluation.position and evaluation.position.replace(' ','') != position.title.replace(' ','')
            or evaluation.round_no and evaluation.round_no != interview.round_no):
        raise ValueError('候选人、岗位或轮次与关联面试不一致')
    p = Proposal(intent='INTERVIEW_FEEDBACK', application_id=app.id, round_no=interview.round_no,
                 evaluation=evaluation.summary, decision=payload.decision)
    _, reason = validate_proposal(p, db)
    if reason:
        raise ValueError(reason)
    old_stage = app.stage
    interview.evaluation = evaluation.summary
    if evaluation.interviewer is not None:
        interview.interviewer = evaluation.interviewer.strip() or None
    interview.result = payload.decision
    interview.status = 'COMPLETED'
    if payload.decision == 'PASS':
        app.stage = f'ROUND{interview.round_no+1}_PENDING' if interview.round_no < 3 else 'OFFER_PENDING'
    elif payload.decision == 'REJECT': app.stage = 'REJECTED'
    else: app.stage = f'ROUND{interview.round_no}_FEEDBACK'
    app.version += 1; app.updated_at = now()
    if existing is None:
        existing = InterviewAssessmentDecision(transcript_id=transcript_id, reviewed_json='', decision='PENDING', status='PENDING')
        db.add(existing)
    existing.reviewed_json = evaluation.model_dump_json()
    existing.decision = payload.decision
    existing.status = 'DEFERRED' if payload.decision == 'PENDING' else 'FINAL'
    record_event(db, app, 'INTERVIEW_ASSESSMENT_CONFIRMED',
                 {'transcript_id':transcript_id, 'round_no':interview.round_no,
                  'evaluation':evaluation.summary, 'decision':payload.decision}, old_stage=old_stage)
    db.commit()
    return {'status':'applied', 'application_id':app.id, 'new_stage':app.stage, 'decision':payload.decision}
