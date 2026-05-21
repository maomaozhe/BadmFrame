from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Clip(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clips"

    start_time_sec: Mapped[float] = mapped_column(Float, default=0)
    end_time_sec: Mapped[float] = mapped_column(Float, default=0)
    label: Mapped[str] = mapped_column(String(256), default="")
    notes: Mapped[str] = mapped_column(String(1024), default="")
    anchor_marker_id: Mapped[str | None] = mapped_column(String(36), nullable=True, default=None)
    export_status: Mapped[str] = mapped_column(String(32), default="none")
    exported_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True, default=None)

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    project: Mapped["Project"] = relationship(back_populates="clips")
