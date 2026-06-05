import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.clip import Clip
from app.models.project import Project
from app.services.export_service import export_clip, cancel_export, export_clip_sequence

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory progress registry for active WebSocket subscriptions
_active_exports: dict[str, asyncio.Queue] = {}


class ExportRequest(BaseModel):
    project_id: str
    clip_ids: list[str]
    merge: bool = False


class ExportTaskRead(BaseModel):
    task_id: str
    status: str
    results: list[dict] = []


@router.post("", response_model=ExportTaskRead, status_code=202)
async def submit_export(body: ExportRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == body.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.source_video:
        raise HTTPException(400, "Project has no source video")

    task_id = str(uuid.uuid4())
    queue: asyncio.Queue = asyncio.Queue()
    _active_exports[task_id] = queue

    asyncio.create_task(_run_export(task_id, project.id, body.clip_ids, body.merge, db, queue))
    return ExportTaskRead(task_id=task_id, status="accepted")


@router.get("/{task_id}", response_model=ExportTaskRead)
async def get_export_status(task_id: str):
    if task_id not in _active_exports:
        raise HTTPException(404, "Export task not found")
    return ExportTaskRead(task_id=task_id, status="processing")


@router.get("/{task_id}/download")
async def download_export(task_id: str, clip_id: str):
    """Redirect to download an exported clip file. Not implemented for inline serving."""
    raise HTTPException(501, "Download via static file serving — see /storage/exports/")


@router.delete("/{task_id}", status_code=204)
async def cancel_export_task(task_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel a running export. Note: in-process exports cannot be preempted."""
    if task_id in _active_exports:
        queue = _active_exports.pop(task_id)
        await queue.put({"status": "cancelled"})
    # Also revert any clips that were set to 'exporting'
    # Best-effort — the task may already be writing
    raise HTTPException(501, "Cancel not yet implemented for in-process exports")


@router.websocket("/{task_id}/ws")
async def export_progress(websocket: WebSocket, task_id: str):
    await websocket.accept()
    queue = _active_exports.get(task_id)
    if not queue:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close()
        return

    try:
        while True:
            msg = await asyncio.wait_for(queue.get(), timeout=30)
            await websocket.send_json(msg)
            if msg.get("status") in ("all_done", "cancelled", "error"):
                break
    except asyncio.TimeoutError:
        await websocket.send_json({"status": "timeout", "message": "No progress updates"})
    except WebSocketDisconnect:
        pass
    finally:
        if task_id in _active_exports:
            del _active_exports[task_id]


async def _run_export(
    task_id: str,
    project_id: str,
    clip_ids: list[str],
    merge: bool,
    db: AsyncSession,
    queue: asyncio.Queue,
):
    results = []
    try:
        if merge:
            clips: list[Clip] = []
            for clip_id in clip_ids:
                result = await db.execute(
                    select(Clip)
                    .options(selectinload(Clip.project).selectinload(Project.source_video))
                    .where(Clip.id == clip_id, Clip.project_id == project_id)
                )
                clip = result.scalar_one_or_none()
                if clip:
                    clips.append(clip)
            if not clips:
                await queue.put({"status": "error", "error": "No clips found"})
                return
            await queue.put({"clip_index": 0, "total": len(clips), "status": "exporting_merged"})
            out_path = await export_clip_sequence(clips, project_id)
            await queue.put({
                "status": "all_done",
                "results": [{"id": "merged", "status": "completed", "path": str(out_path)}],
            })
            return

        for i, clip_id in enumerate(clip_ids):
            result = await db.execute(
                select(Clip)
                .options(selectinload(Clip.project).selectinload(Project.source_video))
                .where(Clip.id == clip_id, Clip.project_id == project_id)
            )
            clip = result.scalar_one_or_none()
            if not clip:
                await queue.put({"clip_id": clip_id, "status": "error", "error": "Clip not found"})
                continue

            await queue.put({"clip_index": i, "total": len(clip_ids), "clip_id": clip_id, "status": "exporting"})
            try:
                await export_clip(clip, project_id, db)
                results.append({"id": clip_id, "status": "completed", "path": clip.exported_file_path})
                await queue.put({"clip_index": i + 1, "total": len(clip_ids), "clip_id": clip_id, "status": "completed"})
            except Exception as e:
                logger.error("Export failed for clip %s: %s", clip_id, e)
                clip.export_status = "failed"
                await db.commit()
                results.append({"id": clip_id, "status": "failed", "error": str(e)})
                await queue.put({"clip_index": i, "total": len(clip_ids), "clip_id": clip_id, "status": "failed", "error": str(e)})

        await queue.put({"status": "all_done", "results": results})
    except Exception as e:
        logger.error("Export task %s crashed: %s", task_id, e)
        await queue.put({"status": "error", "error": str(e)})
