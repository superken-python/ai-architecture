import asyncio
import os
import wave

import numpy as np
import pytest

from rvt_ai.engines.fake import FakeAsrEngine, FakeMtEngine, FakeVadEngine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.pipeline.scheduler import AsrScheduler
from rvt_ai.pipeline.segmenter import SegmentStats
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, AsrPartial, MtDelta, MtFinal, Vad

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../models"))
SPEECH_WAV = os.path.join(os.path.dirname(__file__), "../fixtures/speech_16k.wav")


@pytest.mark.asyncio
async def test_session_detects_quiet_far_speech_with_real_vad():
    if not os.path.exists(os.path.join(MODELS_DIR, "silero_vad.onnx")):
        pytest.skip("silero_vad.onnx model not downloaded yet")
    with wave.open(SPEECH_WAV) as w:
        speech = np.frombuffer(w.readframes(w.getnframes()), np.int16)
    # Giảm 26 dB (~ -50 dBFS): trước đây luật `rms > 0.04` không bao giờ nhận đoạn này là tiếng nói
    far = (speech.astype(np.float32) * 10 ** (-26 / 20)).astype(np.int16)
    audio = np.concatenate([far, np.zeros(16000, dtype=np.int16)]).tobytes()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession(
        "test-far", SileroVadEngine(model_dir=MODELS_DIR), FakeAsrEngine(), FakeMtEngine(), mock_send_event
    )
    await session.handle_turn_start("A")
    for i in range(0, len(audio), 1280):  # khung 40 ms như AudioWorklet
        await session.handle_audio_chunk(audio[i : i + 1280])
    await asyncio.sleep(0.3)

    assert any(isinstance(e, Vad) and e.speaking for e in events)
    assert len([e for e in events if isinstance(e, AsrFinal)]) >= 1


@pytest.mark.asyncio
async def test_session_basic_flow():
    vad = FakeVadEngine()
    asr = FakeAsrEngine()
    mt = FakeMtEngine()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-1", vad, asr, mt, mock_send_event)

    # 1. Turn start A
    await session.handle_turn_start("A")

    # 2. Add speech chunk
    # Create 300ms of speech
    chunk_speech = b"\x01" * int(16000 * 2 * 0.3)
    await session.handle_audio_chunk(chunk_speech)

    # Wait to make sure MT tasks don't get triggered early
    await asyncio.sleep(0.1)

    # 3. Add silence to trigger final
    chunk_silence = b"\x00" * int(16000 * 2 * 0.6)  # 600ms silence
    await session.handle_audio_chunk(chunk_silence)

    # Give MT tasks time to run
    await asyncio.sleep(0.5)

    # Check emitted events
    assert any(isinstance(e, Vad) and e.speaking is True for e in events)
    assert any(isinstance(e, Vad) and e.speaking is False for e in events)

    asr_finals = [e for e in events if isinstance(e, AsrFinal)]
    assert len(asr_finals) == 1
    assert asr_finals[0].side == "A"
    assert asr_finals[0].lang == "vi"  # Default from fake ASR

    mt_finals = [e for e in events if isinstance(e, MtFinal)]
    assert len(mt_finals) == 2
    targets = [e.target for e in mt_finals]
    assert "en" in targets
    assert "ja" in targets


@pytest.mark.asyncio
async def test_session_vad_event_follows_segmenter_through_short_pause():
    vad = FakeVadEngine()
    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-3", vad, FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    await session.handle_turn_start("A")

    await session.handle_audio_chunk(b"\x01" * int(16000 * 2 * 0.3))  # 300ms speech
    await session.handle_audio_chunk(b"\x00" * int(16000 * 2 * 0.2))  # 200ms pause < min_silence_ms

    # Khoảng lặng ngắn giữa câu không được báo "ngừng nói" (trước đây event vad nhấp nháy theo từng chunk)
    vad_events = [e.speaking for e in events if isinstance(e, Vad)]
    assert all(vad_events) and len(vad_events) >= 1


