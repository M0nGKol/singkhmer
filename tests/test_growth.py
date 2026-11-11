"""Growing the corpus and the word list: corpus files, observed spellings, new words."""

import csv

from singkhmer.corpus import read_corpus, write_sentences
from singkhmer.lexicon import build_lexicon, load_lexicon, observed_spellings
from singkhmer.new_words import add_words, find_new_words, write_new_words
from singkhmer.schema import write_jsonl


def test_write_sentences_cleans_and_segments(tmp_path):
    out = tmp_path / "c.txt"
    docs = ["ខ្ញុំចង់ទៅញ៉ាំបាយ។ hello world only. ខ្ញុំចង់ទៅញ៉ាំបាយ។", "ក" * 500 + "។"]
    res = write_sentences(docs, out, progress_every=0)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines == ["ខ្ញុំ ចង់ ទៅ ញ៉ាំ បាយ ។"]        # English and duplicate dropped, run-on skipped
    assert res["documents"] == 2 and res["sentences_kept"] == 1


def test_read_corpus_accepts_several_files(tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("ខ្ញុំ ទៅ\n", encoding="utf-8")
    b.write_text("បង មក\n", encoding="utf-8")
    assert list(read_corpus([a, b])) == [["ខ្ញុំ", "ទៅ"], ["បង", "មក"]]


def _verified(rom, km, verified=True):
    return {"id": "oc-h-00001", "romanized": rom, "khmer": km, "verified": verified,
            "tokens": [{"rom": rom, "lang": "km", "km": km}]}


def test_observed_spellings_count_real_people_only(tmp_path):
    ann = tmp_path / "ann.jsonl"
    write_jsonl(ann, [_verified("jg", "ចង់"), _verified("jg?", "ចង់?"), _verified("jong", "ចង់", False)])
    survey = tmp_path / "survey.csv"
    survey.write_text("participant,word_khmer,typed\np1,ចង់,jong\np2,ចង់,JG\n", encoding="utf-8")
    pairs = observed_spellings([ann], survey)
    assert pairs[("ចង់", "jg")] == 3                     # 2 verified sentences + 1 survey answer
    assert pairs[("ចង់", "jong")] == 1                   # the unverified sentence is ignored


def test_build_lexicon_adds_counts_and_new_words(tmp_path):
    corpus = tmp_path / "c.txt"
    corpus.write_text("ខ្ញុំ ចង់ ទៅ\n", encoding="utf-8")
    seed = tmp_path / "seed.jsonl"
    write_jsonl(seed, [{"khmer": "ចង់", "variants": {"jong": 1}, "sources": ["seed"]}])
    ann = tmp_path / "ann.jsonl"
    write_jsonl(ann, [_verified("jg", "ចង់"), _verified("nham", "ញ៉ាំ")])
    out = tmp_path / "lex.jsonl"
    build_lexicon(corpus, seed, out, annotated=[ann])
    lex = load_lexicon(out)
    assert lex["ចង់"]["variants"] == {"jong": 1, "jg": 1}
    assert "observed" in lex["ញ៉ាំ"]["sources"]           # a word seen only in verified data


def test_new_words_round_trip(tmp_path):
    lexicon = {"ទៅ": {"khmer": "ទៅ", "variants": {"tov": 1}, "generated": [], "freq": 100},
               "មាន": {"khmer": "មាន", "variants": {}, "generated": ["mean"], "freq": 100}}
    rows = find_new_words(["tov mean meeting", "mean te"], lexicon, min_count=1)
    by_word = {r["romanized"]: r for r in rows}
    assert "tov" not in by_word                            # already spelled by a person
    assert by_word["mean"]["count"] == 2 and by_word["mean"]["suggestions"] == "មាន"
    assert by_word["meeting"]["suggestions"] == ""         # English: nothing to suggest

    tsv = tmp_path / "new.tsv"
    write_new_words(rows, tsv)
    with open(tsv, encoding="utf-8-sig") as f:
        filled = list(csv.DictReader(f, delimiter="\t"))
    for r in filled:
        r["khmer"] = "មាន" if r["romanized"] == "mean" else ""
    with open(tsv, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=filled[0].keys(), delimiter="\t")
        w.writeheader()
        w.writerows(filled)

    words = tmp_path / "chat_words.tsv"
    words.write_text("# header\nទៅ\tgo\ttov\n", encoding="utf-8")
    assert add_words(tsv, words)["new_words"] == 1
    assert words.read_text(encoding="utf-8").splitlines()[-1] == "មាន\t\tmean"
    assert add_words(tsv, words)["new_words"] == 0         # running twice changes nothing
