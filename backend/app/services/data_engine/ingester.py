import os

import pandas as pd


class DataIngestionError(Exception):
    pass


def read_file(file_path: str) -> pd.DataFrame:
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    readers = {
        ".csv": _read_csv,
        ".xlsx": _read_xlsx,
        ".xls": _read_xls,
    }

    reader = readers.get(ext)
    if reader is None:
        raise DataIngestionError(f"Unsupported file format: {ext}")

    try:
        return reader(file_path)
    except DataIngestionError:
        raise
    except Exception as e:
        raise DataIngestionError(f"Failed to read file: {e}") from e


def _read_csv(file_path: str) -> pd.DataFrame:
    return pd.read_csv(file_path)


def _read_xlsx(file_path: str) -> pd.DataFrame:
    return pd.read_excel(file_path, engine="openpyxl")


def _read_xls(file_path: str) -> pd.DataFrame:
    return pd.read_excel(file_path, engine="xlrd")


def get_shape(df: pd.DataFrame) -> tuple[int, int]:
    return df.shape[0], df.shape[1]
