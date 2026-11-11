import random

import pytest

from singkhmer.romanize import romanization_variants, romanize, sample_romanization

# Typical chat spellings the rule-based romanizer should produce
EXPECTED = {
    "ទៅ": "tov",
    "កាត់": "kat",
    "សក់": "sok",
    "សុខ": "sok",
    "សប្បាយ": "sabay",
    "ខ្ញុំ": "khnhom",
    "ញ៉ាំ": "nham",
    "បាយ": "bay",
    "នេះ": "nis",
    "ណាស់": "nas",
    "ល្អ": "lo",
    "ល្អៗ": "lo2",
    "ថ្ងៃ": "thngai",
    "ស្អែក": "saek",
    "មាន": "mean",
    "អត់": "ot",
    "បង": "bong",
    "ឆ្ងាញ់": "chhnganh",
    "មិត្ត": "mit",
    "ហើយ": "haey",
    "ទិញ": "tinh",
    "លុយ": "luy",
    "ម៉ោង": "mong",
}


@pytest.mark.parametrize("khmer,roman", EXPECTED.items())
def test_typical_spelling(khmer, roman):
    assert romanize(khmer) == roman


def test_variants_include_real_chat_forms():
    assert "jong" in romanization_variants("ចង់", k=6)
    assert "ptes" in romanization_variants("ផ្ទះ", k=6)
    assert "rean" in romanization_variants("រៀន", k=6)


def test_sampling_is_reproducible():
    a = [sample_romanization("សប្បាយ", random.Random(1)) for _ in range(5)]
    b = [sample_romanization("សប្បាយ", random.Random(1)) for _ in range(5)]
    assert a == b


def test_never_crashes_on_odd_input():
    for word in ["", "្", "ក្", "៍", "ក៍", "ប្រយោជន៍", "ឥឡូវ", "ឱ្យ", "ធម៌"]:
        romanize(word)
