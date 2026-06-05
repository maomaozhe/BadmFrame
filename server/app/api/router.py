from fastapi import APIRouter

from app.api.analysis import router as analysis_router
from app.api.clips import router as clips_router
from app.api.exports import router as exports_router
from app.api.markers import router as markers_router
from app.api.projects import router as projects_router
from app.api.videos import router as videos_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(analysis_router, tags=["analysis"])
api_router.include_router(videos_router, prefix="/videos", tags=["videos"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(markers_router, prefix="/projects", tags=["markers"])
api_router.include_router(clips_router, prefix="/projects", tags=["clips"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
