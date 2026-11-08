"""Index patent records into PostgreSQL (upsert + embeddings + FTS)."""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patent import Patent
from app.services.embedding_service import embed_texts

BATCH_SIZE = 32


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _build_search_text(record: dict) -> str:
    parts = [
        record.get("title", ""),
        record.get("abstract", ""),
        record.get("claims", ""),
        " ".join(record.get("ipc_codes", [])),
        " ".join(record.get("applicants", [])),
        " ".join(record.get("inventors", [])),
    ]
    return " ".join(p for p in parts if p)


async def upsert_patents(
    session: AsyncSession,
    records: list[dict],
    *,
    recreate_embeddings: bool = False,
) -> int:
    """Upsert patent dicts; returns number of records processed."""
    if not records:
        return 0

    loaded = 0
    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start : batch_start + BATCH_SIZE]
        texts = [_build_search_text(r) for r in batch]
        embeddings = embed_texts(texts)

        for record, embedding in zip(batch, embeddings):
            search_text = _build_search_text(record)
            values = {
                "patent_number": record["patent_number"],
                "title": record["title"],
                "abstract": record.get("abstract", ""),
                "claims": record.get("claims", ""),
                "ipc_codes": record.get("ipc_codes", []),
                "application_date": _parse_date(record.get("application_date")),
                "publication_date": _parse_date(record.get("publication_date")),
                "status": record.get("status", ""),
                "applicants": record.get("applicants", []),
                "inventors": record.get("inventors", []),
                "embedding": embedding,
            }
            stmt = insert(Patent).values(**values)
            if recreate_embeddings:
                update_cols = {
                    k: stmt.excluded[k]
                    for k in values
                    if k != "patent_number"
                }
            else:
                update_cols = {
                    k: stmt.excluded[k]
                    for k in values
                    if k not in ("patent_number", "embedding")
                }
                update_cols["embedding"] = stmt.excluded.embedding

            stmt = stmt.on_conflict_do_update(
                index_elements=["patent_number"],
                set_=update_cols,
            )
            await session.execute(stmt)
            await session.execute(
                text(
                    "UPDATE patents SET search_vector = "
                    "to_tsvector('russian', :txt) "
                    "WHERE patent_number = :num"
                ),
                {"txt": search_text, "num": record["patent_number"]},
            )
            loaded += 1

        await session.commit()

    return loaded
