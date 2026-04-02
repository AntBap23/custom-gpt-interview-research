import logging
from typing import List

from utils.pdf_parser import extract_questions_from_text


logger = logging.getLogger(__name__)


def extract_text_from_txt(txt_file) -> str:
    """
    Extract text from a TXT file, handling common encodings gracefully.
    """
    try:
        txt_file.seek(0)
        raw_content = txt_file.read()
        if isinstance(raw_content, str):
            return raw_content.strip()

        for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
            try:
                return raw_content.decode(encoding).strip()
            except UnicodeDecodeError:
                continue

        return raw_content.decode("utf-8", errors="ignore").strip()
    except Exception:
        logger.exception("Error extracting text from TXT")
        return ""


def extract_questions_from_txt(txt_file) -> List[str]:
    """
    Extract likely interview questions from a TXT file.
    """
    text_content = extract_text_from_txt(txt_file)
    if not text_content.strip():
        return []

    return extract_questions_from_text(text_content)
