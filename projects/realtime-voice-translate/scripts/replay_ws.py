"""Đo trễ phụ đề của server RVT bằng cách phát một file WAV qua WebSocket đúng nhịp thời gian thực.

Script đóng vai web app: gửi `session.start`, `turn.start`, các khung PCM16 40 ms, rồi `turn.stop`; ghi lại lúc gửi
từng khung và lúc nhận từng event, rồi tính trễ cho từng câu. Không cần micro hay trình duyệt, nên đo lặp lại được
và so được trước/sau mỗi thay đổi.

Ví dụ trong mạng nội bộ (xem docs/06-dich-kip-loi-noi-nhanh.md §6):

    ffmpeg -i onepiece.mp4 -ss 60 -t 180 -ac 1 -ar 16000 -sample_fmt s16 onepiece.wav
    uv run --with websockets python scripts/replay_ws.py --url wss://192.168.2.69:8443/ws --insecure \
        --wav onepiece.wav --lang ja --target vi --out onepiece.json
"""

import argparse
import asyncio
import bisect
import json
import math
import ssl
import statistics
import sys
import time
import wave
from dataclasses import dataclass

import websockets

CHUNK_BYTES = 1280  # 40 ms PCM16 mono 16 kHz, đúng như AudioWorklet của web app
CHUNK_S = 0.04


@dataclass
class Segment:
    first: int  # khung đầu tiên server báo "đang nói"
    last: int  # khung server chốt câu (báo hết nói), hoặc khung cuối cùng nếu câu kết thúc vì turn.stop
    uid: int | None = None


def pct(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * len(ordered)))]


def fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f} s"


