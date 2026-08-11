from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class CleanedDataset(Base):
    __tablename__ = "cleaned_datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    cleaned_file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    rows_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rows_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns_before: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    columns_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_values_handled: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates_removed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleaning_status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    cleaning_operations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="cleaned_datasets")
