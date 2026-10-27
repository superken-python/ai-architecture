"""Nhãn ngôn ngữ theo chữ nhận dạng, và câu không có chữ thì không dịch (docs 10 §13, ảnh chụp Video & Họp)."""

import asyncio

import pytest

from rvt_ai.engines.fake import FakeVadEngine
from rvt_ai.pipeline.lid_policy import correct_language, script_language
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, MtFinal

# Câu thật trong ảnh chụp: nửa A khoá 日本語, người nói tiếng Việt
VI_LINE = "Vì cái đó nó tiểu như so với phần mềm thì IBA đó là những cái category number."


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (VI_LINE, "vi"),
        ("Vâng.", "vi"),
        ("はい。", "ja"),
        ("ありがとうございました。", "ja"),
        ("IBAのカテゴリー番号です。", "ja"),
        ("OK, let's start the meeting.", "en"),
        ("I like the café here.", None),  # một chữ có dấu trong câu tiếng Anh: không đủ để coi là tiếng Việt
        ("2", None),
        ("OK", None),
    ],
)
def test_script_language(text, expected):
    assert script_language(text) == expected


def test_correct_language():
    assert correct_language(VI_LINE, "ja") == "vi"
    assert correct_language("はい。", "vi") == "ja"
    assert correct_language("OK, let's start the meeting.", "ja") == "en"
    assert correct_language("Toi di hoc", "vi") == "vi"  # tiếng Việt không dấu: giữ ngôn ngữ đã khoá
    assert correct_language("2", "ja") == "ja"


class _TextAsr:
    """ASR giả: trả lần lượt các câu cho sẵn, ngôn ngữ đúng như đã khoá (như Whisper khi bị ép ngôn ngữ)."""

    def __init__(self, texts):
        self.texts = list(texts)

    def transcribe(self, audio, language=None, **kwargs):
        return self.texts.pop(0), language or "ja", {"ja": 1.0, "en": 0.0, "vi": 0.0}


class _RecordingMt:
    def __init__(self):
        self.calls = []

    async def translate_stream(self, text, source_lang, target_lang, context="", hints=None):
        self.calls.append((text, source_lang, target_lang))
        yield "Vâng."


async def _run(texts, side_lang="ja", targets=("vi",)):
    events: list = []

    async def send(event):
        events.append(event)

    mt = _RecordingMt()
    session = RVTSession("lang", FakeVadEngine(), _TextAsr(texts), mt, send, glossary=None)
    session.sides_config["A"] = side_lang
    session.targets = list(targets)
    await session.handle_turn_start("A")
    for _ in texts:
        await session.handle_audio_chunk(b"\x01" * int(16000 * 2 * 0.3))
        await session.handle_audio_chunk(b"\x00" * int(16000 * 2 * 0.6))
        await asyncio.sleep(0.05)
    await asyncio.sleep(0.2)
    await asyncio.gather(*session.active_tasks, return_exceptions=True)
    await session.scheduler.stop()
    return events, mt


@pytest.mark.asyncio
async def test_vietnamese_speech_on_japanese_side_is_labelled_vi_and_not_translated_to_vi():
    events, mt = await _run([VI_LINE])
    finals = [e for e in events if isinstance(e, AsrFinal)]
    assert [(f.lang, f.text) for f in finals] == [("vi", VI_LINE)]
    assert mt.calls == []  # đích là tiếng Việt: không dịch tiếng Việt sang tiếng Việt


@pytest.mark.asyncio
async def test_japanese_line_is_translated_but_text_without_letters_is_not():
    events, mt = await _run(["今日の会議を始めます。", "2"])
    finals = [(e.lang, e.text) for e in events if isinstance(e, AsrFinal)]
    assert finals == [("ja", "今日の会議を始めます。"), ("ja", "2")]
    assert mt.calls == [("今日の会議を始めます。", "ja", "vi")]
    assert [e.text for e in events if isinstance(e, MtFinal)] == ["Vâng."]
