"""Dịch theo đoạn ở chế độ Video & Họp (docs 10 §13.9): gom câu liền nhau, dịch lại cả đoạn, bỏ lần dịch cũ."""

import asyncio

import pytest

from rvt_ai.engines.fake import FakeAsrEngine, FakeVadEngine
from rvt_ai.engines.ports import MtHints
from rvt_ai.pipeline.mt_validator import mt_validator
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, AsrPartial, MtDelta, MtFinal, SessionStart, SidesUpdate

SPEECH = b"\x01" * 1280  # 40 ms, như AudioWorklet
SILENCE = b"\x00" * 1280


class RecordingMt:
    """Bộ dịch giả: ghi nguồn và ngữ cảnh mỗi lượt; lượt thứ n trả "Lượt n có … ký tự." (chữ Latin, qua validator)."""

    def __init__(self, fail_calls: set[int] | None = None):
        self.calls: list[tuple[str, MtHints | None]] = []
        self.fail_calls = fail_calls or set()
        self.gates: dict[int, asyncio.Event] = {}

    async def translate_stream(self, text, source_lang, target_lang, context="", hints=None):
        n = len(self.calls) + 1
        self.calls.append((text, hints))
        if n in self.fail_calls:
            raise RuntimeError("API không trả lời")
        yield f"Lượt {n} "
        if n in self.gates:
            await self.gates[n].wait()
        yield f"có {len(text)} ký tự."


async def make_session(mt, mt_unit="paragraph", targets=("vi",)):
    events = []

    async def send(event):
        events.append(event)

    mt_validator._exact_cache.clear()
    session = RVTSession("para", FakeVadEngine(), FakeAsrEngine(), mt, send)
    await session.handle_session_start(SessionStart(targets=list(targets), mt_unit=mt_unit))
    return session, events


async def final(session, uid, text, start_ms, end_ms, lang="ja"):
    await session._emit_final_and_mt(
        uid, "A", text, lang, {lang: 1.0}, False, end_ms - (start_ms or 0), start_ms, end_ms
    )


async def drain(session):
    await asyncio.gather(*session.active_tasks)


@pytest.mark.asyncio
async def test_sentences_in_one_paragraph_are_translated_together():
    mt = RecordingMt()
    session, events = await make_session(mt)
    await final(session, 10, "人の、え、なんか就労の作業が", 0, 5000)
    await drain(session)
    await final(session, 11, "なんか減らすんじゃないかなということです。", 5200, 9000)
    await drain(session)

    assert [e.paragraph_id for e in events if isinstance(e, AsrFinal)] == [10, 10]
    assert [text for text, _ in mt.calls] == [
        "人の、え、なんか就労の作業が",
        "人の、え、なんか就労の作業がなんか減らすんじゃないかなということです。",
    ]
    finals = [e for e in events if isinstance(e, MtFinal)]
    assert [(e.utterance_id, e.revision) for e in finals] == [(10, 1), (10, 2)]
    assert finals[-1].text.startswith("Lượt 2")
    assert all(e.revision is not None for e in events if isinstance(e, MtDelta))


@pytest.mark.asyncio
async def test_long_pause_starts_new_paragraph_with_previous_one_as_context():
    mt = RecordingMt()
    session, events = await make_session(mt)
    await final(session, 1, "まず一つ目の話です。", 0, 3000)
    await drain(session)
    await final(session, 2, "次に二つ目の話です。", 6000, 9000)
    await drain(session)

    assert [e.paragraph_id for e in events if isinstance(e, AsrFinal)] == [1, 2]
    first_translation = next(e.text for e in events if isinstance(e, MtFinal) and e.utterance_id == 1)
    _, hints = mt.calls[1]
    assert hints.history == [("まず一つ目の話です。", first_translation)]
    # Câu của chính đoạn không bị đưa vào ngữ cảnh lần nữa
    await final(session, 3, "続きです。", 9100, 10000)
    await drain(session)
    text, hints = mt.calls[2]
    assert text == "次に二つ目の話です。続きです。"
    assert [src for src, _ in hints.history] == ["まず一つ目の話です。"]


