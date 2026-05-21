from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.clip import Clip
    from app.models.marker import Marker
    from app.models.video import SourceVideo


class Project(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    source_video: Mapped["SourceVideo | None"] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="joined"
    )
    markers: Mapped[list["Marker"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    clips: Mapped[list["Clip"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
