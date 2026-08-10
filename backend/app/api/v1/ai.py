from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "service": "ai"}


@router.post("/ask")
def ask_question():
    return {"message": "AI assistant endpoint — Phase 1 placeholder"}


@router.post("/insights")
def generate_insights():
    return {"message": "AI insights endpoint — Phase 1 placeholder"}
