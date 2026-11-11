# AI drafting prompt

Paste the prompt below into any capable AI assistant, followed by up to 50 real
romanized lines. Save the answer as a `.tsv` file and run `singkhmer new-drafts`.

**The AI's output is only a draft.** It often misspells Khmer. Every line must be
reviewed by a native speaker before it is marked verified. Never use AI output directly
in the test set.

---

```
You convert romanized Khmer chat messages ("Sing Khmer") into Khmer script, word by word.

For each input line, output ONE line in this exact format, with TAB characters between the
three fields:

SOURCE<TAB>ROMANIZED<TAB>PAIRS

- SOURCE: copy the source label I give you (e.g. own_chat).
- ROMANIZED: the input line, unchanged.
- PAIRS: every space-separated word of the input, in order, as  word=khmer  joined with " | ".

Rules:
1. Romanized Khmer words (including abbreviations like jg, hz, sl, kh) -> standard Khmer spelling.
2. English words, numbers, emoji and placeholders like <NAME> stay exactly as typed: meeting=meeting
3. Keep punctuation attached to its word: te?=ទេ?
4. "2" after a word means repetition: lo2=ល្អៗ
5. Do not split or merge words. Do not add words. Do not translate English.
6. Output only the lines, no explanations.

Example input (source = own_chat):
tomorrow mean meeting te bong?
tov kat sok

Example output:
own_chat	tomorrow mean meeting te bong?	tomorrow=tomorrow | mean=មាន | meeting=meeting | te=ទេ | bong?=បង?
own_chat	tov kat sok	tov=ទៅ | kat=កាត់ | sok=សក់

Source = <SOURCE LABEL>
Lines:
<PASTE LINES HERE>
```
