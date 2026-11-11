# Data folders

Data moves through these folders in one direction. Each step reads the folder before it
and writes to the next one; nothing is edited by hand except during review.

| Folder | Holds | In git? |
| --- | --- | --- |
| `seed/` | Small hand-made starting files: chat lexicon, drafted example sentences | **yes** |
| `raw/` | Data exactly as collected (Wikipedia, chat exports, survey CSVs) | no (private/large) |
| `interim/` | Cleaned, scrubbed, segmented data; AI drafts; synthetic pairs | no |
| `annotated/` | Human-reviewed records from `review-import` | no (track with DVC) |
| `processed/` | Final `train.jsonl`, `dev.jsonl`, `test.jsonl`, `lexicon.jsonl` | no (track with DVC) |
| `release/` | Versioned files + dataset card for Hugging Face (`make release`) | no |

## Seed files

- `seed/chat_words.tsv`: everyday chat words and how people spell them
  (`khmer <TAB> meaning <TAB> spelling1,spelling2,...`). Edit this file by hand.
- `seed/chat_lexicon.jsonl`: built from `chat_words.tsv` by `make seed`. Do not edit it directly.
- `seed/dev_draft.jsonl`: 30 drafted example sentences built from `seed/dev_draft.tsv` by `make seed`.
  They show the format and serve as a smoke test. They are `verified: false` and must
  never be used as test data.

## Versioning

Large data is tracked with [DVC](https://dvc.org) so each model can point to an exact
data version:

```bash
pip install dvc
dvc init
dvc add data/annotated data/processed
git add data/annotated.dvc data/processed.dvc && git commit -m "Track data v0.1"
```
