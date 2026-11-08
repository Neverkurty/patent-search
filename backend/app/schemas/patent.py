"""Pydantic schemas aligned with contracts/patent.schema.json."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class PatentSummary(BaseModel):
    patent_number: str
    title: str
    abstract: str
    ipc_codes: list[str] = Field(default_factory=list)
    publication_date: date | None = None
    status: str = ""


class PatentDetail(PatentSummary):
    claims: str = ""
    application_date: date | None = None
    applicants: list[str] = Field(default_factory=list)
    inventors: list[str] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["hybrid", "semantic", "keyword"] = "hybrid"
    live: bool = Field(
        default=True,
        description="Подгружать свежие результаты с ФИПС перед поиском по БД",
    )


class SearchScores(BaseModel):
    semantic: float | None = None
    keyword: float | None = None
    final: float


class SearchResultItem(BaseModel):
    patent: PatentSummary
    scores: SearchScores


class SearchResponse(BaseModel):
    query: str
    mode: str
    results: list[SearchResultItem]
    total: int
    live: bool = False
    fips_message: str | None = None
    fips_fetched: int = 0
