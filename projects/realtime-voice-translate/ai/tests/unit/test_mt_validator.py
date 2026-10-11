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


def test_mt_validator_repetition_collapse():
    raw_en_loop = "Châu is eating riceChâu is eating riceChâu is eating rice"
    res1 = mt_validator.validate("Châu đang ăn cơm", "vi", "en", raw_en_loop)
    assert res1.is_valid is True
    assert res1.cleaned_text == "Châu is eating rice"

    raw_scared = "Too scared, too scared.Sợ quá, sợ quá.Too scared, too scared.No notes, just the translation."
    res2 = mt_validator.validate("Sợ quá, sợ quá.", "vi", "en", raw_scared)
    assert res2.is_valid is True
    assert res2.cleaned_text == "Too scared, too scared."

    raw_ja_loop = "チャウがご飯を食べていますChâu đang ăn cơmチャウがご飯を食べています"
    res3 = mt_validator.validate("Châu đang ăn cơm", "vi", "ja", raw_ja_loop)
    assert res3.is_valid is True
    assert res3.cleaned_text == "チャウがご飯を食べています"


def test_mt_validator_strip_chatbot_responses_and_explanations():
    orig = "Alo, tôi đang nghe, tôi đang nói nè. Có ai nghe không?"
    raw = (
        "Alo, I'm listening, I'm talking now. Is anyone listening? "
        "I'm sorry, I'm not sure what you mean by \"I'm not sure what you mean by "
        "'Could you please clarify your question? I'm sorry, I'm not sure what you mean by "
        "\"I'm not sure what you mean by 'Could you please explain it better?"
    )
    res = mt_validator.validate(orig, "vi", "en", raw)
    assert res.is_valid is True
    assert res.cleaned_text == "Alo, I'm listening, I'm talking now. Is anyone listening?"


def test_mt_validator_strip_japanese_latin_leak():
    orig = "Alo, tôi đang nghe, tôi đang nói nè. Có ai nghe không?"
    raw_ja = (
        "アロ、聞いてるよ、話してるんだ。誰か聞いてる？"
        "Alo, I'm listening now. Is anyone listening? This is the most important thing..."
    )
    res = mt_validator.validate(orig, "vi", "ja", raw_ja)
    assert res.is_valid is True
    assert res.cleaned_text == "アロ、聞いてるよ、話してるんだ。誰か聞いてる？"
