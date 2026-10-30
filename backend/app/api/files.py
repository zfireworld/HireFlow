"""简历文件上传与解析接口。"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from ..config import MAX_UPLOAD_BYTES
from ..db import get_db
from ..services.documents import read_resume
from ..services.resume_files import stage_resume, storage

router=APIRouter()

async def prepare_resume_upload(file: UploadFile, db: Session):
    """验证大小和内容后暂存文件，事务由调用方提交或回滚。"""
    name=Path(file.filename or 'resume').name[:180]
    ext=Path(name).suffix.lower()
    if ext not in ('.txt','.pdf','.docx'): raise HTTPException(400,'仅支持 UTF-8 TXT 或可提取文字的 PDF、DOCX 简历')
    contents=await file.read(MAX_UPLOAD_BYTES+1)
    if len(contents)>MAX_UPLOAD_BYTES: raise HTTPException(413,'文件不得超过5MB')
    if not contents: raise HTTPException(400,'上传文件为空')
    try:
        extracted=read_resume(contents,ext)
    except Exception as exc:
        raise HTTPException(400,f'文件无法读取：{str(exc)[:120]}')
    if not extracted.strip(): raise HTTPException(422,'未提取到文字：扫描版PDF请转为文本PDF后再上传')
    if len(extracted)>100000: raise HTTPException(413,'简历文字超出长度限制')
    return stage_resume(db, name, contents, extracted)


@router.post('/files',status_code=201)
async def upload_file(file:UploadFile=File(...),db:Session=Depends(get_db)):
    """上传独立简历供后续评估；提交失败时清理文件。"""
    record, save_path = await prepare_resume_upload(file, db)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.remove(save_path)
        raise
    return {'id':record.id,'filename':record.filename,'characters':len(record.extracted_text),'preview':record.extracted_text[:320]}
