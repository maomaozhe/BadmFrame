from pathlib import Path
import subprocess

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.project import Project
from app.models.video import SourceVideo
from app.services import rally_detection as rally_service


@pytest.mark.anyio
async def test_rally_api_starts_background_task_and_exposes_progress(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"video")

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    test_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with test_session() as session:
        project = Project(name="Rally")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="sample.mp4",
            file_path=str(video_file),
            duration_sec=600,
            width=960,
            height=544,
            frame_rate=29,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id
        video_path = video.file_path

    submitted = {}

    def fake_submit_rally_detection(**kwargs):
        submitted.update(kwargs)
        rally_service.save_rally_progress(
            kwargs["task_id"],
            {
                "stage": "queued",
                "progress": 0.01,
                "message": "Queued for TrackNetV3 inference",
            },
        )

    monkeypatch.setattr("app.api.rallies.submit_rally_detection", fake_submit_rally_detection)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_resp = await client.post(f"/api/v1/videos/{video_id}/rallies")

            assert start_resp.status_code == 202
            payload = start_resp.json()
            assert payload["status"] == "running"
            assert payload["task_id"]
            assert submitted["task_id"] == payload["task_id"]
            assert submitted["video_path"] == Path(video_path)

            progress_resp = await client.get(f"/api/v1/videos/{video_id}/rallies/{payload['task_id']}/progress")

            assert progress_resp.status_code == 200
            assert progress_resp.json() == {
                "stage": "queued",
                "progress": 0.01,
                "message": "Queued for TrackNetV3 inference",
            }
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
async def test_rally_api_requires_real_video_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    test_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with test_session() as session:
        project = Project(name="Rally")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="missing.mp4",
            file_path=str(tmp_path / "missing.mp4"),
            duration_sec=600,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/videos/{video_id}/rallies")

            assert resp.status_code == 400
            assert "Source video not found" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_rally_detection_uses_skip_inpaintnet_by_default(tmp_path, monkeypatch):
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"video")
    pipeline_script = tmp_path / "run_pipeline.py"
    pipeline_script.write_text("print('pipeline')", encoding="utf-8")
    config_file = tmp_path / "tracknet.json"
    config_file.write_text("{}", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")
    monkeypatch.setattr(rally_service, "_resolve_pipeline_script", lambda: pipeline_script)
    monkeypatch.setattr(rally_service, "_resolve_tracknet_config", lambda: config_file)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        output_dir = Path(cmd[cmd.index("--output-dir") + 1])
        rally_service.save_rally_progress(
            output_dir.name,
            {"stage": "completed", "progress": 1.0, "message": "Done"},
        )
        (output_dir / "rally_candidates.json").write_text(
            '{"candidates": []}',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(rally_service.subprocess, "run", fake_run)

    result = rally_service.run_rally_detection(
        task_id="task-1",
        video_id="video-1",
        project_id=None,
        video_path=video_file,
    )

    assert result["status"] == "completed"
    assert "--skip-inpaintnet" in captured["cmd"]
