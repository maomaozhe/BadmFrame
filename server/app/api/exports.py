import asyncio
import io
import json
import logging
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db
from app.models.clip import Clip
from app.models.job import ExportJob
from app.models.project import Project
from app.services.export_service import export_clip, cancel_export, export_clip_sequence
from app.schemas.export import ExportJobRead, ExportRequest, ExportTaskRead

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory progress registry for active WebSocket subscriptions.
_active_exports: dict[str, asyncio.Queue] = {}


@router.post("", response_model=ExportTaskRead, status_code=202)
async def submit_export(
    body: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.id == body.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Project not found")
    if not project.source_video:
        raise HTTPException(400, "Project has no source video")

    task_id = str(uuid.uuid4())
    mode = "merged" if body.merge else body.mode
    job = ExportJob(
        task_id=task_id,
        project_id=project.id,
        status="queued",
        mode=mode,
        preset=body.preset,
        results_json="[]",
    )
    db.add(job)
    await db.commit()

    queue: asyncio.Queue = asyncio.Queue()
    _active_exports[task_id] = queue
    session_factory = async_sessionmaker(db.bind, class_=AsyncSession, expire_on_commit=False)

    background_tasks.add_task(
        _run_export,
        task_id,
        project.id,
        body.clip_ids,
        mode == "merged",
        body.preset,
        session_factory,
        queue,
    )
    return ExportTaskRead(task_id=task_id, status="queued", mode=mode, preset=body.preset)


@router.get("/{task_id}", response_model=ExportTaskRead)
async def get_export_status(task_id: str, db: AsyncSession = Depends(get_db)):
    job = await _get_export_job(task_id, db)
    if not job:
        raise HTTPException(404, "Export task not found")
    return _export_task_read(job)


@router.get("/projects/{project_id}", response_model=list[ExportJobRead])
async def list_project_exports(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Project not found")
    jobs = await db.execute(
        select(ExportJob)
        .where(ExportJob.project_id == project_id)
        .order_by(ExportJob.created_at.desc())
    )
    return [_export_job_read(job) for job in jobs.scalars()]


def _resolve_export_path(raw: str) -> Path:
    """Resolve an export result path to an absolute path.
    New exports store absolute paths; legacy relative paths are resolved vs CWD."""
    p = Path(raw)
    if p.is_absolute():
        return p
    return p.resolve()


@router.get("/{task_id}/download")
async def download_export(task_id: str, clip_id: str | None = None, db: AsyncSession = Depends(get_db)):
    """Download exported file(s). The browser prompts the user for a save path."""
    logger.info("Download requested: task_id=%s clip_id=%s", task_id, clip_id)

    job = await _get_export_job(task_id, db)
    if not job:
        logger.warning("Download 404: task_id=%s not found", task_id)
        raise HTTPException(404, "Export task not found")
    if job.status != "completed":
        logger.warning("Download 400: task_id=%s status=%s", task_id, job.status)
        raise HTTPException(400, f"Export not completed (status: {job.status})")

    results: list[dict] = json.loads(job.results_json or "[]")
    logger.info("Download: task_id=%s raw_results=%s", task_id, job.results_json[:500])

    results = [r for r in results if r.get("status") == "completed" and r.get("path")]
    if not results:
        logger.warning("Download 404: no completed results for task_id=%s", task_id)
        raise HTTPException(404, "No completed export results found")

    if clip_id:
        match = next((r for r in results if r["id"] == clip_id), None)
        if not match:
            logger.warning("Download 404: clip_id=%s not in results for task_id=%s", clip_id, task_id)
            raise HTTPException(404, f"Clip {clip_id} not found in export results")
        file_path = _resolve_export_path(match["path"])
        logger.info("Download: resolved path=%s exists=%s", file_path, file_path.exists())
        if not file_path.exists():
            logger.error("Download 404: file missing: %s", file_path)
            raise HTTPException(404, f"Exported file not found on disk: {file_path}")
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=file_path.name,
        )

    if job.mode == "merged":
        file_path = _resolve_export_path(results[0]["path"])
        logger.info("Download merged: path=%s exists=%s", file_path, file_path.exists())
        if not file_path.exists():
            logger.error("Download 404: merged file missing: %s", file_path)
            raise HTTPException(404, f"Exported file not found on disk: {file_path}")
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=file_path.name,
        )

    # Multiple separate files → zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in results:
            fp = _resolve_export_path(r["path"])
            if fp.exists():
                zf.write(fp, fp.name)
            else:
                logger.warning("Download: skipping missing file: %s", fp)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="export_{task_id[:8]}.zip"'},
    )


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
    preset: str,
    session_factory: async_sessionmaker[AsyncSession],
    queue: asyncio.Queue,
):
    results = []
    try:
        async with session_factory() as db:
            job = await _get_export_job(task_id, db)
            if not job:
                await queue.put({"status": "error", "error": "Export job not found"})
                return
            job.status = "running"
            await db.commit()

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
                    await _mark_export_failed(job, "No clips found", db)
                    await queue.put({"status": "error", "error": "No clips found"})
                    return
                await queue.put({"clip_index": 0, "total": len(clips), "status": "exporting_merged"})
                out_path = await export_clip_sequence(clips, project_id, preset=preset)
                results = [{"id": "merged", "status": "completed", "path": str(out_path)}]
                await _mark_export_completed(job, results, db)
                await queue.put({
                    "status": "all_done",
                    "results": results,
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

            await _mark_export_completed(job, results, db)
            await queue.put({"status": "all_done", "results": results})
    except Exception as e:
        logger.error("Export task %s crashed: %s", task_id, e)
        try:
            async with session_factory() as db:
                job = await _get_export_job(task_id, db)
                if job:
                    await _mark_export_failed(job, str(e), db)
        finally:
            await queue.put({"status": "error", "error": str(e)})


async def _get_export_job(task_id: str, db: AsyncSession) -> ExportJob | None:
    result = await db.execute(select(ExportJob).where(ExportJob.task_id == task_id))
    return result.scalar_one_or_none()


async def _mark_export_completed(job: ExportJob, results: list[dict], db: AsyncSession) -> None:
    job.status = "completed"
    job.results_json = json.dumps(results, ensure_ascii=False)
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def _mark_export_failed(job: ExportJob, error: str, db: AsyncSession) -> None:
    job.status = "failed"
    job.error = error
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()


def _export_task_read(job: ExportJob) -> ExportTaskRead:
    return ExportTaskRead(
        task_id=job.task_id,
        status=job.status,
        mode=job.mode,
        preset=job.preset,
        results=json.loads(job.results_json or "[]"),
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )


def _export_job_read(job: ExportJob) -> ExportJobRead:
    return ExportJobRead(
        task_id=job.task_id,
        project_id=job.project_id,
        status=job.status,
        mode=job.mode,
        preset=job.preset,
        results=json.loads(job.results_json or "[]"),
        error=job.error,
        created_at=job.created_at,
        completed_at=job.completed_at,
    )
