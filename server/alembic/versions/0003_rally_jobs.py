"""Add rally_jobs table and content_sha256 to source_videos

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "source_videos",
        sa.Column("content_sha256", sa.String(64), nullable=True),
    )
    op.create_index("ix_source_videos_content_sha256", "source_videos", ["content_sha256"], unique=True)

    op.create_table(
        "rally_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("task_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("params_json", sa.Text, nullable=True),
        sa.Column("result_path", sa.String(1024), nullable=True),
        sa.Column("progress", sa.Float, nullable=False, server_default="0"),
        sa.Column("duration_sec", sa.Float, nullable=False, server_default="0"),
        sa.Column("candidate_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("video_id", sa.String(36), sa.ForeignKey("source_videos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_rally_jobs_task_id", "rally_jobs", ["task_id"], unique=True)
    op.create_index("ix_rally_jobs_project_id", "rally_jobs", ["project_id"])
    op.create_index("ix_rally_jobs_video_id", "rally_jobs", ["video_id"])


def downgrade() -> None:
    op.drop_table("rally_jobs")
    op.drop_index("ix_source_videos_content_sha256", "source_videos")
    op.drop_column("source_videos", "content_sha256")
