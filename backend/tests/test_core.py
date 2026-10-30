import json
import uuid
import pytest
from sqlalchemy import select, func
from app.db import SessionLocal
from app.entities import Message, Application, Candidate, Interview, Event, Outbox
from app.schemas import Proposal
from app.services.demo_parser import demo_parse
from app.services.recruitment import STAGES, apply_proposal, validate_proposal

def run_event(p, ext=None):
    with SessionLocal() as db:
        msg=Message(source='web',external_message_id=ext or uuid.uuid4().hex,
                    content='示例消息',sender_id='hr-demo')
        db.add(msg);db.commit()
        msg_id=msg.id
    return apply_proposal(Proposal.model_validate(p), msg_id,'hr-demo'),msg_id

def test_resume_then_rounds_and_offer():
    first,_=run_event({'intent':'RESUME_RECEIVED','candidate_name':'张晨','position':'Python后端工程师'})
    aid=first['application_id']
    assert first['new_stage']=='SCREENING'
    r,_=run_event({'intent':'HR_EVALUATION','application_id':aid,'evaluation':'技术不错，建议面试'})
    assert r['new_stage']=='ROUND1_PENDING'
    r,_=run_event({'intent':'INTERVIEW_SCHEDULE','application_id':aid,'round_no':1,
                    'scheduled_at':'2026-11-02 15:00','interviewer':'李工'})
    assert r['new_stage']=='ROUND1_SCHEDULED'
    r,_=run_event({'intent':'INTERVIEW_FEEDBACK','application_id':aid,'round_no':1,
                   'evaluation':'Python基础扎实，一面通过','decision':'PASS'})
    assert r['new_stage']=='ROUND2_PENDING'
    r,_=run_event({'intent':'INTERVIEW_SCHEDULE','application_id':aid,'round_no':2,
                    'scheduled_at':'2026-11-04 14:00'})
    assert r['new_stage']=='ROUND2_SCHEDULED'
    r,_=run_event({'intent':'INTERVIEW_FEEDBACK','application_id':aid,'round_no':2,
                  'evaluation':'架构扎实','decision':'PASS'})
    assert r['new_stage']=='ROUND3_PENDING'
    r,_=run_event({'intent':'INTERVIEW_SCHEDULE','application_id':aid,'round_no':3,
                    'scheduled_at':'2026-11-06 10:00'})
    r,_=run_event({'intent':'INTERVIEW_FEEDBACK','application_id':aid,'round_no':3,
                  'evaluation':'表现优秀','decision':'PASS'})
    assert r['new_stage']=='OFFER_PENDING'
    r,_=run_event({'intent':'STATUS_UPDATE','application_id':aid,'next_stage':'OFFER_ACCEPTED'})
    assert r['new_stage']=='OFFER_ACCEPTED'
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Interview.id)))==3
        assert db.scalar(select(func.count(Event.id)))==9
        assert db.scalar(select(func.count(Outbox.id)))==9


def test_wrong_round_and_missing_date_go_to_review():
    result,_=run_event({'intent':'RESUME_RECEIVED','candidate_name':'张晨','position':'Python后端工程师'})
    aid=result['application_id']
    with SessionLocal() as db:
        _,reason=validate_proposal(Proposal(intent='INTERVIEW_SCHEDULE',application_id=aid,round_no=2,scheduled_at='2026-11-02 15:00'),db)
        assert reason is not None
        _,reason=validate_proposal(Proposal(intent='INTERVIEW_SCHEDULE',application_id=aid,round_no=1),db)
        assert reason is not None


def test_duplicate_message_does_not_insert_new_event():
    with SessionLocal() as db:
        m=Message(source='web',external_message_id='unique-message-1',content='简历')
        db.add(m);db.commit();mid=m.id
    p=Proposal(intent='RESUME_RECEIVED',candidate_name='张晨',position='Python后端工程师')
    one=apply_proposal(p,mid,'hr-demo')
    two=apply_proposal(p,mid,'hr-demo')
    assert one['event_id']==two['event_id']
    with SessionLocal() as db: assert db.scalar(select(func.count(Event.id)))==1


def test_same_name_two_jobs_does_not_ambiguously_update():
    run_event({'intent':'RESUME_RECEIVED','candidate_name':'张晨','position':'Python后端工程师'})
    run_event({'intent':'RESUME_RECEIVED','candidate_name':'张晨','position':'Java后端工程师'})
    with SessionLocal() as db:
        _,reason=validate_proposal(Proposal(intent='HR_EVALUATION',candidate_name='张晨',evaluation='建议面试'),db)
        assert '多岗位' in reason


def test_demo_rule_extraction_is_explicit():
    p=demo_parse('这是张晨的简历','姓名：张晨\n岗位：Python后端工程师\n技能：Python，SQL')
    assert p.intent=='RESUME_RECEIVED' and p.candidate_name=='张晨'
    assert p.position=='Python后端工程师'
    q=demo_parse('一面结束，技术扎实，一面通过，安排二面','', 'app-id')
    assert q.intent=='INTERVIEW_FEEDBACK' and q.decision=='PASS' and q.round_no==1
    assert q.application_id=='app-id'
    schedule=demo_parse('安排一面，2026-11-02 15:00，面试官李工','', 'app-id')
    assert schedule.candidate_name is None
    assert schedule.intent=='INTERVIEW_SCHEDULE'
    assert schedule.scheduled_at=='2026-11-02 15:00'


def test_selected_application_does_not_treat_interview_suggestion_as_name():
    p=demo_parse('HR初筛评价：经验匹配，建议面试', '', 'app-id')
    assert p.intent=='HR_EVALUATION'
    assert p.candidate_name is None
    assert p.application_id=='app-id'
    named=demo_parse('李四的面试反馈：一面通过', '', 'app-id')
    assert named.candidate_name=='李四'
