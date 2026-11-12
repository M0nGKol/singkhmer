# SingKhmer

**Data pipeline and benchmark for turning romanized Khmer chat text ("Sing Khmer") into Khmer script.**

```
tomorrow mean meeting te bong?   →   tomorrow មាន meeting ទេបង?
tov kat sok                       →   ទៅកាត់សក់        (sok = hair)
sok sabay te?                     →   សុខសប្បាយទេ?      (sok = well-being)
```

Many Cambodians type Khmer with English letters, without a fixed spelling, and mix in
English words. Existing work converts **single words**. This project builds the data for
**sentence-level, real-world, code-mixed** conversion, where the rest of the sentence
decides which Khmer word is meant.

> Status: **v0.1.** Data pipeline, synthetic generator and a first context-aware
> converter (v1) work. Real human-verified data is being collected.

## What is in this repository

| Part | What it does |
| --- | --- |
| `singkhmer` Python package | Normalization, segmentation, chat-style romanizer, lexicon, synthetic pairs, review workflow, validation, splits, stats |
| `data/seed/` | 113 everyday chat words with their spellings; 30 example sentences |
| `schemas/` | JSON Schemas for sentence records and lexicon entries |
| `docs/` | [Data collection guide](docs/DATA_COLLECTION.md), [annotation guideline](docs/ANNOTATION_GUIDELINE.md) |
| `prompts/` | [AI drafting prompt](prompts/ai_draft.md) for the draft → human review loop |
| `tests/` | Unit tests, including checks that the seed data always validates |

## Quick start

```bash
git clone https://github.com/<your-username>/singkhmer.git && cd singkhmer
python -m venv .venv && source .venv/bin/activate
make setup          # pip install -e ".[dev]"
make test

make download       # Khmer Wikipedia, ~35 MB
make corpus         # clean + word-segment (LIMIT=3000 articles by default)
make webcorpus      # stream Khmer web text from FineWeb-2 (DOCS=20000)
make lexicon        # word frequencies + human and generated spellings
make synth          # synthetic sentence pairs (N_SYNTH=50000)
make validate stats
make release VERSION=v0.1   # once you have verified data (see below)
```

Sample synthetic pairs from the generator:

```
min mean karbyeabal                    →   មិនមានការព្យាបាល
sukphap jea ey                         →   សុខភាពជាអ្វី
orneamyo ng teuk sat nov khet kambta   →   អនាម័យនិងទឹកស្អាតនៅខេត្តកំពត
```

## The converter (model v1)

```bash
make lexicon                    # words + spellings from every corpus file
singkhmer train-lm              # word trigram language model -> models/lm.pkl.gz
singkhmer convert "tov kat sok" "sok sabay te?"
```

```
tov kat sok  ->  ទៅកាត់សក់
    sok            សក់          km    1.00   (or: សុខ, សោក, សុក្រ)
sok sabay te?  ->  សុខសប្បាយទេ?
    sok            សុខ          km    0.99   (or: សក់, សោក, សុក)
```

How it works: each romanized word gets Khmer candidates from the lexicon (human spellings
first, then rule-based guesses, then one-letter typo matches); common English words,
numbers and emoji stay as typed. **B0** picks the best candidate for each word alone.
**B2** runs a beam search with a word trigram language model, so the rest of the sentence
decides (`sok` = hair after `kat`, well-being before `sabay`). Every word comes with a
confidence and alternatives.

First baseline (v1, before real chat data):

| Test set | Model | Sentence acc. | Word acc. | Top-3 | English kept | CER |
| --- | --- | --- | --- | --- | --- | --- |
| 30 drafted chat sentences | B0 | 76.7% | 94.2% | 99.0% | 92.3% | 4.7% |
| | **B2** | **90.0%** | **97.1%** | **100%** | **100%** | **1.4%** |
| 857 held-out synthetic sentences | B0 | 6.1% | 63.1% | 84.2% | – | 45.0% |
| | **B2** | **12.1%** | **69.9%** | **85.7%** | – | **41.1%** |

These are early, indicative numbers: the chat set is small and AI-drafted, and the
synthetic set is formal web/Wikipedia text with noisy generated spellings. The language
model has only seen formal text so far, so chat phrases such as `te bong` (ទេបង) are still
hard. The real benchmark will be the human-verified test set.

