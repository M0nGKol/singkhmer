"""Grow the word list from real text.

1. `singkhmer new-words`  reads romanized lines (your chats, comments) and lists the
   words no person has spelled in the lexicon yet, most frequent first, with Khmer
   suggestions from the romanizer. You fill in the `khmer` column (leave English blank).
2. `singkhmer add-words`  merges the filled rows into data/seed/chat_words.tsv.
3. `make seed` (or `singkhmer build-seed`) rebuilds the seed lexicon.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from .lexicon import EDGE_PUNCT, clean_spelling, human_keys, key_index
from .normalize import is_khmer_word, normalize_khmer, normalize_roman, roman_key
from .seed import parse_word_line

WORD = re.compile(r"[a-z][a-z0-9']*")
COLUMNS = ["romanized", "count", "suggestions", "khmer", "example"]


def find_new_words(lines: Iterable[str], lexicon: dict[str, dict], min_count: int = 2,
                   top: int = 500) -> list[dict]:
    known = human_keys(lexicon)
    idx = key_index(lexicon, min_freq=5, n_generated=4)
    counts: Counter = Counter()
    example: dict[str, str] = {}
    for line in lines:
        text = normalize_roman(line)
        for tok in text.split():
            w = tok.strip(EDGE_PUNCT)
            if WORD.fullmatch(w) and roman_key(w) not in known:
                counts[w] += 1
                example.setdefault(w, text)
    rows = []
    for w, n in counts.most_common():
        if n < min_count or len(rows) >= top:
            break
        rows.append({"romanized": w, "count": n,
                     "suggestions": " / ".join(idx.get(roman_key(w), [])[:3]),
                     "khmer": "", "example": example[w][:120]})
    return rows


def write_new_words(rows: list[dict], out: str | Path) -> int:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8-sig", newline="") as f:     # BOM: Excel shows Khmer
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def add_words(filled_tsv: str | Path, words_tsv: str | Path) -> dict:
    """Merge rows with a filled `khmer` column into chat_words.tsv (edited in place)."""
    path = Path(words_tsv)
    lines = path.read_text(encoding="utf-8").splitlines()
    where = {}
    for i, line in enumerate(lines):
        parsed = parse_word_line(line)
        if parsed:
            where[parsed[0]] = i
    added = new = skipped = 0
    with open(filled_tsv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            kh = normalize_khmer((row.get("khmer") or "").strip())
            sp = clean_spelling(row.get("romanized") or "")
            if not kh:
                continue                                      # left blank: English or unsure
            if not sp or not is_khmer_word(kh):
                skipped += 1
                continue
            if kh in where:
                i = where[kh]
                khmer, meaning, spellings = (lines[i].split("\t") + ["", ""])[:3]
                current = [s.strip() for s in spellings.split(",") if s.strip()]
                if sp not in current:
                    lines[i] = "\t".join([khmer, meaning, ",".join(current + [sp])])
                    added += 1
            else:
                lines.append(f"{kh}\t\t{sp}")
                where[kh] = len(lines) - 1
                new += 1
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"spellings_added": added, "new_words": new, "skipped_invalid": skipped}
