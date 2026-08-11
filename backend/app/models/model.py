from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class TrainedModel(Base):
    __tablename__ = "trained_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_type: Mapped[str] = mapped_column(String(128), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)
    hyperparameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    model_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    experiment: Mapped["Experiment"] = relationship(
        "Experiment", back_populates="trained_models",
        foreign_keys="TrainedModel.experiment_id",
    )
    reports: Mapped[list["Report"]] = relationship(
        "Report", back_populates="trained_model", cascade="all, delete-orphan"
    )
