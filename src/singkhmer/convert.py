"""Romanized Khmer sentence -> Khmer script.

Pipeline for each sentence:
  1. Split into words; keep punctuation attached (te? -> ទេ?).
  2. Candidates per word from the lexicon:
       human spellings  (seed list, verified data, survey)   strongest
       generated        (rule-based romanizer)               weaker
       fuzzy            (one letter different, e.g. typos)   weakest
     Common English words, numbers and emoji are kept as typed.
  3. Pick the best sentence:
       B0  each word alone: the candidate with the best prior
       B2  beam search: prior + n-gram language model over the whole sentence
  4. Report a confidence and alternatives for every word.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass

from .lm import EOS, NGramLM
from .normalize import normalize_roman, roman_key
from .schema import render_khmer

EDGE = " ?!.,;:\"()"
# Keeping a word as typed skips the language model, so it pays a fixed cost instead,
# roughly the log-probability of an ordinary Khmer word. Without it, "keep" always wins.
KEEP_LM_COST = -8.0
# Frequent English words in Cambodian chat. Words that are also Khmer spellings by a real
# person (mean, ban, men, ...) are NOT treated as English: human spellings win.
ENGLISH = {
    "a", "an", "and", "are", "at", "be", "boss", "bro", "but", "by", "call", "can", "chat", "check",
    "class", "coffee", "come", "cool", "cute", "delivery", "deadline", "do", "done", "email", "exam",
    "file", "for", "free", "from", "game", "get", "go", "good", "group", "hello", "hey", "hi",
    "homework", "how", "i", "in", "internet", "is", "it", "job", "just", "know", "late", "like",
    "link", "live", "love", "meeting", "message", "milk", "miss", "movie", "my", "need", "new", "nice",
    "no", "not", "now", "of", "office", "ok", "okay", "on", "online", "or", "order", "phone", "photo",
    "pic", "please", "price", "project", "promotion", "sale", "see", "send", "shop", "shopping", "so",
    "song", "sorry", "sure", "team", "tea", "test", "text", "thank", "thanks", "that", "the", "this",
    "to", "today", "tomorrow", "update", "video", "wait", "want", "we", "welcome", "what", "when",
    "where", "who", "why", "wifi", "will", "with", "work", "wow", "yes", "yesterday", "you", "your",
    "app", "facebook", "telegram", "tiktok", "youtube", "instagram", "zoom",
}


@dataclass
class Cand:
    km: str | None          # Khmer word, or None = keep the word as typed
    prior: float            # log-probability of this reading of the spelling
    kind: str               # human | generated | fuzzy | keep


def _logsoftmax(scores: list[float]) -> list[float]:
    m = max(scores)
    z = m + math.log(sum(math.exp(s - m) for s in scores))
    return [s - z for s in scores]


def _split_punct(tok: str) -> tuple[str, str, str]:
    core = tok.strip(EDGE)
    if not core:
        return "", tok, ""
    start = tok.index(core)
    return tok[:start], core, tok[start + len(core):]


class Converter:
    def __init__(self, lexicon: dict[str, dict], lm: NGramLM | None = None, beam: int = 8,
                 max_cands: int = 6, lm_weight: float = 1.0, prior_weight: float = 1.0):
        self.lm, self.beam, self.max_cands = lm, beam, max_cands
        self.lm_weight, self.prior_weight = lm_weight, prior_weight
        self.exact: dict[str, dict[str, float]] = defaultdict(dict)
        self.human: set[str] = set()
        for kh, e in lexicon.items():
            bonus = 0.15 * math.log1p(e.get("freq", 0))
            for sp, c in e.get("variants", {}).items():
                k = roman_key(sp)
                self.human.add(k)
                self._add(k, kh, 3.0 + math.log1p(c) + bonus)
            for r, sp in enumerate(e.get("generated", [])):
                self._add(roman_key(sp), kh, 1.0 - 0.4 * r + bonus)
        self.deletes: dict[str, set[str]] = defaultdict(set)     # one-deletion index for typos
        for k in self.exact:
            if len(k) >= 4:
                for i in range(len(k)):
                    self.deletes[k[:i] + k[i + 1:]].add(k)

    def _add(self, key: str, kh: str, score: float) -> None:
        if key:
            self.exact[key][kh] = max(self.exact[key].get(kh, -99.0), score)

    # --- candidates -------------------------------------------------------------------
    def candidates(self, core: str) -> list[Cand]:
        word = normalize_roman(core)
        key = roman_key(word)
        if not key or not re.search(r"[a-z]", word) or word.startswith("<"):
            return [Cand(None, 0.0, "keep")]                     # number, emoji, placeholder
        if key in self.human:
            ranked = sorted(self.exact[key].items(), key=lambda x: -x[1])[: self.max_cands]
            cands = [Cand(kh, s, "human") for kh, s in ranked]
        elif word in ENGLISH:
            return [Cand(None, 0.0, "keep")]
        elif key in self.exact:
            ranked = sorted(self.exact[key].items(), key=lambda x: -x[1])[: self.max_cands]
            cands = [Cand(kh, s, "generated") for kh, s in ranked] + [Cand(None, -1.0, "keep")]
        else:
            near = set(self.deletes.get(key, ())) | {k for i in range(len(key))
                                                     for k in [key[:i] + key[i + 1:]] if k in self.exact}
            for i in range(len(key)):
                near |= self.deletes.get(key[:i] + key[i + 1:], set())
            pool: dict[str, float] = {}
            for k in near:
                for kh, s in self.exact[k].items():
                    pool[kh] = max(pool.get(kh, -99.0), s - 2.0)
            ranked = sorted(pool.items(), key=lambda x: -x[1])[: self.max_cands]
            cands = [Cand(kh, s, "fuzzy") for kh, s in ranked] + [Cand(None, 0.5, "keep")]
        for c, lp in zip(cands, _logsoftmax([c.prior for c in cands])):
            c.prior = lp
        return cands

    # --- decoding ---------------------------------------------------------------------
    def _step(self, c: Cand, hist: list[str], n_opts: int) -> float:
        """Score of choosing c after the Khmer words in hist. English words are skipped
        in the history, so "មាន [meeting] ទេ" still connects មាន and ទេ."""
        s = self.prior_weight * c.prior
        if self.lm and n_opts > 1:
            s += self.lm_weight * (KEEP_LM_COST if c.km is None else self.lm.logprob(c.km, hist))
        return s

    def _path_score(self, choices: list[Cand], n_opts: list[int]) -> float:
        total, hist = 0.0, []
        for c, n in zip(choices, n_opts):
            total += self._step(c, hist, n)
            if c.km is not None:
                hist.append(c.km)
        if self.lm and hist:
            total += self.lm_weight * self.lm.logprob(EOS, hist)
        return total

    def convert(self, text: str) -> dict:
        toks = normalize_roman(text).split()
        parts = [_split_punct(t) for t in toks]
        options = [self.candidates(core) if core else [Cand(None, 0.0, "keep")] for _, core, _ in parts]

        if self.lm is None:                                       # B0: best prior for each word
            best = [max(opts, key=lambda c: c.prior) for opts in options]
        else:                                                     # B2: beam search with the LM
            beams: list[tuple[float, list[Cand], list[str]]] = [(0.0, [], [])]
            for opts in options:
                nxt = []
                for score, path, hist in beams:
                    for c in opts:
                        s = score + self._step(c, hist, len(opts))
                        nxt.append((s, path + [c], hist if c.km is None else hist + [c.km]))
                beams = sorted(nxt, key=lambda b: -b[0])[: self.beam]
            # the end of the sentence counts too ("... ទេ" is a likely ending)
            beams = sorted(beams, key=lambda b: -(b[0] + (self.lm_weight * self.lm.logprob(EOS, b[2])
                                                          if b[2] else 0.0)))
            best = beams[0][1]

        n_opts = [len(o) for o in options]
        out_tokens = []
        for i, ((pre, core, post), opts) in enumerate(zip(parts, options)):
            chosen = best[i]
            alt_scores = []
            for c in opts:                                        # re-score each option in context
                trial = best[:i] + [c] + best[i + 1:]
                alt_scores.append((self._path_score(trial, n_opts) if self.lm else c.prior, c))
            probs = _logsoftmax([s for s, _ in alt_scores])
            conf = math.exp(next(p for p, (_, c) in zip(probs, alt_scores) if c is chosen))
            alts = [c.km for _, c in sorted(alt_scores, key=lambda x: -x[0])
                    if c.km and c is not chosen][:3]
            rom = toks[i]
            if chosen.km is None:
                lang = "en" if re.fullmatch(r"[a-z']+", core) else ("num" if re.search(r"\d", core) and
                                                                    not re.search(r"[a-z]", core) else "other")
                tok = {"rom": rom, "lang": lang, "km": rom}
            else:
                tok = {"rom": rom, "lang": "km", "km": pre.strip() + chosen.km + post.rstrip(",")}
            tok["confidence"] = round(conf, 3)
            tok["source"] = chosen.kind
            if alts:
                tok["alternatives"] = alts
            out_tokens.append(tok)
        return {"input": text, "khmer": render_khmer(out_tokens), "tokens": out_tokens}
