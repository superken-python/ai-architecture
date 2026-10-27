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


# API kiểu OpenAI chạy trên cloud (docs 10 §13). "llama-cpp" là server llama.cpp cục bộ.
HOSTED_PROVIDERS = ("openai", "azure")
# Tham số không bao giờ bỏ khi API báo lỗi: thiếu chúng thì không còn là một lượt dịch
_REQUIRED_PARAMS = ("messages", "model", "stream")
_DEPLOYMENT_IN_URL = re.compile(r"/deployments/([^/?]+)")


def deployment_from_url(url: str) -> str:
    """Tên deployment trong "Target URI" của Azure: …/openai/deployments/gpt-5.4-mini/chat/completions?api-version=…"""
    found = _DEPLOYMENT_IN_URL.search(url)
    return found.group(1) if found else ""


def default_reasoning_effort(model: str) -> str:
    """Mức suy luận thấp nhất theo họ model, để dịch nhanh.

    gpt-5.1 trở đi (gpt-5.4-mini…): "none", cũng là mặc định của các bản này. gpt-5, gpt-5-mini, gpt-5-nano:
    "minimal" (mặc định là "medium", chậm). Model khác: không gửi. Đoán theo tên model hoặc deployment; đặt tên
    deployment khác thì ghi rõ bằng RVT_MT_REASONING_EFFORT.
    """
    name = model.lower()
    if re.search(r"gpt-5\.\d", name):
        return "none"
    if re.search(r"gpt-5(?![.\d])", name):
        return "minimal"
    return ""


def hosted_payload(
    payload: dict,
    model: str,
    reasoning_effort: str = "",
    max_completion_tokens: int = 1024,
    include_model: bool = True,
) -> dict:
    """Đổi payload của llama.cpp sang dạng API kiểu OpenAI (OpenAI, Azure OpenAI; docs 09 §5.6, docs 10 §13).

    Model GPT-5 không nhận temperature, top_p, max_tokens; các bản mới còn không nhận stop. Nên chỉ gửi những gì cần:
    giới hạn token (gồm cả token suy luận, nên đặt rộng), mức suy luận, tên model. Không có chuỗi dừng: engine tự dừng ở
    cuối dòng đầu tiên.
    """
    out = {k: v for k, v in payload.items() if k not in ("top_p", "temperature", "stop", "max_tokens")}
    if max_completion_tokens:
        out["max_completion_tokens"] = max(max_completion_tokens, payload["max_tokens"])
    if reasoning_effort:
        out["reasoning_effort"] = reasoning_effort
    if model and include_model:
        out["model"] = model
    return out


