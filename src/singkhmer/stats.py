"""Dataset statistics for the dataset card and the paper."""

from __future__ import annotations

from collections import Counter


def sentence_stats(records: list[dict]) -> dict:
    n = len(records)
    if not n:
        return {"sentences": 0}
    tokens = [t for r in records for t in r["tokens"]]
    langs = Counter(t["lang"] for t in tokens)
    km_words = {t["km"] for t in tokens if t["lang"] == "km"}
    return {
        "sentences": n,
        "by_split": dict(Counter(r["split"] for r in records)),
        "by_source": dict(Counter(r["source"] for r in records)),
        "by_origin": dict(Counter(r["origin"] for r in records)),
        "verified": sum(r["verified"] for r in records),
        "tokens": len(tokens),
        "avg_tokens_per_sentence": round(len(tokens) / n, 2),
        "token_langs": dict(langs),
        "code_mixed_sentences_pct": round(100 * sum(
            any(t["lang"] == "en" for t in r["tokens"]) for r in records) / n, 1),
        "ambiguous_sentences_pct": round(100 * sum(
            bool(r.get("ambiguous")) or any(t.get("alternatives") for t in r["tokens"])
            for r in records) / n, 1),
        "unique_khmer_words": len(km_words),
    }


def lexicon_stats(entries: list[dict]) -> dict:
    with_human = [e for e in entries if e.get("variants")]
    return {
        "words": len(entries),
        "words_with_human_spellings": len(with_human),
        "avg_human_spellings_per_word": round(
            sum(len(e["variants"]) for e in with_human) / len(with_human), 2) if with_human else 0,
        "avg_generated_spellings_per_word": round(
            sum(len(e.get("generated", [])) for e in entries) / len(entries), 2) if entries else 0,
    }
