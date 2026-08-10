from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "profiling"}


@router.get("/")
def profile_dataset():
    return {"message": "Dataset profiling endpoint — Phase 1 placeholder"}
