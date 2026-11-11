# Collecting data on your own

This project is designed to be run by **one person**. You do not need a crowdsourcing
app. The plan combines four cheap sources of real text with AI drafting and your own
review, and adds synthetic data for volume.

| Source | What it gives | Effort | Goes into |
| --- | --- | --- | --- |
| 1. Your own chat messages | Real romanized Khmer, no permission problems | Low | train / dev / test |
| 2. Friends donating messages (Google Form) | More writers, more spelling variety | Low | train / dev / test |
| 3. Public comments | Real public text, many writers | Medium | test (see privacy rules) |
| 4. Spelling survey (Google Form) | How many ways people spell each word | Low | lexicon + paper study |
| 5. Synthetic pairs from Wikipedia | Volume for training | None (automatic) | train only |

**Targets for v0.1:** 1,000 human-verified sentences (about 400 for test), 30 survey
answers, 50,000 synthetic pairs.

---

## 1. Your own chats (start here)

Your own messages are the easiest real data: you wrote them, so you can publish them.

1. Telegram Desktop → Settings → Advanced → **Export Telegram data** → select only
   *Personal chats*, format **JSON**. You get `result.json`.
2. Extract your own romanized messages (personal data is scrubbed automatically):
   ```bash
   singkhmer extract-telegram --json path/to/result.json --me "Your Name" \
       --out data/raw/own_chat/telegram_lines.txt
   ```
3. Read the file once and delete anything private (names, places, personal stories).

Other apps (Messenger, WhatsApp): copy messages into a text file, then
`singkhmer find-candidates --input file.txt --out data/raw/own_chat/other_lines.txt`.

Only **your** messages are extracted. Other people's messages need their consent (see 2).

## 2. Friends donating messages

Make a Google Form with:
- a consent checkbox (text below),
- one long-answer field: "Paste 10 recent messages you typed in romanized Khmer",
- optional age group (18–24, 25–34, …). Never ask for names or phone numbers.

> **Consent text:** "I agree that the messages I paste here can be published in an open
> research dataset about romanized Khmer. I removed names, phone numbers and anything
> private. I understand I can ask for my messages to be removed at any time."

Export the responses as CSV, put the messages in a text file, and run `find-candidates`.

## 3. Public comments

Facebook pages and YouTube videos about food, shopping and phones have many romanized
comments.

- Copy only the comment **text**, never usernames or profile pictures.
- Keep a list of where you collected from (page/video URL and date) in `data/raw/SOURCES.md`.
- **Check each platform's terms before you publish raw comments.** If you are unsure,
  use these comments only in your private evaluation, or release them in a separate
  file under a research-only license.
- Set `group` to the page or video, so comments from the same place stay in one split.

## 4. Spelling survey

A Google Form with 50 common words written in Khmer script. For each one, ask: "How do
you type this word when you chat in English letters?" Aim for 30 people (classmates,
club members, online groups). This gives the spelling-variation study in the paper.

## 5. AI draft → your review (the main loop)

Writing Khmer script for every real message by hand is slow. Let an AI draft it, then
fix the draft. Fixing is much faster than writing from scratch.

```bash
# a) Ask an AI to convert real lines into the pairs format (prompt: prompts/ai_draft.md).
#    Save its answer as a TSV:  source <TAB> romanized <TAB> pairs
# b) Turn the TSV into draft records
singkhmer new-drafts --tsv data/interim/batch01.tsv --out data/interim/batch01.drafts.jsonl --prefix oc
# c) Open a review sheet (Google Sheets or Excel)
singkhmer review-export --jsonl data/interim/batch01.drafts.jsonl --csv data/interim/batch01.review.csv
# d) In the sheet: fix the pairs column, set status = ok or drop
# e) Import the reviewed sheet
singkhmer review-import --csv data/interim/batch01.review.csv --out data/annotated/batch01.jsonl
```

Rules:
- Follow [`ANNOTATION_GUIDELINE.md`](ANNOTATION_GUIDELINE.md).
- Work in batches of 50. Thirty minutes a day is about 50–60 sentences, so 1,000 sentences
  takes about three weeks.
- **Second check:** ask one friend to review 10% of your sentences (100) without seeing
  your answers. Report the agreement rate in the paper.

## 6. Grow the corpus and the word list

**More Khmer text (automatic).** Wikipedia is formal. Add web text, which is closer to
everyday writing:

```bash
pip install -e ".[corpus]"                     # once: adds the `datasets` package
singkhmer add-corpus --docs 20000              # FineWeb-2 Khmer -> data/interim/corpus_fineweb2.txt
singkhmer build-lexicon --corpus data/interim/corpus.txt data/interim/corpus_fineweb2.txt
```

About 2,000 documents give 20,000+ sentences in under a minute. FineWeb-2 is ODC-By 1.0
and also subject to Common Crawl's terms of use: credit it (see `DATA_LICENSE.md`).

**More real spellings (you).** Find the words in your own messages that no person has
spelled in the lexicon yet:

```bash
singkhmer new-words --input data/raw/own_chat/telegram_lines.txt    # -> data/interim/new_words.tsv
```

Open `new_words.tsv` in Google Sheets or Excel. Most frequent words come first, with Khmer
suggestions. Fill the `khmer` column; leave English words blank. Then:

```bash
singkhmer add-words          # merges your answers into data/seed/chat_words.tsv
make seed                    # rebuilds the seed lexicon
```

**Real counts.** Every verified sentence and every survey answer is a real spelling.
Count them when you build the lexicon:

```bash
singkhmer build-lexicon --annotated data/annotated/*.jsonl --survey data/raw/survey/answers.csv
```

The survey CSV needs two columns: `word_khmer` and `typed` (one row per answer).

## 7. Synthetic data (automatic)

```bash
make download corpus lexicon synth        # Wikipedia → corpus → lexicon → synthetic pairs
```

Synthetic pairs are always `origin: synthetic` and `verified: false`. The validator
refuses them in dev and test.

## 8. Build the splits

```bash
singkhmer split data/annotated/*.jsonl --out-dir data/processed
singkhmer validate data/processed/*.jsonl
singkhmer stats data/processed/*.jsonl
```

---

## Privacy and consent

- Remove names, usernames, phone numbers, emails, addresses and links before anything
  reaches `data/interim/`. The scrubber catches phones, @users, emails and URLs. **Names
  must be removed by you:** replace them with `<name>`.
- Never commit raw exports or consent forms. `data/raw/` and `private/` are in `.gitignore`.
- Keep a removal process: if someone asks, delete their records and note the change in
  `CHANGELOG.md`.
- Do not collect from private groups or chats you were not part of.
