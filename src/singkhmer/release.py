"""Package a versioned, ready-to-publish dataset release.

data/release/<version>/
    test.jsonl              human-verified benchmark (never trained on)
    dev.jsonl               human-verified, for tuning
    train.jsonl             human-verified training data
    train_synthetic.jsonl   rule-based pairs from Khmer Wikipedia (CC BY-SA 4.0)
    lexicon.jsonl           Khmer words with human and generated spellings
    stats.json              numbers for the dataset card and the paper
    README.md               dataset card (Hugging Face format), numbers filled in
    SHA256SUMS              checksums so anyone can verify the files
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .lexicon import key_index
from .normalize import roman_key
from .schema import read_jsonl, validate_lexicon_entry, validate_record, write_jsonl
from .stats import lexicon_stats, sentence_stats

HUMAN_SPLITS = ("test", "dev", "train")


def _load(path: Path) -> list[dict]:
    return list(read_jsonl(path)) if path.exists() else []


def _public(r: dict) -> dict:
    """Remove fields that can identify where a message came from."""
    r = dict(r)
    if "group" in r:  # e.g. a page URL or chat name -> short anonymous hash
        r["group"] = "g-" + hashlib.sha1(r["group"].encode("utf-8")).hexdigest()[:8]
    return r


def _mark_ambiguity(rows: list[dict], idx: dict[str, list[str]]) -> None:
    """Add `alternatives` (other Khmer words with the same spelling) and `ambiguous`."""
    for r in rows:
        for t in r["tokens"]:
            if t["lang"] == "km" and "alternatives" not in t:
                alts = [w for w in idx.get(roman_key(t["rom"]), []) if w != t["km"].rstrip("?!.,")][:3]
                if alts:
                    t["alternatives"] = alts
        r["ambiguous"] = any(t.get("alternatives") for t in r["tokens"])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_release(processed: str | Path, synthetic: str | Path, lexicon: str | Path,
                 out_root: str | Path, version: str, allow_empty: bool = False) -> dict:
    processed, out = Path(processed), Path(out_root) / version
    splits = {s: _load(processed / f"{s}.jsonl") for s in HUMAN_SPLITS}
    synth = _load(Path(synthetic))
    lex = _load(Path(lexicon))

    problems = []
    for name, rows in splits.items():
        for r in rows:
            errs = validate_record(r)
            if not r["verified"]:
                errs.append("not human-verified")
            if errs:
                problems.append(f"{name}:{r.get('id')}: {'; '.join(errs)}")
    for r in synth:
        if validate_record(r):
            problems.append(f"synthetic:{r.get('id')}: invalid")
    for e in lex:
        if validate_lexicon_entry(e):
            problems.append(f"lexicon:{e.get('khmer')}: invalid")
    if not splits["test"] and not allow_empty:
        problems.append("test split is empty (collect and verify data first, or pass --allow-empty)")
    if problems:
        raise ValueError("release refused:\n  " + "\n  ".join(problems[:20]))

    idx = key_index({e["khmer"]: e for e in lex})
    for rows in splits.values():
        _mark_ambiguity(rows, idx)

    out.mkdir(parents=True, exist_ok=True)
    for name, rows in splits.items():
        write_jsonl(out / f"{name}.jsonl", (_public(r) for r in rows))
    write_jsonl(out / "train_synthetic.jsonl", synth)
    write_jsonl(out / "lexicon.jsonl", lex)

    stats = {
        "version": version,
        "date": datetime.now(timezone.utc).date().isoformat(),
        **{name: sentence_stats(rows) for name, rows in splits.items()},
        "train_synthetic": sentence_stats(synth),
        "lexicon": lexicon_stats(lex),
    }
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "README.md").write_text(_card(version, stats), encoding="utf-8")
    files = sorted(p for p in out.iterdir() if p.name != "SHA256SUMS")
    (out / "SHA256SUMS").write_text("".join(f"{_sha256(p)}  {p.name}\n" for p in files))
    return {"release": str(out), **{k: len(v) for k, v in splits.items()},
            "train_synthetic": len(synth), "lexicon": len(lex)}


def _card(version: str, s: dict) -> str:
    def n(split):
        return s[split].get("sentences", 0)

    human = [s[x] for x in HUMAN_SPLITS if s[x].get("sentences")]
    pct = (lambda key: round(sum(h[key] * h["sentences"] for h in human) / sum(h["sentences"] for h in human), 1)
           if human else 0.0)
    return f"""---
language: [km, en]
license: cc-by-4.0
task_categories: [text2text-generation]
tags: [khmer, transliteration, romanization, code-mixing, low-resource]
pretty_name: SingKhmer (romanized Khmer to Khmer script)
---

# SingKhmer {version}

Romanized Khmer chat text ("Sing Khmer") paired with Khmer script, aligned word by word,
with language tags for code-mixed Khmer and English.

| File | Sentences | What it is |
| --- | --- | --- |
| `test.jsonl` | {n('test')} | Human-verified benchmark. Never train on it. |
| `dev.jsonl` | {n('dev')} | Human-verified, for tuning. |
| `train.jsonl` | {n('train')} | Human-verified training data. |
| `train_synthetic.jsonl` | {n('train_synthetic')} | Rule-based pairs from Khmer Wikipedia (CC BY-SA 4.0). |
| `lexicon.jsonl` | {s['lexicon']['words']} words | Khmer words with human and generated spellings. |

Human-verified data: {pct('code_mixed_sentences_pct')}% of sentences mix in English;
{pct('ambiguous_sentences_pct')}% contain a spelling that fits more than one Khmer word.
Full numbers: `stats.json`.

## Example

```json
{{"romanized": "tomorrow mean meeting te bong?", "khmer": "tomorrow មាន meeting ទេបង?",
 "tokens": [{{"rom": "tomorrow", "lang": "en", "km": "tomorrow"}}, {{"rom": "mean", "lang": "km", "km": "មាន"}}]}}
```

## How it was made

Real messages (the author's own chats, messages donated with consent, public comments)
were drafted into Khmer script with AI help and corrected by a native speaker following
the annotation guideline. Personal data was removed. Synthetic pairs come from Khmer
Wikipedia sentences and a rule-based chat-style romanizer.

## Limits

The test set is small and written mostly by young, urban speakers. Synthetic sentences are
formal Wikipedia text with no English mixed in.

## License

Human annotations: CC BY 4.0. `train_synthetic.jsonl`: CC BY-SA 4.0 (derived from Wikipedia).
Verify files with `sha256sum -c SHA256SUMS`.
"""
