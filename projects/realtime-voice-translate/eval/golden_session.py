"""Phát lại một bộ golden qua RVTSession thật theo đồng hồ ảo, rồi dựng lại màn hình như web/src/state/useStore.ts.

golden_eval.py chỉ đo VAD + segmenter + nhận dạng từng đoạn. Script này chạy thêm toàn bộ logic của session: nhận dạng
tạm, chốt sớm, prompt ngữ cảnh, lọc câu bịa, ghép phần đuôi, xoá thẻ "ma". Sau đó nó đếm những lỗi người xem thấy được:

- thẻ đã chốt bị xoá;
- thẻ chữ tạm còn treo;
- chữ tạm ghi đè lên thẻ đã chốt;
- câu hiện hai lần;
- mảnh câu bị đưa đi dịch riêng;
- câu bịa còn trên màn hình.

Cách chạy:

- Đồng hồ ảo: `asyncio.sleep`, bộ hẹn giờ của session và `time.time()` đều chạy theo thời gian của audio. Mỗi khung
  40 ms được đưa vào đúng nhịp như web app gửi lên, nên 14 phút audio chỉ mất bằng thời gian GPU nhận dạng.
- ASR: `FasterWhisperEngine` thật theo profile. Mỗi lần nhận dạng "tốn" đúng thời gian chạy thật trên máy (`--latency
  measured`), hoặc theo mô hình cố định 0,15 s + 0,04 s cho mỗi giây audio (`--latency model`).
- MT: trong lúc phát lại không gọi model dịch, chỉ ghi lại câu nguồn được đưa đi dịch. Có `--mt-url` thì sau khi phát
  xong, các câu đó được dịch lần lượt như app (`mt_eval.AppLikeTranslator`: glossary, 2 câu trước kèm bản dịch) và chấm
  chrF cả bài so với `<golden>/translation/ja-vi.jsonl`. Chữ nghe sai và câu cắt khác nhau nên không ghép được từng câu;
  điểm này đi cùng `mt_eval.py` (dịch câu nguồn đúng) để tách phần lỗi do nghe với phần lỗi do dịch (docs 09 §5.1).

Xem docs/08-ra-soat-ban-cai-dat-07.md §2.

    docker exec -it rvt_ai uv run python eval/golden_session.py --golden eval/golden_1 --skip-lines 12-25,180- \\
        --out /tmp/golden_1_session.json
    # kèm chấm dịch cả chuỗi
    docker exec -it rvt_ai uv run python eval/golden_session.py --golden eval/golden_1 --skip-lines 12-25,180- \\
        --mt-url http://mt:8080/v1
    # chế độ chỉ nghe, tiếng Việt một người nói: thêm WER, CER (docs 10 §10.2)
    docker exec -it rvt_ai uv run python eval/golden_session.py --golden eval/golden_vi_1 --side-lang vi \\
        --profile packs/profiles/listen.yaml --capture mic
"""

import argparse
import asyncio
import difflib
import glob
import json
import os
import re
import selectors
import time
import types
from pathlib import Path

import numpy as np
import rvt_ai.pipeline.scheduler as scheduler_mod
import rvt_ai.pipeline.session as session_mod
import yaml
from golden_eval import load_audio, norm, parse_ranges, score
from loguru import logger
from rvt_ai.engines.asr_whisper import FasterWhisperEngine
from rvt_ai.engines.registry import build_asr_engine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.packs.loader import ProfileConfig
from rvt_ai.pipeline.segmenter import SegmenterConfig
from rvt_contracts.messages import MtFinal, SessionStart, SideConfig
from wer import score_text

FRAME = 640  # 40 ms PCM16 mono 16 kHz, như AudioWorklet của web app
HALLUCINATION = re.compile(r"ご視聴|チャンネル登録|^[\s・…。]*(?:おわり|終わり|字幕)[\s・…。！!]*$")


class _VirtualSelector(selectors.DefaultSelector):
    """Không bao giờ chờ thật: nếu không có I/O sẵn sàng thì nhảy đồng hồ ảo tới bộ hẹn giờ gần nhất."""

    loop: "VirtualClockLoop"

    def select(self, timeout=None):
        ready = super().select(0)
        if ready:
            return ready
        if timeout is None:
            raise RuntimeError("Không còn việc nào được hẹn giờ: session bị treo?")
        self.loop.virtual_time += max(0.0, timeout)
        return []


