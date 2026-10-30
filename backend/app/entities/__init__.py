"""集中导入所有实体，供启动建表和业务模块使用。"""
from .common import uid, now
from .recruitment import Candidate, Position, Application, Resume, Interview, InterviewTranscript
from .workflow import Message, Event, Review
from .sync import Outbox
from .assessments import ResumeAssessment, InterviewAssessmentDecision
