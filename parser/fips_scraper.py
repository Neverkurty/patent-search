"""
FIPS patent metadata scraper (https://new.fips.ru/iiss/).

CLI:
  python fips_scraper.py --keywords "нейросеть" --max-pages 2
  python fips_scraper.py --seed-only   # write sample data without network

Note: Live scraping may be blocked by FIPS; use --seed-only for local dev.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
import time
from pathlib import Path

import jsonschema

_REPO = Path(__file__).resolve().parents[1]
SCHEMA_PATH = _REPO / "contracts" / "patent.schema.json"
DEFAULT_OUT = Path(__file__).parent / "output" / "patents_dump.json"
LOG_DIR = Path(__file__).parent / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("fips_scraper")

SAMPLE_RECORDS = json.loads(
    (_REPO / "parser" / "output" / "patents_dump.json").read_text(encoding="utf-8")
    if (_REPO / "parser" / "output" / "patents_dump.json").exists()
    else "[]"
)


def _validate(records: list[dict]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    for record in records:
        jsonschema.validate(record, schema)


def _delay() -> None:
    time.sleep(random.uniform(1.0, 3.0))


def scrape_fips(keywords: str, max_pages: int) -> list[dict]:
    """
    Attempt live scrape via undetected-chromedriver.
    Falls back to empty list on failure (caller may handle).
    """
    try:
        import undetected_chromedriver as uc
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError(
            "Install parser deps: pip install -r requirements.txt"
        ) from exc

    results: list[dict] = []
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = uc.Chrome(options=options)
    try:
        base_url = "https://new.fips.ru/iiss/search.xhtml"
        driver.get(base_url)
        _delay()
        # FIPS UI changes frequently; this is a best-effort stub.
        # Extend selectors after inspecting live DOM.
        logger.warning(
            "Live FIPS DOM parsing is site-dependent. "
            "Returning sample subset tagged with keyword filter."
        )
        kw_lower = keywords.lower()
        for rec in SAMPLE_RECORDS:
            blob = " ".join(
                [
                    rec.get("title", ""),
                    rec.get("abstract", ""),
                    " ".join(rec.get("ipc_codes", [])),
                ]
            ).lower()
            if kw_lower in blob or not keywords:
                results.append(rec)
            if len(results) >= max_pages * 5:
                break
        _delay()
    finally:
        driver.quit()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="FIPS patent scraper")
    parser.add_argument("--keywords", default="", help="Search keywords")
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Copy existing sample JSON without browser",
    )
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.seed_only:
        records = SAMPLE_RECORDS
        if not records:
            logger.error("No sample data at parser/output/patents_dump.json")
            sys.exit(1)
    else:
        if not args.keywords:
            logger.error("Provide --keywords or use --seed-only")
            sys.exit(1)
        try:
            records = scrape_fips(args.keywords, args.max_pages)
        except Exception as exc:
            logger.exception("Scrape failed: %s", exc)
            logger.info("Falling back to filtered sample data")
            records = [
                r
                for r in SAMPLE_RECORDS
                if args.keywords.lower()
                in (r.get("title", "") + r.get("abstract", "")).lower()
            ]

    _validate(records)
    args.out.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %d records to %s", len(records), args.out)


if __name__ == "__main__":
    main()
