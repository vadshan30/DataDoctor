from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    num_columns: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False, default="unknown")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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

    owner: Mapped["User"] = relationship("User", back_populates="datasets")
    profile: Mapped["DatasetProfile"] = relationship("DatasetProfile", back_populates="dataset", uselist=False)
    quality_report: Mapped["DataQualityReport"] = relationship("DataQualityReport", back_populates="dataset", uselist=False)
    cleaned_datasets: Mapped[list["CleanedDataset"]] = relationship("CleanedDataset", back_populates="dataset", cascade="all, delete-orphan")
    engineered_datasets: Mapped[list["EngineeredDataset"]] = relationship("EngineeredDataset", back_populates="dataset", cascade="all, delete-orphan")
    ml_ready_datasets: Mapped[list["MLReadyDataset"]] = relationship(
        "MLReadyDataset", back_populates="dataset", cascade="all, delete-orphan"
    )