class VirtualClockLoop(asyncio.SelectorEventLoop):
    def __init__(self) -> None:
        selector = _VirtualSelector()
        super().__init__(selector)
        selector.loop = self
        self.virtual_time = 0.0

    def time(self) -> float:
        return self.virtual_time


def _repeats(prev: str, cur: str) -> bool:
    """Thẻ sau mở đầu gần giống hệt thẻ trước (chịu được dấu câu, ズレ/ずれ...): câu bị hiện hai lần.

    Video cũng có câu lặp thật ("おはよう" hai lần), nên so số này giữa hai bản code, đừng đòi bằng 0.
    """
    a, b = norm(prev), norm(cur)
    return len(a) >= 4 and difflib.SequenceMatcher(None, a, b[: len(a)], autojunk=False).ratio() >= 0.75


def replay_screen(events: list[dict]) -> dict:
    """Chép cách useStore.ts xử lý asr.partial / asr.final: final rỗng thì xoá thẻ, final có chữ thì chốt thẻ."""
    cards: dict[int, dict] = {}
    wiped, partial_over_final, ghost_cleared, refinal = [], 0, 0, 0
    for ev in events:
        if ev["type"] not in ("asr.partial", "asr.final"):
            continue
        uid, text = ev["utterance_id"], ev["text"]
        card = cards.get(uid)
        if ev["type"] == "asr.partial":
            if card and card["final"]:
                partial_over_final += 1
                card["text"] = text  # useStore ghi đè chữ của thẻ đã chốt
            elif card:
                card["text"] = text
            else:
                cards[uid] = {"uid": uid, "text": text, "final": False, "t": ev["t"]}
        elif not text.strip():
            if card and card["final"] and card["text"].strip():
                wiped.append({"t": ev["t"], "uid": uid, "text": card["text"]})
            elif card:
                ghost_cleared += 1
            cards.pop(uid, None)
        else:
            if card and card["final"]:
                refinal += 1
            cards[uid] = {"uid": uid, "text": text, "final": True, "t": ev["t"]}
    finals = [c for _, c in sorted(cards.items()) if c["final"]]
    duplicated = [b["text"] for a, b in zip(finals, finals[1:], strict=False) if _repeats(a["text"], b["text"])]
    return {
        "finals": finals,
        "wiped": wiped,
        "stuck_partials": [c for c in cards.values() if not c["final"]],
        "partial_over_final": partial_over_final,
        "ghost_cleared": ghost_cleared,
        "refinal": refinal,
        "duplicated": duplicated,
    }


def run_session(
    pcm: np.ndarray,
    profile: ProfileConfig,
    asr,
    models_dir: str,
    side_lang: str,
    target: str,
    latency: str,
    capture: str = "tab",
) -> tuple[list[dict], list[tuple[float, str]], list[dict]]:
    loop = VirtualClockLoop()
    asyncio.set_event_loop(loop)
    session_mod.time = types.SimpleNamespace(time=lambda: 1.7e9 + loop.time())

    async def to_thread_virtual(fn, *args, **kwargs):
        started = time.perf_counter()
        result = fn(*args, **kwargs)
        spent = time.perf_counter() - started if latency == "measured" else 0.15 + 0.04 * len(args[0]) / 32000
        await asyncio.sleep(spent)
        return result

    patched = types.SimpleNamespace(**{k: getattr(asyncio, k) for k in dir(asyncio) if not k.startswith("__")})
    patched.to_thread = to_thread_virtual
    scheduler_mod.asyncio = patched

    logs: list[tuple[float, str]] = []
    logger.remove()
    logger.add(lambda m: logs.append((round(loop.time(), 2), m.record["message"])), level="DEBUG")

    events: list[dict] = []
    mt_requests: list[dict] = []

    async def send_event(event) -> None:
        events.append({"t": round(loop.time(), 3), **event.model_dump()})

    async def record_mt(self, uid: int, text: str, source: str, tgt: str) -> None:
        mt_requests.append({"t": round(loop.time(), 3), "uid": uid, "text": text, "target": tgt})
        await asyncio.sleep(0.5)
        await self.send_event(MtFinal(utterance_id=uid, target=tgt, text=f"[{tgt}] {text}"))

    cfg = SegmenterConfig(**profile.vad.model_dump(exclude={"engine"}))
    vad = SileroVadEngine(model_dir=models_dir)
    # Bộ dịch không được gọi (_run_mt bị thay bằng record_mt), chỉ cần khác None để session đưa câu đi dịch. Profile chỉ
    # nghe (mt: none) thì không có bộ dịch, như trên server (docs 10 §10.3).
    mt = None if profile.mt.engine == "none" else object()
    session = session_mod.RVTSession("golden", vad, asr, mt, send_event, segmenter_config=cfg)
    session._run_mt = types.MethodType(record_mt, session)
    n = len(pcm) // FRAME

    async def drive() -> None:
        await session.handle_session_start(
            SessionStart(sides={"A": SideConfig(lang=side_lang), "B": SideConfig(lang=target)}, targets=[target])
        )
        await session.handle_turn_start("A", capture)
        wall = time.time()
        for i in range(n):
            await session.handle_audio_chunk(pcm[i * FRAME : (i + 1) * FRAME].tobytes())
            await asyncio.sleep(FRAME / 16000)  # 640 mẫu ở 16 kHz = 40 ms
            if i and i % 1500 == 0:
                print(f"  {i * 0.04:5.0f} s audio sau {time.time() - wall:4.0f} s", flush=True)
        await asyncio.sleep(10)
        await session.handle_turn_stop()
        await asyncio.sleep(10)
        await asyncio.gather(*session.active_tasks, return_exceptions=True)
        await session.close()

    loop.run_until_complete(drive())
    return events, logs, mt_requests


