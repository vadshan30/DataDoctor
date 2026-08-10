from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "reports"}


@router.get("/")
def list_reports():
    return {"message": "Report listing endpoint — Phase 1 placeholder"}


@router.post("/generate")
def generate_report():
    return {"message": "Report generation endpoint — Phase 1 placeholder"}
