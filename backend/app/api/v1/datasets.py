import os
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.dataset import DatasetListResponse, DatasetResponse, UploadResponse
from app.services.data_engine.ingester import DataIngestionError, get_shape, read_file
from app.utils.helpers import ensure_directories, generate_unique_filename
from app.utils.validators import is_allowed_file, is_within_size_limit

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "datasets"}


@router.get("/", response_model=DatasetListResponse)
def list_datasets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    datasets = (
        db.query(Dataset)
        .filter(Dataset.owner_id == current_user.id)
        .order_by(Dataset.created_at.desc())
        .all()
    )
    return DatasetListResponse(
        datasets=[DatasetResponse.model_validate(d) for d in datasets],
        total=len(datasets),
    )


@router.post("/upload", response_model=UploadResponse)
def upload_dataset(
    file: UploadFile = File(...),
    description: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    if not is_allowed_file(file.filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Supported: .csv, .xlsx, .xls",
        )

    ensure_directories()

    unique_name = generate_unique_filename(file.filename)
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    file_size = 0
    with open(file_path, "wb") as buffer:
        while chunk := file.file.read(8192):
            file_size += len(chunk)
            if not is_within_size_limit(file_size):
                buffer.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds maximum allowed size",
                )
            buffer.write(chunk)

    if file_size == 0:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is empty",
        )

    try:
        df = read_file(file_path)
        num_rows, num_columns = get_shape(df)
        if num_rows == 0 or num_columns == 0:
            raise DataIngestionError("Dataset is empty or has no columns")
    except DataIngestionError as e:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    _, ext = os.path.splitext(file.filename)
    file_type = ext.lstrip('.').lower() if ext else "unknown"

    dataset = Dataset(
        name=file.filename,
        description=description,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
        num_rows=num_rows,
        num_columns=num_columns,
        version=1,
        status="uploaded",
        owner_id=current_user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return UploadResponse(
        message="Dataset uploaded successfully",
        dataset=DatasetResponse.model_validate(dataset),
    )
