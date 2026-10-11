"""Đo phần nghe của pipeline thật trên một bộ golden (audio + phụ đề tham chiếu), không cần trình duyệt hay WebSocket.

Chạy đúng Silero VAD + Segmenter (theo profile) + FasterWhisperEngine của app trên toàn bộ audio, mỗi lần một khung
40 ms như web app gửi lên, rồi so chữ nhận được với phụ đề tham chiếu. Không chạy nhận dạng tạm, chốt sớm hay dịch.
Xem docs/07-bat-kip-loi-thoai-phim.md §9.

Trên server GPU (container rvt_ai có sẵn model và thư viện; mp4/aac được giải mã bằng PyAV):

    docker cp eval rvt_ai:/app/eval
    docker exec -it rvt_ai uv run python eval/golden_eval.py --golden eval/golden_1 --skip-lines 12-25,180- \\
        --out /tmp/golden_1.json
"""

import argparse
import difflib
import glob
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import av
import numpy as np
import yaml
from rvt_ai.engines.asr_whisper import FasterWhisperEngine
from rvt_ai.engines.vad_silero import SileroVadEngine
from rvt_ai.packs.loader import ProfileConfig
from rvt_ai.pipeline.segmenter import Segmenter, SegmenterConfig

FRAME = 640  # 40 ms PCM16 mono 16 kHz, như AudioWorklet của web app
PUNCT = re.compile(r"[\s、。，,．.！!？?・…「」『』（）()〜~—\-]")


def norm(text: str) -> str:
    """Bỏ nhãn [音楽], dấu câu và khoảng trắng; chuẩn hoá NFKC để so ký tự."""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\[[^\]]*\]", "", text)
    return PUNCT.sub("", text)


def load_audio(path: str) -> np.ndarray:
    """Giải mã file audio/video bất kỳ thành PCM16 mono 16 kHz bằng PyAV (cài sẵn cùng faster-whisper).

    Không dùng faster_whisper.audio.decode_audio: bản 1.2.1 gọi av.open(metadata_errors=...), PyAV 19 đã bỏ tham số này.
    """
    pieces = []
    with av.open(path) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(container.streams.audio[0]):
            pieces += [out.to_ndarray().reshape(-1) for out in resampler.resample(frame)]
        pieces += [out.to_ndarray().reshape(-1) for out in resampler.resample(None)]
    return np.concatenate(pieces).astype(np.int16)


def parse_ranges(spec: str) -> list[tuple[int, int]]:
    """'12-25,180-' → [(12, 25), (180, 10**9)] (số dòng tính từ 1, gồm cả hai đầu)."""
    out = []
    for part in filter(None, (p.strip() for p in spec.split(","))):
        lo, _, hi = part.partition("-")
        out.append((int(lo), int(hi) if hi else 10**9) if _ else (int(lo), int(lo)))
    return out


def segment(pcm: np.ndarray, cfg: SegmenterConfig, models_dir: str) -> tuple[list[dict], np.ndarray]:
    vad = SileroVadEngine(model_dir=models_dir)
    state = vad.create_state()
    seg = Segmenter(cfg)
    n = len(pcm) // FRAME
    probs = np.zeros(n, np.float32)
    finals = []
    for i in range(n):
        chunk = pcm[i * FRAME : (i + 1) * FRAME].tobytes()
        probs[i] = vad.process(chunk, state)
        _, final, buf = seg.add_chunk(chunk, float(probs[i]))
        if final and buf:
            # Đoạn bị cắt khi vẫn đang nói (vượt max_ms) thì phần còn lại nằm lại trong buffer của segmenter
            cut = seg.is_speaking
            end_s = (i + 1) * 0.04 - (len(seg.buffer) / 32000 if cut else 0.0)
            finals.append(
                {"start": round(end_s - len(buf) / 32000, 2), "end": round(end_s, 2), "cut": cut, "audio": buf}
            )
    tail = seg.force_final()
    if tail:
        finals.append(
            {"start": round(n * 0.04 - len(tail) / 32000, 2), "end": round(n * 0.04, 2), "cut": False, "audio": tail}
        )
    return finals, probs


