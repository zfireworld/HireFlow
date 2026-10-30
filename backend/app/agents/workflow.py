"""编排聊天消息的提取、业务校验和人工审核中断。"""
from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from ..db import SessionLocal
from .proposal import extract_proposal
from ..schemas import Proposal
from ..services.recruitment import validate_proposal
from ..config import CHECKPOINT_FILE

class WorkflowState(TypedDict, total=False):
    """工作流检查点只保存业务状态，不保存请求中的模型密钥。"""
    content: str
    resume_text: str
    application_id: str | None
    proposal: dict[str, Any]
    reason: str | None
    resolved_app: str | None
    approved: bool

def extract_node(state: WorkflowState):
    """已有提案时直接复用，否则通过配置的模式提取操作。"""
    if state.get('proposal') is not None:
        return {'proposal':state['proposal']}
    proposal = extract_proposal(state.get('content', ''), state.get('resume_text', ''),state.get('application_id'))
    return {'proposal':proposal.model_dump()}

def validate_node(state: WorkflowState):
    """只检查提案能否执行，不修改数据库。"""
    with SessionLocal() as db:
        app_id,reason=validate_proposal(Proposal.model_validate(state['proposal']), db)
    return {'resolved_app':app_id,'reason':reason}

def gate_node(state: WorkflowState):
    """暂停等待人工审核；恢复时节点可能重跑，因此不在此写数据库。"""
    result=interrupt({'reason':state['reason'],'proposal':state['proposal']})
    if not isinstance(result,dict) or not result.get('approved'):
        return {'approved':False}
    return {'approved':True,'proposal':result.get('proposal',state['proposal'])}

def route(state: WorkflowState):
    return 'gate' if state.get('reason') else END

def create_graph(checkpointer: SqliteSaver):
    """校验失败时进入审核节点，通过时直接结束并交由调用方执行。"""
    builder=StateGraph(WorkflowState)
    builder.add_node('extract',extract_node)
    builder.add_node('validate',validate_node)
    builder.add_node('gate',gate_node)
    builder.add_edge(START,'extract')
    builder.add_edge('extract','validate')
    builder.add_conditional_edges('validate',route,{'gate':'gate', END:END})
    builder.add_edge('gate',END)
    return builder.compile(checkpointer=checkpointer)

def create_checkpointer():
    import sqlite3
    conn=sqlite3.connect(str(CHECKPOINT_FILE),check_same_thread=False)
    return conn,SqliteSaver(conn)
