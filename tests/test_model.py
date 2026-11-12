"""Language model, converter (B0 / B2) and evaluation on a tiny hand-made world."""

from singkhmer.convert import Converter
from singkhmer.evaluate import edit_distance, evaluate
from singkhmer.lm import NGramLM

LEXICON = {
    "ទៅ": {"khmer": "ទៅ", "variants": {"tov": 1}, "generated": [], "freq": 50},
    "កាត់": {"khmer": "កាត់", "variants": {"kat": 1}, "generated": [], "freq": 20},
    "សក់": {"khmer": "សក់", "variants": {"sok": 1}, "generated": [], "freq": 10},
    "សុខ": {"khmer": "សុខ", "variants": {"sok": 1}, "generated": [], "freq": 30},
    "សប្បាយ": {"khmer": "សប្បាយ", "variants": {"sabay": 1}, "generated": [], "freq": 30},
    "ទេ": {"khmer": "ទេ", "variants": {"te": 1}, "generated": [], "freq": 40},
    "មាន": {"khmer": "មាន", "variants": {}, "generated": ["mean"], "freq": 60},
    "ពិបាក": {"khmer": "ពិបាក", "variants": {}, "generated": ["pibak"], "freq": 20},
}
CORPUS = [["ទៅ", "កាត់", "សក់"]] * 5 + [["សុខ", "សប្បាយ", "ទេ"]] * 5 + [["មាន", "ទេ"]] * 3


def _lm():
    return NGramLM(order=3).fit(CORPUS, min_count=1)


def test_lm_prefers_seen_sequences():
    lm = _lm()
    assert lm.score(["ទៅ", "កាត់", "សក់"]) > lm.score(["ទៅ", "កាត់", "សុខ"])


def test_lm_save_load(tmp_path):
    lm = _lm()
    lm.save(tmp_path / "lm.pkl.gz")
    again = NGramLM.load(tmp_path / "lm.pkl.gz")
    assert again.score(["សុខ", "សប្បាយ"]) == lm.score(["សុខ", "សប្បាយ"])


def test_context_picks_the_right_word():
    conv = Converter(LEXICON, _lm())
    assert conv.convert("tov kat sok")["khmer"] == "ទៅកាត់សក់"
    assert conv.convert("sok sabay te?")["khmer"] == "សុខសប្បាយទេ?"


def test_english_numbers_and_typos():
    conv = Converter(LEXICON, _lm())
    res = conv.convert("mean meeting 10 te")
    assert [t["lang"] for t in res["tokens"]] == ["km", "en", "num", "km"]
    assert res["khmer"] == "មាន meeting 10 ទេ"
    assert conv.convert("pibakk")["tokens"][0]["km"] == "ពិបាក"      # one extra letter


def test_tokens_report_confidence_and_alternatives():
    tok = Converter(LEXICON, _lm()).convert("tov kat sok")["tokens"][2]
    assert tok["km"] == "សក់" and "សុខ" in tok["alternatives"]
    assert 0 < tok["confidence"] <= 1


def test_b0_without_lm_still_works():
    assert Converter(LEXICON, None).convert("tov")["khmer"] == "ទៅ"


def test_evaluate_metrics():
    gold = [{"romanized": "tov kat sok", "khmer": "ទៅកាត់សក់",
             "tokens": [{"rom": "tov", "lang": "km", "km": "ទៅ"}, {"rom": "kat", "lang": "km", "km": "កាត់"},
                        {"rom": "sok", "lang": "km", "km": "សក់"}]}]
    res = evaluate(Converter(LEXICON, _lm()), gold)
    assert res["sentence_acc"] == 100.0 and res["word_acc"] == 100.0 and res["cer"] == 0.0
    assert edit_distance("abc", "abd") == 1
