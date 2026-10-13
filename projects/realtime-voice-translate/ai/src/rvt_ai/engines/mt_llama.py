import json
import re
from collections.abc import AsyncGenerator

import httpx

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import MtEngine, MtHints
from rvt_ai.prompts.loader import get_prompt_loader
from rvt_contracts.messages import Lang

# Lời giải thích nối sau một câu: "…. This means …", "…. Sensei means teacher". Không bắt câu dịch bình thường bắt đầu
# bằng "Sensei" ("Thầy ơi! Sensei đến muộn quá." từng bị cắt còn "Thầy ơi! Sensei", docs 09 §9)
EXPLANATION_AFTER_SENTENCE = (
    r"([.!?。！？])\s*(?:this\s|the\s|sensei\s+(?:means|is|refers|can)\b|it\s|in\s|meaning:|note:)"
)

LANG_NAMES: dict[str, str] = {"vi": "Vietnamese", "en": "English", "ja": "Japanese"}

# Ví dụ hội thoại trung tính (docs 09 §5.4): câu thường ngày, câu cảm thán, câu bị cắt giữa chừng, câu có tên riêng.
# Không lấy câu của một phim cụ thể, để bản dịch không bị kéo theo từ và văn phong của phim đó.
FEW_SHOTS: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("ja", "vi"): [
        ("遅れてごめん!電車が止まっちゃってさ。", "Xin lỗi tớ đến muộn! Tàu điện bị dừng giữa chừng ấy."),
        ("ユイちゃん、ちょっと待ってよ!", "Yui ơi, đợi tớ một chút!"),
        ("明日の会議は何時からですか?", "Cuộc họp ngày mai bắt đầu lúc mấy giờ ạ?"),
        ("それって、つまり", "Thế tức là"),
    ],
    ("ja", "en"): [
        ("遅れてごめん!電車が止まっちゃってさ。", "Sorry I'm late! The train stopped on the way."),
        ("ユイちゃん、ちょっと待ってよ!", "Yui, wait for me!"),
        ("それって、つまり", "So that means"),
    ],
    ("vi", "ja"): [
        ("Xin chào, hôm nay bạn thấy thế nào?", "こんにちは、今日の気分はどうですか？"),
        ("Cảm ơn bạn rất nhiều nhé!", "どうもありがとうございます！"),
    ],
}


