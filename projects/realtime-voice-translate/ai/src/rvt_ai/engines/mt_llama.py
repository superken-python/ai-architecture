import json
import re
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
        return bool(
            target_lang in ("vi", "ja")
            and re.search(r"([.!?。！？])\s*(?:this\s|the\s|sensei\s|it\s|in\s|meaning:|note:)", lower)
        )

    async def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = ""
    ) -> AsyncGenerator[str, None]:
        lang_names = {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
        }
        tgt_name = lang_names.get(target_lang, target_lang)

        base_instruction = (
            f"You are a strict, direct subtitle translator. Translate the speech directly into {tgt_name}.\n"
            "CRITICAL RULES:\n"
            "1. Output ONLY the raw translated text, nothing else.\n"
            "2. NEVER include any notes, explanations, parentheses, cultural background, comments, "
            "or vocabulary meanings (e.g. do NOT write '(Note: ...)', '(Sensei means...)', '(Informal)', "
            "or '(Used when...)').\n"
            "3. NEVER explain cultural terms, titles, honorifics (like Sensei, Senpai, San, Kun, Chan), or grammar.\n"
            "4. NEVER include preambles like 'Here is the translation:' or conversational pleasantries.\n"
            "5. Output exactly one single line."
        )
        if context and context.strip():
            prompt = (
                f"{base_instruction}\n\nPrevious speech context:\n{context.strip()}\n\nSpeech to translate:\n{text}"
            )
        else:
            prompt = f"{base_instruction}\n\nSpeech to translate:\n{text}"
        messages = [{"role": "user", "content": prompt}]

        # Dynamic max_tokens scaled with source text length:
        # Non-spaced languages (Japanese) scale by char count, others by word count
        if source_lang == "ja" or len(text.split()) <= 1:
            dynamic_max_tokens = max(128, min(512, len(text) * 3))
        else:
            dynamic_max_tokens = max(128, min(512, max(len(text.split()), 1) * 4))

        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": dynamic_max_tokens,
            "temperature": 0.1,
            "top_p": 0.7,
            "stop": [
                "\n",
                "\n\n",
                "【",
                "**",
                "—",
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
