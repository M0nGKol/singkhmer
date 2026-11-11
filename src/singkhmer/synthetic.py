"""Generate synthetic (romanized, Khmer) sentence pairs from segmented Khmer text.

Every record is marked origin="synthetic", verified=false, so it can never leak into
the test set. Limits to keep in mind (and to state in the paper):
  * source sentences are Wikipedia prose, more formal than chat;
  * no English code-mixing is inserted; real data supplies that.
"""

from __future__ import annotations

import random
from pathlib import Path

from .corpus import read_corpus
from .lexicon import key_index, load_lexicon
from .normalize import KHMER_PUNCT, is_khmer_word, roman_key
from .romanize import REPEAT, sample_romanization
from .schema import render_khmer, write_jsonl


def _spell(word: str, entry: dict | None, rng: random.Random, p_human: float) -> str:
    variants = (entry or {}).get("variants", {})
    if variants and rng.random() < p_human:
        spellings = list(variants)
        weights = [variants[s] + 1 for s in spellings]          # +1 smoothing
        return rng.choices(spellings, weights=weights, k=1)[0]
    return sample_romanization(word, rng)


def _merge_repeat(words: list[str]) -> list[str]:
    """Attach a stand-alone ៗ to the word before it (ល្អ ៗ -> ល្អៗ)."""
    out: list[str] = []
    for w in words:
        if w == REPEAT and out:
            out[-1] += REPEAT
        else:
            out.append(w)
    return out


def generate(corpus: str | Path, lexicon_path: str | Path, out: str | Path, n: int = 50000,
             seed: int = 13, min_words: int = 3, max_words: int = 14, max_chars: int = 90,
             p_human: float = 0.8, version: str = "v0.1") -> int:
    rng = random.Random(seed)
    lex = load_lexicon(lexicon_path)
    idx = key_index(lex)
    drop = KHMER_PUNCT | set(",.!?;:")

    def clean(words: list[str]) -> list[str]:
        """Drop punctuation tokens (chat rarely uses ។) and attach stand-alone ៗ."""
        return _merge_repeat([w for w in words if w == REPEAT or not set(w) <= drop])

    pool = [
        ws for ws in (clean(w) for w in read_corpus(corpus))
        if min_words <= len(ws) <= max_words
        and sum(len(w) for w in ws) <= max_chars
        and all(is_khmer_word(w) for w in ws)               # no digits, Latin or symbols
    ]
    rng.shuffle(pool)

    def records():
        made = 0
        for words in pool:
            if made >= n:
                return
            tokens = []
            for w in words:
                rom = _spell(w, lex.get(w), rng, p_human)
                if not rom.strip():
                    break                                   # unspellable word: skip sentence
                tok = {"rom": rom, "lang": "km", "km": w}
                alts = [a for a in idx.get(roman_key(rom), []) if a != w][:3]
                if alts:
                    tok["alternatives"] = alts
                tokens.append(tok)
            if len(tokens) < len(words):
                continue
            made += 1
            yield {
                "id": f"syn-wiki-{made:07d}",
                "romanized": " ".join(t["rom"] for t in tokens),
                "khmer": render_khmer(tokens),
                "tokens": tokens,
                "source": "synthetic_wiki",
                "origin": "synthetic",
                "verified": False,
                "split": "train",
                "ambiguous": any("alternatives" in t for t in tokens),
                "version": version,
            }

    return write_jsonl(out, records())
