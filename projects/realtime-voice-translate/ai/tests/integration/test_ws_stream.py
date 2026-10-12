import json
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from rvt_ai.api.stream import active_sessions
from rvt_ai.core.config import settings
from rvt_ai.main import app


def test_websocket_session_uses_profile_vad_config():
    # Trước đây stream.py tạo RVTSession không truyền segmenter_config → profile chỉ đổi được threshold
    with TestClient(app) as client, client.websocket_connect("/ws", subprotocols=["rvt.v1"]) as ws:
        ready = json.loads(ws.receive_text())
        config = active_sessions[ready["session_id"]].segmenter.config
        profile_vad = app.state.profile.vad
        assert (config.threshold, config.neg_threshold) == (profile_vad.threshold, profile_vad.neg_threshold)
        assert (config.min_speech_ms, config.min_silence_ms) == (profile_vad.min_speech_ms, profile_vad.min_silence_ms)
        assert config.preroll_ms == profile_vad.preroll_ms


def test_websocket_end_to_end_flow():
    with TestClient(app) as client, client.websocket_connect("/ws", subprotocols=["rvt.v1"]) as ws:
        # 1. Expect session.ready
        ready_raw = ws.receive_text()
        ready = json.loads(ready_raw)
        assert ready["type"] == "session.ready"
        assert "session_id" in ready

        # 2. Send ping, expect pong
        ws.send_text(json.dumps({"type": "ping", "t": 12345}))
        pong = json.loads(ws.receive_text())
        assert pong["type"] == "pong"
        assert pong["t"] == 12345

        # 3. Send session.start
        ws.send_text(
            json.dumps(
                {
                    "type": "session.start",
                    "protocol": 1,
                    "audio": {"rate": 16000, "format": "pcm_s16le"},
                    "sides": {"A": {"lang": "auto"}, "B": {"lang": "auto"}},
                }
            )
        )

        # 4. Send turn.start for side A
        ws.send_text(json.dumps({"type": "turn.start", "side": "A"}))

        # 5. Send speech audio (300ms)
        speech_bytes = b"\x01" * int(16000 * 2 * 0.3)
        ws.send_bytes(speech_bytes)

        # Expect vad speaking: True
        vad1 = json.loads(ws.receive_text())
        assert vad1["type"] == "vad"
        assert vad1["speaking"] is True

        # 6. Send silence (600ms) to trigger final
        silence_bytes = b"\x00" * int(16000 * 2 * 0.6)
        ws.send_bytes(silence_bytes)

        # Collect events until we receive both mt.finals
        received_types = []
        mt_finals = []
        asr_final = None

        start_wait = time.time()
        while time.time() - start_wait < 5.0 and len(mt_finals) < 2:
            msg = json.loads(ws.receive_text())
            received_types.append(msg["type"])
            if msg["type"] == "asr.final":
                asr_final = msg
            elif msg["type"] == "mt.final":
                mt_finals.append(msg)

        assert asr_final is not None
        assert asr_final["side"] == "A"
        assert asr_final["lang"] in ("vi", "en", "ja")
        assert len(mt_finals) == 2

        # 7. Test invalid message handling
        ws.send_text(json.dumps({"type": "nonexistent_type"}))
        err_msg = json.loads(ws.receive_text())
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "invalid_message"


def _ready(ws) -> dict:
    msg = json.loads(ws.receive_text())
    assert msg["type"] == "session.ready"
    return msg


def _pong(ws, t: int) -> None:
    ws.send_text(json.dumps({"type": "ping", "t": t}))
    msg = json.loads(ws.receive_text())
    assert msg["type"] == "pong" and msg["t"] == t


def test_same_client_id_replaces_previous_connection_with_4409():
    # Trang nối lại sau khi mất mạng: kết nối cũ (thường đã chết) bị đóng bằng 4409, kết nối mới dùng được
    # (docs 08 §4.3)
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws?client_id=page-1", subprotocols=["rvt.v1"]) as old,
    ):
        _ready(old)
        with client.websocket_connect("/ws?client_id=page-1", subprotocols=["rvt.v1"]) as new:
            _ready(new)
            with pytest.raises(WebSocketDisconnect) as exc:
                old.receive_text()
            assert exc.value.code == 4409
            _pong(new, 1)


def test_different_client_ids_keep_both_connections():
    # Mỗi tab một client_id: hai tab không được đá nhau (873d676 dùng chung mã trong localStorage)
    with (
        TestClient(app) as client,
        client.websocket_connect("/ws?client_id=tab-a", subprotocols=["rvt.v1"]) as a,
        client.websocket_connect("/ws?client_id=tab-b", subprotocols=["rvt.v1"]) as b,
    ):
        _ready(a)
        _ready(b)
        _pong(a, 1)
        _pong(b, 2)


def test_reconnecting_page_is_not_blocked_by_its_own_stale_session(monkeypatch):
    # Đủ phiên: trang khác bị từ chối 4429, nhưng chính trang có phiên cũ nối lại thì được nhận vì phiên cũ bị thay
    with TestClient(app) as client:
        monkeypatch.setattr(settings, "MAX_SESSIONS", len(active_sessions) + 1)
        with client.websocket_connect("/ws?client_id=page-1", subprotocols=["rvt.v1"]) as old:
            _ready(old)
            with client.websocket_connect("/ws?client_id=page-2", subprotocols=["rvt.v1"]) as other:
                with pytest.raises(WebSocketDisconnect) as exc:
                    other.receive_text()
                assert exc.value.code == 4429
            with client.websocket_connect("/ws?client_id=page-1", subprotocols=["rvt.v1"]) as new:
                _ready(new)
                with pytest.raises(WebSocketDisconnect) as exc:
                    old.receive_text()
                assert exc.value.code == 4409
                _pong(new, 3)
