"""Tạo một bộ golden từ video YouTube hoặc TED có phụ đề do người làm (docs 10 §10.2).

Chỉ nhận phụ đề người tải lên (YouTube: "subtitles"), không nhận phụ đề tự động ("automatic captions"): phụ đề tự
động là kết quả của một model nhận dạng khác, không dùng làm đáp án được. Không có phụ đề người làm thì dừng.

    # xem video có những phụ đề nào
    uv run --no-project --with yt-dlp python eval/fetch_golden.py URL --list
    # tạo eval/golden_en_1 (audio/, subtitle/<tên>.txt, url.txt, source.json)
    uv run --no-project --with yt-dlp python eval/fetch_golden.py URL --lang en --name golden_en_1

Chỉ dùng cho đo nội bộ. Ưu tiên video có giấy phép cho phép (TED: CC BY-NC-ND; YouTube: lọc "Creative Commons").
Audio không được commit (eval/.gitignore); phụ đề và url.txt thì commit để người khác tải lại đúng video.
"""

import argparse
import json
import re
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
_TIMING = re.compile(r"^\s*\d{1,2}:\d{2}(:\d{2})?[.,]\d{3}\s*-->")
_TAG = re.compile(r"<[^>]+>")


def vtt_to_lines(vtt: str) -> list[str]:
    """Chữ của từng cue trong WebVTT/SRT, mỗi cue một dòng. Bỏ tiêu đề, số thứ tự, mốc thời gian, thẻ định dạng và
    dòng lặp lại liền nhau (phụ đề cuộn hay lặp dòng trước)."""
    lines: list[str] = []
    cue: list[str] = []

    def flush() -> None:
        text = " ".join(" ".join(cue).split())
        if text and (not lines or lines[-1] != text):
            lines.append(text)
        cue.clear()

    for raw in vtt.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:", "STYLE", "REGION")) or _TIMING.match(line):
            continue
        if line.isdigit() and not cue:  # số thứ tự cue của SRT
            continue
        cue.append(_TAG.sub("", line).replace("&nbsp;", " ").replace("&amp;", "&"))
    flush()
    return lines


def _manual_track(info: dict, lang: str) -> str | None:
    """Mã phụ đề người làm khớp ngôn ngữ (vi, vi-VN, en-US...)."""
    for code in (info.get("subtitles") or {}):
        if code == lang or code.split("-")[0] == lang:
            return code
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url")
    parser.add_argument("--lang", default="vi", help="ngôn ngữ nói trong video: vi hoặc en")
    parser.add_argument("--name", default="", help="tên thư mục trong eval/, ví dụ golden_vi_1")
    parser.add_argument("--list", action="store_true", help="chỉ in các phụ đề có sẵn")
    args = parser.parse_args()

    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        info = ydl.extract_info(args.url, download=False)
    manual = sorted((info.get("subtitles") or {}).keys())
    auto = sorted((info.get("automatic_captions") or {}).keys())
    duration = info.get("duration") or 0
    print(f"{info.get('title')} · {duration / 60:.1f} phút · giấy phép: {info.get('license') or 'không ghi'}")
    print(f"  phụ đề người làm: {', '.join(manual) or 'không có'}")
    print(f"  phụ đề tự động:   {len(auto)} ngôn ngữ (không dùng làm đáp án)")
    if args.list:
        return

    track = _manual_track(info, args.lang)
    if track is None:
        sys.exit(f"✗ Không có phụ đề người làm cho '{args.lang}'. Chọn video khác.")
    if not args.name:
        sys.exit("✗ Cần --name, ví dụ --name golden_vi_1")
    out = EVAL_DIR / args.name
    (out / "audio").mkdir(parents=True, exist_ok=True)
    (out / "subtitle").mkdir(parents=True, exist_ok=True)

    opts = {
        "quiet": True,
        "format": "bestaudio/best",
        "outtmpl": str(out / "audio" / "%(id)s.%(ext)s"),
        "writesubtitles": True,
        "writeautomaticsub": False,
        "subtitleslangs": [track],
        "subtitlesformat": "vtt/srt/best",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([args.url])

    sub_files = sorted((out / "audio").glob(f"*.{track}.*"))
    if not sub_files:
        sys.exit(f"✗ Không tải được phụ đề {track}")
    lines = vtt_to_lines(sub_files[0].read_text(encoding="utf-8", errors="replace"))
    for f in sub_files:
        f.unlink()
    (out / "subtitle" / f"{info.get('id')}.{args.lang}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "url.txt").write_text(args.url + "\n", encoding="utf-8")
    source = {
        "url": args.url,
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "license": info.get("license"),
        "duration_s": duration,
        "language": args.lang,
        "subtitle_track": track,
        "subtitle_kind": "manual",
    }
    (out / "source.json").write_text(json.dumps(source, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ {out}: {len(lines)} dòng phụ đề, {duration / 60:.1f} phút audio")
    print("  Nghe lại vài đoạn và sửa phụ đề nếu lệch lời nói trước khi dùng làm đáp án.")


if __name__ == "__main__":
    main()
