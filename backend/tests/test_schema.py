"""Validate sample patents against JSON schema."""

import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "contracts" / "patent.schema.json"
SAMPLE = REPO / "parser" / "output" / "patents_dump.json"


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA.read_text(encoding="utf-8"))


@pytest.fixture
def records() -> list[dict]:
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


def test_sample_file_exists():
    assert SAMPLE.exists()


def test_all_records_valid(schema: dict, records: list[dict]):
    assert len(records) >= 5
    for record in records:
        jsonschema.validate(record, schema)
