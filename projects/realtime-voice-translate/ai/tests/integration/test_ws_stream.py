import json
import time

from fastapi.testclient import TestClient

from rvt_ai.main import app


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
