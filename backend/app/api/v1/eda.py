from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "eda"}


@router.get("/")
def run_eda():
    return {"message": "Exploratory data analysis endpoint — Phase 1 placeholder"}
