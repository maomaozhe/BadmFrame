import pytest


@pytest.mark.anyio
async def test_create_marker(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]

    resp = await async_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"timestamp_sec": 12.5, "label": "杀球", "color": "red"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["timestamp_sec"] == 12.5
    assert data["label"] == "杀球"
    assert data["color"] == "red"


@pytest.mark.anyio
async def test_update_marker(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    marker_resp = await async_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"timestamp_sec": 5.0, "label": "", "color": "yellow"},
    )
    mid = marker_resp.json()["id"]

    resp = await async_client.put(
        f"/api/v1/projects/{pid}/markers/{mid}",
        json={"label": "网前失误", "color": "blue"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["label"] == "网前失误"
    assert data["color"] == "blue"


@pytest.mark.anyio
async def test_delete_marker(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    marker_resp = await async_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"timestamp_sec": 5.0, "label": "", "color": "yellow"},
    )
    mid = marker_resp.json()["id"]

    resp = await async_client.delete(f"/api/v1/projects/{pid}/markers/{mid}")
    assert resp.status_code == 204


@pytest.mark.anyio
async def test_marker_defaults(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    resp = await async_client.post(
        f"/api/v1/projects/{pid}/markers",
        json={"timestamp_sec": 30.0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["label"] == ""
    assert data["color"] == "yellow"
