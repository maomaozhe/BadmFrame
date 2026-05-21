import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


def ensure_dirs() -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.thumbnails_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)


async def save_upload(file: UploadFile) -> Path:
    ensure_dirs()
    safe_name = Path(file.filename).name if file.filename else "upload.mp4"
    dest = settings.uploads_dir / safe_name
    # avoid overwriting: append suffix if exists
    counter = 1
    while dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest = settings.uploads_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    with open(dest, "wb") as f:
        while chunk := await file.read(8 * 1024 * 1024):  # 8 MB chunks
            f.write(chunk)
    return dest


def cleanup_project_files(project_id: str) -> None:
    """Remove all files associated with a project."""
    for dir_path in (settings.uploads_dir, settings.thumbnails_dir, settings.exports_dir):
        if not dir_path.exists():
            continue
        for child in dir_path.iterdir():
            if child.name.startswith(project_id):
                if child.is_file():
                    child.unlink()
                elif child.is_dir():
                    shutil.rmtree(child)
