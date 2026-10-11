import re

from pydantic import BaseModel

from rvt_contracts.messages import Lang

# Regex for Japanese characters (Hiragana, Katakana, Kanji)
JA_REGEX = re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]")
# Regex for Latin characters (English, Vietnamese)
LATIN_REGEX = re.compile(r"[a-zA-ZÀ-ỹ]")


class ValidationResult(BaseModel):
    is_valid: bool
    cleaned_text: str
    error_reason: str | None = None


class MtValidator:
    def __init__(self):
        # In-memory exact match cache: (source_lang, target_lang, normalized_text) -> translation
        self._exact_cache: dict[tuple[Lang, Lang, str], str] = {}

    def get_cached(self, source_lang: Lang, target_lang: Lang, text: str) -> str | None:
        key = (source_lang, target_lang, text.strip().lower())
        return self._exact_cache.get(key)

    def cache_translation(self, source_lang: Lang, target_lang: Lang, text: str, translation: str) -> None:
        if len(text.strip()) < 50:  # Only cache short phrases
            key = (source_lang, target_lang, text.strip().lower())
            self._exact_cache[key] = translation.strip()

    def clean(self, raw_translation: str, original_text: str = "", target_lang: Lang = "en") -> str:
        cleaned = raw_translation.strip()
        if not cleaned:
            return ""

        # 1. Strip surrounding quotation marks or code blocks
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned.strip("`").strip()
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        # 2. Take only the first non-empty line (speech translation should never have multi-line commentary)
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            cleaned = lines[0]

        # 3. Strip common preambles
        preambles = [
            r"^Here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*",
            r"^Here['’]s\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*",
            r"^Sure,?\s*(?:here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*)?",
            r"^Certainly,?\s*(?:here\s+is\s+the\s+(?:[a-zA-Z]+\s+)?translation(?:\s+into\s+[a-zA-Z]+)?:?\s*)?",
            r"^The\s+translation(?:\s+into\s+[a-zA-Z]+)?\s+is:?\s*",
            r"^Translation\s*(?:into\s+[a-zA-Z]+)?:?\s*",
            r"^Translated\s+text:?\s*",
            r"^Vietnamese:?\s*",
            r"^Japanese:?\s*",
            r"^English:?\s*",
            r"^Bản\s+dịch:?\s*",
            r"^Câu\s+dịch:?\s*",
            r"^Dịch:?\s*",
            r"^翻訳:?\s*",
            r"^翻译(?:成|为)?(?:越南语|英语|日语)?:?\s*",
            r"^意思是:?\s*",
            r"^Input:\s*.*?\s*Translation:\s*",
        ]
        for p in preambles:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # 4. Remove parenthetical explanations, cultural notes, and annotations
        has_orig_parens = bool(re.search(r"[\(\[（【]", original_text))
        paren_explanation_pattern = (
            r"\s*[\(\[（【]\s*(?:"
            r"Note|Notes|Explanation|Meaning|Context|Literal|Literally|"
            r"Sensei|Senpai|Honorific|Informal|Formal|Polite|Casual|Slang|"
            r"Refers|Referring|This\s+means|Used\s+(?:when|to|as)|In\s+Japanese|"
            r"In\s+Vietnamese|In\s+English|A\s+term\s+of|Commonly\s+used|"
            r"Ghi\s+chú|Lưu\s+ý|Giải\s+thích|Ý\s+nghĩa|Nghĩa\s+là"
            r").*?[\)\]）】]"
        )
        cleaned = re.sub(paren_explanation_pattern, "", cleaned, flags=re.IGNORECASE).strip()

        # If original text had no parentheses, and target is vi or ja, strip any parenthetical English/Latin notes
        if not has_orig_parens and target_lang in ("vi", "ja"):
            cleaned = re.sub(
                r"\s*[\(\[（【][a-zA-Z0-9\s,.'’\"—\-:;!?]+[\)\]）】]",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip()

        # 5. Remove note / explanation / reasoning suffixes and conversational chatbot responses
        note_markers = [
            (
                r"I['’]m sorry,\s*(?:I['’]m not sure|I don['’]t understand|could you|"
                r"can you|what do you|as an AI|please clarify|but I).*"
            ),
            (
                r"I am sorry,\s*(?:I am not sure|I do not understand|could you|"
                r"can you|what do you|as an AI|please clarify|but I).*"
            ),
            r"I['’]m not sure what you mean.*",
            r"I am not sure what you mean.*",
            r"I don['’]t understand what you mean.*",
            r"I do not understand what you mean.*",
            r"Could you please (?:clarify|explain|repeat).*",
            r"Can you please (?:clarify|explain|repeat).*",
            r"Would you please (?:clarify|explain|repeat).*",
            r"Please clarify (?:your question|what you mean).*",
            r"Please explain (?:what you mean|it better).*",
            r"What do you mean by.*",
            r"How can I help you today.*",
            r"How may I assist you today.*",
            r"As an AI.*",
            r"As a language model.*",
            r"This is the most important thing.*",
            r"They are very friendly.*",
            r"No notes.*",
            r"No note.*",
            r"【.*",
            r"—.*",
            r"\*\*.*",
            r"Translate the following.*",
            r"Note:?.*",
            r"Notes:?.*",
            r"Explanation:?.*",
            r"Meaning:?.*",
            r"Literal\s+translation:?.*",
            r"Ghi chú:?.*",
            r"Lưu ý:?.*",
            r"Ý nghĩa:?.*",
            r"Giải thích:?.*",
            r"Alright, let's translate.*",
            r"Sure, here is.*",
            r"Here's the translation:?.*",
            r"Tôi xin lỗi, tôi không hiểu.*",
            r"Tôi không hiểu ý bạn.*",
            r"Bạn có thể giải thích rõ hơn.*",
            r"Ý bạn là gì.*",
            r"申し訳ありませんが、.*(?:分かりかねます|質問|理解).*",
            r"ご質問の意味が.*",
            r"これが最も重要.*",
            r"という意味.*",
            r"説明:?.*",
            r"注意:?.*",
            r"補足:?.*",
            r"翻译[为成][:：].*",
            r"意思[是为][:：].*",
        ]
        for marker in note_markers:
            cleaned = re.sub(marker, "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

        # 6. Trailing explanation sentences appended after punctuation
        trailing_expl_regex = (
            r"([.!?。！？])\s*(?:"
            r"(?:This|That|It)\s+(?:means|sentence|phrase|translates|is|implies|refers)|"
            r"The\s+(?:speaker|word|phrase|meaning|translation|sentence|term)|"
            r"Here\s+(?:is|,|we)|"
            r"In\s+(?:English|Vietnamese|Japanese|this\s+context)|"
            r"(?:Meaning|Note|Notes|Explanation|Literal|Literally|Context)\s*:?|"
            r"(?:Sensei|Senpai)\s+(?:means|is|refers|can)|"
            r"Used\s+(?:when|to|as)|"
            r"An?\s+(?:expression|term)\s+of"
            r").*"
        )
        cleaned = re.sub(trailing_expl_regex, r"\1", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

        # Hyphen/dash explanations
        cleaned = re.sub(
            r"\s*[-–—:]\s*(?:Note|Explanation|Meaning|Context|Sensei|This\s+means|The\s+speaker).*",
            "",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        ).strip()

        # Strip appended chatbot apologies after end-of-sentence punctuation if not an apology source
        is_source_apology = bool(
            re.search(r"(?:xin lỗi|xin loi|sorry|すみません|すいません|ごめん|申し訳)", original_text, re.IGNORECASE)
        )
        if not is_source_apology:
            cleaned = re.sub(r"([.!?。！？])\s*I['’]m sorry.*", r"\1", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
            cleaned = re.sub(r"([.!?。！？])\s*I am sorry.*", r"\1", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()
            cleaned = re.sub(
                r"([.!?。！？])\s*申し訳ありません.*", r"\1", cleaned, flags=re.IGNORECASE | re.DOTALL
            ).strip()

        # 7. For Japanese target: if Latin text appears after Japanese script, cut off Latin babble
        if target_lang == "ja":
            m_ja = re.search(
                r"([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF][\s\.\?!。！？]*)([a-zA-Z]{3,}.*)",
                cleaned,
            )
            if m_ja:
                cleaned = cleaned[: m_ja.start(2)].strip()

        # 8. For Vietnamese target: if pure ASCII English sentence appears after punctuation, strip it
        if target_lang == "vi":
            m_vi_trail = re.search(r"([.!?])\s+([A-Za-z\s,.'’\"—\-:;]+)$", cleaned)
            if m_vi_trail:
                trailing_segment = m_vi_trail.group(2).strip()
                en_indicator_words = {
                    "means",
                    "meaning",
                    "teacher",
                    "speaker",
                    "refers",
                    "referring",
                    "informal",
                    "formal",
                    "polite",
                    "casual",
                    "slang",
                    "translation",
                    "translates",
                    "sentence",
                    "phrase",
                    "note",
                    "notes",
                    "explanation",
                    "context",
                    "literally",
                    "literal",
                    "japanese",
                    "vietnamese",
                    "english",
                    "honorific",
                    "respect",
                    "cultural",
                    "culture",
                    "implies",
                    "indicating",
                    "indicates",
                    "used",
                    "term",
                    "addressing",
                    "respectful",
                }
                words = set(re.findall(r"[a-zA-Z]+", trailing_segment.lower()))
                if words & en_indicator_words or trailing_segment.lower().startswith(
                    ("this ", "the ", "it ", "in ", "note", "sensei ")
                ):
                    cleaned = cleaned[: m_vi_trail.start(1) + 1].strip()

        # 9. Strip original text echo if model echoed the source input
        if original_text and len(original_text.strip()) > 3:
            cleaned = re.sub(re.escape(original_text.strip()), "", cleaned, flags=re.IGNORECASE).strip()

        # 10. Collapse contiguous repetition loop pattern: (X)(X)+
        m = re.match(r"^(.{3,}?)\1+", cleaned)
        if m:
            cleaned = m.group(1).strip()

        # 11. Deduplicate consecutive identical sentences/phrases
        parts = re.split(r"([.!?。！？\n])", cleaned)
        sentences: list[str] = []
        curr = ""
        for p in parts:
            curr += p
            if p in ".!?。！？\n":
                if curr.strip() and (not sentences or sentences[-1].strip().lower() != curr.strip().lower()):
                    sentences.append(curr.strip())
                curr = ""
        if curr.strip() and (not sentences or sentences[-1].strip().lower() != curr.strip().lower()):
            sentences.append(curr.strip())
        joiner = "" if target_lang == "ja" else " "
        if sentences:
            cleaned = joiner.join(sentences)

        # 12. Cap excessive sentences if original text was short
        if original_text and len(original_text.strip()) > 0:
            orig_enders = len(re.findall(r"[.!?。！？]", original_text)) or 1
            max_allowed = 2 if orig_enders == 1 else orig_enders
            c_parts = re.split(r"([.!?。！？])", cleaned)
            if len(c_parts) > max_allowed * 2:
                reconstructed = []
                c_count = 0
                for i in range(0, len(c_parts) - 1, 2):
                    sent = c_parts[i] + c_parts[i + 1]
                    if sent.strip():
                        c_count += 1
                        reconstructed.append(sent.strip())
                        if c_count >= max_allowed:
                            break
                if reconstructed:
                    cleaned = joiner.join(reconstructed)

        # 13. Final loop collapse check
        m2 = re.match(r"^(.{4,}?)\1+$", cleaned)
        if m2:
            cleaned = m2.group(1).strip()

        return cleaned

    def validate(
        self, original_text: str, source_lang: Lang, target_lang: Lang, raw_translation: str
    ) -> ValidationResult:
        cleaned = self.clean(raw_translation, original_text=original_text, target_lang=target_lang)

        # 1. Non-empty check
        if not cleaned:
            return ValidationResult(is_valid=False, cleaned_text="", error_reason="Empty translation")

        # 2. Repeated source check
        if cleaned.lower() == original_text.strip().lower() and len(cleaned) > 3:
            return ValidationResult(is_valid=False, cleaned_text=cleaned, error_reason="Repeated source sentence")

        # 3. Script validation
        if target_lang == "ja":
            # Target ja should contain kana or kanji if source has letters
            if any(c.isalpha() for c in original_text) and not JA_REGEX.search(cleaned):
                return ValidationResult(is_valid=False, cleaned_text=cleaned, error_reason="Missing Japanese script")
        elif target_lang in ("vi", "en"):
            if not LATIN_REGEX.search(cleaned):
                return ValidationResult(is_valid=False, cleaned_text=cleaned, error_reason="Missing Latin script")
            if target_lang == "vi" and JA_REGEX.search(cleaned):
                return ValidationResult(
                    is_valid=False, cleaned_text=cleaned, error_reason="Contains CJK characters in Vietnamese output"
                )
            elif target_lang == "en":
                cjk_matches = JA_REGEX.findall(cleaned)
                latin_matches = LATIN_REGEX.findall(cleaned)
                if len(cjk_matches) >= len(latin_matches):
                    return ValidationResult(
                        is_valid=False,
                        cleaned_text=cleaned,
                        error_reason="Predominantly CJK characters in English output",
                    )

        return ValidationResult(is_valid=True, cleaned_text=cleaned)


mt_validator = MtValidator()
