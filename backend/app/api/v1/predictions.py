from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "predictions"}


@router.post("/")
def predict():
    return {"message": "Prediction endpoint — Phase 1 placeholder"}