```bash
singkhmer evaluate --data data/interim/synthetic_eval.jsonl   # B0 vs B2 side by side
```

## How the data is built

```
 real text (own chats, donated messages, public comments)
        │  scrub personal data · keep romanized-Khmer lines
        ▼
 AI draft (prompts/ai_draft.md) ──► review in a spreadsheet ──► verified records
                                                                     │
 Wikipedia + web ─► corpus ─► lexicon ─► synthetic pairs (train only) │
                                │                                    ▼
             seed + survey spellings                    split → train / dev / test
```

| Command | Purpose |
| --- | --- |
| `singkhmer extract-telegram` | Your own romanized messages from a Telegram export |
| `singkhmer find-candidates` | Keep romanized-Khmer lines from any text file |
| `singkhmer new-drafts` / `review-export` / `review-import` | AI draft → spreadsheet review → verified data |
| `singkhmer build-corpus` / `add-corpus` | Wikipedia / web text (FineWeb-2) → clean, segmented corpus |
| `singkhmer build-lexicon` / `synth` | Corpus → lexicon (with real spelling counts) → synthetic pairs |
| `singkhmer new-words` / `add-words` | Find words in your chats that nobody has spelled yet → add them to the word list |
| `singkhmer split` | Leak-free train/dev/test assignment |
| `singkhmer show` | Look inside any data file: samples, `--search`, `--random` |
| `singkhmer validate` / `stats` | Check every rule; print dataset statistics |
| `singkhmer train-lm` / `convert` / `evaluate` | Train the language model, convert sentences, score B0 vs B2 |
| `singkhmer release` | Package `data/release/<version>/` with dataset card, stats and checksums |

## Data format

One JSON object per line, aligned word by word:

```json
{"id": "te-h-00001",
 "romanized": "tomorrow mean meeting te bong?",
 "khmer": "tomorrow មាន meeting ទេបង?",
 "tokens": [{"rom": "tomorrow", "lang": "en", "km": "tomorrow"},
            {"rom": "mean", "lang": "km", "km": "មាន"},
            {"rom": "meeting", "lang": "en", "km": "meeting"},
            {"rom": "te", "lang": "km", "km": "ទេ"},
            {"rom": "bong?", "lang": "km", "km": "បង?"}],
 "source": "donated_chat", "origin": "ai_draft_human_fixed",
 "verified": true, "split": "test", "version": "v0.1"}
```

Rules enforced by `singkhmer validate`:
- the tokens join exactly into `romanized` and `khmer`;
- English, number and emoji tokens keep their text;
- Khmer text is normalized the same way everywhere;
- only human-verified records can be in dev or test, and synthetic data never can;
- no duplicate ids.

## The romanizer

`singkhmer.romanize` is a rule-based, chat-style romanizer (not UNGEGN or ALA-LC). It
handles the two consonant series, subscripts, register shifters, final consonants and
`ៗ`, and samples realistic variation (`ch/j`, `ou/u`, `ea/ia`, final `s/h`, dropped `h`):

```python
>>> from singkhmer.romanize import romanize, romanization_variants
>>> romanize("ខ្ញុំ"), romanize("ល្អៗ"), romanize("ឆ្ងាញ់")
('khnhom', 'lo2', 'chhnganh')
>>> romanization_variants("ចង់")
['chong', 'cang', 'jong', 'chang', 'cong']
```

It is approximate by design and only used for synthetic data and candidate spellings.
Real human spellings always take priority.

## Related work

- [AkaraAlpha](https://github.com/netra-ai-lab/Romanized-Khmer-to-Khmer-Transliteration) (2026): word-level romanized Khmer → Khmer (BiGRU).
- Sentence-level work for other languages: Sinhala ([Swa-Bhasha](https://arxiv.org/abs/2507.09245)), Indic ([IndoNLP 2025](https://arxiv.org/abs/2501.05816)).

## License

Code: [MIT](LICENSE). Data: see [DATA_LICENSE.md](DATA_LICENSE.md) (CC BY 4.0 for our
annotations; third-party sources keep their licenses).

## Acknowledgements

Khmer Wikipedia contributors (source text for synthetic data) · the khmer-nltk library (word segmentation).

## Citation

See [`CITATION.cff`](CITATION.cff).
