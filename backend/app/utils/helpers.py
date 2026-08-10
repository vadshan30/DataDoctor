import os
import uuid
from pathlib import Path

from app.core.config import settings


def ensure_directories() -> None:
    for directory in (settings.UPLOAD_DIR, settings.MODEL_DIR, settings.REPORT_DIR):
        Path(directory).mkdir(parents=True, exist_ok=True)


def generate_unique_filename(original_filename: str) -> str:
    _, ext = os.path.splitext(original_filename)
    return f"{uuid.uuid4().hex}{ext}"
