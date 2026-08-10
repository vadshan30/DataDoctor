from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "datasets"}


@router.get("/")
def list_datasets():
    return {"message": "Dataset listing endpoint — Phase 1 placeholder"}


@router.post("/upload")
def upload_dataset():
    return {"message": "Dataset upload endpoint — Phase 1 placeholder"}
