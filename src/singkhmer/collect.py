"""Collect REAL romanized Khmer on your own: your Telegram messages, or any text file
(comments you copied, notes, survey answers). Personal data is scrubbed first.

Only your OWN messages are extracted from chat exports by default. Other people's
messages need their consent (see docs/DATA_COLLECTION.md).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .normalize import normalize_roman, roman_key

PII_PATTERNS = [
    (re.compile(r"https?://\S+|www\.\S+"), "<URL>"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "<EMAIL>"),
    (re.compile(r"@\w{3,}"), "<USER>"),
    (re.compile(r"(?:\+?855|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{3,4}"), "<PHONE>"),
    (re.compile(r"\b\d{9,}\b"), "<NUMBER>"),
]
# very common romanized Khmer chat words, used to spot romanized Khmer quickly
CORE_WORDS = {
    "nh", "knhom", "khnhom", "nhom", "bong", "oun", "ot", "at", "mean", "min", "te", "teh", "tov",
    "tv", "mok", "mk", "nham", "nyam", "bay", "na", "nas", "nis", "neh", "nuh", "jg", "jong",
    "chong", "ban", "ey", "ei", "avey", "hz", "haey", "heuy", "del", "dae", "lo2", "lo", "sok",
    "sabay", "chea", "jea", "tver", "thver", "dg", "deng", "doeng", "kom", "chol", "jol", "pel",
    "thngai", "saek", "s'aek", "rean", "sala", "luy", "tinh", "ah", "ach", "srolanh", "sl", "knea",
    "mouy", "pi", "bei", "buon", "pram", "oy", "oey", "hai", "mng", "mech", "mes", "yang", "som",
    "arkun", "akun", "orkun", "kor", "kar", "karngear", "phong", "nov", "nv", "chos", "choh",
    "brab", "prab", "tae", "ke", "kh", "puk", "yerng", "yg", "eng", "aeng",
}


def scrub(text: str) -> str:
    for pat, repl in PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


def looks_romanized_khmer(text: str, known_keys: set[str] | None = None, threshold: float = 0.35) -> bool:
    """Latin-script text where enough words are known romanized Khmer words."""
    if re.search(r"[ក-៿]", text):          # already in Khmer script
        return False
    words = [roman_key(w) for w in normalize_roman(text).split()]
    words = [w for w in words if w and not w.isdigit()]
    if len(words) < 2:
        return False
    keys = (known_keys or set()) | {roman_key(w) for w in CORE_WORDS}
    return sum(w in keys for w in words) / len(words) >= threshold


def _telegram_text(msg: dict) -> str:
    t = msg.get("text", "")
    if isinstance(t, list):                          # Telegram splits formatted text into parts
        t = "".join(p if isinstance(p, str) else p.get("text", "") for p in t)
    return t


def extract_telegram(export_json: str | Path, me: str, known_keys: set[str] | None = None) -> list[str]:
    """Your own romanized-Khmer messages from a Telegram Desktop export (result.json)."""
    data = json.loads(Path(export_json).read_text(encoding="utf-8"))
    chats = data.get("chats", {}).get("list", [data])  # full export or a single chat export
    out = []
    for chat in chats:
        for msg in chat.get("messages", []):
            if msg.get("type") != "message" or msg.get("from") != me:
                continue
            text = scrub(_telegram_text(msg)).strip()
            if text and len(text) <= 200 and looks_romanized_khmer(text, known_keys):
                out.append(normalize_roman(text))
    return list(dict.fromkeys(out))                  # drop exact duplicates, keep order


def find_candidates(lines, known_keys: set[str] | None = None) -> list[str]:
    """Filter any list of lines down to likely romanized-Khmer ones (scrubbed)."""
    out = []
    for line in lines:
        text = scrub(line).strip()
        if text and len(text) <= 200 and looks_romanized_khmer(text, known_keys):
            out.append(normalize_roman(text))
    return list(dict.fromkeys(out))
