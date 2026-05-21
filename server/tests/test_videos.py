import pytest

# Video upload tests require FFmpeg installed on the host.
# These are marked as skipped by default; run with --run-ffmpeg to include.


@pytest.mark.anyio
async def test_upload_non_video_rejected(async_client):
    resp = await async_client.post(
        "/api/v1/videos/upload",
        files={"file": ("test.txt", b"not a video", "text/plain")},
    )
    assert resp.status_code == 400
    assert "video" in resp.json()["detail"].lower()


@pytest.mark.anyio
async def test_get_video_not_found(async_client):
    resp = await async_client.get("/api/v1/videos/nonexistent")
    assert resp.status_code == 404
