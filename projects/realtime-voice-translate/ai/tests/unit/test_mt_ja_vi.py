"""Dịch Nhật → Việt: chữ Nhật còn sót, "Sensei", glossary, xưng hô, ngữ cảnh có bản dịch trước (docs 09 §9)."""

import os

import pytest

from rvt_ai.engines.fake import FakeAsrEngine, FakeVadEngine
from rvt_ai.engines.mt_llama import LlamaCppMtEngine, build_messages
from rvt_ai.engines.ports import MtHints
from rvt_ai.packs.glossary import load_glossary, load_phrasebook
from rvt_ai.pipeline.kana import katakana_to_romaji
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import MtFinal

PACKS = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packs"))
NARUTO = load_glossary(["default", "naruto"], packs_dir=PACKS)


class _RecordingMt:
    """Bộ dịch giả: trả lần lượt các bản dịch cho sẵn, ghi lại hints của mỗi lượt."""

    def __init__(self, outputs: list[str]):
        self.outputs = outputs
        self.calls: list[tuple[str, MtHints | None]] = []

    async def translate_stream(self, text, source_lang, target_lang, context="", hints=None):
        self.calls.append((text, hints))
        yield self.outputs.pop(0)


def _session(mt, events):
    async def send(event):
        events.append(event)

    return RVTSession("test-ja-vi", FakeVadEngine(), FakeAsrEngine(), mt, send, glossary=NARUTO)


def _finals(events):
    return [e.text for e in events if isinstance(e, MtFinal)]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Thầy カカシ, thầy đến muộn rồi.", "Thầy Kakashi, thầy đến muộn rồi."),
        ("ナルト, サスケ", "Naruto, Sasuke"),
        ("ラーメン", "Ramen"),
        ("チャクラ", "Chakura"),
        ("マッチ", "Matchi"),
        ("Không có chữ Nhật.", "Không có chữ Nhật."),
    ],
)
def test_katakana_to_romaji(text, expected):
    assert katakana_to_romaji(text) == expected


def test_glossary_matches_longest_form_and_fixes_leftovers():
    assert NARUTO.match("カカシ先生、遅刻ですよ。", "ja", "vi") == [("カカシ先生", "thầy Kakashi")]
    assert ("火影", "Hokage") in NARUTO.match("火影になるんだ!", "ja", "vi")
    assert NARUTO.fix_leftovers("Tớ sẽ trở thành 火影!", "vi") == "Tớ sẽ trở thành Hokage!"
    assert NARUTO.addressing["vi"]


def test_phrasebook_translates_short_interjections():
    book = load_phrasebook("ja", packs_dir=PACKS)
    assert book.lookup("え?", "vi") == "Hả?"
    assert book.lookup("うん。", "vi") == "Ừ."
    assert book.lookup("くそっ", "vi") == "Chết tiệt!"
    assert book.lookup("先生、遅刻ですよ。", "vi") is None


def test_sensei_after_punctuation_is_not_treated_as_explanation():
    # Bản cũ cắt "Thầy ơi! Sensei đến muộn quá." còn "Thầy ơi! Sensei" (docs 09 §9)
    assert not LlamaCppMtEngine._is_babble("Thầy ơi! Sensei đến muộn quá.", "vi")
    assert not LlamaCppMtEngine._is_babble("Đúng vậy. Sensei nói thế.", "vi")
    assert LlamaCppMtEngine._is_babble("Thầy ơi! Sensei means teacher", "vi")


def test_prompt_has_glossary_history_addressing_and_neutral_examples():
    hints = MtHints(
        history=[("先生、遅刻ですよ!", "Thầy đến muộn rồi đấy!"), ("ああ。", None)],
        glossary=[("カカシ先生", "thầy Kakashi")],
        addressing=["Học trò nói với Kakashi: xưng 'em', gọi 'thầy'."],
    )
    system, user = (m["content"] for m in build_messages("カカシ先生、遅いよ!", "ja", "vi", hints=hints))
    assert "Học trò nói với Kakashi" in system
    assert "Kiki" not in system and "khổng lồ" not in system  # ví dụ cũ lấy từ một phim khác
    assert "may be cut off mid-sentence" in system
    assert "カカシ先生 → thầy Kakashi" in user
    assert "- 先生、遅刻ですよ! → Thầy đến muộn rồi đấy!" in user
    assert "- ああ。\n" in user + "\n"  # câu trước chưa dịch xong: chỉ có câu nguồn
    assert user.endswith("Translate from Japanese to Vietnamese:\nカカシ先生、遅いよ!")


@pytest.mark.asyncio
async def test_glossary_term_left_in_kanji_is_replaced_not_retried():
    # Bản cũ loại "Tớ sẽ trở thành 火影!" vì còn chữ Nhật rồi dịch lại không có ngữ cảnh (docs 09 §9)
    events: list = []
    mt = _RecordingMt(["Tớ sẽ trở thành 火影!"])
    session = _session(mt, events)
    session.recent_context.append("俺は火影になるんだ!")
    await session._run_mt(1, "俺は火影になるんだ!", "ja", "vi")
    assert _finals(events) == ["Tớ sẽ trở thành Hokage!"]
    assert len(mt.calls) == 1


@pytest.mark.asyncio
async def test_katakana_name_is_romanized():
    events: list = []
    mt = _RecordingMt(["Ê, ナルト! Đợi đã!"])
    session = _session(mt, events)
    await session._run_mt(1, "おい、ナル!待って!", "ja", "vi")  # tên viết khác glossary: vẫn đổi sang romaji
    assert _finals(events) == ["Ê, Naruto! Đợi đã!"]


@pytest.mark.asyncio
async def test_retry_keeps_history_and_glossary():
    events: list = []
    mt = _RecordingMt(["Đúng 正午 nhé.", "Đúng giữa trưa nhé."])
    session = _session(mt, events)
    session._remember_translation("集合は朝5時だ。", "vi", "Tập trung lúc 5 giờ sáng.")
    session.recent_context.extend(["集合は朝5時だ。", "正午ぴったりにな。"])
    await session._run_mt(2, "正午ぴったりにな。", "ja", "vi")
    assert _finals(events) == ["Đúng giữa trưa nhé."]
    (_, first), (_, retry) = mt.calls
    assert retry.strict and not first.strict
    assert retry.history == [("集合は朝5時だ。", "Tập trung lúc 5 giờ sáng.")]


@pytest.mark.asyncio
async def test_next_line_gets_previous_translation_and_addressing():
    events: list = []
    mt = _RecordingMt(["Thầy ơi, thầy đến muộn rồi!", "Xin lỗi, có con mèo chạy ngang qua."])
    session = _session(mt, events)
    for uid, line in enumerate(["カカシ先生、遅刻ですよ!", "悪い悪い、猫が目の前を横切ってな。"]):
        session.recent_context.append(line)
        await session._run_mt(uid, line, "ja", "vi")
    _, hints = mt.calls[1]
    assert hints.history == [("カカシ先生、遅刻ですよ!", "Thầy ơi, thầy đến muộn rồi!")]
    assert any("Kakashi" in a for a in hints.addressing)
    _, first = mt.calls[0]
    assert ("カカシ先生", "thầy Kakashi") in first.glossary


@pytest.mark.asyncio
async def test_interjection_uses_phrasebook_without_model():
    events: list = []
    mt = _RecordingMt([])
    session = _session(mt, events)
    await session._run_mt(1, "え?", "ja", "vi")
    assert _finals(events) == ["Hả?"]
    assert mt.calls == []
