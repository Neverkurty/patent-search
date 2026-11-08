"""Hybrid patent search: keyword (FTS), semantic (pgvector), RRF fusion."""

from __future__ import annotations

import asyncio

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.patent import Patent
from app.services.fips_live_service import fetch_patents_from_fips
from app.services.patent_index_service import upsert_patents
from app.schemas.patent import (
    PatentSummary,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    SearchScores,
)
from app.services.embedding_service import embed_query

RRF_K = 60


def _to_summary(patent: Patent) -> PatentSummary:
    return PatentSummary(
        patent_number=patent.patent_number,
        title=patent.title,
        abstract=patent.abstract,
        ipc_codes=patent.ipc_codes or [],
        publication_date=patent.publication_date,
        status=patent.status or "",
    )


async def _keyword_search(
    session: AsyncSession, query: str, top_k: int
) -> list[tuple[Patent, float]]:
    ts_query = func.websearch_to_tsquery("russian", query)
    rank = func.ts_rank_cd(Patent.search_vector, ts_query).label("rank")
    pattern = f"%{query}%"
    stmt: Select = (
        select(Patent, rank)
        .where(
            or_(
                Patent.search_vector.op("@@")(ts_query),
                Patent.title.ilike(pattern),
                Patent.abstract.ilike(pattern),
                Patent.claims.ilike(pattern),
            )
        )
        .order_by(rank.desc())
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], float(row[1] or 0)) for row in rows]


async def _semantic_search(
    session: AsyncSession, query: str, top_k: int
) -> list[tuple[Patent, float]]:
    vector = embed_query(query)
    distance = Patent.embedding.cosine_distance(vector).label("distance")
    similarity = (1 - distance).label("similarity")
    stmt: Select = (
        select(Patent, similarity)
        .where(Patent.embedding.isnot(None))
        .order_by(distance.asc())
        .limit(top_k)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], float(row[1] or 0)) for row in rows]


def _rrf_fuse(
    ranked_lists: list[list[tuple[Patent, float]]],
) -> list[tuple[Patent, float, float | None, float | None]]:
    """Reciprocal Rank Fusion across ranked result lists."""
    scores: dict[str, dict] = {}

    for source_idx, ranked in enumerate(ranked_lists):
        for rank, (patent, raw_score) in enumerate(ranked, start=1):
            key = patent.patent_number
            if key not in scores:
                scores[key] = {
                    "patent": patent,
                    "rrf": 0.0,
                    "semantic": None,
                    "keyword": None,
                }
            scores[key]["rrf"] += 1.0 / (RRF_K + rank)
            if source_idx == 0:
                scores[key]["semantic"] = raw_score
            else:
                scores[key]["keyword"] = raw_score

    fused = sorted(scores.values(), key=lambda x: x["rrf"], reverse=True)
    return [
        (
            item["patent"],
            item["rrf"],
            item["semantic"],
            item["keyword"],
        )
        for item in fused
    ]


async def _fetch_and_index_live(
    session: AsyncSession, query: str
) -> tuple[str | None, int]:
    settings = get_settings()
    if not settings.fips_live_enabled:
        return None, 0

    records, message = await asyncio.wait_for(
        asyncio.to_thread(
            fetch_patents_from_fips,
            query,
            max_results=settings.fips_live_max_results,
            cache_ttl=settings.fips_search_cache_ttl,
        ),
        timeout=settings.fips_live_timeout_sec,
    )
    if records:
        await upsert_patents(session, records)
    return message, len(records)


async def search_patents(
    session: AsyncSession, request: SearchRequest
) -> SearchResponse:
    top_k = request.top_k
    query = request.query.strip()
    fips_message: str | None = None
    fips_fetched = 0

    if request.live:
        try:
            fips_message, fips_fetched = await _fetch_and_index_live(session, query)
        except TimeoutError:
            fips_message = "Таймаут запроса к ФИПС — показаны результаты из локальной базы"
        except Exception as exc:
            fips_message = f"ФИПС недоступен: {exc}"

    if request.mode == "keyword":
        ranked = await _keyword_search(session, query, top_k)
        results = [
            SearchResultItem(
                patent=_to_summary(p),
                scores=SearchScores(keyword=kw, final=kw),
            )
            for p, kw in ranked
        ]
    elif request.mode == "semantic":
        ranked = await _semantic_search(session, query, top_k)
        results = [
            SearchResultItem(
                patent=_to_summary(p),
                scores=SearchScores(semantic=sem, final=sem),
            )
            for p, sem in ranked
        ]
    else:
        sem_list = await _semantic_search(session, query, top_k * 2)
        kw_list = await _keyword_search(session, query, top_k * 2)
        fused = _rrf_fuse([sem_list, kw_list])[:top_k]
        results = [
            SearchResultItem(
                patent=_to_summary(p),
                scores=SearchScores(
                    semantic=sem,
                    keyword=kw,
                    final=rrf,
                ),
            )
            for p, rrf, sem, kw in fused
        ]

    if request.live:
        if fips_fetched > 0:
            pass
        elif results:
            base = fips_message or "ФИПС: новых документов нет"
            fips_message = f"{base}. Показаны совпадения из локальной базы: {len(results)}"
        elif not fips_message:
            fips_message = "Ничего не найдено ни в ФИПС, ни в локальной базе"

    return SearchResponse(
        query=query,
        mode=request.mode,
        results=results,
        total=len(results),
        live=request.live,
        fips_message=fips_message,
        fips_fetched=fips_fetched,
    )


async def get_patent_by_number(
    session: AsyncSession, patent_number: str
) -> Patent | None:
    stmt = select(Patent).where(Patent.patent_number == patent_number)
    return (await session.execute(stmt)).scalar_one_or_none()
