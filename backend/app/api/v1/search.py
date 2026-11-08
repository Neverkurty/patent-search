"""Search API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.patent import SearchRequest, SearchResponse
from app.services.search_service import search_patents

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    """Hybrid, semantic, or keyword patent search."""
    return await search_patents(db, body)
