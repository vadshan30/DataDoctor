import os

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet"}
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB


def is_allowed_file(filename: str) -> bool:
    _, ext = os.path.splitext(filename)
    return ext.lower() in ALLOWED_EXTENSIONS


def is_within_size_limit(size_bytes: int) -> bool:
    return 0 < size_bytes <= MAX_UPLOAD_SIZE
