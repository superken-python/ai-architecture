from rvt_ai.pipeline.mt_validator import mt_validator


def test_mt_validator_valid():
    res = mt_validator.validate("Hello world", "en", "vi", "Xin chào thế giới")
    assert res.is_valid is True
    assert res.cleaned_text == "Xin chào thế giới"


def test_mt_validator_japanese_script():
    # Valid Japanese with kanji/kana
    res = mt_validator.validate("Good morning", "en", "ja", "おはようございます")
    assert res.is_valid is True

    # Invalid Japanese: Latin text returned instead of Japanese script
    res_bad = mt_validator.validate("Good morning", "en", "ja", "Hello there")
    assert res_bad.is_valid is False
    assert "Missing Japanese script" in (res_bad.error_reason or "")


def test_mt_validator_preamble_removal():
    res = mt_validator.validate("Hello", "en", "vi", "Here is the translation: Xin chào")
    assert res.is_valid is True
    assert res.cleaned_text == "Xin chào"


def test_mt_validator_caching():
    mt_validator.cache_translation("en", "vi", "Thank you", "Cảm ơn")
    cached = mt_validator.get_cached("en", "vi", "Thank you")
    assert cached == "Cảm ơn"


def test_mt_validator_note_and_input_stripping():
    raw_en = (
        "Input: Xin chào xin chào Translation: Hello, hello"
        "**Note:** The translation provided above is a direct translation."
    )
    res = mt_validator.validate("Xin chào xin chào", "vi", "en", raw_en)
    assert res.is_valid is True
    assert res.cleaned_text == "Hello, hello"

    raw_ja = (
        "Input: Xin chào xin chào Translation: こんにちは、こんにちは"
        "Alright, let's translate that into Japanese. Translation: こんにちは、こんにちは**Note:** Explanation..."
    )
    res_ja = mt_validator.validate("Xin chào xin chào", "vi", "ja", raw_ja)
    assert res_ja.is_valid is True
    assert res_ja.cleaned_text == "こんにちは、こんにちは"
