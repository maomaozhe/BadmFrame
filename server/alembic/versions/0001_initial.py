"""Initial schema — projects, source_videos, markers, clips

Revision ID: 0001
Revises:
Create Date: 2026-05-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "source_videos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("file_name", sa.String(512), nullable=False, server_default=""),
        sa.Column("file_path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("duration_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("width", sa.Integer, nullable=False, server_default="0"),
        sa.Column("height", sa.Integer, nullable=False, server_default="0"),
        sa.Column("frame_rate", sa.Float, nullable=False, server_default="0"),
        sa.Column("codec", sa.String(128), nullable=False, server_default=""),
        sa.Column("is_vfr", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("file_size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("import_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), unique=True),
    )
    op.create_table(
        "markers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("label", sa.String(256), nullable=False, server_default=""),
        sa.Column("color", sa.String(32), nullable=False, server_default="yellow"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE")),
    )
    op.create_table(
        "clips",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("start_time_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("end_time_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("label", sa.String(256), nullable=False, server_default=""),
        sa.Column("notes", sa.String(1024), nullable=False, server_default=""),
        sa.Column("anchor_marker_id", sa.String(36), nullable=True),
        sa.Column("export_status", sa.String(32), nullable=False, server_default="none"),
        sa.Column("exported_file_path", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE")),
    )
    op.create_index("ix_source_videos_project_id", "source_videos", ["project_id"])
    op.create_index("ix_markers_project_id", "markers", ["project_id"])
    op.create_index("ix_clips_project_id", "clips", ["project_id"])


def downgrade() -> None:
    op.drop_table("clips")
    op.drop_table("markers")
    op.drop_table("source_videos")
    op.drop_table("projects")
