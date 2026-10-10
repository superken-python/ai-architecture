import asyncio
import json
import time
import sys
import websockets

async def run_smoke_ws(url: str = "ws://localhost:8000/ws"):
    print(f"Connecting to {url}...")
    try:
        async with websockets.connect(url, subprotocols=["rvt.v1"]) as ws:
            print("Connected with subprotocol rvt.v1.")
            
            # 1. Expect session.ready
            ready_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            ready = json.loads(ready_raw)
            assert ready["type"] == "session.ready", f"Unexpected initial event: {ready}"
            print(f"✓ session.ready received: session_id={ready['session_id']}")

            # 2. Ping / Pong
            t_now = int(time.time() * 1000)
            await ws.send(json.dumps({"type": "ping", "t": t_now}))
            pong_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            pong = json.loads(pong_raw)
            assert pong["type"] == "pong" and pong["t"] == t_now, f"Invalid pong: {pong}"
            print("✓ ping / pong latency check passed")

            # 3. Session Start
            await ws.send(json.dumps({
                "type": "session.start",
                "protocol": 1,
                "audio": {"rate": 16000, "format": "pcm_s16le"},
                "sides": {"A": {"lang": "auto"}, "B": {"lang": "auto"}}
            }))
            print("✓ session.start sent")

            # 4. Turn Start A
            await ws.send(json.dumps({"type": "turn.start", "side": "A"}))
            print("✓ turn.start (side A) sent")

            # 5. Send Audio Chunks (300ms speech + 600ms silence)
            t_start = time.time()
            speech_bytes = b"\x01" * int(16000 * 2 * 0.3)
            await ws.send(speech_bytes)

            silence_bytes = b"\x00" * int(16000 * 2 * 0.6)
            await ws.send(silence_bytes)

            # 6. Collect final events
            asr_final = None
            mt_finals = []
            
            while len(mt_finals) < 2 and time.time() - t_start < 8.0:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                if isinstance(msg_raw, str):
                    msg = json.loads(msg_raw)
                    m_type = msg.get("type")
                    if m_type == "vad":
                        print(f"  [event vad] speaking={msg['speaking']}")
                    elif m_type == "asr.partial":
                        print(f"  [event asr.partial] text='{msg['text']}'")
                    elif m_type == "asr.final":
                        asr_final = msg
                        print(f"✓ [event asr.final] text='{msg['text']}' lang={msg['lang']}")
                    elif m_type == "mt.final":
                        mt_finals.append(msg)
                        print(f"✓ [event mt.final] target={msg['target']} text='{msg['text']}'")

            assert asr_final is not None, "Did not receive asr.final"
            assert len(mt_finals) == 2, f"Expected 2 mt.finals, got {len(mt_finals)}"
            e2e_ms = int((time.time() - t_start) * 1000)
            print(f"✓ ALL SMOKE CHECKS PASSED in {e2e_ms}ms!")
            return True

    except Exception as e:
        print(f"✗ Smoke test failed: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws"
    success = asyncio.run(run_smoke_ws(target_url))
    sys.exit(0 if success else 1)
