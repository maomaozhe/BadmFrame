import pytest

from app.config import settings


@pytest.mark.anyio
async def test_analysis_history_lists_latest_result(async_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")

    from app.schemas.analysis import AnalysisResultRead, AnalysisSegment
    from app.services import analysis as analysis_service

    project_resp = await async_client.post("/api/v1/projects", json={"name": "Analysis history"})
    project_id = project_resp.json()["id"]

    from app.database import get_db
    from app.main import app
    from app.models.video import SourceVideo

    async for db in app.dependency_overrides[get_db]():
        video = SourceVideo(
            file_name="source.mp4",
            file_path=str(tmp_path / "source.mp4"),
            duration_sec=12,
            project_id=project_id,
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)
        video_id = video.id
        break

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
                AnalysisSegment(start_sec=0, end_sec=2, confidence=0.7, reason=["low_activity"], state="cut"),
                AnalysisSegment(start_sec=2, end_sec=10, confidence=0.9, reason=["high_motion"], state="keep"),
            ],
        )
        analysis_service.save_analysis_result(result)
        return result

    monkeypatch.setattr("app.api.analysis.run_video_analysis", fake_run_video_analysis)

    start_resp = await async_client.post(f"/api/v1/videos/{video_id}/analysis", json={"mode": "balanced"})
    assert start_resp.status_code == 202
    task_id = start_resp.json()["task_id"]

    latest_resp = await async_client.get(f"/api/v1/projects/{project_id}/analysis/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["task_id"] == task_id
    assert latest["status"] == "completed"
    assert latest["keep_segments"] == 1

    history_resp = await async_client.get(f"/api/v1/projects/{project_id}/analysis")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert [job["task_id"] for job in history] == [task_id]
