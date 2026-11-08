"""Patent ORM model with pgvector embedding and full-text search."""

from datetime import date

from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Date, Index, String, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Patent(Base):
    """Russian patent metadata and search vectors."""

    __tablename__ = "patents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    patent_number: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str] = mapped_column(Text, default="", nullable=False)
    claims: Mapped[str] = mapped_column(Text, default="", nullable=False)
    ipc_codes: Mapped[list[str]] = mapped_column(
        ARRAY(String(32)), default=list, nullable=False
    )
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    applicants: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    inventors: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    embedding = mapped_column(Vector(384), nullable=True)
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    __table_args__ = (
        Index(
            "ix_patents_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index("ix_patents_ipc_codes", "ipc_codes", postgresql_using="gin"),
    )


async def init_db(engine) -> None:
    """Create extension and tables."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