def build_messages(
    text: str, source_lang: Lang, target_lang: Lang, context: str = "", hints: MtHints | None = None
) -> list[dict[str, str]]:
    """Prompt cho một lượt dịch. Phần hệ thống chỉ phụ thuộc cặp ngôn ngữ và quy ước xưng hô, nên llama.cpp dùng lại
    được bộ nhớ đệm prompt giữa các lượt; glossary và các câu trước nằm ở phần người dùng."""
    hints = hints or MtHints()
    src_name = LANG_NAMES.get(source_lang, source_lang)
    tgt_name = LANG_NAMES.get(target_lang, target_lang)

    system_content = (
        f"You are a professional, high-accuracy subtitle translator. "
        f"Translate spoken dialogue from {src_name} directly and naturally into {tgt_name}.\n\n"
        "CRITICAL RULES:\n"
        f"1. Output ONLY the raw {tgt_name} translation on a single line, nothing else.\n"
        "2. NEVER include any explanations, notes, pronunciation, pinyin, romaji, parentheses, "
        "cultural commentary, or conversational remarks.\n"
    )
    if target_lang == "vi":
        system_content += (
            "3. VIETNAMESE LANGUAGE REQUIREMENTS (STRICT):\n"
            "   - The translation MUST be 100% in natural Vietnamese using standard Latin script"
            " with diacritics (chữ Quốc ngữ).\n"
            "   - STRICTLY FORBIDDEN: DO NOT output or retain any Chinese characters (Hanzi / 汉字 / 漢字) or"
            " Japanese characters (Kanji / Kana) in the output under any circumstances.\n"
            "   - Translate all spoken words, colloquialisms, idioms, and fantasy/anime dialogue"
            " (including abilities, titles, and creatures) completely into Vietnamese.\n"
            "   - Choose Vietnamese pronouns that fit who is speaking to whom, and keep them consistent with the"
            " previous lines.\n"
        )
    elif target_lang == "ja":
        system_content += (
            "3. JAPANESE LANGUAGE REQUIREMENTS (STRICT):\n"
            "   - The translation MUST be natural spoken Japanese script (Kanji, Hiragana, Katakana).\n"
            "   - STRICTLY FORBIDDEN: Do not output English or Latin characters.\n"
        )
    elif target_lang == "en":
        system_content += (
            "3. ENGLISH LANGUAGE REQUIREMENTS (STRICT):\n"
            "   - The translation MUST be natural spoken English.\n"
            "   - STRICTLY FORBIDDEN: Do not output Chinese or Japanese characters.\n"
        )
    if source_lang == "ja" and target_lang in ("vi", "en"):
        system_content += "4. Write Japanese personal names in Latin letters (for example Naruto, Kakashi).\n"
    system_content += (
        "5. The input is one line of live subtitles and may be cut off mid-sentence. Translate only what is there;"
        " never complete the sentence or add content.\n"
    )
    if hints.addressing:
        system_content += "\nADDRESSING CONVENTIONS:\n" + "".join(f"- {a}\n" for a in hints.addressing)
    shots = FEW_SHOTS.get((source_lang, target_lang))
    if shots:
        system_content += "\nFEW-SHOT EXAMPLES:\n" + "".join(f"Input: {i}\nOutput: {o}\n" for i, o in shots)

    parts: list[str] = []
    if hints.glossary:
        parts.append(
            "Glossary (use exactly these translations): " + "; ".join(f"{src} → {tgt}" for src, tgt in hints.glossary)
        )
    if hints.history:
        lines = "".join(f"- {src} → {tr}\n" if tr else f"- {src}\n" for src, tr in hints.history)
        parts.append(f"Previous lines (source → translation already shown):\n{lines.rstrip()}")
    elif context and context.strip():
        parts.append(f"Previous context: {context.strip()}")
    if hints.strict:
        parts.append(f"Your previous answer still contained {src_name} characters. Write everything in {tgt_name}.")
    parts.append(f"Translate from {src_name} to {tgt_name}:\n{text}")

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n\n".join(parts)},
    ]


