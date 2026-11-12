import csv

from singkhmer.collect import looks_romanized_khmer, scrub
from singkhmer.review import new_drafts, parse_pairs, review_export, review_import
from singkhmer.schema import read_jsonl
from singkhmer.splits import assign_splits


def test_parse_pairs_guesses_languages():
    toks = parse_pairs("send=send | file=file | mk=មក | 10=10 | 😭=😭")
    assert [t["lang"] for t in toks] == ["en", "en", "km", "num", "other"]


def test_draft_review_round_trip(tmp_path):
    tsv = tmp_path / "in.tsv"
    tsv.write_text("own_chat\ttov kat sok\ttov=ទៅ | kat=កាត់ | sok=សុខ\n", encoding="utf-8")
    drafts = tmp_path / "drafts.jsonl"
    new_drafts(tsv, drafts, prefix="oc")
    sheet = tmp_path / "review.csv"
    review_export(drafts, sheet)

    with open(sheet, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    rows[0]["pairs"] = "tov=ទៅ | kat=កាត់ | sok=សក់"        # the reviewer fixes the AI's mistake
    rows[0]["status"] = "ok"
    with open(sheet, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    out = tmp_path / "verified.jsonl"
    res = review_import(sheet, out)
    assert res["verified"] == 1 and not res["invalid"]
    rec = next(read_jsonl(out))
    assert rec["khmer"] == "ទៅកាត់សក់"
    assert rec["origin"] == "ai_draft_human_fixed" and rec["verified"] is True


def test_scrub_and_detect():
    assert scrub("call me 012 345 678 or @dara_kh") == "call me <PHONE> or <USER>"
    assert looks_romanized_khmer("jg tv nham bay te")
    assert not looks_romanized_khmer("see you at the meeting tomorrow")
    assert not looks_romanized_khmer("ចង់ទៅញ៉ាំបាយទេ")


def test_splits_are_stable_and_safe():
    recs = [{"id": f"oc-h-{i:05d}", "romanized": f"tov {i}", "khmer": f"ទៅ {i}", "verified": True,
             "group": f"chat{i % 7}"} for i in range(200)]
    recs.append({"id": "syn-wiki-0000001", "romanized": "x", "khmer": "ក", "verified": False})
    a = {r["id"]: r["split"] for r in assign_splits([dict(r) for r in recs])}
    b = {r["id"]: r["split"] for r in assign_splits([dict(r) for r in recs])}
    assert a == b
    assert a["syn-wiki-0000001"] == "train"
    groups = {}
    for r in recs[:-1]:
        groups.setdefault(r["group"], set()).add(a[r["id"]])
    assert all(len(s) == 1 for s in groups.values())     # a chat never spans two splits


def test_release_refuses_unverified_and_packages_verified(tmp_path):
    import json

    import pytest

    from singkhmer.release import make_release
    from singkhmer.schema import write_jsonl

    good = {"id": "te-h-00001", "romanized": "tov kat sok", "khmer": "ទៅកាត់សក់",
            "tokens": [{"rom": "tov", "lang": "km", "km": "ទៅ"}, {"rom": "kat", "lang": "km", "km": "កាត់"},
                       {"rom": "sok", "lang": "km", "km": "សក់"}],
            "source": "own_chat", "origin": "human", "verified": True, "split": "test",
            "version": "v0.1", "group": "chat with a friend"}
    proc = tmp_path / "processed"
    write_jsonl(proc / "test.jsonl", [good])
    lex = tmp_path / "lex.jsonl"
    write_jsonl(lex, [{"khmer": "ទៅ", "variants": {"tov": 1}}])
    out = tmp_path / "release"

    res = make_release(proc, tmp_path / "none.jsonl", lex, out, "v0.1")
    rel = out / "v0.1"
    assert res["test"] == 1
    assert {p.name for p in rel.iterdir()} >= {"test.jsonl", "README.md", "stats.json", "SHA256SUMS"}
    rec = json.loads((rel / "test.jsonl").read_text(encoding="utf-8"))
    assert rec["group"].startswith("g-")                  # where it came from is anonymized

    bad = dict(good, id="te-h-00002", verified=False)
    write_jsonl(proc / "test.jsonl", [bad])
    with pytest.raises(ValueError):
        make_release(proc, tmp_path / "none.jsonl", lex, out, "v0.2")


def test_show_prints_readable_samples(tmp_path, capsys):
    from singkhmer.cli import main
    from singkhmer.schema import write_jsonl

    lex = tmp_path / "lex.jsonl"
    write_jsonl(lex, [{"khmer": "ចង់", "variants": {"jg": 2, "jong": 1}, "generated": ["chong"], "meaning": "want"}])
    main(["show", str(lex)])
    out = capsys.readouterr().out
    assert "ចង់  [want]" in out and "people: jg(2), jong(1)" in out and "guessed: chong" in out
