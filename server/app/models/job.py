from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AnalysisJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analysis_jobs"

    task_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    result_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0)
    duration_sec: Mapped[float] = mapped_column(Float, default=0)
    keep_segments: Mapped[int] = mapped_column(Integer, default=0)
    cut_segments: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    video_id: Mapped[str] = mapped_column(ForeignKey("source_videos.id", ondelete="CASCADE"))


class ExportJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "export_jobs"

    task_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    mode: Mapped[str] = mapped_column(String(32), default="separate")
    preset: Mapped[str] = mapped_column(String(32), default="auto")
    results_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
