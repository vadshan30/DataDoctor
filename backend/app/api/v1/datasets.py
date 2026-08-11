import os
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.dataset import Dataset
from app.models.user import User
from app.models.dataset_profile import DatasetProfile
from app.models.data_quality_report import DataQualityReport
from app.models.cleaned_dataset import CleanedDataset
from app.schemas.dataset import DatasetListResponse, DatasetResponse, UploadResponse
from app.schemas.profiling import DatasetProfileResponse
from app.schemas.quality import DataQualityResponse
from app.schemas.cleaning import CleaningResultResponse, CleaningResultListResponse
from app.services.data_engine.ingester import DataIngestionError, get_shape, read_file
from app.services.data_engine.profiler import generate_profile
from app.services.data_engine.quality import analyze_quality
from app.services.data_engine.cleaner import clean_dataset
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


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
def get_dataset_profile(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
        
    # Check for existing profile
    profile = db.query(DatasetProfile).filter(DatasetProfile.dataset_id == dataset_id).first()
    if profile:
        return DatasetProfileResponse.model_validate(profile.profile_data)
        
    # If no profile, generate it
    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Physical file missing")
        
    try:
        df = read_file(dataset.file_path)
    except DataIngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))
        
    profile_response = generate_profile(df)
    
    # Save the profile
    new_profile = DatasetProfile(
        dataset_id=dataset_id,
        profile_data=profile_response.model_dump()
    )
    db.add(new_profile)
    db.commit()
    
    return profile_response


@router.get("/{dataset_id}/quality", response_model=DataQualityResponse)
def get_dataset_quality(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
        
    # Check for existing report
    report = db.query(DataQualityReport).filter(DataQualityReport.dataset_id == dataset_id).first()
    if report:
        return DataQualityResponse.model_validate(report.report_data)
        
    # If no report, generate it
    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Physical file missing")
        
    try:
        df = read_file(dataset.file_path)
    except DataIngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))
        
    quality_response = analyze_quality(df, dataset_id=dataset_id)

    # Save the report
    new_report = DataQualityReport(
        dataset_id=dataset_id,
        quality_score=quality_response.quality_score,
        report_data=quality_response.model_dump()
    )
    db.add(new_report)
    db.commit()

    return quality_response


@router.post("/{dataset_id}/clean", response_model=CleaningResultResponse)
def clean_dataset_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Physical file missing")

    try:
        result = clean_dataset(dataset.file_path, settings.UPLOAD_DIR)
    except (DataIngestionError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleaning failed: {str(e)}")

    cleaned_record = CleanedDataset(
        dataset_id=dataset_id,
        original_file_path=result["original_file_path"],
        cleaned_file_path=result["cleaned_file_path"],
        rows_before=result["rows_before"],
        rows_after=result["rows_after"],
        columns_before=result["columns_before"],
        columns_after=result["columns_after"],
        missing_values_handled=result["missing_values_handled"],
        duplicates_removed=result["duplicates_removed"],
        cleaning_status=result["cleaning_status"],
        cleaning_operations=result["cleaning_operations"],
    )
    db.add(cleaned_record)
    db.commit()
    db.refresh(cleaned_record)

    return CleaningResultResponse.model_validate(cleaned_record)


@router.get("/{dataset_id}/cleaned", response_model=CleaningResultListResponse)
def get_cleaned_datasets(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    cleaned = (
        db.query(CleanedDataset)
        .filter(CleanedDataset.dataset_id == dataset_id)
        .order_by(CleanedDataset.created_at.desc())
        .all()
    )

    return CleaningResultListResponse(
        cleaned_datasets=[CleaningResultResponse.model_validate(c) for c in cleaned],
        total=len(cleaned),
    )
