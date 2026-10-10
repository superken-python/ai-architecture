import asyncio
from collections.abc import AsyncGenerator

from rvt_contracts.messages import Lang


class FakeVadState:
    def reset(self) -> None:
        pass


class FakeVadEngine:
    def create_state(self) -> FakeVadState:
        return FakeVadState()

    def process(self, chunk: bytes, state: FakeVadState) -> bool:
        # If chunk has non-zero bytes, it's speech
        return any(b != 0 for b in chunk)


class FakeAsrEngine:
    def transcribe(self, audio: bytes, language: Lang | None = None) -> tuple[str, Lang, dict[Lang, float]]:
        lang: Lang = language or "vi"
        probs: dict[Lang, float] = {"vi": 0.05, "en": 0.05, "ja": 0.05}
        probs[lang] = 0.90

        sample_texts = {
            "vi": "Hôm nay thời tiết rất đẹp.",
            "en": "Today the weather is very nice.",
            "ja": "今日はとてもいい天気ですね。",
        }
        text = sample_texts.get(lang, "Hôm nay thời tiết rất đẹp.")
        return (text, lang, probs)


class FakeMtEngine:
    async def translate_stream(
        self, text: str, source_lang: Lang, target_lang: Lang, context: str = ""
    ) -> AsyncGenerator[str, None]:
        translations = {
            ("vi", "ja"): "今日はとてもいい天気ですね。",
            ("vi", "en"): "Today the weather is very nice.",
            ("ja", "vi"): "Hôm nay thời tiết rất đẹp.",
            ("ja", "en"): "Today the weather is very nice.",
            ("en", "vi"): "Hôm nay thời tiết rất đẹp.",
            ("en", "ja"): "今日はとてもいい天気ですね。",
        }

        res = translations.get((source_lang, target_lang), f"[{target_lang}] {text}")
        # Yield words with small delay to simulate streaming
        parts = res.split(" ") if " " in res else list(res)
        for part in parts:
            yield part + (" " if " " in res else "")
            await asyncio.sleep(0.02)
