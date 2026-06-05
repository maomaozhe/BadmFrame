import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.config import settings
from app.models.base import Base
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.analysis import AnalysisParams
from app.services.analysis import FeatureWindow, detect_play_windows, params_for_mode


def test_detect_play_windows_outputs_keep_and_cut_segments():
    features = [
        *[FeatureWindow(i, i + 1, 0.1, 0.05) for i in range(0, 4)],
        *[FeatureWindow(i, i + 1, 0.8, 0.5) for i in range(4, 12)],
        *[FeatureWindow(i, i + 1, 0.1, 0.05) for i in range(12, 22)],
        *[FeatureWindow(i, i + 1, 0.78, 0.45) for i in range(22, 30)],
        *[FeatureWindow(i, i + 1, 0.08, 0.03) for i in range(30, 36)],
    ]

    segments = detect_play_windows(features, params_for_mode(AnalysisParams(mode="balanced")), 36)

    assert [segment.state for segment in segments] == ["cut", "keep", "cut", "keep", "cut"]
    keep_segments = [segment for segment in segments if segment.state == "keep"]
    assert keep_segments[0].start_sec <= 4
    assert keep_segments[0].end_sec >= 12
    assert keep_segments[0].confidence > 0.6


def test_detect_play_windows_aggressive_keeps_less_than_conservative():
    features = [
        *[FeatureWindow(i, i + 1, 0.12, 0.05) for i in range(0, 4)],
        *[FeatureWindow(i, i + 1, 0.58, 0.25) for i in range(4, 9)],
        *[FeatureWindow(i, i + 1, 0.12, 0.05) for i in range(9, 16)],
    ]

    conservative = detect_play_windows(features, params_for_mode(AnalysisParams(mode="conservative")), 16)
    aggressive = detect_play_windows(features, params_for_mode(AnalysisParams(mode="aggressive")), 16)

    conservative_keep = sum(s.end_sec - s.start_sec for s in conservative if s.state == "keep")
    aggressive_keep = sum(s.end_sec - s.start_sec for s in aggressive if s.state == "keep")
    assert conservative_keep >= aggressive_keep


@pytest.mark.anyio
async def test_analysis_api_and_apply_auto_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")
    from app.schemas.analysis import AnalysisResultRead, AnalysisSegment
    from app.services import analysis as analysis_service

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    test_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def override_get_db():
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with test_session() as session:
        project = Project(name="Auto")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="sample.mp4",
            file_path=str(tmp_path / "sample.mp4"),
            duration_sec=40,
            width=1920,
            height=1080,
            frame_rate=30,
            codec="h264",
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id
        project_id = project.id

    def fake_run_video_analysis(*, task_id, video_id, project_id, video_path, duration_sec, body):
        result = AnalysisResultRead(
            task_id=task_id,
            video_id=video_id,
            project_id=project_id,
            status="completed",
            params=body,
            progress=1,
            duration_sec=duration_sec,
            segments=[
                AnalysisSegment(start_sec=0, end_sec=5, confidence=0.7, reason=["low_activity"], state="cut"),
                AnalysisSegment(start_sec=5, end_sec=18, confidence=0.9, reason=["high_motion"], state="keep"),
                AnalysisSegment(start_sec=18, end_sec=40, confidence=0.7, reason=["low_activity"], state="cut"),
            ],
        )
        analysis_service.save_analysis_result(result)
        return result

    monkeypatch.setattr("app.api.analysis.run_video_analysis", fake_run_video_analysis)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start_resp = await client.post(
                f"/api/v1/videos/{video_id}/analysis",
                json={"mode": "balanced"},
            )
            assert start_resp.status_code == 202
            task_id = start_resp.json()["task_id"]

            result_resp = await client.get(f"/api/v1/videos/{video_id}/analysis/{task_id}")
            assert result_resp.status_code == 200
            result = result_resp.json()
            assert result["status"] == "completed"
            assert any(segment["state"] == "keep" for segment in result["segments"])
            assert any(segment["state"] == "cut" for segment in result["segments"])

            apply_resp = await client.post(
                f"/api/v1/projects/{project_id}/auto-clips/apply",
                json={"task_id": task_id, "replace_existing_auto": True},
            )
            assert apply_resp.status_code == 200
            assert apply_resp.json()["clips_created"] > 0
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.anyio
async def test_analysis_api_requires_real_video_file(tmp_path, monkeypatch):
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
        project = Project(name="Auto")
        session.add(project)
        await session.flush()
        video = SourceVideo(
            file_name="missing.mp4",
            file_path=str(tmp_path / "missing.mp4"),
            duration_sec=40,
            project_id=project.id,
        )
        session.add(video)
        await session.commit()
        video_id = video.id

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(f"/api/v1/videos/{video_id}/analysis", json={"mode": "balanced"})
            assert resp.status_code == 400
            assert "Source video not found" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
