from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "explainability"}


@router.get("/")
def explain():
    return {"message": "Model explainability endpoint — Phase 1 placeholder"}
