import io
from fastapi.testclient import TestClient

from rvt_ai.main import app


def test_rest_health_endpoints():
    with TestClient(app) as client:
        # 1. Health live
        res_live = client.get("/api/health/live")
        assert res_live.status_code == 200
        assert res_live.json() == {"status": "ok"}

        # 2. Health ready
        res_ready = client.get("/api/health/ready")
        assert res_ready.status_code == 200
        data_ready = res_ready.json()
        assert data_ready["ready"] is True
        assert "profile" in data_ready
        assert "pack_revision" in data_ready

        # 3. Metrics
        res_metrics = client.get("/api/metrics")
        assert res_metrics.status_code == 200
        data_metrics = res_metrics.json()
        assert "active_sessions" in data_metrics
        assert "max_sessions" in data_metrics


def test_rest_session_and_translate():
    with TestClient(app) as client:
        # 1. Session token
        res_sess = client.post("/api/v1/session", json={"access_code": ""})
        assert res_sess.status_code == 200
        data_sess = res_sess.json()
        assert "token" in data_sess
        assert data_sess["expires_in"] > 0

        # 2. Translate endpoint
        res_tr = client.post("/api/v1/translate", json={"text": "Hello world", "source": "en"})
        assert res_tr.status_code == 200
        data_tr = res_tr.json()
        assert data_tr["source"] == "en"
        assert "vi" in data_tr["translations"]
        assert "ja" in data_tr["translations"]

        # 3. Speech-translate endpoint
        fake_wav = io.BytesIO(b"\x01" * 3200)
        res_st = client.post(
            "/api/v1/speech-translate",
            files={"file": ("test.wav", fake_wav, "audio/wav")}
        )
        assert res_st.status_code == 200
        data_st = res_st.json()
        assert "text" in data_st
        assert "source_lang" in data_st
        assert "translations" in data_st
