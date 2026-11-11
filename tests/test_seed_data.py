"""The committed seed files must always pass both the Python rules and the JSON schemas."""

import json
from pathlib import Path

import jsonschema

from singkhmer.schema import read_jsonl, validate_lexicon_entry, validate_record

ROOT = Path(__file__).resolve().parents[1]


def _schema(name):
    return json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_dev_draft_is_valid():
    schema = _schema("sentence.schema.json")
    for r in read_jsonl(ROOT / "data/seed/dev_draft.jsonl"):
        jsonschema.validate(r, schema)
        assert validate_record(r) == [], r["id"]
        assert r["verified"] is False          # drafts stay unverified until a human checks them


def test_seed_lexicon_is_valid():
    schema = _schema("lexicon.schema.json")
    entries = list(read_jsonl(ROOT / "data/seed/chat_lexicon.jsonl"))
    assert len(entries) >= 100
    for e in entries:
        jsonschema.validate(e, schema)
        assert validate_lexicon_entry(e) == [], e["khmer"]
