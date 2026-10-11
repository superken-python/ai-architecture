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

    def clean(self, raw_translation: str) -> str:
        cleaned = raw_translation.strip()

        # 1. Remove note / explanation / reasoning suffixes and special brackets
        note_markers = [
            r"【.*",
            r"—.*",
            r"\*\*.*",
            r"Translate the following.*",
            r"Note:?.*",
            r"Explanation:?.*",
            r"Ghi chú:?.*",
            r"Alright, let's translate.*",
            r"Sure, here is.*",
            r"Here's the translation:?.*",
        ]
        for marker in note_markers:
            cleaned = re.sub(marker, "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

        # 2. Remove prefix like "Input: ... Translation: ..."
        cleaned = re.sub(r"^Input:\s*.*?\s*Translation:\s*", "", cleaned, flags=re.IGNORECASE | re.DOTALL).strip()

        # 3. Remove common preambles
        preambles = [
            r"^Here is the translation:?\s*",
            r"^Translation:?\s*",
            r"^Bản dịch:?\s*",
            r"^翻訳:?\s*",
            r"^The translation is:?\s*",
        ]
        for p in preambles:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

        # 4. Strip surrounding quotation marks
        if (cleaned.startswith('"') and cleaned.endswith('"')) or (
            cleaned.startswith("'") and cleaned.endswith("'")
        ):
            cleaned = cleaned[1:-1].strip()

        # If multiple lines, take the first non-empty line
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if lines:
            cleaned = lines[0]

        return cleaned

    def validate(
        self, original_text: str, source_lang: Lang, target_lang: Lang, raw_translation: str
    ) -> ValidationResult:
        cleaned = self.clean(raw_translation)

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
