"""Lab OPS-05 · Trung cấp: chuyển một model Whisper sang CTranslate2 ở nhiều kiểu số, rồi đo kích thước, tốc độ,
độ chính xác để chọn kiểu chạy.

Chạy ở thư mục gốc repo (lần đầu tải torch, transformers vào bộ đệm của uv và model gốc ~150 MB):

    uv run --no-project --python 3.12 --with "ctranslate2==4.8.4" --with "transformers[torch]==5.21.0" \\
        --with huggingface_hub --with "faster-whisper==1.2.1" --with psutil \\
        python labs/ops-05-trung-cap-luong-tu-whisper/lab.py

Model mặc định vinai/PhoWhisper-tiny, cùng họ với PhoWhisper-large mà app dùng cho tiếng Việt. Bộ đo mặc định: 31 câu
tiếng Việt có nhạc nền của video chữ cái (dự án g9), cắt theo phụ đề. Kết quả ghi vào work/ket-qua.md.
"""

import argparse
import contextlib
import gc
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
VOICE = ROOT / "projects" / "realtime-voice-translate"
# Dùng lại code của dự án dịch giọng nói: script chuyển model (docs 11) và cách tính WER tiếng Việt
sys.path[:0] = [str(LAB), str(VOICE / "scripts"), str(VOICE / "eval")]
import convert_whisper_ct2 as conv  # noqa: E402
import luong_tu as lt  # noqa: E402
import wer  # noqa: E402

G9_MEDIA = ROOT / "projects" / "g9-video-chu-cai" / "media"
STORE_TYPES = ("float32", "float16", "int8_float16")
# (kiểu lưu, kiểu chạy); dòng đầu là bản gốc để so. CPU không có float16, GPU chạy float32 chậm và tốn VRAM.
COMBOS = {
    "cpu": [("float32", "float32"), ("float16", "float32"), ("float32", "int8"), ("int8_float16", "float32")],
    "cuda": [("float32", "float32"), ("float16", "float16"), ("float16", "int8_float16"), ("int8_float16", "float16")],
}


def load_audio(path: Path) -> np.ndarray:
    """Audio/video bất kỳ → float32 mono 16 kHz bằng PyAV (cài sẵn cùng faster-whisper).

    Không dùng faster_whisper.decode_audio: bản 1.2.1 gọi av.open(metadata_errors=...), PyAV 19 đã bỏ tham số này.
    """
    import av

    pieces = []
    with av.open(str(path)) as container:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in container.decode(container.streams.audio[0]):
            pieces += [out.to_ndarray().reshape(-1) for out in resampler.resample(frame)]
        pieces += [out.to_ndarray().reshape(-1) for out in resampler.resample(None)]
    return np.concatenate(pieces).astype(np.float32) / 32768.0


def rss_mb() -> float | None:
    try:
        import psutil
    except ImportError:
        return None
    return psutil.Process().memory_info().rss / 1e6


def size_mb(path: Path) -> float:
    return path.stat().st_size / 1e6


def step_source(model: str, work: Path) -> Path:
    print("\n== 1 · Tải model gốc một lần (chỉ cấu hình, tokenizer, một loại trọng số)")
    if Path(model).is_dir():
        source = Path(model)
    else:
        source = work / "goc"
        if not (source / "config.json").exists():
            conv.download(model, str(source))
    for f in sorted(source.glob("*")):
        if f.is_file() and f.suffix in (".bin", ".safetensors"):
            mb = size_mb(f)
            print(f"   {f.name}: {mb:.1f} MB ≈ {mb / 4:.1f} triệu tham số nếu lưu float32 (4 byte mỗi tham số)")
    return source


def step_convert(source: Path, work: Path) -> dict[str, float]:
    print("\n== 2 · Chuyển sang CTranslate2 ở ba kiểu lưu")
    sizes = {}
    for store in STORE_TYPES:
        out = work / f"ct2-{store}"
        if not (out / "model.bin").exists():
            t0 = time.perf_counter()
            conv.convert(str(source), str(out), store)
            print(f"   {store}: chuyển trong {time.perf_counter() - t0:.1f} s")
        sizes[store] = size_mb(out / "model.bin")
    for store, mb in sizes.items():
        print(f"   {store:13} model.bin {mb:8.1f} MB  = {mb / sizes['float32']:.0%} của float32")
    return sizes


def step_clips(audio_path: Path, vtt_path: Path, limit: int) -> tuple[list[np.ndarray], list[str], float]:
    print(f"\n== 3 · Bộ đo: {audio_path.name}, cắt theo {vtt_path.name}")
    audio = load_audio(audio_path)
    cues = lt.parse_vtt(vtt_path.read_text(encoding="utf-8"))[: limit or None]
    clips = [lt.cut(audio, c) for c in cues]
    seconds = sum(len(c) for c in clips) / 16000
    print(f"   {len(clips)} câu, {seconds:.0f} giây lời nói (audio cả bài {len(audio) / 16000:.0f} giây)")
    return clips, [c.text for c in cues], seconds


