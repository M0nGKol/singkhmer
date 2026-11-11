"""Assign train / dev / test without leaks.

* Only human-verified records can reach dev or test.
* Records sharing a `group` (e.g. the same chat thread or video) land in the same split,
  so near-identical sentences cannot sit on both sides.
* The assignment is a hash of the group, so re-running gives the same split.
* Exact duplicates (same romanized + khmer) are kept once, in the strictest split.
"""

from __future__ import annotations

import hashlib
from collections import Counter

from .normalize import normalize_roman

ORDER = {"test": 0, "dev": 1, "train": 2}


def _bucket(group: str) -> int:
    return int(hashlib.sha1(group.encode("utf-8")).hexdigest(), 16) % 100


def assign_splits(records: list[dict], test_pct: int = 40, dev_pct: int = 10) -> list[dict]:
    """While data is scarce, test gets a large share: the benchmark matters most.
    Lower test_pct once you have more than ~3,000 verified sentences."""
    for r in records:
        if r["verified"]:
            b = _bucket(r.get("group") or r["id"])
            r["split"] = "test" if b < test_pct else "dev" if b < test_pct + dev_pct else "train"
        else:
            r["split"] = "train"
    best: dict[tuple, dict] = {}
    for r in sorted(records, key=lambda r: ORDER[r["split"]]):
        key = (normalize_roman(r["romanized"]), r["khmer"])
        best.setdefault(key, r)
    return list(best.values())


def split_counts(records: list[dict]) -> Counter:
    return Counter(r["split"] for r in records)
