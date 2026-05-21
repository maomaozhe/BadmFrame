import pytest


@pytest.mark.anyio
async def test_create_project(async_client):
    resp = await async_client.post("/api/v1/projects", json={"name": "测试项目"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "测试项目"
    assert data["id"]
    assert data["markers"] == []
    assert data["clips"] == []
    assert data["source_video"] is None


@pytest.mark.anyio
async def test_list_projects(async_client):
    await async_client.post("/api/v1/projects", json={"name": "P1"})
    await async_client.post("/api/v1/projects", json={"name": "P2"})
    resp = await async_client.get("/api/v1/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.anyio
async def test_get_project(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    resp = await async_client.get(f"/api/v1/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "P"


@pytest.mark.anyio
async def test_update_project(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "旧名称"})
    pid = create_resp.json()["id"]
    resp = await async_client.put(f"/api/v1/projects/{pid}", json={"name": "新名称"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "新名称"


@pytest.mark.anyio
async def test_delete_project(async_client):
    create_resp = await async_client.post("/api/v1/projects", json={"name": "P"})
    pid = create_resp.json()["id"]
    resp = await async_client.delete(f"/api/v1/projects/{pid}")
    assert resp.status_code == 204
    resp = await async_client.get(f"/api/v1/projects/{pid}")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_project_not_found(async_client):
    resp = await async_client.get("/api/v1/projects/nonexistent")
    assert resp.status_code == 404
