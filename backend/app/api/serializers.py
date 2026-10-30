"""将数据库实体转换为接口使用的字典。"""
import json
from sqlalchemy import select
from ..entities import Candidate, Position, InterviewTranscript, InterviewAssessmentDecision
from ..services.recruitment import STAGES

def nice_date(value): return value.isoformat(timespec='seconds') if value else None

def candidate_data(c):
    return {'id':c.id,'name':c.name,'phone':c.phone,'email':c.email,'education':c.education,'skills':c.skills,'work_years':c.work_years,'created_at':nice_date(c.created_at)}

def app_data(a,db):
    c=db.get(Candidate,a.candidate_id);p=db.get(Position,a.position_id)
    return {'id':a.id,'candidate_id':a.candidate_id,'candidate_name':c.name if c else '',
            'position':p.title if p else '', 'stage':a.stage,'stage_label':STAGES.get(a.stage,a.stage),
            'round_no':a.round_no,'owner':a.owner,'version':a.version,'updated_at':nice_date(a.updated_at)}

def transcript_data(record:InterviewTranscript, db=None):
    """返回原始模型结果及可选的人工修订结果。"""
    review=db.scalar(select(InterviewAssessmentDecision).where(InterviewAssessmentDecision.transcript_id==record.id)) if db else None
    return {'id':record.id,'filename':record.filename,'characters':len(record.transcript_text),
            'text':record.transcript_text,'summary':json.loads(record.summary_json),
            'model':record.model_name,'created_at':nice_date(record.created_at),
            'review':{'decision':review.decision,'status':review.status,'evaluation':json.loads(review.reviewed_json)} if review else None}
