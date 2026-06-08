"""Persist analysis and export job history

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("params_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("result_path", sa.String(1024), nullable=True),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("duration_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("keep_segments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cut_segments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("source_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_analysis_jobs_task_id", "analysis_jobs", ["task_id"], unique=True)
    op.create_index("ix_analysis_jobs_project_id", "analysis_jobs", ["project_id"])
    op.create_index("ix_analysis_jobs_video_id", "analysis_jobs", ["video_id"])

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("mode", sa.String(32), nullable=False, server_default="separate"),
        sa.Column("preset", sa.String(32), nullable=False, server_default="auto"),
        sa.Column("results_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_export_jobs_task_id", "export_jobs", ["task_id"], unique=True)
    op.create_index("ix_export_jobs_project_id", "export_jobs", ["project_id"])


def downgrade() -> None:
    op.drop_table("export_jobs")
    op.drop_table("analysis_jobs")
