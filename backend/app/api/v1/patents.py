"""Patent detail endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.patent import PatentDetail
from app.services.search_service import get_patent_by_number

router = APIRouter()


@router.get("/patents/{patent_number}", response_model=PatentDetail)
async def get_patent(
    patent_number: str,
    db: AsyncSession = Depends(get_db),
) -> PatentDetail:
    patent = await get_patent_by_number(db, patent_number)
    if patent is None:
        raise HTTPException(status_code=404, detail="Патент не найден")
    return PatentDetail(
        patent_number=patent.patent_number,
        title=patent.title,
        abstract=patent.abstract,
        claims=patent.claims or "",
        ipc_codes=patent.ipc_codes or [],
        application_date=patent.application_date,
        publication_date=patent.publication_date,
        status=patent.status or "",
        applicants=patent.applicants or [],
        inventors=patent.inventors or [],
    )
