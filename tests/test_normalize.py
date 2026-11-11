from singkhmer.normalize import is_khmer_word, normalize_khmer, normalize_roman, roman_key


def test_removes_zero_width_spaces():
    assert normalize_khmer("ខ្ញុំ\u200bទៅ") == "ខ្ញុំទៅ"


def test_joins_split_vowel():
    # េ + ា typed separately should become ោ
    assert normalize_khmer("កេា") == "កោ"


def test_reorders_vowel_typed_before_subscript():
    # ខ + ុ + ្ញ + ំ  ->  ខ + ្ញ + ុ + ំ
    assert normalize_khmer("ខុ្ញំ") == "ខ្ញុំ"


def test_shifter_goes_before_vowel():
    assert normalize_khmer("ញា៉ំ") == "ញ៉ាំ"


def test_is_idempotent():
    s = "សុខសប្បាយទេ? ញ៉ាំបាយនៅ"
    assert normalize_khmer(normalize_khmer(s)) == normalize_khmer(s)


def test_khmer_word_check():
    assert is_khmer_word("ផ្ទះ")
    assert not is_khmer_word("១២")      # digits
    assert not is_khmer_word("។")       # punctuation
    assert not is_khmer_word("abc")


def test_roman_normalization_keeps_spelling():
    assert normalize_roman("  Tov   KAT sok ") == "tov kat sok"
    assert roman_key("Arkunnn") == "arkun"
    assert roman_key("s'aek") == "saek"
