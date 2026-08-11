from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EngineeredDataset(Base):
    __tablename__ = "engineered_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cleaned_dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("cleaned_datasets.id", ondelete="SET NULL"), nullable=True, index=True
    )
    original_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    engineered_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    rows_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_names: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feature_engineering_operations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    engineering_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="engineered_datasets"
    )
    cleaned_dataset: Mapped["CleanedDataset | None"] = relationship("CleanedDataset")
