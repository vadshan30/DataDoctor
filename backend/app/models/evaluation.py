from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trained_model_id: Mapped[int] = mapped_column(
        ForeignKey("trained_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    primary_metric: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    averaging_strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    experiment: Mapped["Experiment"] = relationship("Experiment")
    trained_model: Mapped["TrainedModel"] = relationship("TrainedModel")
