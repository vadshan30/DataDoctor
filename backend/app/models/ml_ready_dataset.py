from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class MLReadyDataset(Base):
    __tablename__ = "ml_ready_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    engineered_dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("engineered_datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cleaned_dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("cleaned_datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_dataset_type: Mapped[str] = mapped_column(String(50), nullable=False, default="original")
    source_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    ml_ready_file_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    target_column: Mapped[str] = mapped_column(String(255), nullable=False)
    rows_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    train_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    test_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    original_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    numeric_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    categorical_columns: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feature_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    test_size: Mapped[float] = mapped_column(nullable=False, default=0.20)
    random_state: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    preprocessing_operations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="ml_ready_datasets")
    engineered_dataset: Mapped["EngineeredDataset | None"] = relationship("EngineeredDataset")
    cleaned_dataset: Mapped["CleanedDataset | None"] = relationship("CleanedDataset")
