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


def test_mt_validator_preserves_genuine_apologies():
    # Japanese apology to English
    res_ja_en = mt_validator.validate("すみません。", "ja", "en", "I'm sorry.")
    assert res_ja_en.is_valid is True
    assert res_ja_en.cleaned_text == "I'm sorry."

    # Vietnamese apology to English
    res_vi_en = mt_validator.validate("Tôi xin lỗi.", "vi", "en", "I'm sorry.")
    assert res_vi_en.is_valid is True
    assert res_vi_en.cleaned_text == "I'm sorry."

    # Vietnamese apology to Japanese
    res_vi_ja = mt_validator.validate("Xin lỗi bạn.", "vi", "ja", "申し訳ありません。")
    assert res_vi_ja.is_valid is True
    assert res_vi_ja.cleaned_text == "申し訳ありません。"


def test_mt_validator_strip_parenthetical_english_explanations():
    # 1. Cultural term parenthetical note (Sensei)
    orig = "先生、宿題を持ってきました。"
    raw1 = "Thưa thầy, em mang bài tập về nhà đến rồi. (Sensei means teacher in Japanese)"
    res1 = mt_validator.validate(orig, "ja", "vi", raw1)
    assert res1.is_valid is True
    assert res1.cleaned_text == "Thưa thầy, em mang bài tập về nhà đến rồi."

    # 2. Vietnamese parenthetical note
    raw2 = "Thưa thầy, em mang bài tập về nhà đến rồi. (Sensei có nghĩa là thầy giáo)"
    res2 = mt_validator.validate(orig, "ja", "vi", raw2)
    assert res2.is_valid is True
    assert res2.cleaned_text == "Thưa thầy, em mang bài tập về nhà đến rồi."

    # 3. Formality / usage parentheticals
    res3 = mt_validator.validate("やあ", "ja", "vi", "Chào bạn! (Informal)")
    assert res3.is_valid is True
    assert res3.cleaned_text == "Chào bạn!"

    res4 = mt_validator.validate("了解", "ja", "vi", "Tôi hiểu rồi. (Used when expressing agreement)")
    assert res4.is_valid is True
    assert res4.cleaned_text == "Tôi hiểu rồi."


def test_mt_validator_strip_trailing_english_sentences():
    orig = "先生、宿題を持ってきました。"
    # Trailing sentence explaining the term
    raw1 = "Thưa thầy, em mang bài tập về nhà đến rồi. Sensei means teacher in Japanese."
    res1 = mt_validator.validate(orig, "ja", "vi", raw1)
    assert res1.is_valid is True
    assert res1.cleaned_text == "Thưa thầy, em mang bài tập về nhà đến rồi."

    # Trailing sentence starting with 'This sentence means...'
    raw2 = "Thưa thầy, em mang bài tập về nhà đến rồi. This sentence is spoken politely to a teacher."
    res2 = mt_validator.validate(orig, "ja", "vi", raw2)
    assert res2.is_valid is True
    assert res2.cleaned_text == "Thưa thầy, em mang bài tập về nhà đến rồi."

    # Trailing sentence starting with 'The speaker...'
    raw3 = "Thưa thầy, em mang bài tập về nhà đến rồi. The speaker is addressing their instructor respectfully."
    res3 = mt_validator.validate(orig, "ja", "vi", raw3)
    assert res3.is_valid is True
    assert res3.cleaned_text == "Thưa thầy, em mang bài tập về nhà đến rồi."


def test_mt_validator_strip_multiline_and_preambles():
    # Multi-line note
    orig = "先生"
    raw_multi = "Thưa thầy.\nNote: In Japanese culture, Sensei is an honorific title."
    res_multi = mt_validator.validate(orig, "ja", "vi", raw_multi)
    assert res_multi.is_valid is True
    assert res_multi.cleaned_text == "Thưa thầy."


def test_mt_validator_preserves_bold_dashes_and_three_sentences():
    # 1. Bold markers: **text** should not wipe out the sentence
    orig1 = "今日の課題は…2つの鈴を奪うことだ"
    raw1 = "**Nhiệm vụ hôm nay** là cướp hai cái chuông."
    res1 = mt_validator.validate(orig1, "ja", "vi", raw1)
    assert res1.is_valid is True
    assert res1.cleaned_text == "Nhiệm vụ hôm nay là cướp hai cái chuông."

    # 2. Em-dash should be kept as punctuation and not cut off the rest of sentence
    orig2 = "待てよ!"
    raw2 = "Đợi đã — ê!"
    res2 = mt_validator.validate(orig2, "ja", "vi", raw2)
    assert res2.is_valid is True
    assert "Đợi đã" in res2.cleaned_text and "ê!" in res2.cleaned_text

    # 3. 3-sentence translation from ja without punctuation should keep all 3 sentences
    orig3 = "先生どこだよ他のクラスはもう来てるのにうちらだけ"
    raw3 = "Thầy đâu rồi? Lớp khác đến hết rồi. Chỉ còn mỗi bọn mình."
    res3 = mt_validator.validate(orig3, "ja", "vi", raw3)
    assert res3.is_valid is True
    assert res3.cleaned_text == "Thầy đâu rồi? Lớp khác đến hết rồi. Chỉ còn mỗi bọn mình."

    # Preamble: 'Here is the translation into Vietnamese:'
    raw_preamble = "Here is the translation into Vietnamese: Chào buổi sáng."
    res_preamble = mt_validator.validate("Good morning", "en", "vi", raw_preamble)
    assert res_preamble.is_valid is True
    assert res_preamble.cleaned_text == "Chào buổi sáng."

    # Hyphen explanation
    raw_dash = "Thưa thầy - Sensei refers to a teacher or doctor."
    res_dash = mt_validator.validate("先生", "ja", "vi", raw_dash)
    assert res_dash.is_valid is True
    assert res_dash.cleaned_text == "Thưa thầy"


def test_mt_validator_strips_double_quotes():
    # 873d676 gọi `endsWith` (tên hàm JS) nên mọi bản dịch bắt đầu bằng " đều ném AttributeError (docs 08 §3.1)
    res = mt_validator.validate("こんにちは", "ja", "vi", '"Xin chào"')
    assert res.is_valid is True
    assert res.cleaned_text == "Xin chào"

    # Chỉ có ngoặc mở thì giữ nguyên, không được lỗi
    res_open = mt_validator.validate("行こう", "ja", "vi", '"Đi thôi')
    assert res_open.is_valid is True
    assert res_open.cleaned_text == '"Đi thôi'
