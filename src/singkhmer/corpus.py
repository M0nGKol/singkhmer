"""Build the Khmer text corpus: clean, normalized, word-segmented sentences.

Sources (each written to its own file, so licenses stay traceable):
  * Khmer Wikipedia            data/interim/corpus.txt            CC BY-SA 4.0
  * web text, e.g. FineWeb-2   data/interim/corpus_fineweb2.txt   ODC-By 1.0

Output format: one sentence per line, words separated by a single space. These files
feed the lexicon (word frequencies), the synthetic generator and, later, KenLM.
"""

from __future__ import annotations

import sys
import urllib.request
from collections.abc import Iterable, Iterator
from pathlib import Path

from .segment import clean_sentence, segment_words, split_sentences

WIKI_URL = (
    "https://huggingface.co/datasets/wikimedia/wikipedia/resolve/main/"
    "20231101.km/train-00000-of-00001.parquet"
)
# name -> (Hugging Face dataset, config, split, text field)
WEB_PRESETS = {
    "fineweb2": ("HuggingFaceFW/fineweb-2", "khm_Khmr", "train", "text"),
}


def download_wiki(out: str | Path, url: str = WIKI_URL) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        print(f"already downloaded: {out}")
        return out
    print(f"downloading {url}")
    urllib.request.urlretrieve(url, out)
    return out


def write_sentences(texts: Iterable[str], out: str | Path, min_words: int = 3,
                    max_words: int = 40, max_chars: int = 400, progress_every: int = 1000) -> dict:
    """Clean + normalize + segment documents and write one sentence per line.
    Run-on "sentences" longer than max_chars (web pages without ។) are skipped early."""
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    docs = kept = total = 0
    with open(out, "w", encoding="utf-8") as f:
        for text in texts:
            docs += 1
            if progress_every and docs % progress_every == 0:
                print(f"  {docs} documents, {kept} sentences kept", file=sys.stderr, flush=True)
            for raw in split_sentences(text or ""):
                total += 1
                if len(raw) > max_chars:
                    continue
                s = clean_sentence(raw)
                if not s or s in seen:
                    continue
                words = segment_words(s)
                if min_words <= len(words) <= max_words:
                    seen.add(s)
                    f.write(" ".join(words) + "\n")
                    kept += 1
    return {"documents": docs, "sentences_seen": total, "sentences_kept": kept, "out": str(out)}


def build_corpus(wiki_parquet: str | Path, out: str | Path, limit: int | None = None) -> dict:
    """Khmer Wikipedia (parquet) -> corpus file."""
    import pandas as pd

    df = pd.read_parquet(wiki_parquet, columns=["text"])
    if limit:
        df = df.head(limit)
    return write_sentences(df["text"], out)


def stream_web_corpus(out: str | Path, preset: str | None = "fineweb2", dataset: str | None = None,
                      config: str | None = None, split: str = "train", text_field: str = "text",
                      n_docs: int = 50000) -> dict:
    """Stream the first n_docs documents of a Hugging Face text dataset (no full download)."""
    try:
        from datasets import load_dataset
    except ImportError as e:
        raise SystemExit('this needs the "datasets" package: pip install -e ".[corpus]"') from e
    if dataset is None:
        dataset, config, split, text_field = WEB_PRESETS[preset]
    ds = load_dataset(dataset, name=config, split=split, streaming=True)
    # take() ends the stream cleanly; cutting it off early can hang the process at exit
    texts = (doc.get(text_field, "") for doc in ds.take(n_docs))
    return write_sentences(texts, out)


def read_corpus(paths: str | Path | Iterable[str | Path]) -> Iterator[list[str]]:
    """Yield word lists from one corpus file or several."""
    if isinstance(paths, (str, Path)):
        paths = [paths]
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                words = line.split()
                if words:
                    yield words
