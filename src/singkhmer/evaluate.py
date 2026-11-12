"""Score a converter against gold sentence records.

Metrics (all in %, except latency):
  sentence_acc   whole Khmer sentence exactly right (spaces ignored)
  word_acc       Khmer words right (gold lang = km)
  top3_acc       gold Khmer word among the first 3 options shown to the user
  english_kept   English / number / emoji tokens left unchanged
  cer            character error rate of the Khmer sentence (lower is better)
  ms_p50/ms_p95  conversion time per sentence
"""

from __future__ import annotations

import re
import time

from .convert import EDGE, Converter


def _squash(s: str) -> str:
    return re.sub(r"\s+", "", s)


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def evaluate(conv: Converter, records: list[dict]) -> dict:
    sent_ok = words = word_ok = top3 = eng = eng_ok = chars = errs = 0
    times = []
    for r in records:
        t0 = time.perf_counter()
        pred = conv.convert(r["romanized"])
        times.append((time.perf_counter() - t0) * 1000)
        gold, guess = _squash(r["khmer"]), _squash(pred["khmer"])
        sent_ok += gold == guess
        chars += len(gold)
        errs += edit_distance(guess, gold)
        if len(pred["tokens"]) != len(r["tokens"]):
            continue                                   # tokens do not line up: sentence metrics only
        for g, p in zip(r["tokens"], pred["tokens"]):
            if g["lang"] == "km":
                words += 1
                gk, pk = g["km"].strip(EDGE), p["km"].strip(EDGE)
                word_ok += gk == pk
                top3 += gk in ([pk] + p.get("alternatives", []))[:3]
            else:
                eng += 1
                eng_ok += p["lang"] != "km" and p["km"] == g["km"]
    times.sort()

    def pct(a, b):
        return round(100 * a / b, 1) if b else None

    return {
        "sentences": len(records),
        "sentence_acc": pct(sent_ok, len(records)),
        "word_acc": pct(word_ok, words),
        "top3_acc": pct(top3, words),
        "english_kept": pct(eng_ok, eng),
        "cer": pct(errs, chars),
        "ms_p50": round(times[len(times) // 2], 1) if times else None,
        "ms_p95": round(times[int(len(times) * 0.95) - 1], 1) if times else None,
    }
