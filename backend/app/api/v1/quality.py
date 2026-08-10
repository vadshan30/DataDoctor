from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "quality"}


@router.get("/")
def diagnose_quality():
    return {"message": "Data quality diagnosis endpoint — Phase 1 placeholder"}
