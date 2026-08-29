from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentResponse, ExperimentListResponse

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "experiments"}


@router.get("/", response_model=ExperimentListResponse)
def list_experiments(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Filter by experiment name"),
    status: str | None = Query(default=None, description="Filter by experiment status"),
    dataset_id: int | None = Query(default=None, description="Filter by dataset ID"),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=100, le=500, description="Pagination limit"),
):
    """List all experiments across all datasets with filtering and pagination."""
    query = db.query(Experiment)

    if q:
        query = query.filter(Experiment.name.ilike(f"%{q}%"))

    if status:
        query = query.filter(Experiment.status == status)

    if dataset_id is not None:
        query = query.filter(Experiment.dataset_id == dataset_id)

    total = query.count()
    experiments = query.order_by(Experiment.created_at.desc()).offset(skip).limit(limit).all()

    # Get dataset names for each experiment and build responses
    experiment_responses = []
    for exp in experiments:
        dataset = db.query(Dataset).filter(Dataset.id == exp.dataset_id).first()
        exp_dict = exp.__dict__
        exp_dict["dataset_name"] = dataset.name if dataset else None
        experiment_responses.append(ExperimentResponse.model_validate(exp_dict))

    return ExperimentListResponse(experiments=experiment_responses, total=total)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(experiment_id: int, db: Session = Depends(get_db)):
    """Get a single experiment by ID."""
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    dataset = db.query(Dataset).filter(Dataset.id == experiment.dataset_id).first()
    exp_dict = experiment.__dict__
    exp_dict["dataset_name"] = dataset.name if dataset else None

    return ExperimentResponse.model_validate(exp_dict)


@router.post("/")
def create_experiment():
    return {"message": "Experiment creation endpoint — Phase 1 placeholder"}
