from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "models"}


@router.post("/train")
def train_model():
    return {"message": "Model training endpoint — Phase 1 placeholder"}


@router.get("/")
def list_models():
    return {"message": "Model listing endpoint — Phase 1 placeholder"}
