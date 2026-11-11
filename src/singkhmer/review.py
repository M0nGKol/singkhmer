"""AI-draft + human-review workflow, done in a spreadsheet.

1. Put real romanized lines in a TSV:   source <TAB> romanized <TAB> pairs
   where pairs is an AI (or your own) draft like:  tov=ទៅ | kat=កាត់ | sok=សក់
   (prompts/ai_draft.md gives an AI prompt that outputs exactly this format.)
2. `singkhmer new-drafts`     TSV  -> JSONL records (origin=ai_draft, verified=false)
3. `singkhmer review-export`  JSONL -> CSV; open it in Google Sheets or Excel.
   Fix the pairs column, set status to ok / drop.
4. `singkhmer review-import`  CSV -> verified JSONL (origin=ai_draft_human_fixed).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from .normalize import is_khmer_char, normalize_khmer, normalize_roman
from .schema import read_jsonl, render_khmer, validate_record, write_jsonl

PAIR_SEP = " | "


def parse_pairs(pairs: str) -> list[dict]:
    """'tov=ទៅ | meeting=meeting | 10=10' -> token dicts with a guessed lang."""
    tokens = []
    for part in [p.strip() for p in pairs.split("|") if p.strip()]:
        rom, _, km = part.partition("=")
        rom, km = normalize_roman(rom), km.strip() or rom.strip()
        if any(is_khmer_char(c) for c in km):
            lang, km = "km", normalize_khmer(km)
        elif re.fullmatch(r"[\d.,:/%$-]+", rom):
            lang = "num"
        elif re.fullmatch(r"<[a-z]+>|[^\w\s]+|.*\d.*", rom):
            lang = "other"
        else:
            lang = "en"
        if lang != "km":
            km = rom
        tokens.append({"rom": rom, "lang": lang, "km": km})
    return tokens


def tokens_to_pairs(tokens: list[dict]) -> str:
    return PAIR_SEP.join(f"{t['rom']}={t['km']}" for t in tokens)


def _record(rid: str, source: str, tokens: list[dict], origin: str, verified: bool,
            version: str, notes: str = "") -> dict:
    r = {
        "id": rid, "romanized": " ".join(t["rom"] for t in tokens), "khmer": render_khmer(tokens),
        "tokens": tokens, "source": source, "origin": origin, "verified": verified,
        "split": "unassigned", "version": version,
    }
    if notes:
        r["notes"] = notes
    return r


def new_drafts(tsv: str | Path, out: str | Path, prefix: str = "rd", version: str = "v0.1") -> int:
    rows = []
    with open(tsv, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            source, _romanized, pairs = (line.rstrip("\n").split("\t") + ["", "", ""])[:3]
            rows.append(_record(f"{prefix}-draft-{len(rows) + 1:05d}", source.strip(), parse_pairs(pairs),
                                "ai_draft", False, version))
    return write_jsonl(out, rows)


def review_export(jsonl: str | Path, csv_out: str | Path) -> int:
    rows = list(read_jsonl(jsonl))
    Path(csv_out).parent.mkdir(parents=True, exist_ok=True)
    with open(csv_out, "w", encoding="utf-8-sig", newline="") as f:   # BOM so Excel shows Khmer
        w = csv.writer(f)
        w.writerow(["id", "source", "romanized", "pairs", "status", "notes"])
        for r in rows:
            w.writerow([r["id"], r["source"], r["romanized"], tokens_to_pairs(r["tokens"]), "", ""])
    return len(rows)


def review_import(csv_in: str | Path, out: str | Path, version: str = "v0.1") -> dict:
    kept, dropped, pending, bad = [], 0, 0, []
    with open(csv_in, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            status = (row.get("status") or "").strip().lower()
            if status == "drop":
                dropped += 1
                continue
            if status != "ok":
                pending += 1
                continue
            rid = row["id"].replace("-draft-", "-h-")
            r = _record(rid, row["source"], parse_pairs(row["pairs"]), "ai_draft_human_fixed",
                        True, version, row.get("notes", ""))
            errs = validate_record(r)
            (bad.append((rid, errs)) if errs else kept.append(r))
    write_jsonl(out, kept)
    return {"verified": len(kept), "dropped": dropped, "not_reviewed": pending, "invalid": bad}