def score(ref_lines: list[str], skip: list[tuple[int, int]], hyp_text: str) -> dict:
    ref, is_dialogue, spans = "", [], []
    for no, line in enumerate(ref_lines, 1):
        piece = norm(line)
        dialogue = not any(lo <= no <= hi for lo, hi in skip)
        if piece:
            spans.append((len(ref), len(ref) + len(piece), dialogue, line))
        ref += piece
        is_dialogue += [dialogue] * len(piece)
    hyp = norm(hyp_text)
    matched = [False] * len(ref)
    hyp_matched = 0
    for block in difflib.SequenceMatcher(None, ref, hyp, autojunk=False).get_matching_blocks():
        for k in range(block.a, block.a + block.size):
            matched[k] = True
        hyp_matched += block.size
    total = sum(is_dialogue)
    caught = sum(1 for k in range(len(ref)) if is_dialogue[k] and matched[k])
    lines = [s for s in spans if s[2] and s[1] - s[0] >= 3]
    missed = [s[3] for s in lines if sum(matched[s[0] : s[1]]) / (s[1] - s[0]) < 0.6]
    return {
        "dialogue_chars_caught_pct": round(100 * caught / max(1, total), 1),
        "hyp_chars_matching_ref_pct": round(100 * hyp_matched / max(1, len(hyp)), 1),
        "dialogue_lines_caught": f"{len(lines) - len(missed)}/{len(lines)}",
        "missed_lines": missed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", default="", help="thư mục có audio/<file> và subtitle/<file>.txt")
    parser.add_argument("--audio", default="", help="file audio (bỏ qua nếu dùng --golden)")
    parser.add_argument("--ref", default="", help="phụ đề tham chiếu, mỗi dòng một câu (bỏ qua nếu dùng --golden)")
    parser.add_argument(
        "--skip-lines", default="", help="dòng phụ đề không tính là lời thoại, ví dụ bài hát: 12-25,180-"
    )
    parser.add_argument(
        "--profile", default=os.path.join(os.environ.get("RVT_PACKS_DIR", "packs"), "profiles/balanced.yaml")
    )
    parser.add_argument("--models-dir", default=os.environ.get("RVT_MODELS_DIR", "models"))
    parser.add_argument("--language", default="ja")
    parser.add_argument("--max-seconds", type=float, default=0, help="chỉ đo đoạn đầu (0 = toàn bộ)")
    parser.add_argument("--out", default="", help="ghi báo cáo JSON (kèm từng đoạn)")
    args = parser.parse_args()

    audio_path = args.audio or sorted(glob.glob(os.path.join(args.golden, "audio", "*")))[0]
    ref_path = args.ref or sorted(glob.glob(os.path.join(args.golden, "subtitle", "*.txt")))[0]
    profile = ProfileConfig.model_validate(yaml.safe_load(Path(args.profile).read_text(encoding="utf-8")))
    cfg = SegmenterConfig(**profile.vad.model_dump(exclude={"engine"}))

    pcm = load_audio(audio_path)
    if args.max_seconds:
        pcm = pcm[: int(args.max_seconds * 16000)]
    print(
        f"Audio {len(pcm) / 16000:.0f} s · profile {profile.name} · VAD {cfg.threshold}/{cfg.neg_threshold} · "
        f"đoạn tối đa {cfg.max_ms}/{cfg.hard_max_ms} ms",
        flush=True,
    )

    finals, probs = segment(pcm, cfg, args.models_dir)
    cuts = [f for f in finals if f["cut"]]
    in_speech = [f for f in cuts if probs[max(0, int(round(f["end"] / 0.04)) - 1)] >= cfg.neg_threshold]
    print(
        f"{len(finals)} đoạn, {len(cuts)} đoạn bị cắt khi đang nói, trong đó {len(in_speech)} điểm cắt rơi vào khung "
        f"VAD ≥ {cfg.neg_threshold} (đang có tiếng nói)",
        flush=True,
    )

    engine = FasterWhisperEngine(
        model_size=profile.asr.model, device=profile.asr.device, compute_type=profile.asr.compute_type
    )
    t0, rows = time.time(), []
    for f in finals:
        text, _, _ = engine.transcribe(f.pop("audio"), language=args.language)
        rows.append({**f, "text": text})
    print(f"Nhận dạng {len(rows)} đoạn trong {time.time() - t0:.0f} s; {sum(not r['text'] for r in rows)} đoạn ra rỗng")

    ref_lines = Path(ref_path).read_text(encoding="utf-8").splitlines()
    if args.max_seconds:
        print("(--max-seconds: điểm so với toàn bộ phụ đề nên tỉ lệ bắt được sẽ thấp — chỉ dùng để so trước/sau)")
    result = score(ref_lines, parse_ranges(args.skip_lines), "".join(r["text"] for r in rows))
    summary = {k: v for k, v in result.items() if k != "missed_lines"}
    print(json.dumps(summary, ensure_ascii=False))
    print("Ví dụ câu thoại không bắt được:", *result["missed_lines"][:10], sep="\n  ")
    if args.out:
        report = {
            "audio": audio_path,
            "profile": profile.name,
            "segments": len(rows),
            "cuts": len(cuts),
            "cuts_in_speech": len(in_speech),
            **result,
            "rows": rows,
        }
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
        print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
