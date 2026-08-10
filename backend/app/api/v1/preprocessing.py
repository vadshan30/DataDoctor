from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "preprocessing"}


@router.post("/")
def preprocess():
    return {"message": "Preprocessing endpoint — Phase 1 placeholder"}
