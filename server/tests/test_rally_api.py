import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.project import Project
from app.models.video import SourceVideo


@pytest.mark.anyio
async def test_rally_import_and_get_result(tmp_path, monkeypatch):
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
        project = Project(name="Rallies")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="sample.mp4",
            file_path=str(tmp_path / "sample.mp4"),
            duration_sec=80,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id
        project_id = project.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            import_resp = await client.post(
                f"/api/v1/videos/{video_id}/rallies/import",
                json={
                    "video": "sample.mp4",
                    "source": "imported-json",
                    "candidates": [
                        {
                            "id": "rally-002",
                            "startSec": 30,
                            "endSec": 40,
                            "confidence": 0.7,
                        },
                        {
                            "id": "rally-001",
                            "startSec": 10,
                            "endSec": 20,
                            "confidence": 0.8,
                        },
                    ],
                },
            )
            assert import_resp.status_code == 200
            imported = import_resp.json()
            assert imported["status"] == "completed"
            assert imported["video_id"] == video_id
            assert imported["project_id"] == project_id
            assert imported["duration_sec"] == 80
            assert [candidate["id"] for candidate in imported["candidates"]] == ["rally-001", "rally-002"]
            assert imported["candidates"][0]["review_state"] == "pending"

            task_id = imported["task_id"]
            get_resp = await client.get(f"/api/v1/videos/{video_id}/rallies/{task_id}")
            assert get_resp.status_code == 200
            assert get_resp.json()["task_id"] == task_id
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
async def test_rally_import_requires_existing_video(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    test_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/videos/missing-video/rallies/import",
                json={"candidates": []},
            )
            assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
async def test_rally_import_rejects_invalid_candidate_range(tmp_path, monkeypatch):
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
        project = Project(name="Rallies")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="sample.mp4",
            file_path=str(tmp_path / "sample.mp4"),
            duration_sec=80,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/videos/{video_id}/rallies/import",
                json={
                    "candidates": [
                        {"id": "rally-001", "startSec": 20, "endSec": 20, "confidence": 0.8},
                    ],
                },
            )
            assert resp.status_code == 422
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
async def test_apply_rally_candidates_creates_clips_for_accepted_and_adjusted_only(tmp_path, monkeypatch):
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
        project = Project(name="Rallies")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="sample.mp4",
            file_path=str(tmp_path / "sample.mp4"),
            duration_sec=80,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        project_id = project.id
        video_id = video.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            import_resp = await client.post(
                f"/api/v1/videos/{video_id}/rallies/import",
                json={
                    "candidates": [
                        {"id": "rally-001", "startSec": 10, "endSec": 20, "confidence": 0.81, "reviewState": "accepted"},
                        {"id": "rally-002", "startSec": 30, "endSec": 42, "confidence": 0.72, "reviewState": "adjusted"},
                        {"id": "rally-003", "startSec": 45, "endSec": 50, "confidence": 0.5, "reviewState": "rejected"},
                        {"id": "rally-004", "startSec": 60, "endSec": 70, "confidence": 0.6, "reviewState": "pending"},
                    ],
                },
            )
            assert import_resp.status_code == 200
            task_id = import_resp.json()["task_id"]

            apply_resp = await client.post(
                f"/api/v1/projects/{project_id}/rallies/apply",
                json={"task_id": task_id},
            )
            assert apply_resp.status_code == 200
            assert apply_resp.json()["clips_created"] == 2

            project_resp = await client.get(f"/api/v1/projects/{project_id}")
            clips = project_resp.json()["clips"]
            assert [clip["label"] for clip in clips] == ["有效回合 1", "有效回合 2"]
            assert clips[0]["start_time_sec"] == 10
            assert clips[1]["end_time_sec"] == 42
            assert "source:rally-candidate" in clips[0]["notes"]
            assert "confidence:0.81" in clips[0]["notes"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
