from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "BADMFRAME_", "env_file": ".env", "extra": "ignore"}

    database_url: str = "sqlite+aiosqlite:///./storage/badmframe.db"
    redis_url: str = "redis://localhost:6379/0"
    storage_dir: Path = Path("storage")
    max_upload_size: int = 2 * 1024 * 1024 * 1024  # 2 GB
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    export_concurrency: int = 2
    analysis_fps: int = 3
    analysis_width: int = 96
    analysis_height: int = 54
    analysis_extract_audio: bool = True

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def thumbnails_dir(self) -> Path:
        return self.storage_dir / "thumbnails"

    @property
    def exports_dir(self) -> Path:
        return self.storage_dir / "exports"


settings = Settings()
