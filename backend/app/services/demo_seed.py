"""为看板和操作演示补齐固定的虚构数据。"""
from uuid import NAMESPACE_URL, uuid5
from sqlalchemy import select
from ..entities import Application, Candidate, Interview, Position


def demo_id(name: str) -> str:
    """用稳定 ID 标识演示记录，使重复启动能够检查已有数据。"""
    return uuid5(NAMESPACE_URL, 'hireflow-demo-v1:' + name).hex


def seed_demo_data(db):
    """只补齐缺失的演示数据，不覆盖已有招聘进展。"""
    examples = [
        ('lin', '林知远', 'Python后端工程师', 'SCREENING', 0, '本科', 'Python、FastAPI、SQL', 3),
        ('gu', '顾清禾', '前端工程师', 'ROUND1_SCHEDULED', 1, '本科', 'Vue、TypeScript、CSS', 4),
        ('cheng', '程亦然', 'Java后端工程师', 'ROUND2_PENDING', 2, '硕士', 'Java、Spring、MySQL', 5),
    ]
    for key, name, title, stage, round_no, education, skills, years in examples:
        candidate_id, app_id = demo_id('candidate:' + key), demo_id('application:' + key)
        position = db.scalar(select(Position).where(Position.title == title))
        if position is None:
            position = Position(title=title)
            db.add(position)
            db.flush()
        if db.get(Candidate, candidate_id) is None:
            db.add(Candidate(id=candidate_id, name=name, education=education, skills=skills, work_years=years))
            db.flush()
        if db.get(Application, app_id) is None:
            db.add(Application(id=app_id, candidate_id=candidate_id, position_id=position.id,
                               stage=stage, round_no=round_no, owner='hr-demo'))
            db.flush()
        interview_id = demo_id('interview:' + key + ':1')
        if key in ('gu', 'cheng') and db.get(Interview, interview_id) is None:
            existing = db.scalar(select(Interview).where(Interview.application_id == app_id, Interview.round_no == 1))
            if existing is None:
                db.add(Interview(id=interview_id, application_id=app_id, round_no=1,
                                 interviewer='李工', scheduled_at='2026-11-02 15:00',
                                 status='SCHEDULED' if key == 'gu' else 'COMPLETED',
                                 result='PENDING' if key == 'gu' else 'PASS',
                                 evaluation=None if key == 'gu' else '项目经历清晰，一面通过'))
    db.commit()


def demo_examples():
    """返回按招聘阶段排列的快捷演示消息。"""
    prefix = '姓名：林知远，岗位：Python后端工程师，'
    return [{'application_id':demo_id('application:lin'), 'stage':stage, 'text':prefix + text}
            for stage, text in [
                ('SCREENING', 'HR初筛评价：三年 Python 后端经验，技能匹配，建议面试'),
                ('ROUND1_PENDING', '安排一面，2026-11-02 15:00，面试官李工'),
                ('ROUND1_SCHEDULED', '一面结束，时间2026-11-02 15:00，面试官李工，Python 基础扎实，一面通过，安排二面'),
                ('ROUND2_PENDING', '安排二面，2026-11-04 14:00，面试官王工'),
                ('ROUND2_SCHEDULED', '二面结束，时间2026-11-04 14:00，面试官王工，架构思路清晰，二面通过，安排三面'),
                ('ROUND3_PENDING', '安排三面，2026-11-06 10:00，面试官赵工'),
                ('ROUND3_SCHEDULED', '三面结束，时间2026-11-06 10:00，面试官赵工，沟通顺畅，三面通过'),
            ]]
