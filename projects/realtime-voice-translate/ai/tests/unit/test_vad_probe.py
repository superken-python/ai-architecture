"""Dò vùng audio to mà VAD bỏ sót khi thu âm tab (docs 09 §4.1)."""

import asyncio

import numpy as np
import pytest

from rvt_ai.engines.fake import FakeMtEngine
from rvt_ai.pipeline.session import RVTSession
from rvt_ai.pipeline.vad_probe import VadProbe, probe_text_ok
from rvt_contracts.messages import AsrFinal

FRAME = 640  # 40 ms ở 16 kHz
LOUD = (np.sin(np.arange(FRAME) / 3) * 8000).astype(np.int16).tobytes()  # khoảng −15 dBFS
QUIET = (np.sin(np.arange(FRAME) / 3) * 100).astype(np.int16).tobytes()  # khoảng −50 dBFS


def _feed(probe: VadProbe, frames: list[tuple[bytes, float, bool]]) -> list[bytes]:
    out = []
    for chunk, prob, speaking in frames:
        piece = probe.add(chunk, prob, speaking)
        if piece:
            out.append(piece)
    return out


def _ms(audio: bytes) -> int:
    return len(audio) * 1000 // 32000


def test_loud_region_missed_by_vad_is_sent_without_trailing_gap():
    frames = [(LOUD, 0.05, False)] * 75 + [(QUIET, 0.0, False)] * 20  # 3 s to, rồi 0,8 s lặng
    assert [_ms(p) for p in _feed(VadProbe(), frames)] == [3000]


def test_short_gaps_are_kept_inside_one_region():
    frames = ([(LOUD, 0.05, False)] * 25 + [(QUIET, 0.0, False)] * 10) * 2 + [(QUIET, 0.0, False)] * 20
    assert [_ms(p) for p in _feed(VadProbe(), frames)] == [1000 + 400 + 1000]


def test_short_region_and_quiet_or_detected_audio_are_ignored():
    assert _feed(VadProbe(), [(LOUD, 0.05, False)] * 40 + [(QUIET, 0.0, False)] * 20) == []  # 1,6 s
    assert _feed(VadProbe(), [(QUIET, 0.05, False)] * 100) == []  # nhỏ
    assert _feed(VadProbe(), [(LOUD, 0.6, False)] * 100) == []  # VAD đã thấy tiếng nói


def test_long_region_is_split_at_6s():
    frames = [(LOUD, 0.05, False)] * 200 + [(QUIET, 0.0, False)] * 20  # 8 s
    assert [_ms(p) for p in _feed(VadProbe(), frames)] == [6000, 2000]
    # khúc cuối dưới 1 s bị bỏ
    frames = [(LOUD, 0.05, False)] * 170 + [(QUIET, 0.0, False)] * 20  # 6,8 s
    assert [_ms(p) for p in _feed(VadProbe(), frames)] == [6000]


def test_region_ends_when_vad_starts_and_preroll_is_left_to_the_segmenter():
    frames = [(LOUD, 0.05, False)] * 75 + [(LOUD, 0.9, True)]
    assert [_ms(p) for p in _feed(VadProbe(), frames)] == [3000 - 400]


@pytest.mark.parametrize(
    ("text", "lang", "ok"),
    [
        ("引っかかった!引っかかったよ!", "ja", True),
        ("あーーーっ", "ja", False),
        ("うわあああ!", "ja", False),
        ("ん", "ja", False),
        ("me me me", "ja", False),
        ("I got you!", "en", True),
        ("", None, False),
    ],
)
def test_probe_text_filter(text, lang, ok):
    assert probe_text_ok(text, lang) is ok


class _BlindVad:
    """VAD không thấy gì: mọi khung p = 0,05."""

    def create_state(self):
        return self

    def reset(self):
        pass

    def process(self, chunk, state):
        return 0.05


class _ProbeAsr:
    def __init__(self, text: str):
        self.text = text
        self.calls: list[dict] = []

    def transcribe(self, audio, language=None, vad_mean=None, initial_prompt=None, min_avg_logprob=None):
        self.calls.append({"vad_mean": vad_mean, "prompt": initial_prompt, "min_avg_logprob": min_avg_logprob})
        return self.text, language or "ja", {"ja": 0.9, "en": 0.05, "vi": 0.05}


async def _run(source: str | None, text: str = "引っかかった!引っかかったよ!") -> tuple[list, _ProbeAsr]:
    events: list = []

    async def send(event):
        events.append(event)

    asr = _ProbeAsr(text)
    session = RVTSession("probe", _BlindVad(), asr, FakeMtEngine(), send, vad_probe=True)
    session.sides_config["A"] = "ja"
    await session.handle_turn_start("A", source)
    for _ in range(75):
        await session.handle_audio_chunk(LOUD)
    for _ in range(20):
        await session.handle_audio_chunk(QUIET)
    await asyncio.sleep(0.05)
    await asyncio.gather(*session.active_tasks, return_exceptions=True)
    await session.scheduler.stop()
    return [e for e in events if isinstance(e, AsrFinal)], asr


@pytest.mark.asyncio
async def test_tab_capture_recognizes_region_vad_missed():
    finals, asr = await _run("tab")
    assert [f.text for f in finals] == ["引っかかった!引っかかったよ!"]
    assert asr.calls == [{"vad_mean": 0.0, "prompt": None, "min_avg_logprob": -0.5}]


@pytest.mark.asyncio
async def test_mic_capture_does_not_probe():
    finals, asr = await _run("mic")
    assert finals == [] and asr.calls == []


@pytest.mark.asyncio
async def test_probe_drops_screams():
    finals, asr = await _run("tab", "あーーーっ")
    assert finals == [] and len(asr.calls) == 1
