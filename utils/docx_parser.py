import logging
from typing import List

from docx import Document

from utils.pdf_parser import extract_questions_from_text


logger = logging.getLogger(__name__)


def extract_text_from_docx(docx_file) -> str:
    """
    Extract plain text from a DOCX file.
    """
    try:
        docx_file.seek(0)
        document = Document(docx_file)
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        logger.exception("Error extracting text from DOCX")
        return ""


def extract_questions_from_docx(docx_file) -> List[str]:
    """
    Extract likely interview questions from a DOCX file.
    """
    text_content = extract_text_from_docx(docx_file)
    if not text_content.strip():
        return []

    return extract_questions_from_text(text_content)
