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

        # 1. Remove note / explanation / reasoning suffixes and conversational chatbot responses
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
            r"Ghi chú:?.*",
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
        ]
        for marker in note_markers:
            cleaned = re.sub(marker, "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

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

        # 2. For Japanese target: if Latin text appears after Japanese script, cut off Latin babble
        if target_lang == "ja":
            m_ja = re.search(
                r"([\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF][\s\.\?!。！？]*)([a-zA-Z]{3,}.*)",
                cleaned,
            )
            if m_ja:
                cleaned = cleaned[: m_ja.start(2)].strip()

        # 3. Remove prefix like "Input: ... Translation: ..."
        cleaned = re.sub(r"^Input:\s*.*?\s*Translation:\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

        # 4. Remove common preambles
        preambles = [
            r"^Here is the translation:?\s*",
            r"^Translation:?\s*",
            r"^Bản dịch:?\s*",
            r"^翻訳:?\s*",
            r"^The translation is:?\s*",
        ]
        for p in preambles:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # 5. Strip surrounding quotation marks
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()

        # 6. Strip original text echo if model echoed the source input
        if original_text and len(original_text.strip()) > 3:
            cleaned = re.sub(re.escape(original_text.strip()), "", cleaned, flags=re.IGNORECASE).strip()

        # 7. Collapse contiguous repetition loop pattern: (X)(X)+
        m = re.match(r"^(.{3,}?)\1+", cleaned)
        if m:
            cleaned = m.group(1).strip()

        # 8. Deduplicate consecutive identical sentences/phrases
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

        # 9. Cap excessive sentences if original text was short
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

        # 10. Final loop collapse check
        m2 = re.match(r"^(.{4,}?)\1+$", cleaned)
        if m2:
            cleaned = m2.group(1).strip()

        # If multiple lines, take the first non-empty line
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            cleaned = lines[0]

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
        elif target_lang in ("vi", "en") and not LATIN_REGEX.search(cleaned):
            return ValidationResult(is_valid=False, cleaned_text=cleaned, error_reason="Missing Latin script")

        return ValidationResult(is_valid=True, cleaned_text=cleaned)


mt_validator = MtValidator()
