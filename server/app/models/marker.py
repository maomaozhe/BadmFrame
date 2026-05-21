from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.project import Project


class Marker(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "markers"

    timestamp_sec: Mapped[float] = mapped_column(Float, default=0)
    label: Mapped[str] = mapped_column(String(256), default="")
    color: Mapped[str] = mapped_column(String(32), default="yellow")

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    project: Mapped["Project"] = relationship(back_populates="markers")