async def stream(args: argparse.Namespace) -> tuple[list[float], list[tuple[float, dict]]]:
    with wave.open(args.wav) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (16000, 1, 2):
            sys.exit("WAV phải là 16 kHz, mono, PCM16: ffmpeg -i IN -ac 1 -ar 16000 -sample_fmt s16 OUT.wav")
        pcm = w.readframes(w.getnframes())
    pcm += b"\x00" * int(args.tail * 32000)  # im lặng cuối để server tự chốt câu cuối cùng

    ssl_ctx = None
    if args.url.startswith("wss://"):
        ssl_ctx = ssl.create_default_context()
        if args.insecure:  # chứng chỉ tự ký / CA nội bộ chưa cài trên máy chạy script
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

    sent: list[float] = []  # lúc gửi khung thứ k, tính từ t0
    events: list[tuple[float, dict]] = []  # (lúc nhận, event), tính từ t0
    async with websockets.connect(args.url, subprotocols=["rvt.v1"], ssl=ssl_ctx, max_size=None, open_timeout=10) as ws:
        ready = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        if ready.get("type") != "session.ready":
            sys.exit(f"Server không trả session.ready: {ready}")
        print(f"Đã kết nối: session={ready['session_id']} profile={ready.get('profile')}", flush=True)
        await ws.send(
            json.dumps(
                {
                    "type": "session.start",
                    "protocol": 1,
                    "audio": {"rate": 16000, "format": "pcm_s16le"},
                    "sides": {"A": {"lang": args.lang}, "B": {"lang": args.target}},
                }
            )
        )
        # Audio của video: như web khi thu âm tab, để server bật bước dò VAD (docs 09 §4.1)
        await ws.send(json.dumps({"type": "turn.start", "side": "A", "source": "tab"}))
        t0 = time.monotonic()

        async def receive() -> None:
            async for message in ws:
                if isinstance(message, str):
                    events.append((time.monotonic() - t0, json.loads(message)))

        receiver = asyncio.create_task(receive())
        step = CHUNK_S / args.speed
        for k in range(len(pcm) // CHUNK_BYTES):
            delay = k * step - (time.monotonic() - t0)
            if delay > 0:
                await asyncio.sleep(delay)
            await ws.send(pcm[k * CHUNK_BYTES : (k + 1) * CHUNK_BYTES])
            sent.append(time.monotonic() - t0)
            if k and k % 1500 == 0:
                print(f"  đã gửi {k * CHUNK_S:.0f} s audio, nhận {len(events)} event", flush=True)
        await ws.send(json.dumps({"type": "turn.stop"}))
        stop_at = time.monotonic() - t0
        print(f"Đã gửi hết audio, chờ các câu còn lại (tối đa {args.drain:.0f} s)...", flush=True)
        # Chờ tới khi server im lặng 5 s (đã xử lý xong hàng đợi) hoặc hết thời gian chờ
        while time.monotonic() - t0 < stop_at + args.drain:
            await asyncio.sleep(0.5)
            last = events[-1][0] if events else stop_at
            if time.monotonic() - t0 - max(last, stop_at) > 5:
                break
        receiver.cancel()
    return sent, events


def analyze(sent: list[float], events: list[tuple[float, dict]], args: argparse.Namespace) -> dict:
    # Server hiện gửi một event `vad` cho mỗi khung 40 ms của lượt nói, nên event thứ k ứng với khung k: dựng ranh
    # giới câu theo chỉ số khung thì không lệch vì mạng hay vì server bận. Nếu server chỉ gửi `vad` khi trạng thái
    # đổi (docs/06 §5.4), suy ra khung từ lúc nhận: khung cuối cùng đã gửi trước đó, lệch cỡ độ trễ mạng.
    vad = [(t, ev["speaking"]) for t, ev in events if ev.get("type") == "vad"]
    per_frame = len(vad) == len(sent)
    if per_frame:
        marks = [(k, speaking) for k, (_, speaking) in enumerate(vad)]
    else:
        marks = [(max(0, bisect.bisect_right(sent, t) - 1), speaking) for t, speaking in vad]
    last_frame = len(sent) - 1
    segments: list[Segment] = []
    speaking = False
    for k, flag in marks:
        if flag and not speaking:
            segments.append(Segment(first=k, last=last_frame))
        elif not flag and speaking:
            segments[-1].last = k
        speaking = flag

    # Câu có phần tiếng nói < min_speech_ms bị server bỏ và không tốn utterance_id; các câu còn lại được đánh số
    # 0, 1, 2... theo đúng thứ tự. Khoảng cách khung tối thiểu của một câu được chốt vì im lặng:
    min_frames = math.ceil(args.min_speech_ms / 40) - 1 + math.ceil(args.min_silence_ms / 40)
    uid = 0
    for seg in segments:
        if seg.last - seg.first >= min_frames or seg.last == last_frame:
            seg.uid, uid = uid, uid + 1
    kept = [s for s in segments if s.uid is not None]

    finals: dict[int, tuple[float, dict]] = {}
    partials: dict[int, list[float]] = {}
    mt_final: dict[int, tuple[float, str]] = {}
    errors = 0
    for t, ev in events:
        kind = ev.get("type")
        if kind == "asr.final":
            finals.setdefault(ev["utterance_id"], (t, ev))
        elif kind == "asr.partial":
            partials.setdefault(ev["utterance_id"], []).append(t)
        elif kind == "mt.final" and ev["target"] == args.target:
            mt_final.setdefault(ev["utterance_id"], (t, ev["text"]))
        elif kind == "error":
            errors += 1

    def at(frame: int) -> float:
        return sent[min(frame, len(sent) - 1)]

    rows, mismatched = [], 0
    for seg in kept:
        t_final, ev = finals.get(seg.uid, (None, {}))
        text = ev.get("text", "")
        if t_final is not None:
            # Audio của câu = preroll (1–10 khung, gồm khung đầu) + các khung sau đó → kiểm tra việc ghép câu
            extra_ms = ev.get("audio_ms", 0) - (seg.last - seg.first) * 40
            slack = 0 if per_frame else 80
            mismatched += not 40 - slack <= extra_ms <= args.preroll_ms + 40 + slack
        t_mt, translation = mt_final.get(seg.uid, (None, ""))
        # Đoạn quá ngắn bị bỏ ngay trước đó cũng có thể đã gửi partial với cùng utterance_id → chỉ lấy partial sau đó
        t_partial = next((t for t in partials.get(seg.uid, []) if t >= at(seg.first)), None)
        rows.append(
            {
                "uid": seg.uid,
                "audio_start_s": round(seg.first * CHUNK_S, 2),
                "audio_end_s": round(seg.last * CHUNK_S, 2),
                "length_s": round((seg.last - seg.first) * CHUNK_S, 2),
                "first_partial_s": None if t_partial is None else round(t_partial - at(seg.first), 2),
                "asr_final_s": None if t_final is None else round(t_final - at(seg.last), 2),
                "mt_final_s": None if t_mt is None else round(t_mt - at(seg.last), 2),
                "mt_from_start_s": None if t_mt is None else round(t_mt - at(seg.first), 2),
                "text": text,
                "translation": translation,
            }
        )

    spoken = [r for r in rows if r["text"].strip()]
    hard_s = args.hard_max_ms / 1000 - 0.1  # đoạn bị cắt cứng dài hard_max_ms trừ một khung
    lengths = [r["length_s"] for r in rows]
    mt_lag = [r["mt_final_s"] for r in spoken if r["mt_final_s"] is not None]
    third = max(1, len(mt_lag) // 3)
    chars = sum(len("".join(r["text"].split())) for r in spoken)

    def values(key: str) -> list[float]:
        return [r[key] for r in spoken if r[key] is not None]

    return {
        "audio_s": round(len(sent) * CHUNK_S, 1),
        "timeline": "frame" if per_frame else "receive_time",
        "segments": len(kept),
        "dropped_short": len(segments) - len(kept),
        "with_text": len(spoken),
        "empty_or_missing": len(rows) - len(spoken),
        "mapping_mismatch": mismatched,
        "errors": errors,
        "length_mean_s": statistics.fmean(lengths) if lengths else None,
        "length_max_s": max(lengths) if lengths else None,
        "max_ms": [args.max_ms, args.hard_max_ms],
        "long": sum(args.max_ms / 1000 - 0.1 <= length < hard_s for length in lengths),
        "hard_cut": sum(length >= hard_s for length in lengths),
        "chars_per_s": chars / sum(r["length_s"] for r in spoken) if spoken else None,
        "first_partial_p50_s": pct(values("first_partial_s"), 0.5),
        "asr_final_p50_s": pct(values("asr_final_s"), 0.5),
        "asr_final_p95_s": pct(values("asr_final_s"), 0.95),
        "mt_final_p50_s": pct(mt_lag, 0.5),
        "mt_final_p95_s": pct(mt_lag, 0.95),
        "mt_from_start_p50_s": pct(values("mt_from_start_s"), 0.5),
        "mt_from_start_p95_s": pct(values("mt_from_start_s"), 0.95),
        "mt_first_third_s": statistics.fmean(mt_lag[:third]) if mt_lag else None,
        "mt_last_third_s": statistics.fmean(mt_lag[-third:]) if mt_lag else None,
        "utterances": rows,
    }


def print_report(r: dict, target: str) -> None:
    density = "—" if r["chars_per_s"] is None else f"{r['chars_per_s']:.1f} ký tự/giây"
    soft, hard = (ms / 1000 for ms in r["max_ms"])
    lines = [
        "\n=== Kết quả ===",
        f"Audio {r['audio_s']} s · câu: {r['segments']} (có chữ {r['with_text']}, rỗng/không về "
        f"{r['empty_or_missing']}) · đoạn quá ngắn bị bỏ: {r['dropped_short']} · lỗi: {r['errors']}",
        f"Độ dài câu: TB {fmt(r['length_mean_s'])}, dài nhất {fmt(r['length_max_s'])} · dài {soft:g}–{hard:g} s: "
        f"{r['long']}, bị cắt cứng ở {hard:g} s: {r['hard_cut']} · mật độ chữ: {density}",
        f"Chữ tạm đầu tiên, tính từ lúc bắt đầu câu (p50): {fmt(r['first_partial_p50_s'])}",
        f"Chữ chốt, tính từ lúc server cắt câu: p50 {fmt(r['asr_final_p50_s'])}, p95 {fmt(r['asr_final_p95_s'])}",
        f"Bản dịch '{target}', tính từ lúc server cắt câu: p50 {fmt(r['mt_final_p50_s'])}, "
        f"p95 {fmt(r['mt_final_p95_s'])}",
        f"Bản dịch '{target}', tính từ lúc BẮT ĐẦU câu: p50 {fmt(r['mt_from_start_p50_s'])}, "
        f"p95 {fmt(r['mt_from_start_p95_s'])}",
        f"Trễ bản dịch 1/3 đầu → 1/3 cuối: {fmt(r['mt_first_third_s'])} → {fmt(r['mt_last_third_s'])}",
    ]
    if r["timeline"] != "frame":
        lines.append("(Server không gửi vad cho mọi khung: ranh giới câu suy từ lúc nhận event, lệch cỡ độ trễ mạng.)")
    if r["mapping_mismatch"]:
        lines.append(
            f"\n⚠️  Ghép câu có thể lệch: {r['mapping_mismatch']} câu có audio_ms không khớp độ dài đoạn. "
            "Kiểm tra --min-speech-ms, --min-silence-ms, --preroll-ms theo profile server."
        )
    lines.append(
        "\nCách đọc: tính từ lúc bắt đầu câu lớn mà tính từ lúc cắt câu nhỏ → câu bị gộp dài, phải chờ cắt câu;"
        " trễ tăng dần từ 1/3 đầu tới 1/3 cuối → GPU/hàng đợi không theo kịp."
    )
    print("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default="ws://localhost:8000/ws", help="ví dụ wss://192.168.2.69:8443/ws")
    parser.add_argument("--wav", required=True, help="WAV 16 kHz mono PCM16")
    parser.add_argument("--lang", default="ja", help="ngôn ngữ nói (khoá nửa A), hoặc auto")
    parser.add_argument("--target", default="vi", help="ngôn ngữ phụ đề cần đo")
    parser.add_argument("--speed", type=float, default=1.0, help="tốc độ gửi; 2.0 = nhanh gấp đôi thời gian thực")
    parser.add_argument("--tail", type=float, default=3.0, help="giây im lặng thêm ở cuối")
    parser.add_argument("--drain", type=float, default=60.0, help="giây chờ tối đa sau khi gửi xong")
    parser.add_argument("--insecure", action="store_true", help="bỏ kiểm chứng chỉ TLS (chứng chỉ tự ký)")
    parser.add_argument("--min-speech-ms", type=int, default=200, help="như vad.min_speech_ms của profile server")
    parser.add_argument("--min-silence-ms", type=int, default=500, help="như vad.min_silence_ms của profile server")
    parser.add_argument("--preroll-ms", type=int, default=400, help="như vad.preroll_ms của profile server")
    parser.add_argument("--max-ms", type=int, default=7000, help="như vad.max_ms của profile server")
    parser.add_argument("--hard-max-ms", type=int, default=10000, help="như vad.hard_max_ms của profile server")
    parser.add_argument("--out", default="", help="ghi báo cáo JSON (kèm từng câu)")
    args = parser.parse_args()

    sent, events = asyncio.run(stream(args))
    report = analyze(sent, events, args)
    print_report(report, args.target)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print(f"\nĐã ghi {args.out}")


if __name__ == "__main__":
    main()
