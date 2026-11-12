# Changelog

All notable changes to the code and the data are listed here. Data removals requested by
contributors are also recorded here (without personal details).

## [0.1.0] - 2026-11-11

### Added
- Converter v1: lexicon candidates (human, generated, one-letter typos), English/number
  keeping, word trigram language model (`train-lm`), beam search (B2) vs word-by-word (B0),
  per-word confidence and alternatives (`convert`), and metrics (`evaluate`).
- `singkhmer add-corpus`: stream Khmer web text (FineWeb-2) into its own corpus file;
  `build-lexicon` and `synth` accept several corpus files.
- `singkhmer new-words` / `add-words`: list words from real messages that nobody has spelled
  yet, with Khmer suggestions, and merge your answers into `chat_words.tsv`.
- `build-lexicon --annotated --survey`: count real spellings from verified data and the survey.
- `singkhmer release`: versioned dataset package with dataset card, stats and checksums.
- `singkhmer` package: Khmer normalization, segmentation, chat-style romanizer, lexicon
  builder, synthetic pair generator, Telegram/text collection with personal-data
  scrubbing, AI-draft → spreadsheet review workflow, leak-free splits, validation, stats.
- Seed chat word list (113 everyday words with their romanized spellings), drafted with AI
  help and being checked by the author.
- 30 drafted example sentences (`verified: false`).
- JSON Schemas, data collection guide, annotation guideline.
- CI: lint, tests, seed-data validation.
