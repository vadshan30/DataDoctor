from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "experiments"}


@router.get("/")
def list_experiments():
    return {"message": "Experiment listing endpoint — Phase 1 placeholder"}


@router.post("/")
def create_experiment():
    return {"message": "Experiment creation endpoint — Phase 1 placeholder"}
