"""Word n-gram language model for ranking Khmer word sequences.

It answers one question for the converter: which of several candidate Khmer sentences
reads most naturally? ("ទៅ កាត់ សក់" scores higher than "ទៅ កាត់ សុខ".)

Method: trigram counts with "stupid backoff" (Brants et al., 2007). It is simple, fast
and works well for ranking. It is pure Python, so nothing needs compiling; a KenLM model
can replace it later behind the same `logprob` interface.
"""

from __future__ import annotations

import gzip
import math
import pickle
import random
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

from .corpus import read_corpus
from .normalize import is_khmer_word

BOS, EOS = "<s>", "</s>"


class NGramLM:
    def __init__(self, order: int = 3, alpha: float = 0.4):
        self.order = order
        self.alpha = alpha                      # backoff factor
        self.grams: list[Counter] = [Counter() for _ in range(order)]   # n-gram -> count
        self.ctx: list[Counter] = [Counter() for _ in range(order)]     # context -> count
        self.tokens = 0

    # --- training ---------------------------------------------------------------------
    def fit(self, sentences: Iterable[list[str]], min_count: int = 2) -> NGramLM:
        for words in sentences:
            words = [w for w in words if is_khmer_word(w)]
            if not words:
                continue
            seq = [BOS] * (self.order - 1) + words + [EOS]
            for i in range(self.order - 1, len(seq)):
                for n in range(1, self.order + 1):
                    gram = tuple(seq[i - n + 1 : i + 1])
                    self.grams[n - 1][gram] += 1
                    self.ctx[n - 1][gram[:-1]] += 1
            self.tokens += len(words) + 1
        if min_count > 1:                       # drop rare higher-order n-grams to save memory
            for n in range(1, self.order):
                self.grams[n] = Counter({g: c for g, c in self.grams[n].items() if c >= min_count})
        return self

    # --- scoring ----------------------------------------------------------------------
    def logprob(self, word: str, history: list[str]) -> float:
        """log S(word | last order-1 words of history)."""
        hist = ([BOS] * (self.order - 1) + list(history))[-(self.order - 1):] if self.order > 1 else []
        penalty = 0.0
        for n in range(self.order, 1, -1):
            ctx = tuple(hist[len(hist) - (n - 1):])
            c = self.grams[n - 1].get(ctx + (word,))
            if c:
                return penalty + math.log(c / self.ctx[n - 1][ctx])
            penalty += math.log(self.alpha)
        vocab = len(self.grams[0]) + 1
        return penalty + math.log((self.grams[0].get((word,), 0) + 1) / (self.tokens + vocab))

    def score(self, words: list[str], eos: bool = True) -> float:
        total, hist = 0.0, []
        for w in words + ([EOS] if eos else []):
            total += self.logprob(w, hist)
            hist.append(w)
        return total

    # --- save / load ------------------------------------------------------------------
    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, "wb") as f:
            pickle.dump(self.__dict__, f, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, path: str | Path) -> NGramLM:
        lm = cls()
        with gzip.open(path, "rb") as f:
            lm.__dict__.update(pickle.load(f))
        return lm


def train_lm(corpora: list[str | Path], out: str | Path, order: int = 3, min_count: int = 2,
             holdout: float = 0.02, heldout_out: str | Path | None = None, seed: int = 7) -> dict:
    """Train on corpus files. A small random share of sentences is held out (never seen by
    the model) and written to `heldout_out`, so evaluation data can be made from them."""
    rng = random.Random(seed)
    train, held = [], []
    for words in read_corpus([c for c in corpora if Path(c).exists()]):
        (held if rng.random() < holdout else train).append(words)
    lm = NGramLM(order=order).fit(train, min_count=min_count)
    lm.save(out)
    if heldout_out:
        Path(heldout_out).parent.mkdir(parents=True, exist_ok=True)
        Path(heldout_out).write_text("".join(" ".join(w) + "\n" for w in held), encoding="utf-8")
    return {"train_sentences": len(train), "heldout_sentences": len(held), "tokens": lm.tokens,
            "ngrams": [len(g) for g in lm.grams], "out": str(out)}
