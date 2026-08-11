from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    experiment_type: Mapped[str] = mapped_column(String(64), nullable=False)
    problem_type: Mapped[str] = mapped_column(String(32), nullable=False, default="classification")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ml_ready_dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("ml_ready_datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    target_column: Mapped[str | None] = mapped_column(String(255), nullable=True)
    test_size: Mapped[float] = mapped_column(Float, nullable=False, default=0.20)
    random_state: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    best_model_id: Mapped[int | None] = mapped_column(
        ForeignKey("trained_models.id", ondelete="SET NULL"), nullable=True, index=True
    )
    best_metric: Mapped[str | None] = mapped_column(String(64), nullable=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped["User"] = relationship("User", back_populates="experiments")
    dataset: Mapped["Dataset"] = relationship("Dataset")
    ml_ready_dataset: Mapped["MLReadyDataset | None"] = relationship("MLReadyDataset")
    trained_models: Mapped[list["TrainedModel"]] = relationship(
        "TrainedModel", back_populates="experiment",
        foreign_keys="TrainedModel.experiment_id",
        cascade="all, delete-orphan",
    )
    best_model: Mapped["TrainedModel | None"] = relationship(
        "TrainedModel",
        foreign_keys="Experiment.best_model_id",
    )
