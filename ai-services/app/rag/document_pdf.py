"""Bounded PDF text worker. No OCR, JavaScript execution or network."""
import io
import json
import sys

def extract_pdf(raw):
    if len(raw)>5*1024*1024:raise ValueError('SOURCE_TOO_LARGE')
    try:from pypdf import PdfReader
    except ImportError:raise ValueError('PDF_DEPENDENCY_MISSING') from None
    reader=PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted or len(reader.pages)>200:raise ValueError('PDF_REQUIRES_MANUAL_REVIEW')
    parts=[];size=0
    for page in reader.pages:
        text=page.extract_text() or '';size+=len(text)
        if size>500000:raise ValueError('EXTRACTED_TEXT_TOO_LARGE')
        parts.append(text)
    return '\n\n'.join(parts)

if __name__=='__main__':
    try:print(json.dumps({'text':extract_pdf(sys.stdin.buffer.read(5*1024*1024+1))}))
    except Exception as error:
        allowed={'SOURCE_TOO_LARGE','PDF_DEPENDENCY_MISSING','PDF_REQUIRES_MANUAL_REVIEW','EXTRACTED_TEXT_TOO_LARGE'}
        print(json.dumps({'error':str(error) if str(error) in allowed else 'PDF_INVALID_OR_UNREADABLE'}))
