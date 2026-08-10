from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "features"}


@router.post("/engineering")
def feature_engineering():
    return {"message": "Feature engineering endpoint — Phase 1 placeholder"}
