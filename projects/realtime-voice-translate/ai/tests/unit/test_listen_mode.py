"""Chế độ chỉ nghe trên GPU 8 GB: không có bộ dịch, mỗi ngôn ngữ một model nhận dạng (docs 10 §10.3)."""

import asyncio
import os

import pytest

from rvt_ai.core.config import settings
from rvt_ai.engines.asr_routed import LanguageRoutedAsrEngine, resolve_model
from rvt_ai.engines.fake import FakeAsrEngine, FakeVadEngine
from rvt_ai.engines.registry import build_engines_from_profile
from rvt_ai.packs.loader import PackRegistry
from rvt_ai.pipeline.session import RVTSession
from rvt_contracts.messages import AsrFinal, MtDelta, MtFinal

PACKS = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../packs"))


class _NamedAsr:
    """Engine giả ghi lại tên model và tham số của mỗi lượt."""

    def __init__(self, name: str, calls: list):
        self.name = name
        self.calls = calls

    def transcribe(self, audio, language=None, **kwargs):
        self.calls.append((self.name, language, kwargs))
        return f"{self.name}", language or "en", {"vi": 0.0, "en": 1.0, "ja": 0.0}


def test_listen_profile_has_no_translation_engine():
    profile = PackRegistry(PACKS).get_profile("listen")
    assert profile.mt.engine == "none"
    assert profile.asr.models["vi"] == "phowhisper-large-ct2"
    _, _, mt = build_engines_from_profile(profile)
    assert mt is None


def test_resolve_model(tmp_path):
    (tmp_path / "phowhisper-large-ct2").mkdir()
    assert resolve_model("phowhisper-large-ct2", str(tmp_path)) == str(tmp_path / "phowhisper-large-ct2")
    assert resolve_model("missing-ct2", str(tmp_path)) is None  # phải chuẩn bị trước, không tải được
    assert resolve_model("large-v3-turbo", str(tmp_path)) == "large-v3-turbo"  # faster-whisper tự tải


def test_routed_engine_picks_model_by_language(tmp_path):
    (tmp_path / "phowhisper-large-ct2").mkdir()
    calls: list = []
    engine = LanguageRoutedAsrEngine(
        "large-v3-turbo",
        {"vi": "phowhisper-large-ct2", "en": "large-v3-turbo"},
        lambda name: _NamedAsr(os.path.basename(name), calls),
        models_dir=str(tmp_path),
    )
    assert engine.transcribe(b"", "vi", beam_size=5)[0] == "phowhisper-large-ct2"
    assert engine.transcribe(b"", "en")[0] == "large-v3-turbo"
    assert engine.transcribe(b"", None)[0] == "large-v3-turbo"  # chưa biết ngôn ngữ: model mặc định
    assert calls[0] == ("phowhisper-large-ct2", "vi", {"beam_size": 5})


def test_routed_engine_falls_back_when_model_not_prepared(tmp_path):
    loaded: list[str] = []

    def factory(name):
        loaded.append(name)
        return _NamedAsr(name, [])

    engine = LanguageRoutedAsrEngine("large-v3-turbo", {"vi": "phowhisper-large-ct2"}, factory, str(tmp_path))
    assert loaded == ["large-v3-turbo"]  # không nạp model thiếu, cũng không nạp model mặc định hai lần
    assert engine.transcribe(b"", "vi")[0] == "large-v3-turbo"
    assert engine.model_for("vi") == "large-v3-turbo"


@pytest.mark.asyncio
async def test_session_without_translation_only_emits_transcripts(monkeypatch):
    monkeypatch.setattr(settings, "ASR_FINAL_BEAM_SIZE", 5)
    events: list = []
    calls: list = []

    async def send(event):
        events.append(event)

    class _Asr(FakeAsrEngine):
        def transcribe(self, audio, language=None, **kwargs):
            calls.append(kwargs)
            return super().transcribe(audio, language)

    session = RVTSession("listen", FakeVadEngine(), _Asr(), None, send)
    session.sides_config["A"] = "vi"
    await session.handle_turn_start("A")
    await session.handle_audio_chunk(b"\x01" * int(16000 * 2 * 0.3))
    await session.handle_audio_chunk(b"\x00" * int(16000 * 2 * 0.6))
    await asyncio.sleep(0.3)
    await asyncio.gather(*session.active_tasks, return_exceptions=True)
    await session.scheduler.stop()

    finals = [e for e in events if isinstance(e, AsrFinal)]
    assert len(finals) == 1 and finals[0].lang == "vi"
    assert not [e for e in events if isinstance(e, MtDelta | MtFinal)]
    assert any(c.get("beam_size") == 5 for c in calls)  # câu chốt dùng beam theo RVT_ASR_FINAL_BEAM_SIZE
