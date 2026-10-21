"""Dòng lệnh: python -m chu_cai_video <lệnh>. Gõ `make` trong thư mục dự án để xem các lệnh thường dùng.

assets   tải font, hình, giọng đọc (và model ASR nếu thêm --asr) vào .cache/
sprites  tách nhân vật khỏi video gốc → ảnh động WebP nền trong suốt (cần nhóm phụ thuộc `sprites`)
voice    đọc mọi câu của kịch bản, in độ dài từng câu so với khúc nhạc
frame    vẽ vài khung hình xem thử → out/khung-<giây>.png
render   dựng video → media/video-chu-cai.mp4 + ảnh bìa + chương và phụ đề (.vtt)
qa       máy nghe lại từng câu (ASR) → reports/kiem-tra-giong.md
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from chu_cai_video import assets, audio, config, lesson, music, render, sfx, timeline, voice


@dataclass
class Project:
    lesson: lesson.Lesson
    timeline: timeline.Timeline
    spoken: list[voice.Spoken]
    music: np.ndarray
    voice: np.ndarray
    mixed: np.ndarray
    events: list[sfx.Event]


def prepare(script: Path, engine: str | None = None) -> Project:
    """Kịch bản → dòng thời gian → giọng đọc → tiếng động → nhạc → bản trộn (chưa vẽ hình)."""
    les = lesson.load(script)
    tl = timeline.build(les)
    spoken = voice.speak(les, tl, voice.engine_for(les, engine))
    track = voice.voice_track(spoken, tl.duration)
    events = render.sound_events(les, tl, spoken)
    effects = sfx.render(events, tl.duration, config.SAMPLE_RATE)
    bgm = music.render(tl, config.SAMPLE_RATE)
    mixed = audio.mix(track + effects[: track.size], bgm, config.SAMPLE_RATE)  # nhạc tự hạ khi có lời và tiếng kêu
    return Project(les, tl, spoken, bgm, track, mixed, events)


def make_renderer(p: Project) -> render.Renderer:
    fonts = render.Fonts(assets.font_files())
    pictures = render.pictures_for(p.lesson)
    return render.Renderer(p.lesson, p.timeline, p.spoken, p.music, p.voice, fonts, pictures, p.events)


def poster_time(p: Project) -> float:
    """Ảnh bìa: lúc con vật đầu tiên đang kêu (bong bóng lời đã hiện); không có con vật thì giữa chữ thứ tư."""
    calls = [e for e in p.events if e.cue]
    if calls:
        return calls[0].at + 0.5
    segs = p.timeline.letter_segments()
    seg = segs[min(3, len(segs) - 1)]
    return seg.voice_at + 2.0


def shown(path: Path) -> str:
    """Đường dẫn để in: tương đối với thư mục dự án nếu nằm trong đó."""
    path = path.resolve()
    return str(path.relative_to(config.PROJECT_ROOT)) if path.is_relative_to(config.PROJECT_ROOT) else str(path)


def vtt_time(t: float) -> str:
    h, rest = divmod(t, 3600)
    m, s = divmod(rest, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def chapters_vtt(p: Project) -> str:
    """Chương của video (WebVTT): mở đầu, từng chữ cái, kết thúc — trang web dùng để nhảy tới chữ cần xem."""
    cues = ["WEBVTT", ""]
    for seg in p.timeline.segments:
        if seg.letter:
            title = f"{seg.letter.letter} · {seg.letter.phrase}"
        else:
            title = "Mở đầu" if seg.kind == "intro" else "Kết thúc"
        cues += [f"{vtt_time(seg.start)} --> {vtt_time(seg.end)}", title, ""]
    return "\n".join(cues)


def subtitles_vtt(p: Project) -> str:
    cues = ["WEBVTT", ""]
    for s in p.spoken:
        cues += [f"{vtt_time(s.start)} --> {vtt_time(s.end + 0.4)}", s.text, ""]
    return "\n".join(cues)


def cmd_assets(args: argparse.Namespace) -> int:
    les = lesson.load(args.script)
    print("Font Baloo 2:")
    assets.font_files()
    print("Hình minh họa (Noto Emoji):")
    missing = [x.letter for x in les.letters if x.emoji and assets.emoji_png(x.emoji) is None]
    print("Giọng đọc Piper vi_VN:")
    assets.model_dir(config.VOICE)
    if args.asr:
        print("Model nghe lại (ASR):")
        assets.model_dir(config.ASR)
    print(f"✓ Xong — .cache/ ở {config.CACHE}" + (f"; thiếu hình cho: {', '.join(missing)}" if missing else ""))
    return 0


def cmd_sprites(args: argparse.Namespace) -> int:
    from chu_cai_video import sprites  # nhập muộn: cần onnxruntime

    les = lesson.load(args.script)
    todo = [c for c in les.characters if c.source and (not args.only or c.name in args.only)]
    if not todo:
        print("Không có nhân vật nào có `source` (video gốc) trong kịch bản")
        return 1
    segmenter = sprites.Segmenter()
    for c in todo:
        assert c.source is not None
        began = time.monotonic()
        n = sprites.extract(c.source, c.sprite, segmenter)
        size = c.sprite.stat().st_size / 1e6
        print(f"✓ {c.name}: {shown(c.sprite)} ({n} khung, {size:.1f} MB) sau {time.monotonic() - began:.0f}s")
    return 0


def cmd_voice(args: argparse.Namespace) -> int:
    les = lesson.load(args.script)
    tl = timeline.build(les)
    spoken = voice.speak(les, tl, voice.engine_for(les, args.voice))
    for s in spoken:
        room = s.segment.end - s.segment.voice_at
        print(f"  {s.cue_id:9} {s.duration:4.2f}s / {room:4.2f}s  [{s.source}]  {s.text}")
    print(f"✓ {len(spoken)} câu, video dài {tl.duration:.1f}s")
    return 0


def cmd_frame(args: argparse.Namespace) -> int:
    p = prepare(args.script, args.voice)
    r = make_renderer(p)
    times = args.at or [
        1.5,
        p.timeline.segments[0].end - 0.4,
        *(s.voice_at + 2.0 for s in p.timeline.letter_segments()[:3]),
        p.timeline.segments[-1].start + 3.0,
    ]
    for t in times:
        out = config.OUT / f"khung-{t:06.2f}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        r.frame(t).save(out)
        print(f"  {shown(out)}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    began = time.monotonic()
    p = prepare(args.script, args.voice)
    wav = config.OUT / "am-thanh.wav"
    audio.write_wav(wav, p.mixed, config.SAMPLE_RATE)
    r = make_renderer(p)
    out: Path = args.out
    print(f"Dựng {out.name}: {p.timeline.duration:.1f}s, {config.WIDTH}×{config.HEIGHT}, {config.FPS} hình/giây")
    render.encode(r, wav, out, start=args.start, end=args.end)
    if args.start == 0 and args.end is None:  # bản đầy đủ: thêm ảnh bìa, chương, phụ đề cạnh video
        r.frame(poster_time(p)).save(out.with_name("poster.jpg"), quality=88)
        out.with_name("chuong.vtt").write_text(chapters_vtt(p), encoding="utf-8")
        out.with_name("phu-de.vtt").write_text(subtitles_vtt(p), encoding="utf-8")
    size = out.stat().st_size / 1e6
    print(f"✓ {shown(out)} ({size:.1f} MB) sau {time.monotonic() - began:.0f}s")
    return 0


def cmd_qa(args: argparse.Namespace) -> int:
    from chu_cai_video import qa  # nhập muộn: cần model ASR

    p = prepare(args.script, "piper")
    results = qa.check(p.spoken, p.mixed, qa.Listener())
    text = qa.report(results, args.report)
    print("\n".join(text.splitlines()[8:14]))
    print(f"✓ {shown(args.report)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m chu_cai_video", description=__doc__.splitlines()[0])
    parser.add_argument("--script", type=Path, default=config.DEFAULT_SCRIPT, help="file kịch bản YAML")
    sub = parser.add_subparsers(dest="command", required=True)
    p_assets = sub.add_parser("assets", help="tải tài nguyên vào .cache/")
    p_assets.add_argument("--asr", action="store_true", help="tải cả model nghe lại (~60 MB)")
    p_sprites = sub.add_parser("sprites", help="tách nhân vật khỏi video gốc")
    p_sprites.add_argument("--only", nargs="*", help="chỉ tách các nhân vật có tên này")
    for name in ("voice", "frame", "render"):
        p = sub.add_parser(name)
        p.add_argument("--voice", choices=["piper", "silent"], help="ghi đè voice.engine của kịch bản")
        if name == "frame":
            p.add_argument("--at", type=float, nargs="*", help="các thời điểm (giây) cần vẽ")
        if name == "render":
            p.add_argument("--out", type=Path, default=config.MEDIA / "video-chu-cai.mp4")
            p.add_argument("--start", type=float, default=0.0, help="dựng từ giây này (xem thử một đoạn)")
            p.add_argument("--end", type=float, help="dựng tới giây này")
    p_qa = sub.add_parser("qa", help="máy nghe lại lời đọc")
    p_qa.add_argument("--report", type=Path, default=config.REPORTS / "kiem-tra-giong.md")
    args = parser.parse_args(argv)
    handler = {
        "assets": cmd_assets,
        "sprites": cmd_sprites,
        "voice": cmd_voice,
        "frame": cmd_frame,
        "render": cmd_render,
        "qa": cmd_qa,
    }
    try:
        return handler[args.command](args)
    except (lesson.LessonError, assets.AssetError, ValueError, RuntimeError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
