"""汇总各业务路由并统一添加 API 前缀。"""
from fastapi import APIRouter
from . import system, files, messages, applications, interviews, reviews, management, assessments, model

router=APIRouter(prefix='/api/v1')
for module in (system, files, messages, applications, interviews, reviews, management, assessments, model):
    router.include_router(module.router)
