# Annotation guideline

The goal: for each romanized message, write **the Khmer script the writer meant**, word
by word. Use the pairs format: `rom=km | rom=km | ...`

```
tomorrow mean meeting te bong?
tomorrow=tomorrow | mean=មាន | meeting=meeting | te=ទេ | bong?=បង?
```

## 1. Tokens

- One token per space-separated romanized word, in the original order.
- Keep punctuation attached to its word (`te?=ទេ?`). A comma becomes a space in Khmer.
- Do not split or merge the writer's words. If they wrote `soksabay` as one word, it is
  one token: `soksabay=សុខសប្បាយ`.

## 2. Language tags (set automatically from the pairs, check them)

| Tag | When | Example |
| --- | --- | --- |
| `km` | A romanized Khmer word, including abbreviations | `jg=ចង់`, `hz=ហើយ`, `sl=ស្រលាញ់` |
| `en` | An English word, kept as typed | `meeting=meeting` |
| `num` | Numbers, prices, times | `10=10`, `5$=5$` |
| `other` | Emoji, placeholders, symbols | `😭=😭`, `<name>=<name>` |

Tricky cases:
- Words that look English but are Khmer stay `km`: `mean=មាន`, `ban=បាន`, `men=មែន`, `chas=ចាស`.
- English words spelled the Khmer way are still English: `mitting=mitting` (keep as typed).
- `2` for repetition belongs to the Khmer word: `lo2=ល្អៗ`.

## 3. Khmer spelling

- Write the **standard spelling** (Chuon Nath dictionary) of the word the writer meant,
  even if their romanization is unusual.
- Fix nothing else: do not correct grammar or add words they did not write.
- Do not add spaces between Khmer words; the tool joins them.
- If a word could be two different Khmer words, choose from context, and if it stays
  unclear, write a note.

## 4. Drop a sentence when

- it is not romanized Khmer (mostly English, or already in Khmer script);
- you cannot tell what it means;
- it contains private information you cannot remove.

## 5. Names and private details

Replace names of private people with `<name>`, phone numbers with `<phone>`, and so on
(the scrubber writes `<PHONE>`, `<USER>`, `<URL>`, `<EMAIL>`; all text is stored in lowercase).
Public places and famous names can stay (`phnompenh=ភ្នំពេញ`).

## 6. Quality

- Review in batches of 50 and re-read the batch once before importing.
- A second person checks 10% of sentences independently; disagreements are discussed and
  the guideline is updated with the decision.
