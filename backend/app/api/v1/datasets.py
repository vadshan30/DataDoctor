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
from app.models.engineered_dataset import EngineeredDataset
from app.models.ml_ready_dataset import MLReadyDataset
from app.schemas.dataset import DatasetListResponse, DatasetResponse, UploadResponse
from app.schemas.profiling import DatasetProfileResponse
from app.schemas.quality import DataQualityResponse
from app.schemas.cleaning import CleaningResultResponse, CleaningResultListResponse
from app.schemas.feature_engineering import (
    EngineeringResultListResponse,
    EngineeringResultResponse,
)
from app.schemas.ml_preparation import (
    PrepareRequest,
    MLReadyDatasetResponse,
    MLReadyDatasetListResponse,
)
from app.schemas.experiment import (
    ExperimentCreateRequest,
    ExperimentResponse,
    ExperimentListResponse,
)
from app.schemas.prediction import (
    BatchPredictionRequest,
    PredictionRequest,
)
from app.schemas.report import (
    ReportGenerationRequest,
    ReportListResponse,
    ReportResponse,
)
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.models.prediction import PredictionRecord
from app.models.report import Report
from app.services.data_engine.ingester import DataIngestionError, get_shape, read_file
from app.services.data_engine.profiler import generate_profile
from app.services.data_engine.quality import analyze_quality
from app.services.data_engine.cleaner import clean_dataset
from app.services.data_engine.feature_engineer import engineer_features
from app.services.data_engine.preprocessor import (
    MLPreparationError,
    prepare_ml_dataset,
)
from app.services.ml_engine.trainer import ExperimentError, run_experiment
from app.services.ml_engine.evaluator import (
    EvaluationError,
    evaluate_experiment,
    get_evaluation_summary,
    get_model_comparison,
    get_model_evaluation,
)
from app.services.ml_engine.predictor import (
    PredictionError,
    predict_batch,
    predict_single,
    save_prediction_record,
)
from app.services.ml_engine.explainer import get_feature_importance
from app.services.reporting.report_generator import ReportGenerationError, ReportGenerator
from app.utils.helpers import ensure_directories, generate_unique_filename
from app.utils.validators import is_allowed_file, is_within_size_limit

router = APIRouter()


def _get_owned_dataset(db: Session, dataset_id: int, current_user: User) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")
    return dataset


def _report_response(report: Report) -> ReportResponse:
    return ReportResponse.model_validate(report)


