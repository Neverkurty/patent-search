"""
Load patents from JSON into PostgreSQL with embeddings and FTS vectors.

Usage (from backend/ with venv active):
  python scripts/load_data.py
  python scripts/load_data.py --file ../parser/output/patents_dump.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import jsonschema

_BACKEND = Path(__file__).resolve().parents[1]
_REPO = _BACKEND.parent
sys.path.insert(0, str(_BACKEND))

from app.core.config import get_settings  # noqa: E402
from app.core.database import async_session_factory, engine  # noqa: E402
from app.models.patent import init_db  # noqa: E402
from app.services.patent_index_service import upsert_patents  # noqa: E402


def _validate_records(records: list[dict], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for record in records:
        jsonschema.validate(record, schema)


async def load_patents(file_path: Path, recreate_embeddings: bool) -> int:
    settings = get_settings()
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    records: list[dict] = raw if isinstance(raw, list) else [raw]
    _validate_records(records, settings.patent_schema_path)

    await init_db(engine)
    async with async_session_factory() as session:
        count = await upsert_patents(
            session, records, recreate_embeddings=recreate_embeddings
        )
    return count


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Load patents JSON into DB")
    parser.add_argument("--file", type=Path, default=settings.default_patents_json)
    parser.add_argument("--recreate-embeddings", action="store_true")
    args = parser.parse_args()
    if not args.file.exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    count = asyncio.run(load_patents(args.file, args.recreate_embeddings))
    print(f"Done. Upserted {count} patents.")


if __name__ == "__main__":
    main()
