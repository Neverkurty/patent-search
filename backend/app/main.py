"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import engine
from app.models.patent import init_db
from app.services.embedding_service import get_embedding_model

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db(engine)
    # Warm up embedding model (optional; speeds first search)
    try:
        get_embedding_model()
    except Exception:
        pass
    yield
    await engine.dispose()


app = FastAPI(
    title="Paten Patent Search API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        ext = (
            await conn.execute(
                text(
                    "SELECT EXISTS("
                    "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                    ")"
                )
            )
        ).scalar()
    return {"status": "ok", "database": "connected", "pgvector": bool(ext)}