@router.post("/{dataset_id}/report", response_model=ReportResponse)
def generate_dataset_report_endpoint(
    dataset_id: int,
    request: ReportGenerationRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    cached_report = (
        db.query(Report)
        .filter(Report.dataset_id == dataset.id, Report.report_type == "dataset")
        .order_by(Report.created_at.desc())
        .first()
    )
    if cached_report and not (request and request.regenerate):
        return _report_response(cached_report)
    try:
        report_data = ReportGenerator(db).generate_dataset_report(dataset.id)
        report = Report(
            name=f"{dataset.name} dataset report",
            report_type="dataset",
            dataset_id=dataset.id,
            owner_id=current_user.id,
            status="completed",
            report_data=report_data.model_dump(mode="json"),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return _report_response(report)
    except ReportGenerationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@router.get("/{dataset_id}/report", response_model=ReportResponse)
def get_latest_dataset_report_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_dataset(db, dataset_id, current_user)
    report = (
        db.query(Report)
        .filter(Report.dataset_id == dataset_id, Report.report_type == "dataset")
        .order_by(Report.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No dataset report found")
    return _report_response(report)


@router.get("/{dataset_id}/reports", response_model=ReportListResponse)
def list_dataset_reports_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_dataset(db, dataset_id, current_user)
    reports = (
        db.query(Report)
        .filter(Report.dataset_id == dataset_id)
        .order_by(Report.created_at.desc())
        .all()
    )
    return ReportListResponse(
        reports=[_report_response(report) for report in reports], total=len(reports)
    )


@router.post(
    "/{dataset_id}/experiments/{experiment_id}/report",
    response_model=ReportResponse,
)
def generate_experiment_report_endpoint(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = _get_owned_dataset(db, dataset_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(Experiment.id == experiment_id, Experiment.dataset_id == dataset_id)
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    try:
        report_data = ReportGenerator(db).generate_experiment_report(dataset.id, experiment.id)
        report = Report(
            name=f"{dataset.name} - {experiment.name} report",
            report_type="experiment",
            dataset_id=dataset.id,
            owner_id=current_user.id,
            experiment_id=experiment.id,
            trained_model_id=experiment.best_model_id,
            status="completed",
            report_data=report_data.model_dump(mode="json"),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return _report_response(report)
    except ReportGenerationError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


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


@router.post("/{dataset_id}/engineer_features", response_model=EngineeringResultResponse)
def engineer_features_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    # Prefer the latest cleaned dataset; fall back to the original file
    cleaned = (
        db.query(CleanedDataset)
        .filter(CleanedDataset.dataset_id == dataset_id)
        .order_by(CleanedDataset.created_at.desc())
        .first()
    )

    if cleaned and os.path.exists(cleaned.cleaned_file_path):
        source_file_path = cleaned.cleaned_file_path
        cleaned_dataset_id = cleaned.id
    elif os.path.exists(dataset.file_path):
        source_file_path = dataset.file_path
        cleaned_dataset_id = None
    else:
        raise HTTPException(status_code=404, detail="Physical file missing")

    try:
        result = engineer_features(source_file_path, settings.UPLOAD_DIR)
    except (DataIngestionError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail="Permission denied accessing file")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Feature engineering failed")

    engineered_record = EngineeredDataset(
        dataset_id=dataset_id,
        cleaned_dataset_id=cleaned_dataset_id,
        original_file_path=result["source_file_path"],
        engineered_file_path=result["engineered_file_path"],
        rows_before=result["rows_before"],
        rows_after=result["rows_after"],
        columns_before=result["columns_before"],
        columns_after=result["columns_after"],
        features_added=result["features_added"],
        features_removed=result["features_removed"],
        feature_names=result["new_feature_names"],
        feature_engineering_operations=result["feature_engineering_operations"],
        engineering_status=result["engineering_status"],
    )
    db.add(engineered_record)
    db.commit()
    db.refresh(engineered_record)

    return EngineeringResultResponse.model_validate(engineered_record)


@router.get("/{dataset_id}/engineered", response_model=EngineeringResultListResponse)
def get_engineered_datasets(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    engineered = (
        db.query(EngineeredDataset)
        .filter(EngineeredDataset.dataset_id == dataset_id)
        .order_by(EngineeredDataset.created_at.desc())
        .all()
    )

    return EngineeringResultListResponse(
        engineered_datasets=[EngineeringResultResponse.model_validate(e) for e in engineered],
        total=len(engineered),
    )


@router.post("/{dataset_id}/prepare", response_model=MLReadyDatasetResponse)
def prepare_ml_dataset_endpoint(
    dataset_id: int,
    request: PrepareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    # Prefer the latest engineered dataset; fall back to cleaned; then original
    engineered = (
        db.query(EngineeredDataset)
        .filter(EngineeredDataset.dataset_id == dataset_id)
        .order_by(EngineeredDataset.created_at.desc())
        .first()
    )

    source_dataset_type = "original"
    cleaned_dataset_id_ref = None
    engineered_dataset_id_ref = None

    if engineered and os.path.exists(engineered.engineered_file_path):
        source_file_path = engineered.engineered_file_path
        engineered_dataset_id_ref = engineered.id
        source_dataset_type = "engineered"
    else:
        cleaned = (
            db.query(CleanedDataset)
            .filter(CleanedDataset.dataset_id == dataset_id)
            .order_by(CleanedDataset.created_at.desc())
            .first()
        )
        if cleaned and os.path.exists(cleaned.cleaned_file_path):
            source_file_path = cleaned.cleaned_file_path
            cleaned_dataset_id_ref = cleaned.id
            source_dataset_type = "cleaned"
        elif os.path.exists(dataset.file_path):
            source_file_path = dataset.file_path
            source_dataset_type = "original"
        else:
            raise HTTPException(status_code=404, detail="Physical file missing")

    try:
        result = prepare_ml_dataset(
            source_file_path=source_file_path,
            upload_dir=settings.UPLOAD_DIR,
            target_column=request.target_column,
            test_size=request.test_size,
            random_state=request.random_state,
        )
    except MLPreparationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except (DataIngestionError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ML preparation failed: {str(e)}")

    ml_ready_record = MLReadyDataset(
        dataset_id=dataset_id,
        engineered_dataset_id=engineered_dataset_id_ref,
        cleaned_dataset_id=cleaned_dataset_id_ref,
        source_dataset_type=source_dataset_type,
        source_file_path=result["source_file_path"],
        ml_ready_file_path=result["ml_ready_file_path"],
        preprocessor_path=result.get("preprocessor_path"),
        target_column=result["target_column"],
        rows_before=result["rows_before"],
        rows_after=result["rows_after"],
        train_rows=result["train_rows"],
        test_rows=result["test_rows"],
        original_feature_count=result["original_feature_count"],
        processed_feature_count=result["processed_feature_count"],
        numeric_columns=result["numeric_columns"],
        categorical_columns=result["categorical_columns"],
        feature_names=result["feature_names"],
        test_size=result["test_size"],
        random_state=result["random_state"],
        preprocessing_operations=result["preprocessing_operations"],
        status=result["status"],
    )
    db.add(ml_ready_record)
    db.commit()
    db.refresh(ml_ready_record)

    return MLReadyDatasetResponse.model_validate(ml_ready_record)


@router.get("/{dataset_id}/prepared", response_model=MLReadyDatasetListResponse)
def get_prepared_datasets(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    prepared = (
        db.query(MLReadyDataset)
        .filter(MLReadyDataset.dataset_id == dataset_id)
        .order_by(MLReadyDataset.created_at.desc())
        .all()
    )

    return MLReadyDatasetListResponse(
        prepared_datasets=[MLReadyDatasetResponse.model_validate(p) for p in prepared],
        total=len(prepared),
    )


@router.get("/{dataset_id}/prepared/latest", response_model=MLReadyDatasetResponse)
def get_latest_prepared_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    latest = (
        db.query(MLReadyDataset)
        .filter(MLReadyDataset.dataset_id == dataset_id)
        .order_by(MLReadyDataset.created_at.desc())
        .first()
    )

    if not latest:
        raise HTTPException(status_code=404, detail="No ML-ready dataset preparation found")

    return MLReadyDatasetResponse.model_validate(latest)


@router.post("/{dataset_id}/experiments")
def create_experiment(
    dataset_id: int,
    request: ExperimentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    ml_ready = (
        db.query(MLReadyDataset)
        .filter(
            MLReadyDataset.id == request.ml_ready_dataset_id,
            MLReadyDataset.dataset_id == dataset_id,
        )
        .first()
    )
    if not ml_ready:
        raise HTTPException(
            status_code=404,
            detail="ML-ready dataset not found for this dataset",
        )

    ensure_directories()

    try:
        result = run_experiment(
            db_session=db,
            dataset_id=dataset_id,
            ml_ready_dataset_id=request.ml_ready_dataset_id,
            experiment_name=request.experiment_name,
            target_column=request.target_column,
            problem_type=request.problem_type,
            test_size=ml_ready.test_size,
            random_state=ml_ready.random_state,
        )
    except ExperimentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except (DataIngestionError, FileNotFoundError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Experiment failed: {str(e)}")

    return result


@router.get("/{dataset_id}/experiments", response_model=ExperimentListResponse)
def list_experiments(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    experiments = (
        db.query(Experiment)
        .filter(Experiment.dataset_id == dataset_id)
        .order_by(Experiment.created_at.desc())
        .all()
    )

    return ExperimentListResponse(
        experiments=[ExperimentResponse.model_validate(e) for e in experiments],
        total=len(experiments),
    )


@router.get("/{dataset_id}/experiments/{experiment_id}")
def get_experiment(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    trained_models = (
        db.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )

    models_list = [
        {
            "model_id": idx,
            "model_name": tm.name,
            "algorithm": tm.algorithm,
            "model_type": tm.model_type,
            "status": tm.status,
            "metrics": tm.metrics,
            "hyperparameters": tm.hyperparameters,
            "training_rows": tm.training_rows,
            "validation_rows": tm.validation_rows,
            "feature_count": tm.feature_count,
        }
        for idx, tm in enumerate(trained_models)
    ]

    return {
        "experiment_id": experiment.id,
        "dataset_id": experiment.dataset_id,
        "ml_ready_dataset_id": experiment.ml_ready_dataset_id,
        "name": experiment.name,
        "experiment_type": experiment.experiment_type,
        "problem_type": experiment.problem_type,
        "target_column": experiment.target_column,
        "test_size": experiment.test_size,
        "random_state": experiment.random_state,
        "status": experiment.status,
        "best_model_id": _find_model_index(trained_models, experiment.best_model_id) if experiment.best_model_id else None,
        "best_metric": experiment.best_metric,
        "best_score": experiment.best_score,
        "error_message": experiment.error_message,
        "created_at": experiment.created_at,
        "updated_at": experiment.updated_at,
        "completed_at": experiment.completed_at,
        "models": models_list,
    }


@router.get("/{dataset_id}/experiments/{experiment_id}/best")
def get_best_model(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this dataset")

    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.best_model_id is None:
        raise HTTPException(status_code=404, detail="No best model selected for this experiment")

    trained_models = (
        db.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment.id)
        .order_by(TrainedModel.id)
        .all()
    )

    best_index = _find_model_index(trained_models, experiment.best_model_id)

    best_model = next(
        (tm for tm in trained_models if tm.id == experiment.best_model_id),
        None,
    )
    if not best_model:
        raise HTTPException(status_code=404, detail="Best model record not found")

    return {
        "experiment_id": experiment.id,
        "model_id": best_index,
        "model_name": best_model.name,
        "algorithm": best_model.algorithm,
        "model_type": best_model.model_type,
        "problem_type": experiment.problem_type,
        "metrics": best_model.metrics,
        "hyperparameters": best_model.hyperparameters,
        "training_rows": best_model.training_rows,
        "validation_rows": best_model.validation_rows,
        "feature_count": best_model.feature_count,
    }


def _find_model_index(trained_models: list[TrainedModel], best_db_id: int | None) -> int | None:
    if best_db_id is None:
        return None
    for idx, tm in enumerate(trained_models):
        if tm.id == best_db_id:
            return idx
    return None


# ---------------------------------------------------------------------------
# Shared ownership helpers for Phase 2.8 (evaluation & prediction)
# ---------------------------------------------------------------------------


def _resolve_dataset_and_experiment(
    db: Session,
    dataset_id: int,
    experiment_id: int,
    current_user: User,
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if dataset.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this dataset",
        )

    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return dataset, experiment


def _resolve_trained_model_by_index(
    db: Session, experiment_id: int, model_index: int
) -> tuple[TrainedModel, list[TrainedModel]]:
    trained_models = (
        db.query(TrainedModel)
        .filter(TrainedModel.experiment_id == experiment_id)
        .order_by(TrainedModel.id)
        .all()
    )
    if model_index < 0 or model_index >= len(trained_models):
        raise HTTPException(status_code=404, detail="Model not found")
    return trained_models[model_index], trained_models


# ---------------------------------------------------------------------------
# Evaluation endpoints
# ---------------------------------------------------------------------------


@router.post("/{dataset_id}/experiments/{experiment_id}/evaluate")
def evaluate_experiment_endpoint(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )
    # Re-fetch with ml_ready_dataset relationship loaded to avoid lazy-load
    # surprises across commits.
    db.refresh(experiment)

    try:
        result = evaluate_experiment(db, experiment, current_user.id)
    except EvaluationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {str(e)}",
        )

    return result


@router.get("/{dataset_id}/experiments/{experiment_id}/evaluation")
def get_experiment_evaluation_endpoint(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )

    try:
        summary = get_evaluation_summary(db, experiment)
    except EvaluationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    if not summary["evaluations"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No evaluation results found. Run POST .../evaluate first.",
        )

    return summary


@router.get("/{dataset_id}/experiments/{experiment_id}/models/{model_id}/evaluation")
def get_model_evaluation_endpoint(
    dataset_id: int,
    experiment_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )

    try:
        result = get_model_evaluation(db, experiment, model_id)
    except EvaluationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )

    return result


@router.get("/{dataset_id}/experiments/{experiment_id}/comparison")
def get_model_comparison_endpoint(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )

    try:
        result = get_model_comparison(db, experiment)
    except EvaluationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    return result


@router.get("/{dataset_id}/experiments/{experiment_id}/models/{model_id}/explainability")
def get_model_explainability_endpoint(
    dataset_id: int,
    experiment_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    trained_model, _ = _resolve_trained_model_by_index(db, experiment_id, model_id)
    ml_ready = trained_model.experiment.ml_ready_dataset

    if not trained_model.model_path or not os.path.exists(trained_model.model_path):
        return {
            "model_name": trained_model.name,
            "algorithm": trained_model.algorithm,
            "model_type": "unknown",
            "features": [],
            "is_available": False,
            "message": "Feature importance is unavailable because the model artifact is missing.",
        }

    try:
        result = get_feature_importance(
            trained_model.model_path,
            trained_model.algorithm,
            ml_ready.feature_names if ml_ready else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Explainability extraction failed: {exc}",
        ) from exc

    if result is None:
        return {
            "model_name": trained_model.name,
            "algorithm": trained_model.algorithm,
            "model_type": "unknown",
            "features": [],
            "is_available": False,
            "message": f"Feature importance is not available for {trained_model.algorithm}.",
        }

    return {
        "model_name": trained_model.name,
        "algorithm": trained_model.algorithm,
        "model_type": result.get("type", "unknown"),
        "features": result.get("features", []),
        "is_available": True,
        "message": None,
    }


# ---------------------------------------------------------------------------
# Prediction endpoints
# ---------------------------------------------------------------------------


@router.post("/{dataset_id}/experiments/{experiment_id}/models/{model_id}/predict")
def predict_endpoint(
    dataset_id: int,
    experiment_id: int,
    model_id: int,
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    tm, _ = _resolve_trained_model_by_index(db, experiment_id, model_id)

    try:
        result = predict_single(db, tm.id, request.features, model_index=model_id)
    except PredictionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}",
        )

    save_prediction_record(
        db,
        experiment_id=experiment_id,
        trained_model_id=tm.id,
        input_data=request.features,
        prediction={"prediction": result["prediction"]},
        model_type=result.get("problem_type"),
    )

    return result


@router.post(
    "/{dataset_id}/experiments/{experiment_id}/models/{model_id}/predict/batch"
)
def predict_batch_endpoint(
    dataset_id: int,
    experiment_id: int,
    model_id: int,
    request: BatchPredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    tm, _ = _resolve_trained_model_by_index(db, experiment_id, model_id)

    try:
        result = predict_batch(db, tm.id, request.rows, model_index=model_id)
    except PredictionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}",
        )

    return result


@router.get(
    "/{dataset_id}/experiments/{experiment_id}/models/{model_id}/predict"
)
def get_model_predictions(
    dataset_id: int,
    experiment_id: int,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    tm, _ = _resolve_trained_model_by_index(db, experiment_id, model_id)

    records = (
        db.query(PredictionRecord)
        .filter(PredictionRecord.experiment_id == experiment_id)
        .filter(PredictionRecord.trained_model_id == tm.id)
        .order_by(PredictionRecord.created_at.desc())
        .all()
    )

    return {
        "model_id": model_id,
        "model_name": tm.name,
        "algorithm": tm.algorithm,
        "total_predictions": len(records),
        "predictions": [
            {
                "id": r.id,
                "trained_model_id": r.trained_model_id,
                "input_data": r.input_data,
                "prediction": r.prediction,
                "model_type": r.model_type,
                "created_at": r.created_at,
            }
            for r in records
        ],
    }


@router.get(
    "/{dataset_id}/experiments/{experiment_id}/predictions"
)
def get_experiment_predictions(
    dataset_id: int,
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _resolve_dataset_and_experiment(db, dataset_id, experiment_id, current_user)
    experiment = (
        db.query(Experiment)
        .filter(
            Experiment.id == experiment_id,
            Experiment.dataset_id == dataset_id,
        )
        .first()
    )

    records = (
        db.query(PredictionRecord)
        .filter(PredictionRecord.experiment_id == experiment_id)
        .order_by(PredictionRecord.created_at.desc())
        .all()
    )

    return {
        "experiment_id": experiment.id,
        "experiment_name": experiment.name,
        "total_predictions": len(records),
        "predictions": [
            {
                "id": r.id,
                "trained_model_id": r.trained_model_id,
                "input_data": r.input_data,
                "prediction": r.prediction,
                "model_type": r.model_type,
                "created_at": r.created_at,
            }
            for r in records
        ],
    }
