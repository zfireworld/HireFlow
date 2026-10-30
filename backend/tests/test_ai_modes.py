import pytest
from pydantic import ValidationError

from app.schemas import AIConfig, MessageIn, Proposal
from app.services.demo_summary import summarize_demo


def test_demo_interview_summary_is_explicit_and_grounded():
    text = '姓名：张晨\n岗位：Python后端工程师\n一面\n面试官：介绍项目\n候选人：我做了 Python 接口'
    result = summarize_demo(text)
    assert result.candidate_name == '张晨'
    assert result.position == 'Python后端工程师'
    assert result.round_no == 1
    assert result.topics == ['项目经验', 'Python']
    assert '规则演示（非 AI）' in result.summary
    assert result.strengths == [] and result.concerns == []
    assert result.performance == ['候选人原话：我做了 Python 接口']
    assert result.scores == []


def test_demo_summary_recognizes_declared_names_and_warns_on_unknown_speakers():
    text='候选人姓名：顾清禾\n面试官姓名：李工\n李工：介绍项目\n顾清禾：使用 Vue 开发页面'
    result=summarize_demo(text)
    assert '1 条面试官发言、1 条候选人发言' in result.summary
    assert result.performance==['候选人原话：使用 Vue 开发页面']
    unknown=summarize_demo('发言者甲：介绍项目\n发言者乙：做过开发')
    assert '部分发言人未识别' in unknown.summary
    assert unknown.performance==[]


def test_interview_model_scores_require_actual_transcript_evidence(monkeypatch):
    import json
    from app.agents import interview_summary

    captured = {}
    def fake_completion(system, prompt, **kwargs):
        captured.update(system=system, prompt=prompt)
        return json.dumps({'summary':'讨论了缓存方案', 'performance':['候选人描述了缓存方案'],
                           'suggestions':['追问缓存失效'], 'scores':[
                               {'dimension':'项目实践','score':4,'evidence':'我使用 Redis 缓存','reasoning':'描述了实践'},
                               {'dimension':'架构设计','score':5,'evidence':'设计了高可用集群','reasoning':'经验丰富'},
                               {'dimension':'协作','score':4,'evidence':'','reasoning':'缺少依据'}]})
    monkeypatch.setattr(interview_summary, 'complete_json', fake_completion)
    transcript='候选人：我使用 Redis 缓存。'
    result=interview_summary.summarize_interview(transcript,'顾清禾','前端工程师',1,
        AIConfig(mode='custom',model='test',base_url='http://localhost:11434/v1'))
    assert '逐字稿' in captured['system'] and 'scores' in captured['system']
    assert captured['prompt'].endswith(transcript)
    assert result.scores[0].score==4 and result.scores[0].evidence=='我使用 Redis 缓存'
    assert result.scores[1].score is None and result.scores[1].evidence==''
    assert result.scores[2].score is None
    assert result.suggestions==['追问缓存失效']


def test_model_workflows_accept_wrapped_and_fenced_json(monkeypatch):
    from app.agents import interview_summary, proposal
    config=AIConfig(mode='custom',model='test',base_url='http://localhost:11434/v1')
    monkeypatch.setattr(interview_summary,'complete_json',lambda *_args,**_kwargs:
                        '<think>reasoning</think>\n```json\n{"result":{"summary":"讨论了项目"}}\n```')
    summary=interview_summary.summarize_interview('候选人：做过项目','候选人','岗位',1,config)
    assert summary.summary=='讨论了项目'
    monkeypatch.setattr(proposal,'complete_json',lambda *_args,**_kwargs:
                        '```json\n{"data":{"intent":"INFORMATION_QUERY"}}\n```')
    extracted=proposal.extract_proposal('查看进度',application_id='test-id',config=config)
    assert extracted.intent=='INFORMATION_QUERY' and extracted.application_id=='test-id'


def test_custom_model_settings_require_safe_endpoint():
    with pytest.raises(ValidationError):
        AIConfig(mode='custom', model='m', base_url='http://example.com/v1', api_key='secret')
    config = AIConfig(mode='custom', model='local', base_url='http://127.0.0.1:11434/v1')
    assert config.api_key is None
    payload = MessageIn(external_message_id='example-message', ai_config=config)
    assert payload.ai_config.mode == 'custom'
    assert 'secret' not in repr(AIConfig(mode='custom', model='m', base_url='https://example.com/v1', api_key='secret'))


def test_null_model_decision_defaults_to_pending_only():
    assert Proposal.model_validate_json('{"decision": null}').decision == 'PENDING'
    assert Proposal.model_validate_json('{}').decision == 'PENDING'
    assert Proposal.model_validate_json('{"decision": "PASS"}').decision == 'PASS'
    with pytest.raises(ValidationError):
        Proposal.model_validate_json('{"decision": "UNKNOWN"}')


def test_resume_assessment_prompt_includes_full_text():
    from app.prompts.resume import build_user_prompt
    text='简历文字' * 3000 + '末尾内容'
    assert build_user_prompt(text).endswith(text)


def test_resume_agent_accepts_wrapped_result_and_avoids_guessing_years(monkeypatch):
    from app.agents import resume_assessment
    import json
    monkeypatch.setattr(resume_assessment,'complete_json',lambda *_args,**_kwargs:json.dumps({
        'candidate_name':'林初','result':{'position':'前端工程师','work_years':'3-5年',
        'summary':'从事前端开发','skills':['Vue','TypeScript'],'concerns':None}}))
    result=resume_assessment.evaluate_resume('虚构简历',AIConfig(
        mode='custom',model='test',base_url='http://localhost:11434/v1'))
    assert result.candidate_name=='林初' and result.position=='前端工程师'
    assert result.work_years is None and result.skills=='Vue、TypeScript' and result.concerns==[]