@pytest.mark.asyncio
async def test_session_turn_stop_flushes_audio():
    vad = FakeVadEngine()
    asr = FakeAsrEngine()
    mt = FakeMtEngine()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-2", vad, asr, mt, mock_send_event)

    await session.handle_turn_start("A")
    # Add 400ms of speech without adding silence
    chunk_speech = b"\x01" * int(16000 * 2 * 0.4)
    await session.handle_audio_chunk(chunk_speech)

    # Immediately stop turn before any silence detection occurs
    await session.handle_turn_stop()

    await asyncio.sleep(0.5)

    asr_finals = [e for e in events if isinstance(e, AsrFinal)]
    assert len(asr_finals) == 1
    assert asr_finals[0].side == "A"


@pytest.mark.asyncio
async def test_session_run_mt_stream_and_deltas():
    from rvt_ai.pipeline.mt_validator import mt_validator

    mt_validator._exact_cache.clear()

    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-mt", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    await session._run_mt(uid=1, text="こんにちは", source="ja", target="vi")

    deltas = [e for e in events if isinstance(e, MtDelta)]
    finals = [e for e in events if isinstance(e, MtFinal)]
    assert len(deltas) > 0
    assert len(finals) == 1
    assert finals[0].text == "Hôm nay thời tiết rất đẹp."


def test_strip_committed_prefix_golden_case():
    from rvt_ai.pipeline.session import strip_committed_prefix

    committed = "夢は自分の中に留めておく。"
    full = "夢は自分の中に留めておく俺にあるのは目的だ一族"
    res = strip_committed_prefix(full, committed)
    assert res == "俺にあるのは目的だ一族"

    # Space differences and punctuation
    c2 = "Xin chào các bạn."
    f2 = "Xin chào các bạn! Hôm nay trời đẹp."
    assert strip_committed_prefix(f2, c2) == "Hôm nay trời đẹp."


@pytest.mark.asyncio
async def test_session_all_committed_closes_ghost_card():
    events = []

    async def mock_send_event(event):
        events.append(event)

    session = RVTSession("test-ghost", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.last_partial_uid = 42
    session.committed_sentences = ["夢は自分の中に留めておく。"]

    stats = SegmentStats(speech_ms=2000, prob_mean=0.8, prob_max=0.9)

    # Simulate Whisper returning the sentence that was already committed
    class MockAsr:
        def transcribe(self, *args, **kwargs):
            return "夢は自分の中に留めておく", "ja", {"ja": 1.0}

    session.utterance_id_counter = 42
    session.scheduler = AsrScheduler(MockAsr().transcribe)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)

    # Must emit AsrFinal with text="" for uid=42 to clear the card
    empty_finals = [e for e in events if isinstance(e, AsrFinal) and e.utterance_id == 42 and e.text == ""]
    assert len(empty_finals) == 1


@pytest.mark.asyncio
async def test_session_emits_whole_segment_without_holding_tail():
    # Không giữ phần đuôi sau dấu kết câu để ghép vào đoạn sau nữa (docs 08 §3.4): mỗi đoạn là một thẻ, dịch cả đoạn
    events = []

    async def mock_send_event(event):
        events.append(event)

    texts = iter(["私だって知らないわ。少しは", "我慢しなさい"])

    class ScriptedAsr:
        def transcribe(self, *args, **kwargs):
            return next(texts), "ja", {"ja": 1.0}

    session = RVTSession("test-tail", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(ScriptedAsr().transcribe)
    stats = SegmentStats(speech_ms=2000, prob_mean=0.8, prob_max=0.9)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)
    await asyncio.sleep(2.0)  # nếu còn bộ hẹn giờ giữ phần đuôi (1,5 s) thì nó đã kịp chốt thêm một thẻ

    finals = [(e.utterance_id, e.text) for e in events if isinstance(e, AsrFinal)]
    assert finals == [(0, "私だって知らないわ。少しは"), (1, "我慢しなさい")]
    await session.close()


