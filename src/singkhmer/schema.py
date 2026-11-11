"""Record formats and validation rules for every dataset file.

Sentence record (one JSON object per line):
    id, romanized, khmer, tokens[{rom, lang, km, alternatives?}], source, origin,
    verified, split, version, ambiguous?, annotators?, agreement?, notes?

Lexicon entry (one JSON object per line):
    khmer, variants{spelling: count}, generated[spellings], freq, freq_rank, sources, meaning?
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from .normalize import is_khmer_char, normalize_khmer, normalize_roman

LANGS = {"km", "en", "num", "other"}
SOURCES = {
    "public_comment", "youtube_comment", "donated_chat", "own_chat", "survey",
    "author_draft", "seed_pairs", "synthetic_wiki", "user_feedback",
}
ORIGINS = {"human", "ai_draft_human_fixed", "ai_draft", "synthetic"}
VERIFIED_ORIGINS = {"human", "ai_draft_human_fixed"}
SPLITS = {"train", "dev", "test", "unassigned"}
ID_RE = re.compile(r"^[a-z]{2,5}-[a-z0-9]{1,8}-\d{3,8}$")
PUNCT = set(".,!?;:'\"()-…។៕៖")


def read_jsonl(path: str | Path) -> Iterator[dict]:
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path}:{n}: invalid JSON ({e})") from e


def write_jsonl(path: str | Path, rows: Iterable[dict]) -> int:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def render_khmer(tokens: list[dict]) -> str:
    """Build the Khmer sentence from tokens: Khmer words join with no space; English,
    numbers and other tokens are separated by spaces; a comma after a romanized word
    becomes a space (Khmer marks a pause with a space, not a comma)."""
    out, prev_lang, pause = "", None, False
    for t in tokens:
        piece = t["km"].rstrip(",")
        if prev_lang is not None and (pause or t["lang"] != "km" or prev_lang != "km"):
            out += " "
        out += piece
        prev_lang, pause = t["lang"], t["rom"].endswith(",")
    return out


def _squash(s: str) -> str:
    return re.sub(r"[\s,]", "", s)


def validate_record(r: dict) -> list[str]:
    """Return a list of problems with one sentence record (empty list = valid)."""
    errs: list[str] = []
    for key in ("id", "romanized", "khmer", "tokens", "source", "origin", "verified", "split", "version"):
        if key not in r:
            errs.append(f"missing field '{key}'")
    if errs:
        return errs

    if not ID_RE.match(r["id"]):
        errs.append(f"bad id '{r['id']}' (expected like 'te-h-00042')")
    if r["source"] not in SOURCES:
        errs.append(f"unknown source '{r['source']}'")
    if r["origin"] not in ORIGINS:
        errs.append(f"unknown origin '{r['origin']}'")
    if r["split"] not in SPLITS:
        errs.append(f"unknown split '{r['split']}'")
    if not isinstance(r["verified"], bool):
        errs.append("'verified' must be true/false")
    if r["verified"] and r["origin"] not in VERIFIED_ORIGINS:
        errs.append(f"origin '{r['origin']}' cannot be verified=true")
    if r["split"] == "test" and not (r["verified"] and r["origin"] in VERIFIED_ORIGINS):
        errs.append("test records must be human-verified")
    if r["khmer"] != normalize_khmer(r["khmer"]):
        errs.append("khmer is not normalized (run normalize_khmer)")

    tokens = r["tokens"]
    if not isinstance(tokens, list) or not tokens:
        return errs + ["tokens must be a non-empty list"]
    for i, t in enumerate(tokens):
        if not {"rom", "lang", "km"} <= set(t):
            errs.append(f"token {i}: needs rom, lang, km")
            continue
        if t["lang"] not in LANGS:
            errs.append(f"token {i}: unknown lang '{t['lang']}'")
        if t["lang"] == "km":
            letters = [c for c in t["km"] if c not in PUNCT and not c.isspace()]
            if not letters or not all(is_khmer_char(c) for c in letters):
                errs.append(f"token {i} ('{t['rom']}'): km must be Khmer script")
        elif t["km"] != t["rom"]:
            errs.append(f"token {i} ('{t['rom']}'): non-Khmer tokens keep their text (km == rom)")
        for alt in t.get("alternatives", []):
            if not all(is_khmer_char(c) for c in alt if c not in PUNCT):
                errs.append(f"token {i}: alternative '{alt}' is not Khmer")

    joined_rom = " ".join(t.get("rom", "") for t in tokens)
    if normalize_roman(joined_rom) != normalize_roman(r["romanized"]):
        errs.append("tokens' rom words do not match 'romanized'")
    if _squash(render_khmer(tokens)) != _squash(r["khmer"]):
        errs.append("tokens' km words do not join into 'khmer'")
    return errs


def validate_lexicon_entry(e: dict) -> list[str]:
    errs: list[str] = []
    kh = e.get("khmer", "")
    if not kh or not all(is_khmer_char(c) for c in kh):
        errs.append(f"khmer '{kh}' must be Khmer script only")
    elif kh != normalize_khmer(kh):
        errs.append(f"khmer '{kh}' is not normalized")
    variants = e.get("variants", {})
    if not isinstance(variants, dict):
        errs.append("variants must be an object {spelling: count}")
    else:
        for sp, n in variants.items():
            if not re.fullmatch(r"[a-z0-9' ]+", sp):
                errs.append(f"variant '{sp}' must be lowercase latin letters/digits")
            if not isinstance(n, int) or n < 0:
                errs.append(f"variant '{sp}': count must be a non-negative integer")
    if not variants and not e.get("generated"):
        errs.append("needs at least one variant or generated spelling")
    return errs
