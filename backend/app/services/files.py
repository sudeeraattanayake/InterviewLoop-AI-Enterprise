from io import BytesIO
from pathlib import Path
from uuid import uuid4
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader
from docx import Document
from ..config import get_settings

settings = get_settings()
CV_TYPES = {'.pdf': ('application/pdf',), '.docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document',)}
VIDEO_TYPES = {'video/webm', 'video/mp4', 'audio/webm', 'audio/mp4'}


async def receive_file(upload: UploadFile, category: str, limit_mb: int) -> tuple[str, bytes]:
    folder = settings.root / category
    folder.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or '').suffix.lower()
    if category == 'resumes':
        if suffix not in CV_TYPES:
            raise HTTPException(415, 'CV must be PDF or DOCX')
    else:
        if suffix not in ('.webm', '.mp4') or upload.content_type not in VIDEO_TYPES:
            raise HTTPException(415, 'Recording must be WebM or MP4')
    limit = limit_mb * 1024 * 1024
    chunks, size = [], 0
    while data := await upload.read(1024 * 1024):
        size += len(data)
        if size > limit:
            raise HTTPException(413, f'Max upload size: {limit_mb} MB')
        chunks.append(data)
    body = b''.join(chunks)
    if not body:
        raise HTTPException(400, 'Empty file')
    if suffix == '.pdf' and not body.startswith(b'%PDF'):
        raise HTTPException(415, 'File is not a valid PDF')
    if suffix == '.docx' and not body.startswith(b'PK'):
        raise HTTPException(415, 'File is not a valid DOCX')
    if suffix == '.webm' and not body.startswith(bytes.fromhex('1a45dfa3')):
        raise HTTPException(415, 'Invalid WebM recording')
    if suffix == '.mp4' and b'ftyp' not in body[:32]:
        raise HTTPException(415, 'Invalid MP4 recording')
    name = uuid4().hex + suffix
    file_path = folder / name
    file_path.write_bytes(body)
    return str(file_path), body


def extract_resume(filename: str, data: bytes) -> str:
    try:
        if filename.lower().endswith('.pdf'):
            reader = PdfReader(BytesIO(data))
            if len(reader.pages) > 20:
                raise HTTPException(400, 'CV cannot exceed 20 pages')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            doc = Document(BytesIO(data))
            text = '\n'.join(p.text for p in doc.paragraphs)
            text += '\n' + '\n'.join(' '.join(c.text for c in row.cells) for t in doc.tables for row in t.rows)
        text = text.strip()[:35000]
        if len(text) < 50:
            raise HTTPException(422, 'Could not read enough CV text. Please upload a text-based PDF or DOCX.')
        return text
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(422, 'Unable to extract text from this CV')
