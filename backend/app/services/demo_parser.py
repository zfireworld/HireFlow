"""按固定关键词解析演示消息，不调用大模型。"""
import re
from ..schemas import Proposal

def demo_parse(text: str, resume_text: str, selected_app: str | None = None) -> Proposal:
    """用明确的关键词和格式提取演示提案，并非 AI 推理。"""
    combined = text + '\n' + resume_text
    p = Proposal()
    p.application_id = selected_app
    # 优先提取明确标注的姓名。
    m = re.search(r'(?:姓名[：:\s]*)([\u4e00-\u9fff]{2,5})', combined)
    if not m:
        # 已选申请时只从明确的所属短语提取姓名，避免把“建议面试”等操作误认成姓名。
        if selected_app:
            m = re.search(r'(?:这是|收到|关于|^|[，,：:\s])([\u4e00-\u9fff]{2,4})的(?:简历|一面|二面|三面|面试)', text)
        else:
            m = re.search(r'([\u4e00-\u9fff]{2,4})(?:的|\s*)(?:简历|一面|二面|三面|已接受|已入职|面试)', text)
    name=m.group(1) if m else None
    if name in {'安排','进行','准备','完成','开始','关于','可以','明天','今天','新增','确认','评价','通过','结束','收到','面试','处理','建议','一面','二面','三面'}: name=None
    p.candidate_name = name
    for title in ['Python后端工程师','Python 后端工程师','Java后端工程师','Java 后端工程师','前端工程师','产品经理','数据分析师','算法工程师']:
        if title.lower() in combined.lower(): p.position = title.replace(' ', ''); break
    if '简历' in text or resume_text:
        p.intent = 'RESUME_RECEIVED'
        if '建议面试' in text or '进入面试' in text: p.evaluation = text
    elif '查询' in text or '进度' in text and ('什么' in text or '查看' in text or '现在' in text):
        p.intent = 'INFORMATION_QUERY'
    elif any(w in text for w in ['Offer','offer','入职','退出','终止','淘汰']) and not any(w in text for w in ['一面','二面','三面']):
        p.intent = 'STATUS_UPDATE'
        if '接受' in text: p.next_stage = 'OFFER_ACCEPTED'
        elif '入职' in text: p.next_stage = 'HIRED'
        elif '退出' in text: p.next_stage = 'WITHDRAWN'
        elif '淘汰' in text or '终止' in text: p.next_stage = 'REJECTED'
        elif '发放' in text or '发送' in text: p.next_stage = 'OFFER_PENDING'
    elif any(w in text for w in ['一面','二面','三面']):
        p.round_no = 1 if '一面' in text else 2 if '二面' in text else 3
        if '安排' in text and not any(w in text for w in ['通过','不通过','结束','反馈','评价']):
            p.intent = 'INTERVIEW_SCHEDULE'
            date_match = re.search(r'(20\d{2}[-/]\d{1,2}[-/]\d{1,2})[\sT]*(\d{1,2}:\d{2})?', text)
            if date_match and date_match.group(2):
                p.scheduled_at = date_match.group(1).replace('/', '-') + ' ' + date_match.group(2)
            p.interviewer = (re.search(r'面试官[：:\s]*([\u4e00-\u9fff]{2,5})',text) or [None,None])[1]
        else:
            p.intent = 'INTERVIEW_FEEDBACK'
            if '不通过' in text or '未通过' in text or '淘汰' in text: p.decision = 'REJECT'
            elif '通过' in text: p.decision = 'PASS'
            p.evaluation = text
    elif any(w in text for w in ['评价','建议面试','进入面试','初筛']):
        p.intent = 'HR_EVALUATION'
        p.evaluation = text
    m = re.search(r'工作(?:经验|年限)[：:\s]*(\d+)年', combined)
    if m: p.work_years = int(m.group(1))
    m = re.search(r'学历[：:\s]*([^\s,，;；\n]+)', combined)
    if m: p.education = m.group(1)[:100]
    m = re.search(r'技能[：:\s]*([^\n]+)', combined)
    if m: p.skills = m.group(1)[:500]
    return p