def translate_requests(mt_requests: list[dict], golden: str, api_url: str, glossary: str, target: str) -> dict:
    """Dịch các câu session đã đưa đi dịch, theo đúng thứ tự, rồi chấm chrF cả bài so với bản dịch tham chiếu."""
    from mt_eval import PACKS, AppLikeTranslator, chrf_score, chrf_stats, load_references, translate_all
    from rvt_ai.engines.mt_llama import LlamaCppMtEngine
    from rvt_ai.packs.glossary import load_glossary

    if target != "vi":
        raise SystemExit("--mt-url: bản dịch tham chiếu hiện chỉ có tiếng Việt")
    names = [n for n in glossary.split(",") if n.strip()]
    # API trên cloud (docs 10 §13): khoá và tên model đọc từ RVT_MT_API_KEY, RVT_MT_MODEL như server
    engine = LlamaCppMtEngine(
        api_url=api_url,
        timeout_sec=30.0,
        api_key=os.environ.get("RVT_MT_API_KEY", ""),
        model=os.environ.get("RVT_MT_MODEL", ""),
        reasoning_effort=os.environ.get("RVT_MT_REASONING_EFFORT", "auto"),
    )
    translator = AppLikeTranslator(engine, load_glossary(names, packs_dir=PACKS))
    outs, secs = asyncio.run(translate_all([r["text"] for r in mt_requests], translator))
    for r, o in zip(mt_requests, outs, strict=True):
        r["mt"] = o
    refs = " ".join(r["vi"] for r in load_references(golden))
    secs.sort()
    return {
        "mt_chrf_document": round(chrf_score(chrf_stats(" ".join(outs), refs)), 2),
        "mt_retries": translator.retries,
        "mt_latency_p50_s": round(secs[len(secs) // 2], 3) if secs else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", default="", help="thư mục có audio/<file> và subtitle/<file>.txt")
    parser.add_argument("--audio", default="", help="file audio (bỏ qua nếu dùng --golden)")
    parser.add_argument("--ref", default="", help="phụ đề tham chiếu, mỗi dòng một câu (bỏ qua nếu dùng --golden)")
    parser.add_argument("--skip-lines", default="", help="dòng phụ đề không tính là lời thoại, ví dụ: 12-25,180-")
    parser.add_argument(
        "--profile", default=os.path.join(os.environ.get("RVT_PACKS_DIR", "packs"), "profiles/balanced.yaml")
    )
    parser.add_argument("--models-dir", default=os.environ.get("RVT_MODELS_DIR", "models"))
    parser.add_argument("--side-lang", default="ja", help="ngôn ngữ nửa A (khoá như trên app), hoặc auto")
    parser.add_argument("--target", default="vi", help="ngôn ngữ dịch sang")
    parser.add_argument("--max-seconds", type=float, default=0, help="chỉ phát đoạn đầu (0 = toàn bộ)")
    parser.add_argument("--device", default="", help="thiết bị chạy ASR: cuda hoặc cpu (mặc định theo profile)")
    parser.add_argument("--compute-type", default="", help="kiểu tính toán: float16, int8_float16, int8")
    parser.add_argument(
        "--latency",
        choices=("measured", "model"),
        default="measured",
        help="thời gian mỗi lần nhận dạng: đo thật, hoặc 0,15 s + 0,04 s/giây audio",
    )
    parser.add_argument(
        "--capture", choices=("tab", "mic"), default="tab", help="nguồn audio như web gửi lên; dò VAD chỉ chạy với tab"
    )
    parser.add_argument("--mt-url", default="", help="dịch các câu đã đưa đi dịch bằng llama.cpp ở URL này, chấm chrF")
    parser.add_argument("--glossary", default="default,naruto", help="glossary dùng khi dịch (--mt-url)")
    parser.add_argument("--out", default="", help="ghi báo cáo JSON (kèm mọi thẻ trên màn hình)")
    args = parser.parse_args()

    audio_path = args.audio or sorted(glob.glob(os.path.join(args.golden, "audio", "*")))[0]
    ref_path = args.ref or sorted(glob.glob(os.path.join(args.golden, "subtitle", "*.txt")))[0]
    profile = ProfileConfig.model_validate(yaml.safe_load(Path(args.profile).read_text(encoding="utf-8")))
    pcm = load_audio(audio_path)
    if args.max_seconds:
        pcm = pcm[: int(args.max_seconds * 16000)]
    device = args.device or profile.asr.device
    compute_type = args.compute_type or profile.asr.compute_type
    if device == "cpu" and compute_type == "int8_float16":
        compute_type = "int8"
    if profile.asr.models:
        # Mỗi ngôn ngữ một model, như profile listen (docs 10 §10.3)
        asr = build_asr_engine(profile.asr, device=device, compute_type=compute_type)
    else:
        asr = FasterWhisperEngine(model_size=profile.asr.model, device=device, compute_type=compute_type)
    print(f"Audio {len(pcm) / 16000:.0f} s · profile {profile.name} · ASR {device}/{compute_type}", flush=True)

    events, logs, mt_requests = run_session(
        pcm, profile, asr, args.models_dir, args.side_lang, args.target, args.latency, args.capture
    )
    screen = replay_screen(events)

    def logged(*needles: str) -> int:
        return sum(1 for _, m in logs if all(x in m for x in needles))

    holds = logged("Holding trailing fragment")
    alone = logged("tail fragment", "standalone") + logged("tail fragment", "Returning")
    text = "".join(c["text"] for c in screen["finals"])
    summary = {
        "final_cards": len(screen["finals"]),
        "wiped_final_cards": len(screen["wiped"]),
        "stuck_partial_cards": len(screen["stuck_partials"]),
        "partial_over_final": screen["partial_over_final"],
        "ghost_partials_cleared": screen["ghost_cleared"],
        "duplicated_cards": len(screen["duplicated"]),
        "early_commits": logged("Early-commit stable sentence"),
        "tail_holds": holds,
        "tail_emitted_alone": alone,
        "tail_merged": holds - alone,
        "hallucinations_on_screen": sum(1 for c in screen["finals"] if HALLUCINATION.search(c["text"])),
        "hallucinations_discarded": logged("Discarded"),
        "vad_probe_finals": logged("VAD probe final"),
        "mt_requests": len(mt_requests),
        "mt_fragments_le6_chars": sum(1 for r in mt_requests if len(norm(r["text"])) <= 6),
    }
    ref_lines = Path(ref_path).read_text(encoding="utf-8").splitlines()
    result = score(ref_lines, parse_ranges(args.skip_lines), text)
    summary.update({k: v for k, v in result.items() if k != "missed_lines"})
    if args.side_lang in ("vi", "en"):
        # Tiếng Việt, tiếng Anh: WER theo từ, giữ dấu thanh (docs 10 §10.2)
        spaced = " ".join(c["text"] for c in screen["finals"])
        summary.update(score_text(ref_lines, parse_ranges(args.skip_lines), spaced))
    if args.mt_url:
        summary.update(translate_requests(mt_requests, args.golden, args.mt_url, args.glossary, args.target))
    if args.max_seconds:
        print("(--max-seconds: điểm so với toàn bộ phụ đề nên tỉ lệ bắt được sẽ thấp — chỉ dùng để so trước/sau)")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for w in screen["wiped"][:10]:
        print(f"  thẻ đã chốt bị xoá lúc {w['t']:.1f} s: {w['text']}")
    if args.out:
        report = {"audio": audio_path, "profile": profile.name, **summary, **screen, "mt": mt_requests}
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
