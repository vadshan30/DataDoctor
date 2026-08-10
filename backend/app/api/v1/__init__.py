from fastapi import APIRouter

from app.api.v1 import (
    ai,
    auth,
    datasets,
    eda,
    experiments,
    explainability,
    features,
    models,
    predictions,
    preprocessing,
    profiling,
    quality,
    reports,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(datasets.router, prefix="/datasets", tags=["datasets"])
api_router.include_router(profiling.router, prefix="/profiling", tags=["profiling"])
api_router.include_router(quality.router, prefix="/quality", tags=["quality"])
api_router.include_router(eda.router, prefix="/eda", tags=["eda"])
api_router.include_router(preprocessing.router, prefix="/preprocessing", tags=["preprocessing"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(explainability.router, prefix="/explainability", tags=["explainability"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["predictions"])
