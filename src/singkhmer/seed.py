"""Build the seed chat lexicon from the project's own word list.

Input: data/seed/chat_words.tsv, one word per line:
    khmer <TAB> meaning <TAB> spelling1,spelling2,...

Seed counts are 1 per listed spelling: they mean "attested", not "how many people".
Real counts come later from the spelling survey and verified data.
"""

from __future__ import annotations

import re
from pathlib import Path

from .normalize import is_khmer_char, normalize_khmer, normalize_roman
from .schema import write_jsonl

VALID = re.compile(r"[a-z0-9' ]+")


def parse_word_line(line: str) -> tuple[str, str, list[str]] | None:
    """'ទៅ<TAB>go<TAB>tov,tv' -> ('ទៅ', 'go', ['tov', 'tv']); None for comments/bad lines."""
    if not line.strip() or line.startswith("#"):
        return None
    khmer, meaning, spellings = (line.rstrip("\n").split("\t") + ["", ""])[:3]
    khmer = normalize_khmer(khmer.strip())
    if not khmer or not all(is_khmer_char(c) for c in khmer):
        return None
    clean = [normalize_roman(s) for s in spellings.split(",")]
    return khmer, meaning.strip(), [s for s in clean if s and VALID.fullmatch(s)]


def build_seed(words_tsv: str | Path, out: str | Path) -> int:
    lex: dict[str, dict] = {}
    for line in Path(words_tsv).read_text(encoding="utf-8").splitlines():
        parsed = parse_word_line(line)
        if not parsed:
            continue
        khmer, meaning, spellings = parsed
        e = lex.setdefault(khmer, {"khmer": khmer, "variants": {}, "sources": ["seed"]})
        for sp in spellings:
            e["variants"].setdefault(sp, 1)
        if meaning and not e.get("meaning"):
            e["meaning"] = meaning
    entries = [e for e in lex.values() if e["variants"]]
    return write_jsonl(out, sorted(entries, key=lambda e: e["khmer"]))
