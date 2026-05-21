import pytest


@pytest.mark.anyio
async def test_create_clip(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/projects/{pid}/clips",
        json={"start_time_sec": 10.0, "end_time_sec": 25.0, "label": "好球", "notes": "扣杀得分"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["start_time_sec"] == 10.0
    assert data["end_time_sec"] == 25.0
    assert data["label"] == "好球"
    assert data["notes"] == "扣杀得分"
    assert data["export_status"] == "none"


@pytest.mark.anyio
async def test_update_clip(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    clip_resp = await async_client.post(
        f"/api/v1/projects/{pid}/clips",
        json={"start_time_sec": 10.0, "end_time_sec": 25.0},
    )
    cid = clip_resp.json()["id"]

    resp = await async_client.put(
        f"/api/v1/projects/{pid}/clips/{cid}",
        json={"start_time_sec": 12.0, "end_time_sec": 20.0, "notes": "调整了范围"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["start_time_sec"] == 12.0
    assert data["end_time_sec"] == 20.0
    assert data["notes"] == "调整了范围"


@pytest.mark.anyio
async def test_delete_clip(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    clip_resp = await async_client.post(
        f"/api/v1/projects/{pid}/clips",
        json={"start_time_sec": 10.0, "end_time_sec": 25.0},
    )
    cid = clip_resp.json()["id"]

    resp = await async_client.delete(f"/api/v1/projects/{pid}/clips/{cid}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_clip_defaults(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    resp = await async_client.post(
        f"/api/v1/projects/{pid}/clips",
        json={"start_time_sec": 0, "end_time_sec": 10},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == ""
    assert data["notes"] == ""
    assert data["anchor_marker_id"] is None
    assert data["export_status"] == "none"
    assert data["exported_file_path"] is None
