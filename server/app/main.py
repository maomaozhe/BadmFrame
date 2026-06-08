import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import engine
from app.services.storage import ensure_dirs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_dirs()
    # Verify database connectivity
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Server started. DB=%s", settings.database_url)
    yield
    await engine.dispose()


app = FastAPI(
    title="BadmFrame API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve exported files
exports_abs = settings.exports_dir.resolve()
exports_abs.mkdir(parents=True, exist_ok=True)
app.mount("/storage/exports", StaticFiles(directory=str(exports_abs)), name="exports")

uploads_abs = settings.uploads_dir.resolve()
uploads_abs.mkdir(parents=True, exist_ok=True)
app.mount("/storage/uploads", StaticFiles(directory=str(uploads_abs)), name="uploads")


@app.get("/health")
async def health():
    return {"status": "ok"}