class LlamaCppMtEngine(MtEngine):
    def __init__(self, api_url: str = "http://mt:8080/v1", timeout_sec: float = 5.0):
        self.api_url = api_url.rstrip("/")
        self.timeout_sec = timeout_sec
        self.prompt_loader = get_prompt_loader()

    @staticmethod
    def _is_repeating(text: str) -> bool:
        trimmed = text.strip()
        if len(trimmed) >= 12:
            # Word-level repetition check
            words = trimmed.split()
            if len(words) >= 4:
                for n in range(2, min(8, len(words) // 2 + 1)):
                    if words[-n:] == words[-2 * n : -n]:
                        return True
            # Substring loop check (for Japanese / continuous text)
            for l_sub in range(4, min(35, len(trimmed) // 2 + 1)):
                if trimmed[-l_sub:] == trimmed[-2 * l_sub : -l_sub]:
                    return True
        return False

    @staticmethod
    def _is_babble(text: str, target_lang: Lang) -> bool:
        lower = text.lower()
        babble_markers = [
            "i'm not sure what you mean",
            "i’m not sure what you mean",
            "i don't understand what you mean",
            "i don’t understand what you mean",
            "could you please clarify",
            "could you please explain",
            "can you please clarify",
            "can you please explain",
            "please clarify your question",
            "please explain what you mean",
            "what do you mean by",
            "as an ai",
            "how can i help you",
            "this is the most important thing",
            "they are very friendly",
            "no notes",
            "translate the following",
            "explanation:",
            "note:",
            "notes:",
            "meaning:",
            "literal translation:",
            "(note",
            "(explanation",
            "(meaning",
            "(context",
            "(literal",
            "(informal",
            "(formal",
            "(polite",
            "(sensei",
            "(used ",
            "this means that",
            "this sentence means",
            "this phrase means",
            "this means ",
            "the speaker is",
            "the word ",
            "sensei means",
            "here is the translation",
            "here's the translation",
            "ghi chú:",
            "lưu ý:",
            "giải thích:",
            "ý nghĩa:",
            "ご質問の意味が",
        ]
        if any(b in lower for b in babble_markers):
            return True
        if target_lang == "ja" and any(c in text for c in "abcdefghijklmnopqrstuvwxyz"):
            # If Japanese translation has a long Latin word/phrase, it's likely leaked English babble
            words = text.split()
            if any(len(w) >= 4 and w.isascii() and w.isalpha() for w in words):
                return True
        return bool(target_lang in ("vi", "ja") and re.search(EXPLANATION_AFTER_SENTENCE, lower))

    async def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = "", hints: MtHints | None = None
    ) -> AsyncGenerator[str, None]:
        # Collapse excessive repetitive characters in input text (e.g. scream loop うおおおお... 500 times)
        text = re.sub(r"(.)\1{7,}", r"\1\1\1\1\1", text).strip()
        text = re.sub(r"(.{2,6}?)\1{5,}", r"\1\1\1", text).strip()
        if not text:
            return

        messages = build_messages(text, source_lang, target_lang, context=context, hints=hints)

        # Dynamic max_tokens scaled with source text length, capped at 256 for subtitle stability:
        if source_lang == "ja" or len(text.split()) <= 1:
            dynamic_max_tokens = max(64, min(256, max(len(text), 1) * 2))
        else:
            dynamic_max_tokens = max(64, min(256, max(len(text.split()), 1) * 3))

        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": dynamic_max_tokens,
            "temperature": 0.1,
            "top_p": 0.7,
            # Không dừng ở "—" hay "**": "Đợi đã — ê!" sẽ chỉ còn "Đợi đã". mt_validator và cleanText.ts đã đổi "—"
            # thành ", " và bỏ ký hiệu "**" mà giữ chữ (docs 08 §3.5).
            "stop": [
                "\n",
                "\n\n",
                "【",
                "(Note",
                " (Note",
                "(note",
                " (note",
                "(Explanation",
                " (Explanation",
                "(Meaning",
                " (Meaning",
                "(Literal",
                " (Literal",
                "(Context",
                " (Context",
                "(Informal",
                " (Informal",
                "(Formal",
                " (Formal",
                "(Polite",
                " (Polite",
                "(Sensei",
                " (Sensei",
                "(Used",
                " (Used",
                "Note:",
                "Notes:",
                "Explanation:",
                "Meaning:",
                "Input:",
                "Translation:",
                "Text:",
                "Translate the",
                "No notes",
                "This means",
                " This means",
                "This sentence",
                " This sentence",
                "The speaker",
                " The speaker",
                "Sensei means",
                " Sensei means",
                "I'm not sure what you mean",
                "I’m not sure what you mean",
                "Could you please clarify",
                "Can you please clarify",
                "Could you please explain",
                "As an AI",
                "This is the most",
                "ご質問",
                "翻译",
                "翻译为",
                "翻译成",
                "意思是",
            ],
        }

        accumulated = ""
        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            try:
                async with client.stream("POST", f"{self.api_url}/chat/completions", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                choices = data.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {}).get("content", "")
                                    if delta:
                                        accumulated += delta
                                        if self._is_repeating(accumulated) or self._is_babble(accumulated, target_lang):
                                            break
                                        yield delta
                            except json.JSONDecodeError:
                                pass
            except httpx.HTTPStatusError as e:
                err_body = await e.response.aread()
                err_str = err_body.decode("utf-8", errors="ignore")
                logger.error(f"MT request error to {self.api_url}: HTTP {e.response.status_code} - {err_str}")
                raise
            except httpx.HTTPError as e:
                logger.error(f"MT request error to {self.api_url}: {e}")
                raise
