"""Chat-style romanizer: Khmer script -> romanized Khmer ("Sing Khmer").

This is a heuristic, rule-based generator used to create SYNTHETIC training pairs and
candidate spellings. It is not a standard romanization system (UNGEGN, ALA-LC); it
imitates how Cambodians type Khmer in Latin letters in chats, including common
variation (ch/j, ou/u, ea/ia, final s/h, dropped h in clusters, "2" for ៗ).

Outputs are approximate by design. Real human spellings (data/seed/chat_lexicon.jsonl
and annotated data) always take priority over generated ones.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from .normalize import (
    COENG,
    CONSONANTS,
    DEP_VOWELS,
    INDEP_VOWELS,
    ROBAT,
    SHIFTERS,
    normalize_khmer,
)

BANTOC, TOANDAKHIAT, REAHMUK, NIKAHIT, REPEAT = "់", "៍", "ៈ", "ំ", "ៗ"
SILENT_SIGNS = {"៎", "៏", "័", "៑"}

# consonant: (onset spellings, series)  -- 1 = a-series, 2 = o-series
CONS: dict[str, tuple[list[str], int]] = {
    "ក": (["k"], 1), "ខ": (["kh", "k"], 1), "គ": (["k", "g"], 2), "ឃ": (["kh", "k"], 2),
    "ង": (["ng"], 2), "ច": (["ch", "j", "c"], 1), "ឆ": (["chh", "ch"], 1), "ជ": (["ch", "j"], 2),
    "ឈ": (["chh", "ch"], 2), "ញ": (["nh", "ny"], 2), "ដ": (["d"], 1), "ឋ": (["th", "t"], 1),
    "ឌ": (["d"], 2), "ឍ": (["th", "t"], 2), "ណ": (["n"], 1), "ត": (["t"], 1), "ថ": (["th", "t"], 1),
    "ទ": (["t"], 2), "ធ": (["th", "t"], 2), "ន": (["n"], 2), "ប": (["b", "p"], 1),
    "ផ": (["ph", "p"], 1), "ព": (["p", "b"], 2), "ភ": (["ph", "p"], 2), "ម": (["m"], 2),
    "យ": (["y"], 2), "រ": (["r"], 2), "ល": (["l"], 2), "វ": (["v", "w"], 2), "ឝ": (["s"], 1),
    "ឞ": (["s"], 1), "ស": (["s"], 1), "ហ": (["h"], 1), "ឡ": (["l"], 1), "អ": ([""], 1),
}
SONORANTS = set("ងញនមយរលវ")
SECOND_NON_SONORANT = set("គឃជឈឌឍទធពភ")

FINAL: dict[str, list[str]] = {
    "ក": ["k"], "ខ": ["k"], "គ": ["k"], "ឃ": ["k"], "ង": ["ng"], "ច": ["ch", "j"], "ឆ": ["ch"],
    "ជ": ["ch"], "ឈ": ["ch"], "ញ": ["nh", "n"], "ដ": ["d", "t"], "ឋ": ["t"], "ឌ": ["d"],
    "ឍ": ["t"], "ណ": ["n"], "ត": ["t"], "ថ": ["t"], "ទ": ["t"], "ធ": ["t"], "ន": ["n"],
    "ប": ["b", "p"], "ផ": ["p"], "ព": ["p", "b"], "ភ": ["p"], "ម": ["m"], "យ": ["y", "i"],
    "រ": ["r", ""], "ល": ["l"], "វ": ["v", "w", "o"], "ស": ["s", "h"], "ហ": ["h", ""],
    "ឡ": ["l"], "អ": [""], "ឝ": ["s"], "ឞ": ["s"],
}

# vowel (with its signs) -> (a-series spellings, o-series spellings); first = most common
VOWELS: dict[str, tuple[list[str], list[str]]] = {
    "ា": (["a"], ["ea", "ia", "a"]),
    "ិ": (["e", "i"], ["i", "e"]),
    "ី": (["ei", "ey", "i"], ["i", "y", "ee"]),
    "ឹ": (["oe", "eu", "er"], ["eu", "ue", "e", "er"]),
    "ឺ": (["eu", "oeu", "er"], ["eu", "er"]),
    "ុ": (["o", "u"], ["u", "o"]),
    "ូ": (["o", "ou"], ["u", "ou", "oo"]),
    "ួ": (["uo", "ua", "ou"], ["uo", "ua", "ou", "u"]),
    "ើ": (["ae", "aeu", "er"], ["eu", "er", "oe"]),
    "ឿ": (["oea", "eua", "eu"], ["oea", "eua", "eu"]),
    "ៀ": (["ie", "ia"], ["ie", "ea", "ia"]),
    "េ": (["e", "ay"], ["e"]),
    "ែ": (["ae", "e"], ["ae", "e"]),
    "ៃ": (["ai", "ay"], ["ey", "ei", "ai"]),
    "ោ": (["o", "ao", "ou"], ["ou", "o"]),
    "ៅ": (["ao", "au", "av"], ["ov", "ou", "ow"]),
    "ុំ": (["om", "um"], ["um", "om"]),
    "ំ": (["am", "om"], ["om", "um"]),
    "ាំ": (["am"], ["oam", "eam", "am"]),
    "ះ": (["ah", "eah"], ["eah", "es", "eas"]),
    "ុះ": (["oh", "os"], ["uh", "us"]),
    "េះ": (["eh", "es"], ["is", "ih", "eh"]),
    "ោះ": (["aoh", "oh", "os"], ["uoh", "uh", "oh"]),
    "ិះ": (["eh"], ["ih"]),
    "ាះ": (["ah"], ["eah", "ah"]),
    "ៈ": (["ak", "a"], ["eak", "ea"]),
}
# inherent vowel (no written vowel)
INHERENT_OPEN = (["a", "or"], ["o", "ou"])
INHERENT_CLOSED = (["a", "o"], ["o", "u"])
INHERENT_CLOSED_NG = (["o", "a"], ["o", "u"])      # បង bong, គង kong
INHERENT_BANTOC = (["o", "a"], ["o", "u"])         # អត់ ot, រត់ rot
AA_BANTOC = (["a"], ["oa", "ea"])                  # កាត់ kat, ទាត់ toat

INDEP: dict[str, list[str]] = {
    "ឥ": ["e", "i"], "ឦ": ["ei"], "ឧ": ["o", "u"], "ឩ": ["ou"], "ឪ": ["ov", "au"],
    "ឫ": ["rue", "reu"], "ឬ": ["reu", "rue"], "ឭ": ["lue"], "ឮ": ["leu", "lue"],
    "ឯ": ["ae", "e"], "ឰ": ["ai"], "ឱ": ["ao", "ou", "o"], "ឳ": ["au", "ov"],
}


DOUBLE = re.compile(r"(?<!c)([a-z])\1")     # doubled letter, but not the "hh" in "chh"


@dataclass
class Syllable:
    base: str
    subs: list[str] = field(default_factory=list)
    shifter: str = ""
    vowel: str = ""
    final: str = ""
    bantoc: bool = False


def parse_syllables(word: str) -> list[Syllable]:
    """Split a Khmer word into rough syllables (onset cluster + vowel + final)."""
    w = [c for c in word if c not in SILENT_SIGNS and c != ROBAT]
    n, i, out = len(w), 0, []

    def subs_at(j: int) -> tuple[list[str], int]:
        subs = []
        while j + 1 < n and w[j] == COENG and w[j + 1] in CONSONANTS:
            subs.append(w[j + 1])
            j += 2
        return subs, j

    while i < n:
        ch = w[i]
        if ch not in CONSONANTS and ch not in INDEP_VOWELS:
            i += 1                                        # stray mark or symbol: skip
            continue
        if i + 1 < n and w[i + 1] == TOANDAKHIAT:          # consonant silenced by ៍
            i += 2
            continue
        syl = Syllable(base=ch)
        syl.subs, i = subs_at(i + 1)
        if i < n and w[i] in SHIFTERS:
            syl.shifter, i = w[i], i + 1
        while i < n and (w[i] in DEP_VOWELS or w[i] in (NIKAHIT, "ះ", REAHMUK)):
            syl.vowel += w[i]
            i += 1
        # Decide whether the next consonant closes this syllable (a final consonant).
        if i < n and w[i] in CONSONANTS:
            nxt = w[i + 1] if i + 1 < n else ""
            opens_new = nxt in DEP_VOWELS or nxt in SHIFTERS or nxt in (NIKAHIT, "ះ")
            if not opens_new:
                syl.final = w[i]
                i += 1
                if i < n and w[i] == TOANDAKHIAT:          # silenced consonant
                    syl.final, i = "", i + 1
                if i < n and w[i] == BANTOC:
                    syl.bantoc, i = True, i + 1
                if i < n and w[i] == COENG:
                    trailing, j = subs_at(i)
                    if not trailing:                       # stray coeng: ignore it
                        i += 1
                    elif j >= n:                           # word-final subscripts are silent
                        i = j
                    else:                                  # medial: subscript starts next syllable
                        w[i:i + 2] = [trailing[0]]         # replace coeng+cons with a base cons
                        n = len(w)
        if i < n and w[i] == TOANDAKHIAT:
            i += 1
        out.append(syl)
    return out


def _series(s: Syllable) -> int:
    if s.base in INDEP:
        return 1
    series = CONS.get(s.base, ([""], 1))[1]
    if any(c in SECOND_NON_SONORANT for c in s.subs):
        series = 2
    if s.shifter == "៉":
        series = 1
    elif s.shifter == "៊":
        series = 2
    return series


def _pick(options: list[str], rng: random.Random | None) -> str:
    if rng is None or len(options) == 1:
        return options[0]
    weights = [0.6] + [0.4 / (len(options) - 1)] * (len(options) - 1)
    return rng.choices(options, weights=weights, k=1)[0]


def _syllable_roman(s: Syllable, rng: random.Random | None) -> str:
    ser = _series(s)
    if s.base in INDEP:
        onset, vowel_opts = "", INDEP[s.base]
    else:
        onset = _pick(CONS[s.base][0], rng)
        if s.base == "ប" and s.shifter == "\u17C9":     # ប៉ sounds like p
            onset = "p"
        for sub in s.subs:
            onset += "'" if sub == "អ" else _pick(CONS.get(sub, ([""], 1))[0], rng)
        if s.vowel in VOWELS:
            vowel_opts = VOWELS[s.vowel][ser - 1]
        elif s.vowel:                                     # unknown combination: spell parts
            vowel_opts = ["".join(VOWELS.get(v, ([""], [""]))[ser - 1][0] for v in s.vowel)]
        elif s.bantoc and s.final:
            vowel_opts = INHERENT_BANTOC[ser - 1]
        elif s.final == "ង":
            vowel_opts = INHERENT_CLOSED_NG[ser - 1]
        elif s.final:
            vowel_opts = INHERENT_CLOSED[ser - 1]
        else:
            vowel_opts = INHERENT_OPEN[ser - 1]
        if s.vowel == "ា" and s.bantoc:
            vowel_opts = AA_BANTOC[ser - 1]
    final = _pick(FINAL.get(s.final, [""]), rng) if s.final else ""
    return onset + _pick(vowel_opts, rng) + final


def _chat_noise(word: str, rng: random.Random) -> str:
    """Extra variation typical of chat typing."""
    if rng.random() < 0.6:
        word = word.replace("'", "")                      # s'aek -> saek
    if rng.random() < 0.35:
        word = re.sub(r"^(k|t|p|ch)h(?=[^aeiou])", r"\1", word)   # khnhom -> knhom, thngai -> tngai
    if rng.random() < 0.7:
        word = DOUBLE.sub(r"\1", word)                    # sabbay -> sabay (keeps "chh")
    if rng.random() < 0.15 and word.endswith("s"):
        word = word[:-1] + "h"
    return word


def romanize(word: str) -> str:
    """Most typical chat spelling of a Khmer word (deterministic)."""
    word = normalize_khmer(word)
    rep = word.endswith(REPEAT)
    core = word.rstrip(REPEAT)
    text = "".join(_syllable_roman(s, None) for s in parse_syllables(core))
    text = DOUBLE.sub(r"\1", text.replace("'", ""))
    return text + ("2" if rep else "")


def sample_romanization(word: str, rng: random.Random) -> str:
    """One random but realistic chat spelling of a Khmer word."""
    word = normalize_khmer(word)
    rep = word.endswith(REPEAT)
    core = word.rstrip(REPEAT)
    text = _chat_noise("".join(_syllable_roman(s, rng) for s in parse_syllables(core)), rng)
    if rep:
        text = text + "2" if rng.random() < 0.7 else f"{text} {text}"
    return text


def romanization_variants(word: str, k: int = 5, seed: int = 0, tries: int = 40) -> list[str]:
    """Up to k distinct spellings, most typical first."""
    rng = random.Random(seed)
    seen = [romanize(word)]
    for _ in range(tries):
        v = sample_romanization(word, rng)
        if v and v not in seen:
            seen.append(v)
        if len(seen) >= k:
            break
    return [v for v in seen if v]
