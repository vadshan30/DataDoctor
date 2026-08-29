from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.dataset import Dataset
from app.models.experiment import Experiment
from app.models.report import Report
from app.schemas.report import ReportResponse, ReportListResponse

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "reports"}


@router.get("/", response_model=ReportListResponse)
def list_reports(
    db: Session = Depends(get_db),
    report_type: str | None = Query(default=None, description="Filter by report type"),
    status: str | None = Query(default=None, description="Filter by status"),
    dataset_id: int | None = Query(default=None, description="Filter by dataset ID"),
    experiment_id: int | None = Query(default=None, description="Filter by experiment ID"),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=100, le=500, description="Pagination limit"),
):
    """List all reports across all datasets and experiments with filtering and pagination."""
    query = db.query(Report)

    if report_type:
        query = query.filter(Report.report_type == report_type)

    if status:
        query = query.filter(Report.status == status)

    if dataset_id is not None:
        query = query.filter(Report.dataset_id == dataset_id)

    if experiment_id is not None:
        query = query.filter(Report.experiment_id == experiment_id)

    reports = query.order_by(Report.created_at.desc()).offset(skip).limit(limit).all()

    report_responses = []
    for report in reports:
        report_dict = report.__dict__
        dataset = db.query(Dataset).filter(Dataset.id == report.dataset_id).first()
        report_dict["dataset_name"] = dataset.name if dataset else None
        if report.experiment_id:
            experiment = db.query(Experiment).filter(Experiment.id == report.experiment_id).first()
            report_dict["experiment_name"] = experiment.name if experiment else None
        else:
            report_dict["experiment_name"] = None
        report_dict["name"] = report.name if report.name else f"{report.report_type} report"
        report_responses.append(ReportResponse.model_validate(report_dict))

    total = len(report_responses)

    return ReportListResponse(reports=report_responses, total=total)


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    db: Session = Depends(get_db),
):
    """Download a generated report as a JSON file."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.report_data:
        filename = report.name if report.name else f"report_{report.id}"
        return JSONResponse(
            content=report.report_data,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}.json"',
            },
        )

    return JSONResponse(
        content={"report_id": report.id, "report_type": report.report_type, "report_data": report.report_data},
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="report_{report.id}.json"',
        },
    )


@router.post("/generate")
def generate_report():
    return {"message": "Report generation endpoint — Phase 1 placeholder"}
