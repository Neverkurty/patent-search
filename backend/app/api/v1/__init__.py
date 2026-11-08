from fastapi import APIRouter

from app.api.v1 import patents, search

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(search.router, tags=["search"])
api_router.include_router(patents.router, tags=["patents"])
