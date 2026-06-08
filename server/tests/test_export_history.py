import asyncio
from pathlib import Path

import pytest

from app.config import settings
from app.utils import ffmpeg


@pytest.mark.anyio
async def test_merged_export_is_persisted_and_listed(async_client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", tmp_path / "storage")

    source_path = tmp_path / "source.mp4"
    source_path.write_bytes(b"video")

    async def fake_concat_export(
        video_path: Path,
        ranges: list[tuple[float, float]],
        output_path: Path,
        preset: str = "auto",
    ) -> None:
        assert video_path == source_path
        assert ranges == [(1.0, 3.0), (4.0, 6.0)]
        assert preset == "auto"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"merged")

    monkeypatch.setattr("app.services.export_service.run_concat_export", fake_concat_export)

    project_resp = await async_client.post("/api/v1/projects", json={"name": "Export history"})
    project_id = project_resp.json()["id"]

    from app.database import get_db
    from app.main import app
    from app.models.video import SourceVideo

    async for db in app.dependency_overrides[get_db]():
        video = SourceVideo(
            file_name="source.mp4",
            file_path=str(source_path),
            duration_sec=10,
            project_id=project_id,
        )
        db.add(video)
        await db.commit()
        break

    clip_a = await async_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={"start_time_sec": 1, "end_time_sec": 3, "label": "A"},
    )
    clip_b = await async_client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={"start_time_sec": 4, "end_time_sec": 6, "label": "B"},
    )

    submit_resp = await async_client.post(
        "/api/v1/exports",
        json={
            "project_id": project_id,
            "clip_ids": [clip_a.json()["id"], clip_b.json()["id"]],
            "mode": "merged",
            "preset": "auto",
        },
    )
    assert submit_resp.status_code == 202
    task_id = submit_resp.json()["task_id"]

    status = None
    for _ in range(20):
        await asyncio.sleep(0.01)
        status_resp = await async_client.get(f"/api/v1/exports/{task_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()
        if status["status"] == "completed":
            break

    assert status is not None
    assert status["status"] == "completed"
    assert status["mode"] == "merged"
    assert status["results"][0]["id"] == "merged"
    assert status["results"][0]["path"].endswith(".mp4")

    history_resp = await async_client.get(f"/api/v1/projects/{project_id}/exports")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert [job["task_id"] for job in history] == [task_id]
    assert history[0]["status"] == "completed"


def test_concat_encoder_prefers_nvenc_when_available(monkeypatch):
    monkeypatch.setattr(ffmpeg, "_encoder_available", lambda encoder: encoder == "h264_nvenc")

    assert ffmpeg.select_concat_video_encoder("auto") == ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "23"]


def test_concat_encoder_falls_back_to_x264(monkeypatch):
    monkeypatch.setattr(ffmpeg, "_encoder_available", lambda encoder: False)

    assert ffmpeg.select_concat_video_encoder("auto") == ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"]
