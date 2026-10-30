import asyncio
import json
import sys
from types import ModuleType, SimpleNamespace

import pytest
import httpx
from openai import BadRequestError

from app.clients import hiflow, model
from app.schemas import AIConfig
from app.services import outbox


def test_compatible_model_json_call_and_non_text_failure(monkeypatch):
    captured = {}
    result = SimpleNamespace(content='{"intent":"UNKNOWN"}')

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            captured['options'] = kwargs

        def invoke(self, messages, **kwargs):
            captured['messages'] = messages
            captured['invoke'] = kwargs
            return result

    class FakeMessage:
        def __init__(self, content):
            self.content = content

    openai = ModuleType('langchain_openai')
    openai.ChatOpenAI = FakeChatOpenAI
    core = ModuleType('langchain_core')
    messages = ModuleType('langchain_core.messages')
    messages.SystemMessage = FakeMessage
    messages.HumanMessage = FakeMessage
    monkeypatch.setitem(sys.modules, 'langchain_openai', openai)
    monkeypatch.setitem(sys.modules, 'langchain_core', core)
    monkeypatch.setitem(sys.modules, 'langchain_core.messages', messages)

    assert model.complete_json('system', 'user', timeout=35) == result.content
    assert captured['options']['timeout'] == 35
    assert [m.content for m in captured['messages']] == ['system', 'user']
    assert captured['invoke']['response_format'] == {'type': 'json_object'}
    model.complete_json('system', 'user', timeout=90, config=AIConfig(
        mode='custom', model='local-model', base_url='http://127.0.0.1:11434/v1'))
    assert captured['options']['model'] == 'local-model'
    assert captured['options']['api_key'] == 'not-needed'
    assert captured['options']['base_url'] == 'http://127.0.0.1:11434/v1'
    model.complete_json('system', 'user', timeout=35, config=AIConfig(
        mode='custom', model='remote-model', base_url='https://example.com/v1', api_key='test-key'))
    assert captured['options']['api_key'] == 'test-key'
    result.content = ['not text']
    with pytest.raises(RuntimeError, match='模型输出非文本'):
        model.complete_json('system', 'user', timeout=90)


def test_hiflow_client_sends_event_id_and_propagates_failure(monkeypatch):
    captured = {}
    response = SimpleNamespace(raise_for_status=lambda: None)

    class FakeAsyncClient:
        def __init__(self, **kwargs):
            captured['options'] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            return False

        async def post(self, url, **kwargs):
            captured['url'] = url
            captured['request'] = kwargs
            return response

    monkeypatch.setattr(hiflow.httpx, 'AsyncClient', FakeAsyncClient)
    monkeypatch.setattr(hiflow, 'HIFLOW_WEBHOOK_URL', 'https://example.invalid/hiflow')
    asyncio.run(hiflow.send_event({'event_type': 'INTERVIEW_FEEDBACK'}, 'event-123'))
    assert captured['options']['timeout'] == 10
    assert captured['request']['headers']['X-HireFlow-Event-ID'] == 'event-123'
    assert captured['request']['json'] == {'event_type': 'INTERVIEW_FEEDBACK'}

    def fail():
        raise ValueError('remote rejected')

    response.raise_for_status = fail
    with pytest.raises(ValueError, match='remote rejected'):
        asyncio.run(hiflow.send_event({}, 'event-123'))


def test_outbox_failure_stays_retryable(monkeypatch):
    job = SimpleNamespace(event_id='event-123', payload=json.dumps({'value': 1}),
                          status='pending', retry_count=0, last_error=None, next_retry_at=None)
    commits = []

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def scalars(self, _query):
            return SimpleNamespace(all=lambda: [job])

        def commit(self):
            commits.append(True)

    async def fail(_payload, _event_id):
        raise ValueError('remote rejected')

    monkeypatch.setattr(outbox, 'HIFLOW_WEBHOOK_URL', 'https://example.invalid/hiflow')
    monkeypatch.setattr(outbox, 'SessionLocal', FakeSession)
    monkeypatch.setattr(outbox, 'send_event', fail)
    asyncio.run(outbox.process_outbox())
    assert job.status == 'failed'
    assert job.retry_count == 1
    assert job.last_error == 'remote rejected'
    assert job.next_retry_at is not None
    assert commits == [True]


def test_model_can_fallback_when_json_mode_is_unsupported(monkeypatch):
    calls=[]
    response=httpx.Response(400,request=httpx.Request('POST','http://localhost/v1/chat/completions'))

    class FakeChatOpenAI:
        def __init__(self, **kwargs): pass
        def invoke(self, messages, **kwargs):
            calls.append(kwargs)
            if kwargs:
                raise BadRequestError('response_format is not supported',response=response,body=None)
            return SimpleNamespace(content=[{'type':'text','text':'{"summary":"ok"}'}])

    class FakeMessage:
        def __init__(self, content): self.content=content

    openai_module=ModuleType('langchain_openai');openai_module.ChatOpenAI=FakeChatOpenAI
    core=ModuleType('langchain_core');messages=ModuleType('langchain_core.messages')
    messages.SystemMessage=FakeMessage;messages.HumanMessage=FakeMessage
    monkeypatch.setitem(sys.modules,'langchain_openai',openai_module)
    monkeypatch.setitem(sys.modules,'langchain_core',core)
    monkeypatch.setitem(sys.modules,'langchain_core.messages',messages)
    assert model.complete_json('system','user',timeout=90)=='{"summary":"ok"}'
    assert calls==[{'response_format':{'type':'json_object'}},{}]


def test_other_bad_requests_are_not_retried_without_json_mode(monkeypatch):
    calls=[]
    response=httpx.Response(400,request=httpx.Request('POST','http://localhost/v1/chat/completions'))

    class FakeChatOpenAI:
        def __init__(self, **kwargs): pass
        def invoke(self, messages, **kwargs):
            calls.append(kwargs)
            raise BadRequestError('model does not exist',response=response,body=None)

    class FakeMessage:
        def __init__(self, content): self.content=content

    openai_module=ModuleType('langchain_openai');openai_module.ChatOpenAI=FakeChatOpenAI
    core=ModuleType('langchain_core');messages=ModuleType('langchain_core.messages')
    messages.SystemMessage=FakeMessage;messages.HumanMessage=FakeMessage
    monkeypatch.setitem(sys.modules,'langchain_openai',openai_module)
    monkeypatch.setitem(sys.modules,'langchain_core',core)
    monkeypatch.setitem(sys.modules,'langchain_core.messages',messages)
    with pytest.raises(BadRequestError): model.complete_json('system','user',timeout=90)
    assert len(calls)==1


def test_connection_check_calls_selected_model_and_checks_text(monkeypatch):
    captured={}
    class FakeClient:
        def __init__(self, **kwargs): captured.update(kwargs)
        def invoke(self, messages):
            captured['messages']=messages
            return SimpleNamespace(content='OK')
    openai_module=ModuleType('langchain_openai');openai_module.ChatOpenAI=FakeClient
    monkeypatch.setitem(sys.modules,'langchain_openai',openai_module)
    config=AIConfig(mode='custom',model='vendor-model',base_url='https://example.com/v1',api_key='private-key')
    model.check_connection(config)
    assert captured['model']=='vendor-model'
    assert captured['base_url']=='https://example.com/v1'
    assert captured['max_retries']==0 and captured['max_tokens']==256
