from fastapi import APIRouter

from backend.app.modules.auth.router import router as auth_router
from backend.app.modules.recommendations.router import router as recommendations_router
from backend.app.modules.saved_lists.router import router as saved_lists_router
from backend.app.modules.trends.router import router as trends_router

api_router = APIRouter()
api_router.include_router(recommendations_router)
api_router.include_router(trends_router)
api_router.include_router(auth_router)
api_router.include_router(saved_lists_router)
