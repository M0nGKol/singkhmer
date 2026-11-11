# Common pipeline steps. Run `make help` to list them.
PY ?= python
LIMIT ?= 3000        # Wikipedia articles to process (raise for the full run)
N_SYNTH ?= 50000     # synthetic sentence pairs to generate
VERSION ?= v0.1      # dataset release version
DOCS ?= 20000        # web documents to stream with `make webcorpus`
CORPORA = $(wildcard data/interim/corpus*.txt)

.PHONY: help setup test lint seed download corpus webcorpus lexicon synth newwords addwords split validate stats release all

help:
	@grep -E '^[a-z]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

setup: ## Install the package with dev tools
	$(PY) -m pip install -e ".[dev,corpus]"

test: ## Run unit tests
	pytest -q

lint: ## Lint the code
	ruff check src tests

seed: ## Rebuild the seed lexicon and draft sentences from the .tsv files
	singkhmer build-seed --words data/seed/chat_words.tsv --out data/seed/chat_lexicon.jsonl
	singkhmer new-drafts --tsv data/seed/dev_draft.tsv --out data/seed/dev_draft.jsonl --prefix dev

download: ## Download Khmer Wikipedia (about 35 MB)
	singkhmer download-wiki --out data/raw/km_wiki.parquet

corpus: ## Clean, normalize and word-segment Wikipedia into sentences
	singkhmer build-corpus --wiki data/raw/km_wiki.parquet --limit $(LIMIT) --out data/interim/corpus.txt

webcorpus: ## Stream Khmer web text (FineWeb-2) into data/interim/corpus_fineweb2.txt
	singkhmer add-corpus --docs $(DOCS)

lexicon: ## Build the lexicon from every corpus file (+ seed and generated spellings)
	singkhmer build-lexicon --corpus $(CORPORA) --seed data/seed/chat_lexicon.jsonl --out data/processed/lexicon.jsonl

synth: ## Generate synthetic romanized/Khmer sentence pairs
	singkhmer synth --corpus $(CORPORA) --lexicon data/processed/lexicon.jsonl --n $(N_SYNTH) --out data/interim/synthetic.jsonl

newwords: ## List words from your chats (data/raw/own_chat/*.txt) that nobody has spelled yet
	singkhmer new-words --input $(wildcard data/raw/own_chat/*.txt)

addwords: ## Merge the filled data/interim/new_words.tsv into chat_words.tsv, then rebuild the seed
	singkhmer add-words
	$(MAKE) seed

split: ## Assign train/dev/test for all verified data in data/annotated
	singkhmer split data/annotated/*.jsonl --out-dir data/processed

validate: ## Validate every dataset file
	singkhmer validate data/seed/dev_draft.jsonl data/interim/synthetic.jsonl
	singkhmer validate --kind lexicon data/seed/chat_lexicon.jsonl data/processed/lexicon.jsonl

stats: ## Print dataset statistics
	singkhmer stats data/seed/dev_draft.jsonl data/interim/synthetic.jsonl

release: ## Package data/release/$(VERSION) (needs verified data in data/processed)
	singkhmer release --version $(VERSION)

all: download corpus lexicon synth validate stats ## Run the whole data pipeline