def run_combo(model_dir: Path, device: str, compute: str, clips: list[np.ndarray], language: str) -> dict:
    from faster_whisper import WhisperModel

    gc.collect()
    mem0 = rss_mb()
    t0 = time.perf_counter()
    model = WhisperModel(str(model_dir), device=device, compute_type=compute)
    load_s = time.perf_counter() - t0
    mem1 = rss_mb()

    def transcribe(clip: np.ndarray) -> str:
        segments, _ = model.transcribe(
            clip,
            language=language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
            without_timestamps=True,
            max_new_tokens=128,
        )
        return "".join(s.text for s in segments).strip()

    transcribe(clips[0])  # chạy nháp một câu: lần đầu chậm hơn vì cấp bộ nhớ
    t0 = time.perf_counter()
    texts = [transcribe(c) for c in clips]
    run_s = time.perf_counter() - t0
    mem = mem1 - mem0 if device == "cpu" and mem0 is not None and mem1 is not None else None
    return {"load_s": load_s, "mem_mb": mem, "run_s": run_s, "texts": texts}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="vinai/PhoWhisper-tiny", help="repo Hugging Face hoặc thư mục transformers")
    parser.add_argument("--audio", type=Path, default=G9_MEDIA / "video-chu-cai.mp4")
    parser.add_argument("--vtt", type=Path, default=G9_MEDIA / "phu-de.vtt", help="phụ đề: mốc thời gian và đáp án")
    parser.add_argument("--language", default="vi")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--margin", type=float, default=0.02, help="chênh WER chấp nhận được (0.02 = 2 điểm)")
    parser.add_argument("--limit", type=int, default=0, help="chỉ dùng N câu đầu, để chạy thử nhanh")
    parser.add_argument("--work", type=Path, default=LAB / "work", help="thư mục model và kết quả (không commit)")
    args = parser.parse_args()

    import ctranslate2

    device = args.device
    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    args.work.mkdir(parents=True, exist_ok=True)

    source = step_source(args.model, args.work)
    sizes = step_convert(source, args.work)
    clips, refs, seconds = step_clips(args.audio, args.vtt, args.limit)

    print(f"\n== 4 · Chạy từng cách trên {device}")
    rows = []
    for store, compute in COMBOS[device]:
        result = run_combo(args.work / f"ct2-{store}", device, compute, clips, args.language)
        counts = [wer.word_errors(r, h) for r, h in zip(refs, result["texts"], strict=True)]
        errors, words = [e for e, _ in counts], [n for _, n in counts]
        row = {
            "store": store,
            "compute": compute,
            "size_mb": sizes[store],
            "load_s": result["load_s"],
            "mem_mb": result["mem_mb"],
            "rtf": result["run_s"] / seconds,
            "wer": sum(errors) / max(1, sum(words)),
            "errors": errors,
            "texts": result["texts"],
            "clips": len(clips),
        }
        print(f"   lưu {store:13} chạy {compute:13} RTF {row['rtf']:.3f}  WER {row['wer']:.3f}")
        rows.append(row)

    print(f"\n== 5 · So với bản gốc ({rows[0]['store']}/{rows[0]['compute']}), biên chấp nhận +{args.margin:.2f} WER")
    base = rows[0]
    base["base"] = True
    words = [len(wer.normalize(r).split()) for r in refs]
    for row in rows[1:]:
        row["delta"], row["lo"], row["hi"] = lt.paired_bootstrap(base["errors"], row["errors"], words)
        row["changed"] = sum(
            wer.normalize(a) != wer.normalize(b) for a, b in zip(base["texts"], row["texts"], strict=True)
        )
        row["verdict"] = lt.verdict(row["hi"], row["rtf"], base["rtf"], args.margin)
    table = lt.markdown_table(rows)
    pick = lt.choose(rows, args.margin)
    print(table)
    print(f"→ Nên chọn: lưu {pick['store']}, chạy {pick['compute']}")

    versions = {"ctranslate2": ctranslate2.__version__, "python": platform.python_version()}
    for name in ("faster_whisper", "transformers", "torch"):
        with contextlib.suppress(ImportError):
            versions[name] = __import__(name).__version__
    report = args.work / "ket-qua.md"
    machine = platform.processor() or platform.machine()
    report.write_text(
        f"# Kết quả lab OPS-05\n\n- Model: `{args.model}`\n- Bộ đo: `{args.audio.name}`, {len(clips)} câu, "
        f"{seconds:.0f} giây lời nói\n- Máy: {device}, {machine}, {os.cpu_count()} nhân\n"
        f"- Phiên bản: {', '.join(f'{k} {v}' for k, v in versions.items())}\n\n{table}\n"
        f"Nên chọn: lưu `{pick['store']}`, chạy `{pick['compute']}` (biên +{args.margin:.2f} WER).\n",
        encoding="utf-8",
    )
    details = [{k: v for k, v in r.items() if k != "errors"} | {"refs": refs} for r in rows]
    (args.work / "ket-qua.json").write_text(json.dumps(details, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nĐã ghi {report} và ket-qua.json (chữ từng câu của mỗi cách chạy).")


if __name__ == "__main__":
    main()