@pytest.mark.asyncio
async def test_older_translation_of_the_paragraph_stops_when_a_newer_one_starts():
    mt = RecordingMt()
    mt.gates[1] = asyncio.Event()
    session, events = await make_session(mt)
    await final(session, 1, "最初の部分で", 0, 3000)
    await asyncio.sleep(0.05)  # lần dịch 1 đã gửi chữ đầu và đang chờ
    await final(session, 2, "続きの部分です。", 3100, 6000)
    await asyncio.sleep(0.05)
    mt.gates[1].set()
    await drain(session)

    finals = [e for e in events if isinstance(e, MtFinal)]
    assert [(e.utterance_id, e.revision) for e in finals] == [(1, 2)]
    late = [e for e in events if isinstance(e, MtDelta) and e.revision == 1]
    assert [e.delta for e in late] == ["Lượt 1 "]  # chỉ chữ gửi trước khi có lần mới


@pytest.mark.asyncio
async def test_failed_retranslation_keeps_the_previous_good_translation():
    mt = RecordingMt(fail_calls={2})
    session, events = await make_session(mt)
    await final(session, 1, "最初の部分です。", 0, 3000)
    await drain(session)
    await final(session, 2, "続きです。", 3100, 6000)
    await drain(session)

    finals = [e for e in events if isinstance(e, MtFinal)]
    assert [(e.revision, e.text) for e in finals] == [(1, finals[0].text), (2, finals[0].text)]
    assert not finals[-1].text.startswith("[")


@pytest.mark.asyncio
async def test_segment_mode_is_unchanged():
    mt = RecordingMt()
    session, events = await make_session(mt, mt_unit="segment")
    await final(session, 1, "最初の部分で", 0, 3000)
    await final(session, 2, "続きの部分です。", 3100, 6000)
    await drain(session)

    assert [e.paragraph_id for e in events if isinstance(e, AsrFinal)] == [None, None]
    assert sorted(text for text, _ in mt.calls) == sorted(["最初の部分で", "続きの部分です。"])
    assert all(e.revision is None for e in events if isinstance(e, (MtDelta, MtFinal)))


@pytest.mark.asyncio
async def test_switching_unit_closes_the_open_paragraph():
    mt = RecordingMt()
    session, events = await make_session(mt)
    await final(session, 1, "最初です。", 0, 3000)
    await session.handle_sides_update(SidesUpdate(sides={}, targets=["vi"], mt_unit="segment"))
    await session.handle_sides_update(SidesUpdate(sides={}, targets=["vi"], mt_unit="paragraph"))
    await final(session, 2, "続きです。", 3100, 6000)
    await drain(session)
    assert [e.paragraph_id for e in events if isinstance(e, AsrFinal)] == [1, 2]


@pytest.mark.asyncio
async def test_audio_stream_partials_and_finals_carry_the_paragraph():
    mt = RecordingMt()
    session, events = await make_session(mt, targets=("en",))
    await session.handle_turn_start("A")

    async def segment(speech_chunks=25, silence_chunks=15):
        for _ in range(speech_chunks):  # 1 s nói: có một chữ tạm ở 800 ms
            await session.handle_audio_chunk(SPEECH)
        await asyncio.sleep(0.3)
        for _ in range(silence_chunks):  # 600 ms lặng: chốt câu
            await session.handle_audio_chunk(SILENCE)
        await asyncio.sleep(0.3)

    await segment()
    await segment()
    await session.handle_turn_stop()
    await session.handle_turn_start("A")
    await segment()
    await drain(session)

    finals = [e for e in events if isinstance(e, AsrFinal)]
    partials = [e for e in events if isinstance(e, AsrPartial)]
    pid = finals[0].utterance_id
    assert [e.paragraph_id for e in finals] == [pid, pid, finals[2].utterance_id]
    assert finals[2].utterance_id != pid
    # Chữ tạm của câu thứ hai hiện ngay trong đoạn đang mở; chữ tạm đầu tiên chưa có đoạn
    assert partials[0].paragraph_id is None
    assert any(p.paragraph_id == pid and p.utterance_id == finals[1].utterance_id for p in partials)
    texts = [text for text, _ in mt.calls]
    assert texts[:2] == ["Hôm nay thời tiết rất đẹp.", "Hôm nay thời tiết rất đẹp. Hôm nay thời tiết rất đẹp."]
