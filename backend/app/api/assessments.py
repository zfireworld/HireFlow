"""生成简历参考评价并处理面试官确认。"""
import json
import logging
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from openai import (APIConnectionError, APIStatusError, APITimeoutError,
                    AuthenticationError, BadRequestError, NotFoundError, RateLimitError)
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.orm import Session
from ..agents.resume_assessment import evaluate_resume
from ..db import get_db
from ..entities import Application, Resume, ResumeAssessment
from ..schemas.assessment import ResumeAssessmentCreate, ResumeDecision
from ..services.recruitment import confirm_resume_assessment
from ..services.model_settings import model_name

router = APIRouter(prefix='/resume-assessments')
logger = logging.getLogger(__name__)


def assessment_data(record, db):
    resume = db.get(Resume, record.resume_id)
    return {'id':record.id, 'file_id':record.resume_id, 'filename':resume.filename,
            'application_id':record.application_id, 'evaluation':json.loads(record.generated_json),
            'reviewed':json.loads(record.reviewed_json) if record.reviewed_json else None,
            'model':record.model_name, 'status':record.status, 'decision':record.decision,
            'created_at':record.created_at.isoformat(timespec='seconds')}


@router.post('', status_code=201)
def create_assessment(payload: ResumeAssessmentCreate, db: Session = Depends(get_db)):
    """保存模型或演示结果，具体招聘决定留给人工确认。"""
    resume = db.get(Resume, payload.file_id)
    if not resume:
        raise HTTPException(404, '简历附件不存在')
    if payload.application_id and not db.get(Application, payload.application_id):
        raise HTTPException(404, '关联申请不存在')
    try:
        evaluation = evaluate_resume(resume.extracted_text, payload.ai_config, payload.context)
    # 只返回可定位的错误信息，避免将模型响应或密钥暴露给页面。
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_context=False, include_url=False)
        if any(error['type']=='json_invalid' for error in errors):
            detail = '模型未返回有效 JSON，请检查模型的 JSON 输出支持或重试'
        else:
            fields = sorted({str(error['loc'][0]) for error in errors if error['loc']})
            detail = '模型输出字段格式不符合要求：' + ('、'.join(fields) if fields else '未知字段')
        logger.warning('resume assessment output validation failed: fields=%s',
                       ','.join(str(error['loc'][0]) for error in errors if error['loc']))
        raise HTTPException(502, detail) from exc
    except APITimeoutError as exc:
        logger.warning('resume assessment model request timed out')
        raise HTTPException(504, '模型请求超时，请确认模型服务运行正常或缩短简历后重试') from exc
    except APIConnectionError as exc:
        logger.warning('resume assessment model connection failed')
        raise HTTPException(502, '无法连接模型服务，请检查接口地址、网络和服务状态') from exc
    except AuthenticationError as exc:
        logger.warning('resume assessment model authentication failed')
        raise HTTPException(502, '模型服务认证失败，请检查 API Key') from exc
    except NotFoundError as exc:
        logger.warning('resume assessment model or endpoint not found')
        raise HTTPException(502, '模型或接口不存在，请检查模型名称和 OpenAI 兼容接口地址') from exc
    except RateLimitError as exc:
        logger.warning('resume assessment model rate limited')
        raise HTTPException(503, '模型服务暂时限流，请稍后重试') from exc
    except BadRequestError as exc:
        logger.warning('resume assessment model rejected request')
        if any(marker in str(exc).lower() for marker in ('context_length_exceeded', 'context length', 'maximum context', 'too many tokens')):
            raise HTTPException(502, '简历超出模型上下文限制，请使用支持更长输入的模型或精简文件') from exc
        raise HTTPException(502, '模型服务拒绝请求，请检查模型名称及服务对 JSON 输出的支持') from exc
    except APIStatusError as exc:
        logger.warning('resume assessment model returned status=%s', exc.status_code)
        raise HTTPException(502, '模型服务返回错误，请检查服务日志') from exc
    except RuntimeError as exc:
        logger.warning('resume assessment runtime error: type=%s', type(exc).__name__)
        raise HTTPException(503, '模型配置不完整或模型返回了非文本内容，请检查模型设置') from exc
    except Exception as exc:
        error_id = uuid4().hex[:8]
        logger.error('resume assessment failed: error_id=%s type=%s', error_id, type(exc).__name__)
        raise HTTPException(502, f'简历评估失败，错误类型 {type(exc).__name__}（编号 {error_id}）') from exc
    model = model_name(payload.ai_config)
    record = ResumeAssessment(resume_id=resume.id, application_id=payload.application_id,
                              generated_json=evaluation.model_dump_json(), model_name=model)
    db.add(record); db.commit()
    return assessment_data(record, db)


@router.get('')
def list_assessments(db: Session = Depends(get_db)):
    records = db.scalars(select(ResumeAssessment).order_by(desc(ResumeAssessment.created_at)).limit(100)).all()
    return [assessment_data(record, db) for record in records]


@router.post('/{assessment_id}/decision')
def decide_assessment(assessment_id: str, payload: ResumeDecision, db: Session = Depends(get_db)):
    try:
        return confirm_resume_assessment(db, assessment_id, payload)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc
