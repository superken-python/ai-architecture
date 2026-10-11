import json
from collections.abc import AsyncGenerator

import httpx

from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import MtEngine
from rvt_ai.prompts.loader import get_prompt_loader
from rvt_contracts.messages import Lang


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
            "i'm sorry",
            "i’m sorry",
            "i am sorry",
            "i'm not sure",
            "i’m not sure",
            "i don't understand",
            "i don’t understand",
            "could you please",
            "could you clarify",
            "can you please",
            "please clarify",
            "please explain",
            "what do you mean",
            "as an ai",
            "how can i help",
            "this is the most important",
            "they are very friendly",
            "no notes",
            "translate the",
            "explanation:",
            "note:",
            "notes:",
            "申し訳ありません",
            "ご質問",
            "tôi xin lỗi",
        ]
        if any(b in lower for b in babble_markers):
            return True
        if target_lang == "ja" and any(c in text for c in "abcdefghijklmnopqrstuvwxyz"):
            # If Japanese translation has a long Latin word/phrase, it's likely leaked English babble
            words = text.split()
            if any(len(w) >= 4 and w.isascii() and w.isalpha() for w in words):
                return True
        return False

    async def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = ""
    ) -> AsyncGenerator[str, None]:
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
        }
        tgt_name = lang_names.get(target_lang, target_lang)

        prompt = (
            f"Translate the following speech directly into {tgt_name}. "
            f"Output ONLY the translated sentence, without any conversational response, "
            f"questions, notes, or explanations:\n\n{text}"
        )
        messages = [{"role": "user", "content": prompt}]

        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": 128,
            "temperature": 0.1,
            "top_p": 0.7,
            "stop": [
                "\n\n",
                "【",
                "**",
                "—",
                "Note:",
                "Notes:",
                "Explanation:",
                "Input:",
                "Translation:",
                "Text:",
                "Translate the",
                "No notes",
                "I'm sorry",
                "I’m sorry",
                "I'm not sure",
                "I’m not sure",
                "I don't",
                "I don’t",
                "Could you please",
                "Can you please",
                "This is the most",
                "申し訳ありません",
                "ご質問",
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
            except httpx.HTTPError as e:
                logger.error(f"MT request error to {self.api_url}: {e}")
                raise
