"""Sentence splitting and word segmentation for Khmer text.

Khmer is written without spaces between words, so a segmenter is needed to build word
lists and to align romanized words with Khmer words. khmer-nltk (a CRF model) is used.
"""

from __future__ import annotations

import logging
import re
from functools import lru_cache

from .normalize import khmer_ratio, normalize_khmer

# Khmer sentence enders (។ ៕), Latin ones, and line breaks
_SENT_SPLIT = re.compile(r"(?<=[។៕?!])\s*|\n+")
# Things that are not useful in chat-like sentences
_NOISE = re.compile(r"[\[\]{}()<>«»“”\"|=*#_~^]")


@lru_cache(maxsize=1)
def _tokenizer():
    logging.getLogger("khmer-nltk").setLevel(logging.WARNING)
    from khmernltk import word_tokenize  # imported lazily: loading the model takes a second

    return word_tokenize


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s and s.strip()]


def segment_words(sentence: str) -> list[str]:
    """Normalized Khmer sentence -> list of words (spaces and empty tokens removed)."""
    words = _tokenizer()(normalize_khmer(sentence))
    return [w.strip() for w in words if w.strip()]


def clean_sentence(sentence: str, min_khmer: float = 0.9) -> str | None:
    """Return a cleaned sentence, or None if it is not mostly Khmer prose."""
    s = _NOISE.sub(" ", sentence)
    s = re.sub(r"\s+", " ", s).strip(" .,:;-")
    if not s or khmer_ratio(s) < min_khmer:
        return None
    return normalize_khmer(s)
