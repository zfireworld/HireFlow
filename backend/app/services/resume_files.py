"""保存已解析的简历文件，由调用方控制数据库事务和失败清理。"""
import hashlib
from pathlib import Path
from ..config import UPLOAD_DIR
from ..entities import Resume, uid
from ..storage.files import FileStorage

storage=FileStorage(UPLOAD_DIR)


def stage_resume(db, filename: str, contents: bytes, extracted_text: str) -> tuple[Resume, Path]:
    """写入文件并暂存记录；返回路径供调用方提交失败时删除。"""
    record = Resume(id=uid(), filename=filename, file_path='',
                    file_hash=hashlib.sha256(contents).hexdigest(), extracted_text=extracted_text)
    path = storage.resolve(UPLOAD_DIR / f'{record.id}{Path(filename).suffix.lower()}')
    try:
        storage.write(path.name, contents)
        record.file_path = str(path)
        db.add(record)
    except Exception:
        storage.remove(path)
        raise
    return record, path
