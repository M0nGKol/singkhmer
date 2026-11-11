"""Build the lexicon: Khmer words with their frequency and their romanized spellings.

Two kinds of spellings are kept apart on purpose:
  variants   human spellings with counts: the seed word list (1 = attested), plus every
             spelling seen in verified sentences and in the spelling survey
  generated  guesses from the rule-based romanizer (used only when no human data exists)
"""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path

from .corpus import read_corpus
from .normalize import is_khmer_word, normalize_khmer, normalize_roman, roman_key
from .romanize import romanization_variants
from .schema import read_jsonl, write_jsonl

SPELLING = re.compile(r"[a-z0-9' ]+")
EDGE_PUNCT = " ?!.,;:\"()"


def load_lexicon(path: str | Path) -> dict[str, dict]:
    return {e["khmer"]: e for e in read_jsonl(path)}


def count_words(corpus: str | Path | Iterable[str | Path]) -> Counter:
    counts: Counter = Counter()
    for words in read_corpus(corpus):
        counts.update(w for w in words if is_khmer_word(w))
    return counts


def clean_spelling(rom: str) -> str | None:
    sp = normalize_roman(rom).strip(EDGE_PUNCT)
    return sp if sp and SPELLING.fullmatch(sp) else None


def observed_spellings(annotated: Iterable[str | Path] = (), survey: str | Path | None = None) -> Counter:
    """Count (khmer, spelling) pairs written by real people.

    annotated: verified sentence files (only verified=true records are used)
    survey:    CSV with columns word_khmer, typed (one row per answer)
    """
    pairs: Counter = Counter()
    for path in annotated:
        for r in read_jsonl(path):
            if not r.get("verified"):
                continue
            for t in r["tokens"]:
                kh = normalize_khmer(t["km"].strip(EDGE_PUNCT))
                sp = clean_spelling(t["rom"])
                if t["lang"] == "km" and sp and is_khmer_word(kh):
                    pairs[(kh, sp)] += 1
    if survey:
        with open(survey, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                kh = normalize_khmer((row.get("word_khmer") or "").strip())
                sp = clean_spelling(row.get("typed") or "")
                if sp and is_khmer_word(kh):
                    pairs[(kh, sp)] += 1
    return pairs


def build_lexicon(corpus, seed: str | Path, out: str | Path, top_n: int = 30000, n_generated: int = 4,
                  annotated: Iterable[str | Path] = (), survey: str | Path | None = None) -> int:
    counts = count_words(corpus)
    seed_lex = load_lexicon(seed)
    observed: dict[str, dict[str, int]] = defaultdict(dict)
    for (kh, sp), n in observed_spellings(annotated, survey).items():
        observed[kh][sp] = n
    ranked = [w for w, _ in counts.most_common(top_n)]
    words = list(dict.fromkeys(ranked + list(seed_lex) + list(observed)))   # keep order, no duplicates
    rank = {w: i + 1 for i, w in enumerate(ranked)}

    def entries():
        for w in words:
            s = seed_lex.get(w, {})
            variants = dict(s.get("variants", {}))
            for sp, n in observed.get(w, {}).items():
                variants[sp] = variants.get(sp, 0) + n
            generated = [g for g in romanization_variants(w, k=n_generated) if g not in variants]
            if not variants and not generated:
                continue                    # silent fragment (e.g. a lone consonant + ៍)
            sources = set(s.get("sources", []))
            if w in counts:
                sources.add("corpus")
            if w in observed:
                sources.add("observed")
            e = {"khmer": w, "variants": variants, "generated": generated,
                 "freq": counts.get(w, 0), "freq_rank": rank.get(w), "sources": sorted(sources)}
            if s.get("meaning"):
                e["meaning"] = s["meaning"]
            yield e

    return write_jsonl(out, entries())


def human_keys(lexicon: dict[str, dict]) -> set[str]:
    """roman_keys of every spelling a real person has used."""
    return {roman_key(sp) for e in lexicon.values() for sp in e.get("variants", {})}


def key_index(lexicon: dict[str, dict], min_freq: int = 20, n_generated: int = 1) -> dict[str, list[str]]:
    """roman_key -> Khmer words that can be spelled that way, most frequent first.
    Used to find candidates and to mark ambiguous spellings ("sok" -> សុខ, សក់).
    Rare words (corpus frequency < min_freq, no human spelling) are left out as noise;
    only the n_generated most typical generated spellings are used."""
    idx: dict[str, set[str]] = defaultdict(set)
    for kh, e in lexicon.items():
        if not e.get("variants") and e.get("freq", 0) < min_freq:
            continue
        for sp in list(e.get("variants", {})) + e.get("generated", [])[:n_generated]:
            idx[roman_key(sp)].add(kh)
    freq = {kh: e.get("freq", 0) for kh, e in lexicon.items()}
    return {k: sorted(v, key=lambda w: -freq.get(w, 0)) for k, v in idx.items()}