@pytest.mark.asyncio
async def test_run_mt_keeps_raw_translation_when_validator_crashes(monkeypatch):
    # Bộ làm sạch lỗi thì phải hiện bản dịch thô, không thay bằng "[Lỗi dịch vi]" (docs 08 §3.1)
    from rvt_ai.pipeline.mt_validator import mt_validator

    events = []

    async def mock_send_event(event):
        events.append(event)

    def broken_validate(*args, **kwargs):
        raise AttributeError("'str' object has no attribute 'endsWith'")

    monkeypatch.setattr(mt_validator, "validate", broken_validate)
    session = RVTSession("test-validator-crash", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    await session._run_mt(7, "検証用の一文です。", "ja", "vi")

    finals = [e for e in events if isinstance(e, MtFinal)]
    assert len(finals) == 1
    assert finals[0].text == "Hôm nay thời tiết rất đẹp."
    await session.close()


@pytest.mark.asyncio
async def test_empty_final_does_not_wipe_previous_card():
    # Đoạn 1 có chữ tạm (uid 0) rồi chốt có chữ; đoạn 2 ngắn, chưa có chữ tạm, nhận dạng ra rỗng (ví dụ câu bịa vừa bị
    # lọc). Không được gửi asr.final rỗng cho uid 0 — web sẽ xoá thẻ đã chốt cùng bản dịch (docs 08 §3.2).
    events = []

    async def mock_send_event(event):
        events.append(event)

    texts = iter(["こんにちは。", ""])

    class ScriptedAsr:
        def transcribe(self, *args, **kwargs):
            return next(texts), "ja", {"ja": 1.0}

    session = RVTSession("test-wipe", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(ScriptedAsr().transcribe)
    stats = SegmentStats(speech_ms=900, prob_mean=0.6, prob_max=0.9)
    session.last_partial_uid = 0
    await session._process_final_audio(b"\x01" * 3200, "A", stats)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)

    assert [e.text for e in events if isinstance(e, AsrFinal) and e.utterance_id == 0] == ["こんにちは。"]
    await session.close()


@pytest.mark.asyncio
async def test_all_committed_segment_keeps_early_committed_card():
    # Câu chốt sớm lấy uid của thẻ chữ tạm (5); sau đó không còn chữ tạm mới. Chữ chốt của cả đoạn (uid 6) chỉ còn câu
    # đã chốt nên ra rỗng: không được xoá thẻ 5 (docs 08 §3.2).
    events = []

    async def mock_send_event(event):
        events.append(event)

    class MockAsr:
        def transcribe(self, *args, **kwargs):
            return "夢は自分の中に留めておく", "ja", {"ja": 1.0}

    session = RVTSession("test-commit-wipe", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(MockAsr().transcribe)
    session.last_partial_uid = 5
    session.utterance_id_counter = 6
    session.committed_sentences = ["夢は自分の中に留めておく。"]
    stats = SegmentStats(speech_ms=2000, prob_mean=0.8, prob_max=0.9)
    await session._process_final_audio(b"\x01" * 3200, "A", stats)

    assert not [e for e in events if isinstance(e, AsrFinal) and e.text == ""]
    await session.close()


@pytest.mark.asyncio
async def test_stale_partial_after_final_is_dropped():
    # Chữ tạm gửi đi khi đoạn còn uid 3, nhưng đoạn được chốt trong lúc chờ nên bộ đếm đã sang 4. Kết quả đó là chữ của
    # câu vừa chốt: không được hiện thành thẻ uid 4 (thẻ trùng, có thể treo luôn) (docs 08 §3.7).
    events = []

    async def mock_send_event(event):
        events.append(event)

    class MockAsr:
        def transcribe(self, *args, **kwargs):
            return "落ち着きなさいよ", "ja", {"ja": 1.0}

    session = RVTSession("test-stale", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(MockAsr().transcribe)
    session.current_side = "A"
    session.utterance_id_counter = 4

    await session._process_partial_audio(b"\x01" * 3200, "A", 3)
    assert not [e for e in events if isinstance(e, AsrPartial)]
    assert session.last_partial_uid is None

    # Chữ tạm của đúng đoạn đang nói vẫn hiện bình thường
    await session._process_partial_audio(b"\x01" * 3200, "A", 4)
    assert [e.utterance_id for e in events if isinstance(e, AsrPartial)] == [4]
    await session.close()


@pytest.mark.asyncio
async def test_partial_asr_gets_segment_vad_mean():
    # Chữ tạm cũng phải qua bộ lọc câu bịa theo VAD, nên nhận dạng tạm phải mang vad_mean của đoạn (docs 08 §3.3)
    calls = []

    class RecordingAsr:
        def transcribe(self, audio, language=None, vad_mean=None, initial_prompt=None):
            calls.append({"vad_mean": vad_mean, "initial_prompt": initial_prompt})
            return "テスト", "ja", {"ja": 1.0}

    async def mock_send_event(event):
        pass

    session = RVTSession("test-partial-vad", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(RecordingAsr().transcribe)
    await session.handle_turn_start("A")
    voiced, silent = b"\x01\x00" * 640, b"\x00\x00" * 640
    # 400 ms có tiếng (p = 1) rồi 400 ms lặng (p = 0, vẫn đang nói): chữ tạm bật ở khung thứ 20
    for chunk in [voiced] * 10 + [silent] * 10:
        await session.handle_audio_chunk(chunk)
    for _ in range(100):
        if calls:
            break
        await asyncio.sleep(0.02)

    assert calls
    assert abs(calls[0]["vad_mean"] - 0.5) < 1e-9
    await session.close()


@pytest.mark.asyncio
async def test_final_without_stats_is_not_dropped():
    # stats=None từng làm `stats.prob_mean` ném lỗi bên trong khối try, nên câu bị coi như nhận dạng ra rỗng
    events = []

    async def mock_send_event(event):
        events.append(event)

    class MockAsr:
        def transcribe(self, *args, **kwargs):
            return "こんにちは。", "ja", {"ja": 1.0}

    session = RVTSession("test-no-stats", FakeVadEngine(), FakeAsrEngine(), FakeMtEngine(), mock_send_event)
    session.scheduler = AsrScheduler(MockAsr().transcribe)
    await session._process_final_audio(b"\x01" * 3200, "A")

    assert [e.text for e in events if isinstance(e, AsrFinal)] == ["こんにちは。"]
    await session.close()


@pytest.mark.parametrize(
    ("full", "committed", "expected"),
    [
        # Chữ chốt của cả đoạn thêm "あ、" ở đầu: 873d676 cắt lệch thành "く。俺に…"
        ("あ、夢は自分の中に留めておく。俺にあるのは目的だ", "夢は自分の中に留めておく。", "俺にあるのは目的だ"),
        ("え夢は自分の中に留めておく俺にあるのは目的だ", "夢は自分の中に留めておく。", "俺にあるのは目的だ"),
        # Rơi ký tự đầu: 873d676 không khớp, câu hiện hai lần
        ("は自分の中に留めておく。俺にあるのは目的だ", "夢は自分の中に留めておく。", "俺にあるのは目的だ"),
        # Khác chữ viết: おく → 置く, ズレ → ずれ (golden_1, 482,7 s)
        ("夢は自分の中に留めて置く。俺にあるのは目的だ", "夢は自分の中に留めておく。", "俺にあるのは目的だ"),
        ("ずれてるのは先生の髪型だろ?", "ズレてるのは先生の髪型だろ?", ""),
        # Không liên quan: giữ nguyên, thà hiện trùng còn hơn mất chữ
        ("全然違う文章がここに来るとどうなる", "夢は自分の中に留めておく。", "全然違う文章がここに来るとどうなる"),
        ("そうだそうだ行こう", "そうだ。", "そうだ行こう"),
        ("はい", "はい。", ""),
    ],
)
def test_strip_committed_prefix_tolerates_asr_drift(full, committed, expected):
    # Căn bằng khoảng cách sửa thay cho SequenceMatcher (docs 08 §3.6)
    from rvt_ai.pipeline.session import strip_committed_prefix

    assert strip_committed_prefix(full, committed) == expected
