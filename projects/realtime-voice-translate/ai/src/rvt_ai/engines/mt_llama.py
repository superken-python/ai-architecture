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

    async def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = ""
    ) -> AsyncGenerator[str, None]:
        prompt = self.prompt_loader.render(
            "mt/hy-mt/default.j2", source_lang=source_lang, target_lang=target_lang, text=text, context=context
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a professional real-time voice translator for live speech conversation. "
                    "Translate directly and naturally from the source language to the target language. "
                    "CRITICAL: Output ONLY the translated sentence. "
                    "NEVER output explanations, notes, preambles, greetings, or the original text."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        payload = {
            "messages": messages,
            "stream": True,
            "max_tokens": 128,
            "temperature": 0.0,
            "top_p": 0.9,
            "stop": [
                "\n\n",
                "\nNote:",
                "\n**Note",
                "**Note",
                "Note:",
                "\nExplanation:",
                "Explanation:",
                "Input:",
                "\nInput:",
                "Translation:",
            ],
        }

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
                                        yield delta
                            except json.JSONDecodeError:
                                pass
            except httpx.HTTPError as e:
                logger.error(f"MT request error to {self.api_url}: {e}")
                raise
