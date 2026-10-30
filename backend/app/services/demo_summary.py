"""生成明确标记的离线规则演示摘要，不伪造 AI 评价或评分。"""
import re
from ..schemas import InterviewSummary


def summarize_demo(text: str) -> InterviewSummary:
    """统计发言并提取候选人原话，供人工核对。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    topics = [name for name, pattern in (
        ('项目经验', r'项目|project'), ('Python', r'python'), ('Java', r'java'),
        ('数据库', r'SQL|数据库|MySQL'), ('沟通协作', r'沟通|协作|团队'))
        if re.search(pattern, text, re.I)]
    name = re.search(r'(?:候选人姓名|姓名)[：:\s]*([^\s，,；;]{2,30})', text)
    position = re.search(r'(?:应聘岗位|岗位)[：:\s]*([^\n，,；;]{2,60})', text)
    interviewer = re.search(r'(?:面试官姓名|主面试官)[：:\s]*([\u4e00-\u9fff]{2,5})', text)
    candidate_name=name.group(1) if name else None
    interviewer_name=interviewer.group(1) if interviewer else None
    candidate_labels={'候选人','应聘者','candidate'}
    interviewer_labels={'面试官','interviewer'}
    if candidate_name and candidate_name!=interviewer_name: candidate_labels.add(candidate_name.casefold())
    if interviewer_name and interviewer_name!=candidate_name: interviewer_labels.add(interviewer_name.casefold())
    questions=0
    excerpts=[]
    for line in lines:
        speaker, separator, content=line.partition('：')
        if not separator: speaker, separator, content=line.partition(':')
        if not separator or not content.strip(): continue
        if speaker.strip().casefold() in interviewer_labels: questions+=1
        elif speaker.strip().casefold() in candidate_labels: excerpts.append(content.strip())
    answers=len(excerpts)
    round_match = re.search(r'第\s*([一二三123])\s*轮|([一二三])面', text)
    round_no = {'一':1,'二':2,'三':3,'1':1,'2':2,'3':3}.get(next((group for group in round_match.groups() if group),'')) if round_match else None
    time = re.search(r'20\d{2}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}', text)
    duration = re.search(r'(?:时长|持续)[：:\s]*(\d+\s*(?:分钟|小时))', text)
    topic_text = '、'.join(topics) if topics else '未识别到预设主题关键词'
    summary = (f'规则演示（非 AI）：记录含 {len(lines)} 行文字、{questions} 条面试官发言、'
               f'{answers} 条候选人发言；识别到的主题为{topic_text}。请结合完整原文人工整理评价。')
    if not questions or not answers:
        summary += '部分发言人未识别，请使用“面试官：”“候选人：”或在文首明确标注姓名。'
    return InterviewSummary(candidate_name=name.group(1) if name else None,
                            position=position.group(1).strip() if position else None,
                            round_no=round_no, interviewer=interviewer.group(1) if interviewer else None,
                            interview_time=time.group().replace('/','-') if time else None,
                            duration=duration.group(1) if duration else None,
                            summary=summary, topics=topics,
                            performance=['候选人原话：' + excerpt[:240] for excerpt in excerpts[:3]],
                            suggestions=['请结合面试原文核实岗位相关表现；规则演示不自动评分'])
