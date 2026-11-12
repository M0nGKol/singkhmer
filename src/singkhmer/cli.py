"""Command-line interface: `singkhmer <command> --help` for details."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def cmd_download_wiki(a):
    from .corpus import download_wiki
    download_wiki(a.out)


def cmd_build_corpus(a):
    from .corpus import build_corpus
    _print(build_corpus(a.wiki, a.out, limit=a.limit))


def cmd_add_corpus(a):
    import os

    from .corpus import stream_web_corpus
    _print(stream_web_corpus(a.out, preset=a.preset, dataset=a.dataset, config=a.config,
                             split=a.split, text_field=a.text_field, n_docs=a.docs))
    # The output file is complete. Exit now: the `datasets` streaming threads can crash
    # while Python shuts down, which would turn a finished job into a failed exit code.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def cmd_seed(a):
    from .seed import build_seed
    _print({"seed_words": build_seed(a.words, a.out)})


def cmd_build_lexicon(a):
    from .lexicon import build_lexicon
    n = build_lexicon(a.corpus, a.seed, a.out, top_n=a.top, annotated=a.annotated, survey=a.survey)
    _print({"lexicon_entries": n})


def cmd_synth(a):
    from .synthetic import generate
    _print({"synthetic_pairs": generate(a.corpus, a.lexicon, a.out, n=a.n, seed=a.seed)})


def cmd_new_words(a):
    from .lexicon import load_lexicon
    from .new_words import find_new_words, write_new_words
    lines = [ln for p in a.input for ln in Path(p).read_text(encoding="utf-8").splitlines()]
    rows = find_new_words(lines, load_lexicon(a.lexicon), min_count=a.min_count, top=a.top)
    _print({"new_words": write_new_words(rows, a.out), "out": a.out,
            "next": "fill the khmer column (leave English blank), then run: singkhmer add-words"})


def cmd_add_words(a):
    from .new_words import add_words
    _print({**add_words(a.tsv, a.words), "next": "run: make seed"})


def cmd_train_lm(a):
    from .lm import train_lm
    _print(train_lm(a.corpus, a.out, order=a.order, min_count=a.min_count,
                    holdout=a.holdout, heldout_out=a.heldout_out))


def _converter(a, use_lm: bool = True):
    from .convert import Converter
    from .lexicon import load_lexicon
    from .lm import NGramLM
    lm = NGramLM.load(a.lm) if use_lm else None
    return Converter(load_lexicon(a.lexicon), lm, beam=a.beam)


def cmd_convert(a):
    conv = _converter(a, use_lm=not a.no_lm)
    for text in a.text:
        res = conv.convert(text)
        if a.json:
            _print(res)
            continue
        print(f"{res['input']}  ->  {res['khmer']}")
        for t in res["tokens"]:
            alts = f"   (or: {', '.join(t['alternatives'])})" if t.get("alternatives") else ""
            print(f"    {t['rom']:<14} {t['km']:<12} {t['lang']:<5} {t['confidence']:.2f}{alts}")


def cmd_evaluate(a):
    from .evaluate import evaluate
    from .schema import read_jsonl
    records = [r for p in a.data for r in read_jsonl(p)][: a.limit]
    modes = {"b0": False, "b2": True} if a.mode == "both" else {a.mode: a.mode == "b2"}
    results = {name: evaluate(_converter(a, use_lm=lm), records) for name, lm in modes.items()}
    _print({"data": a.data, **results})


def cmd_validate(a):
    from .schema import read_jsonl, validate_lexicon_entry, validate_record
    check = validate_lexicon_entry if a.kind == "lexicon" else validate_record
    failed = 0
    for path in a.files:
        if not Path(path).exists():
            print(f"skip (not found): {path}")
            continue
        n = bad = 0
        ids = set()
        for n, row in enumerate(read_jsonl(path), 1):
            errs = check(row)
            rid = row.get("id") or row.get("khmer")
            if a.kind == "sentence" and rid in ids:
                errs.append("duplicate id")
            ids.add(rid)
            if errs:
                bad += 1
                if bad <= a.show:
                    print(f"  {path}:{n} [{rid}] " + "; ".join(errs))
        print(f"{'OK ' if not bad else 'BAD'} {path}: {n} rows, {bad} invalid")
        failed += bad
    sys.exit(1 if failed else 0)


def cmd_stats(a):
    from .schema import read_jsonl
    from .stats import lexicon_stats, sentence_stats
    for path in a.files:
        rows = list(read_jsonl(path))
        is_lex = rows and "variants" in rows[0]
        _print({"file": path, **(lexicon_stats(rows) if is_lex else sentence_stats(rows))})


def cmd_split(a):
    from .schema import read_jsonl, write_jsonl
    from .splits import assign_splits, split_counts
    records = [r for p in a.files for r in read_jsonl(p)]
    records = assign_splits(records, a.test_pct, a.dev_pct)
    for split in ("train", "dev", "test"):
        write_jsonl(Path(a.out_dir) / f"{split}.jsonl", [r for r in records if r["split"] == split])
    _print(dict(split_counts(records)))


def cmd_release(a):
    from .release import make_release
    try:
        _print(make_release(a.processed, a.synthetic, a.lexicon, a.out, a.version, a.allow_empty))
    except ValueError as e:
        print(e)
        sys.exit(1)


def cmd_extract_telegram(a):
    from .collect import extract_telegram
    lines = extract_telegram(a.json, a.me)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    _print({"romanized_messages": len(lines), "out": a.out})


def cmd_find_candidates(a):
    from .collect import find_candidates
    lines = find_candidates(Path(a.input).read_text(encoding="utf-8").splitlines())
    Path(a.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    _print({"candidates": len(lines), "out": a.out})


def cmd_new_drafts(a):
    from .review import new_drafts
    _print({"drafts": new_drafts(a.tsv, a.out, prefix=a.prefix)})


def cmd_review_export(a):
    from .review import review_export
    _print({"rows": review_export(a.jsonl, a.csv)})


def cmd_review_import(a):
    from .review import review_import
    res = review_import(a.csv, a.out)
    for rid, errs in res["invalid"]:
        print(f"  invalid {rid}: {'; '.join(errs)}")
    res["invalid"] = len(res["invalid"])
    _print(res)


def main(argv=None):
    p = argparse.ArgumentParser(prog="singkhmer", description="Romanized Khmer data pipeline")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("download-wiki", help="download Khmer Wikipedia (parquet)")
    s.add_argument("--out", default="data/raw/km_wiki.parquet")
    s.set_defaults(func=cmd_download_wiki)

    s = sub.add_parser("build-corpus", help="clean + segment Wikipedia into sentences")
    s.add_argument("--wiki", default="data/raw/km_wiki.parquet")
    s.add_argument("--out", default="data/interim/corpus.txt")
    s.add_argument("--limit", type=int, default=None, help="number of articles (default: all)")
    s.set_defaults(func=cmd_build_corpus)

    s = sub.add_parser("add-corpus", help="stream Khmer web text (FineWeb-2 by default) into a corpus file")
    s.add_argument("--out", default="data/interim/corpus_fineweb2.txt")
    s.add_argument("--docs", type=int, default=50000, help="number of documents to stream")
    s.add_argument("--preset", default="fineweb2", choices=["fineweb2"])
    s.add_argument("--dataset", help="any Hugging Face dataset id (overrides --preset)")
    s.add_argument("--config", help="dataset config, e.g. a language code")
    s.add_argument("--split", default="train")
    s.add_argument("--text-field", default="text")
    s.set_defaults(func=cmd_add_corpus)

    s = sub.add_parser("build-seed", help="build the seed chat lexicon")
    s.add_argument("--words", default="data/seed/chat_words.tsv")
    s.add_argument("--out", default="data/seed/chat_lexicon.jsonl")
    s.set_defaults(func=cmd_seed)

    s = sub.add_parser("build-lexicon", help="word frequencies + human and generated spellings")
    s.add_argument("--corpus", nargs="+", default=["data/interim/corpus.txt"],
                   help="one or more corpus files")
    s.add_argument("--annotated", nargs="*", default=[],
                   help="verified sentence files: their spellings are counted")
    s.add_argument("--survey", help="survey CSV with columns word_khmer, typed")
    s.add_argument("--seed", default="data/seed/chat_lexicon.jsonl")
    s.add_argument("--out", default="data/processed/lexicon.jsonl")
    s.add_argument("--top", type=int, default=30000)
    s.set_defaults(func=cmd_build_lexicon)

    s = sub.add_parser("synth", help="generate synthetic sentence pairs")
    s.add_argument("--corpus", nargs="+", default=["data/interim/corpus.txt"])
    s.add_argument("--lexicon", default="data/processed/lexicon.jsonl")
    s.add_argument("--out", default="data/interim/synthetic.jsonl")
    s.add_argument("--n", type=int, default=50000)
    s.add_argument("--seed", type=int, default=13)
    s.set_defaults(func=cmd_synth)

    s = sub.add_parser("new-words", help="list romanized words no person has spelled in the lexicon yet")
    s.add_argument("--input", nargs="+", required=True, help="text files with romanized lines")
    s.add_argument("--lexicon", default="data/processed/lexicon.jsonl")
    s.add_argument("--out", default="data/interim/new_words.tsv")
    s.add_argument("--min-count", type=int, default=2)
    s.add_argument("--top", type=int, default=500)
    s.set_defaults(func=cmd_new_words)

    s = sub.add_parser("add-words", help="merge a filled new_words.tsv into chat_words.tsv")
    s.add_argument("--tsv", default="data/interim/new_words.tsv")
    s.add_argument("--words", default="data/seed/chat_words.tsv")
    s.set_defaults(func=cmd_add_words)

    s = sub.add_parser("train-lm", help="train the n-gram language model on the corpus files")
    s.add_argument("--corpus", nargs="+",
                   default=["data/interim/corpus.txt", "data/interim/corpus_fineweb2.txt"])
    s.add_argument("--out", default="models/lm.pkl.gz")
    s.add_argument("--order", type=int, default=3)
    s.add_argument("--min-count", type=int, default=2)
    s.add_argument("--holdout", type=float, default=0.02, help="share of sentences kept out of training")
    s.add_argument("--heldout-out", default="data/interim/corpus_heldout.txt")
    s.set_defaults(func=cmd_train_lm)

    for name, fn, hlp in [("convert", cmd_convert, "convert romanized Khmer to Khmer script"),
                          ("evaluate", cmd_evaluate, "score the converter on sentence files")]:
        s = sub.add_parser(name, help=hlp)
        s.add_argument("--lexicon", default="data/processed/lexicon.jsonl")
        s.add_argument("--lm", default="models/lm.pkl.gz")
        s.add_argument("--beam", type=int, default=8)
        s.set_defaults(func=fn)
        if name == "convert":
            s.add_argument("text", nargs="+", help='one or more sentences, e.g. "tov kat sok"')
            s.add_argument("--no-lm", action="store_true", help="B0: no language model")
            s.add_argument("--json", action="store_true")
        else:
            s.add_argument("--data", nargs="+", required=True)
            s.add_argument("--mode", choices=["b0", "b2", "both"], default="both")
            s.add_argument("--limit", type=int, default=None)

    s = sub.add_parser("validate", help="check dataset files against the rules")
    s.add_argument("files", nargs="+")
    s.add_argument("--kind", choices=["sentence", "lexicon"], default="sentence")
    s.add_argument("--show", type=int, default=20, help="max errors to print per file")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("stats", help="dataset statistics")
    s.add_argument("files", nargs="+")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("split", help="assign train/dev/test and write processed files")
    s.add_argument("files", nargs="+")
    s.add_argument("--out-dir", default="data/processed")
    s.add_argument("--test-pct", type=int, default=40)
    s.add_argument("--dev-pct", type=int, default=10)
    s.set_defaults(func=cmd_split)

    s = sub.add_parser("release", help="package a versioned dataset release with card and stats")
    s.add_argument("--version", required=True, help="e.g. v0.1")
    s.add_argument("--processed", default="data/processed")
    s.add_argument("--synthetic", default="data/interim/synthetic.jsonl")
    s.add_argument("--lexicon", default="data/processed/lexicon.jsonl")
    s.add_argument("--out", default="data/release")
    s.add_argument("--allow-empty", action="store_true", help="allow an empty test split (dry run)")
    s.set_defaults(func=cmd_release)

    s = sub.add_parser("extract-telegram", help="your own romanized messages from a Telegram export")
    s.add_argument("--json", required=True, help="result.json from Telegram Desktop export")
    s.add_argument("--me", required=True, help="your display name as it appears in the export")
    s.add_argument("--out", default="data/raw/own_chat/telegram_lines.txt")
    s.set_defaults(func=cmd_extract_telegram)

    s = sub.add_parser("find-candidates", help="keep only romanized-Khmer lines from a text file")
    s.add_argument("--input", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_find_candidates)

    s = sub.add_parser("new-drafts", help="TSV of source/romanized/pairs -> draft JSONL")
    s.add_argument("--tsv", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--prefix", default="rd")
    s.set_defaults(func=cmd_new_drafts)

    s = sub.add_parser("review-export", help="draft JSONL -> CSV for Google Sheets")
    s.add_argument("--jsonl", required=True)
    s.add_argument("--csv", required=True)
    s.set_defaults(func=cmd_review_export)

    s = sub.add_parser("review-import", help="reviewed CSV -> verified JSONL")
    s.add_argument("--csv", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_review_import)

    a = p.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
