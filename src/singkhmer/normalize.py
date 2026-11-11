"""Text normalization for Khmer script and romanized Khmer.

Use the SAME functions at collection, training and inference time. If the Khmer side
is stored in different character orders, a correct prediction can be scored as wrong.
"""

from __future__ import annotations

import re
import unicodedata

# --- Khmer character classes (Unicode block U+1780-U+17FF) ---------------------------
CONSONANTS = {chr(c) for c in range(0x1780, 0x17A3)}          # ក .. អ
INDEP_VOWELS = {chr(c) for c in range(0x17A5, 0x17B4)}        # ឥ .. ឳ
DEP_VOWELS = {chr(c) for c in range(0x17B6, 0x17C6)}          # ា .. ៅ
COENG = "្"                                              # ្  (subscript marker)
RO = "រ"                                                 # រ
SHIFTERS = {"៉", "៊"}                               # ៉ ៊  (register shifters)
ROBAT = "៌"                                              # ៌
SIGNS = {"ំ", "ះ", "ៈ", "់", "៍", "៎", "៏", "័", "៑"}
KHMER_DIGITS = {chr(c) for c in range(0x17E0, 0x17EA)}
KHMER_PUNCT = {"។", "៕", "៖", "ៗ", "៘", "៙", "៚", "៛"}

ZERO_WIDTH = re.compile("[\u200b‌‍⁠﻿­]")

# Deprecated or confusable characters -> preferred form
REPLACEMENTS = {
    "ឣ": "អ",          # deprecated independent vowel -> អ
    "ឤ": "អា",    # deprecated -> អា
    "឴": "",                # invisible inherent vowel
    "឵": "",
    "ឲ": "ឱ",          # ឲ -> ឱ  (as in ឱ្យ)
}
# Vowels typed as two parts -> single code point
SPLIT_VOWELS = {
    "េា": "ោ",    # េ + ា -> ោ
    "េី": "ើ",    # េ + ី -> ើ
    "េិ": "ើ",    # េ + ិ -> ើ  (common typo)
}


def _mark_rank(seq: str) -> int:
    """Sort rank for one mark (or a coeng+consonant pair) inside a cluster."""
    if seq.startswith(COENG):
        return 2 if seq[1:] == RO else 1   # subscript ro goes after other subscripts
    if seq in SHIFTERS:
        return 3
    if seq == ROBAT:
        return 4
    if seq in DEP_VOWELS:
        return 5
    return 6                               # other signs: ំ ះ ់ ៍ ...


def _reorder_cluster(marks: list[str]) -> list[str]:
    return sorted(marks, key=_mark_rank)   # sorted() is stable: equal ranks keep order


def normalize_khmer(text: str) -> str:
    """Canonical Khmer text: NFC, no zero-width characters, fixed vowel parts,
    and a consistent order of marks inside each syllable cluster."""
    text = unicodedata.normalize("NFC", text)
    text = ZERO_WIDTH.sub("", text)
    for old, new in REPLACEMENTS.items():
        text = text.replace(old, new)
    for old, new in SPLIT_VOWELS.items():
        text = text.replace(old, new)

    out: list[str] = []
    marks: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == COENG and i + 1 < len(text) and text[i + 1] in CONSONANTS:
            marks.append(text[i : i + 2])
            i += 2
            continue
        if ch in SHIFTERS or ch == ROBAT or ch in DEP_VOWELS or ch in SIGNS:
            marks.append(ch)
        else:
            out.extend(_reorder_cluster(marks))
            marks = []
            out.append(ch)
        i += 1
    out.extend(_reorder_cluster(marks))
    text = "".join(out)
    return re.sub(r"[ \t]+", " ", text).strip()


def is_khmer_char(ch: str) -> bool:
    return "ក" <= ch <= "៿" or "᧠" <= ch <= "᧿"


def is_khmer_word(word: str) -> bool:
    """A real Khmer word: Khmer letters only, with at least one consonant or independent
    vowel, and no digits or punctuation."""
    return (bool(word) and all(is_khmer_char(c) for c in word)
            and any(c in CONSONANTS or c in INDEP_VOWELS for c in word)
            and not any(c in KHMER_DIGITS or c in KHMER_PUNCT - {"\u17D7"} for c in word))


def khmer_ratio(text: str) -> float:
    """Share of non-space characters that are Khmer."""
    chars = [c for c in text if not c.isspace()]
    return sum(is_khmer_char(c) for c in chars) / len(chars) if chars else 0.0


# --- Romanized Khmer ------------------------------------------------------------------

def normalize_roman(text: str) -> str:
    """Light clean-up that keeps the writer's spelling: lowercase, unify quotes,
    collapse spaces. Do NOT fix spellings here; variation is the data."""
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    return re.sub(r"\s+", " ", text).strip()


def roman_key(word: str) -> str:
    """Lookup key for fuzzy matching: letters and digits only, repeated letters
    collapsed ("arkunnn" -> "arkun", "s'aek" -> "saek")."""
    word = re.sub(r"[^a-z0-9]", "", normalize_roman(word))
    return re.sub(r"([a-z])\1+", r"\1", word)
