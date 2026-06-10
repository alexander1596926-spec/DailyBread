from fastapi import APIRouter

from backend.routes.api import api_router
from backend.routes.embeds import router as embeds_router

router = APIRouter()
router.include_router(api_router, prefix="/api")
router.include_router(embeds_router, prefix="/api/embeds")
