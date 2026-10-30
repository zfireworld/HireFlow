"""提取上传的简历和面试全文，统一检查文件内容与长度。"""
import io

MAX_TRANSCRIPT_CHARS = 60000


def _pdf_text(contents: bytes, invalid_message: str, page_message: str) -> str:
    if not contents.startswith(b'%PDF-'):
        raise ValueError(invalid_message)
    import fitz
    with fitz.open(stream=contents, filetype='pdf') as doc:
        if len(doc) > 25:
            raise ValueError(page_message)
        return '\n'.join(page.get_text() for page in doc)


def _docx_text(contents: bytes) -> str:
    from docx import Document
    document = Document(io.BytesIO(contents))
    sections = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            sections.append(' | '.join(cell.text for cell in row.cells))
    return '\n'.join(sections)


def read_transcript(contents: bytes, extension: str) -> str:
    """读取 UTF-8 文本、PDF 或 DOCX 面试记录。"""
    if extension == '.txt':
        text = contents.decode('utf-8-sig')
    elif extension == '.pdf':
        text = _pdf_text(contents, '不是有效的 PDF 文件', 'PDF 不得超过 25 页')
    elif extension == '.docx':
        text = _docx_text(contents)
    else:
        raise ValueError('仅支持 TXT、PDF 或 DOCX 面试文字')
    if not text.strip():
        raise ValueError('未提取到文字；扫描版 PDF 请先转为可复制文字的文件')
    if len(text) > MAX_TRANSCRIPT_CHARS:
        raise ValueError(f'面试文字不得超过 {MAX_TRANSCRIPT_CHARS} 字；请精简无关内容后重试')
    return text


def read_resume(contents: bytes, extension: str) -> str:
    """从 UTF-8 文本、PDF 或 DOCX 简历提取文字。"""
    if extension == '.txt':
        return contents.decode('utf-8-sig')
    if extension == '.pdf':
        return _pdf_text(contents, '不是有效的PDF文件', '简历PDF页数不得超过25页')
    if extension == '.docx':
        return _docx_text(contents)
    raise ValueError('仅支持 TXT、PDF 或 DOCX 简历')
