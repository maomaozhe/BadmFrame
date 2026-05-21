import asyncio
import logging
from pathlib import Path

from celery import shared_task

from app.config import settings
from app.utils.ffmpeg import run_export

logger = logging.getLogger(__name__)


def _publish_progress(task_id: str, clip_index: int, total: int, status: str) -> None:
    import redis

    try:
        r = redis.from_url(settings.redis_url)
        r.publish(f"export:{task_id}", f"{clip_index}/{total}|{status}")
        r.close()
    except Exception:
        logger.warning("Failed to publish progress", exc_info=True)


@shared_task(bind=True)
def export_clips(self, video_path: str, clips_data: list[dict], task_id: str) -> list[dict]:
    """Export clips via FFmpeg. clips_data is [{id, start_time_sec, end_time_sec}, ...]."""
    results = []
    total = len(clips_data)
    _publish_progress(task_id, 0, total, "started")

    for i, clip in enumerate(clips_data):
        out_dir = settings.exports_dir / task_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{clip['id']}.mp4"

        _publish_progress(task_id, i, total, "exporting")
        try:
            asyncio.run(run_export(
                Path(video_path),
                clip["start_time_sec"],
                clip["end_time_sec"],
                out_path,
            ))
            results.append({"id": clip["id"], "status": "completed", "path": str(out_path)})
        except Exception as e:
            logger.error("Export failed for clip %s: %s", clip["id"], e)
            results.append({"id": clip["id"], "status": "failed", "error": str(e)})

        _publish_progress(task_id, i + 1, total, "completed" if i == total - 1 else "exporting")

    _publish_progress(task_id, total, total, "all_done")
    return results
