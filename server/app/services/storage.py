import hashlib
import shutil
from pathlib import Path

from fastapi import UploadFile

from app.config import settings


def ensure_dirs() -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.thumbnails_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)


def sha256_hex(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file on disk."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


async def save_upload(file: UploadFile) -> tuple[Path, str]:
    """Save an uploaded file to disk. Returns (dest_path, content_sha256)."""
    ensure_dirs()
    safe_name = Path(file.filename).name if file.filename else "upload.mp4"
    dest = settings.uploads_dir / safe_name
    counter = 1
    while dest.exists():
        stem = Path(safe_name).stem
        suffix = Path(safe_name).suffix
        dest = settings.uploads_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    h = hashlib.sha256()
    with open(dest, "wb") as f:
        while chunk := await file.read(8 * 1024 * 1024):  # 8 MB chunks
            h.update(chunk)
            f.write(chunk)
    return dest, h.hexdigest()


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
