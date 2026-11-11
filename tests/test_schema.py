import copy

from singkhmer.schema import render_khmer, validate_lexicon_entry, validate_record

GOOD = {
    "id": "te-h-00001",
    "romanized": "tomorrow mean meeting te bong?",
    "khmer": "tomorrow មាន meeting ទេបង?",
    "tokens": [
        {"rom": "tomorrow", "lang": "en", "km": "tomorrow"},
        {"rom": "mean", "lang": "km", "km": "មាន"},
        {"rom": "meeting", "lang": "en", "km": "meeting"},
        {"rom": "te", "lang": "km", "km": "ទេ"},
        {"rom": "bong?", "lang": "km", "km": "បង?"},
    ],
    "source": "donated_chat",
    "origin": "human",
    "verified": True,
    "split": "test",
    "version": "v0.1",
}


def test_good_record_passes():
    assert validate_record(GOOD) == []


def test_render_rules():
    assert render_khmer(GOOD["tokens"]) == GOOD["khmer"]
    comma = [{"rom": "ot", "lang": "km", "km": "អត់"}, {"rom": "te,", "lang": "km", "km": "ទេ"},
             {"rom": "thlai", "lang": "km", "km": "ថ្លៃ"}]
    assert render_khmer(comma) == "អត់ទេ ថ្លៃ"


def test_synthetic_cannot_be_verified_or_in_test():
    r = copy.deepcopy(GOOD)
    r["origin"] = "synthetic"
    errs = " ".join(validate_record(r))
    assert "cannot be verified" in errs and "human-verified" in errs


def test_mismatched_tokens_are_caught():
    r = copy.deepcopy(GOOD)
    r["khmer"] = "tomorrow មាន meeting ទេ?"
    assert any("join into" in e for e in validate_record(r))


def test_english_token_must_keep_text():
    r = copy.deepcopy(GOOD)
    r["tokens"][0]["km"] = "ថ្ងៃស្អែក"
    assert any("km == rom" in e for e in validate_record(r))


def test_lexicon_entry():
    assert validate_lexicon_entry({"khmer": "ទៅ", "variants": {"tov": 3, "tv": 1}}) == []
    assert validate_lexicon_entry({"khmer": "ទៅ", "variants": {"TOV": 1}})
    assert validate_lexicon_entry({"khmer": "tov", "variants": {"tov": 1}})