class LlamaCppMtEngine(MtEngine):
    """Dịch qua /chat/completions: server llama.cpp cục bộ, hoặc API kiểu OpenAI trên cloud (OpenAI, Azure OpenAI).

    `api_url` là URL gốc (http://mt:8080/v1, https://api.openai.com/v1, https://<resource>.openai.azure.com/openai/v1)
    hoặc URL đầy đủ tới /chat/completions, như "Target URI" của một deployment Azure:
    https://<resource>.cognitiveservices.azure.com/openai/deployments/<deployment>/chat/completions?api-version=…
    Azure nhận khoá qua header `api-key`; OpenAI qua `Authorization: Bearer`.
    """

    def __init__(
        self,
        api_url: str = "http://mt:8080/v1",
        timeout_sec: float = 5.0,
        api_key: str = "",
        model: str = "",
        provider: str = "",
        reasoning_effort: str = "",
        max_completion_tokens: int = 1024,
    ):
        self.api_url = api_url.strip().rstrip("/")
        self.timeout_sec = timeout_sec
        self.api_key = api_key
        # URL của deployment Azure đã có tên deployment: không gửi "model" trong body
        self.deployment = deployment_from_url(self.api_url)
        self.model = model or self.deployment
        # Không ghi provider: đoán theo URL và khoá (có khoá mà không phải Azure thì là API kiểu OpenAI)
        self.provider = provider or ("azure" if ".azure.com" in self.api_url else "openai" if api_key else "llama-cpp")
        self.reasoning_effort = default_reasoning_effort(self.model) if reasoning_effort == "auto" else reasoning_effort
        # Có báo cáo gpt-5.4 vẫn suy luận khi có max_completion_tokens dù đặt "none": khi đó không gửi giới hạn. Engine
        # vẫn thôi đọc ở cuối dòng đầu, nên bản dịch không dài ra được.
        self.max_completion_tokens = 0 if self.reasoning_effort == "none" else max_completion_tokens
        # Tham số model đã từ chối (lỗi 400): không gửi lại ở các lượt sau
        self.dropped_params: set[str] = set()
        self.prompt_loader = get_prompt_loader()

    @property
    def hosted(self) -> bool:
        return self.provider in HOSTED_PROVIDERS

    @property
    def endpoint(self) -> str:
        # URL đầy đủ (Target URI của Azure, có api-version) dùng nguyên; URL gốc thì thêm /chat/completions
        return self.api_url if "/chat/completions" in self.api_url else f"{self.api_url}/chat/completions"

    def request(self, payload: dict) -> tuple[str, dict[str, str], dict]:
        """URL, header và body của một lượt dịch."""
        if not self.hosted:
            return self.endpoint, {}, payload
        body = hosted_payload(
            payload,
            self.model,
            self.reasoning_effort,
            self.max_completion_tokens,
            include_model=not self.deployment,
        )
        for param in self.dropped_params:
            body.pop(param, None)
        azure = self.provider == "azure"
        headers = {"api-key": self.api_key} if azure else {"Authorization": f"Bearer {self.api_key}"}
        return self.endpoint, headers, body

    def adapt_to_error(self, error_body: str, sent: dict) -> bool:
        """Lỗi 400 vì model không nhận một tham số: đổi hoặc bỏ tham số đó cho mọi lượt sau. True nếu nên gửi lại.

        Mỗi bản GPT-5 nhận một bộ tham số khác nhau: gpt-5-mini nhận reasoning_effort "minimal", gpt-5.4-mini thì không
        (thấp nhất là "none"); api-version cũ của Azure có thể chỉ nhận "low"; các bản mới không nhận stop. Thông báo
        lỗi nói tham số nào sai, và với reasoning_effort còn liệt kê các giá trị được nhận.
        """
        try:
            error = json.loads(error_body).get("error") or {}
        except (json.JSONDecodeError, AttributeError):
            error = {}
        message = str(error.get("message") or error_body)
        param = str(error.get("param") or "")
        if not param:
            found = re.search(r"(?:parameter|value|argument)[^']*'([a-z_]+)'", message)
            param = found.group(1) if found else ""

        if param == "reasoning_effort" or "reasoning_effort" in message:
            current = sent.get("reasoning_effort")
            # Muốn không suy luận ("none") mà không được: bỏ hẳn tham số, vì "none" là mặc định của các bản đó
            candidates = ("minimal",) if current == "none" else ("none", "minimal", "low")
            for value in candidates:
                if value != current and f"'{value}'" in message:
                    logger.warning(f"MT model does not accept reasoning_effort={current!r}; using {value!r}")
                    self.reasoning_effort = value
                    if value == "none":
                        self.max_completion_tokens = 0  # như lúc khởi tạo với "none"
                    return True
            if "reasoning_effort" in sent:
                logger.warning("MT model does not accept reasoning_effort; no longer sending it")
                self.dropped_params.add("reasoning_effort")
                return True
            return False
        if param and param in sent and param not in _REQUIRED_PARAMS:
            logger.warning(f"MT model does not accept {param!r}; no longer sending it")
            self.dropped_params.add(param)
            return True
        return False

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
                # Gửi lại tối đa 2 lần khi API từ chối một tham số (adapt_to_error)
                for attempt in range(3):
                    url, headers, body = self.request(payload)
                    async with client.stream("POST", url, json=body, headers=headers) as response:
                        if response.status_code >= 400:
                            # Đọc lỗi khi kết nối còn mở; đọc sau khi đóng thì mất nội dung lỗi
                            error_body = (await response.aread()).decode("utf-8", errors="ignore")
                            retry = response.status_code == 400 and self.hosted and attempt < 2
                            if retry and self.adapt_to_error(error_body, body):
                                continue
                            logger.error(f"MT request error to {url}: HTTP {response.status_code} - {error_body[:500]}")
                            response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            choices = data.get("choices", [])
                            delta = choices[0].get("delta", {}).get("content", "") if choices else ""
                            if not delta:
                                continue
                            line_done = False
                            if self.hosted and "\n" in delta:
                                # API trên cloud không có chuỗi dừng: chỉ lấy dòng đầu rồi thôi đọc, để câu chốt sớm
                                piece = delta if accumulated.strip() else delta.lstrip()
                                if "\n" in piece:
                                    piece, line_done = piece.split("\n", 1)[0], True
                                delta = piece
                            if delta:
                                accumulated += delta
                                if self._is_repeating(accumulated) or self._is_babble(accumulated, target_lang):
                                    break
                                yield delta
                            if line_done:
                                break
                    return
            except httpx.HTTPStatusError:
                raise  # đã ghi log ở trên, kèm nội dung lỗi
            except httpx.HTTPError as e:
                logger.error(f"MT request error to {self.api_url}: {e}")
                raise
