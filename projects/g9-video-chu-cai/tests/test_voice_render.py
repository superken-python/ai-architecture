import dataclasses
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from chu_cai_video import audio, character, cli, config, lesson, qa, render, sfx, sprites, timeline, voice


def test_silent_voice_fits_and_recordings_override(make_script, tmp_path):
    les = lesson.load(make_script(3))
    tl = timeline.build(les)
    rec = tmp_path / "giong-thu-am"
    rec.mkdir()
    t = np.arange(int(1.2 * config.SAMPLE_RATE)) / config.SAMPLE_RATE
    audio.write_wav(rec / "chu-02.wav", (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32), config.SAMPLE_RATE)
    spoken = voice.speak(les, tl, voice.SilentEngine())
    by_id = {s.cue_id: s for s in spoken}
    assert [s.cue_id for s in spoken] == ["mo-dau", "chu-01", "chu-02", "chu-03", "ket-thuc"]
    assert by_id["chu-02"].source == "thu-am" and by_id["chu-01"].source == "silent"
    assert all(s.end <= s.segment.end for s in spoken)
    track = voice.voice_track(spoken, tl.duration)
    assert np.abs(track).max() > 0  # câu thu âm có mặt trong rãnh giọng


class GapEngine:
    """Giả giọng máy: hai tiếng ồn cách nhau một khoảng lặng ngắn (giống dấu phẩy trong câu)."""

    name = "piper"

    def key(self, speed=None):
        return f"gap|{speed}"

    def synth(self, text, speed=None):
        rng = np.random.default_rng(0)
        part = (0.3 * rng.standard_normal(int(0.8 * config.SAMPLE_RATE))).astype(np.float32)
        gap = np.zeros(int(0.1 * config.SAMPLE_RATE), np.float32)
        return np.concatenate([part, gap, part]), config.SAMPLE_RATE


def test_machine_voice_gets_a_longer_pause_before_the_example_word(make_script, tmp_path):
    base = lesson.load(make_script(1))
    tl = timeline.build(base)
    plain = voice.speak(dataclasses.replace(base, voice_pause=0.0), tl, GapEngine(), cache=tmp_path)[1]
    slow = voice.speak(dataclasses.replace(base, voice_pause=0.35), tl, GapEngine(), cache=tmp_path)[1]
    assert slow.duration == pytest.approx(plain.duration + 0.35, abs=0.01)
    assert slow.word_at == pytest.approx(plain.word_at + 0.35, abs=0.01)
    assert plain.word_at == pytest.approx(0.8 + 0.1, abs=0.02)  # từ ví dụ bắt đầu sau khoảng lặng


def test_line_longer_than_its_bars_is_reported(make_script):
    les = lesson.load(make_script(2, music={"bpm": 400, "intro_bars": 4, "letter_bars": 2, "outro_bars": 4}))
    with pytest.raises(ValueError, match="dài hơn khúc nhạc"):
        voice.speak(les, timeline.build(les), voice.SilentEngine())


def test_word_times_split_at_the_example_word(make_script):
    les = lesson.load(make_script(1))
    tl = timeline.build(les)
    seg = tl.segments[1]
    s = voice.Spoken(seg, seg.text(les), np.zeros(2 * config.SAMPLE_RATE, np.float32), "piper", word_at=1.2)
    times = render.word_times(s)
    words = s.text.split()
    assert times == sorted(times) and times[0] == 0.0
    assert times[words.index("như")] == pytest.approx(1.2)


def test_frames_render_offline(make_script):
    p = cli.prepare(make_script(2), "silent")
    r = render.Renderer(p.lesson, p.timeline, p.spoken, p.music, p.voice, render.Fonts({}), {"A": None, "Ă": None})
    seg = p.timeline.segments[1]
    for t in (0.5, seg.voice_at + 1.5, p.timeline.segments[-1].start + 2.0, p.timeline.duration - 0.01):
        img = r.frame(t)
        assert img.size == (config.WIDTH, config.HEIGHT) and img.mode == "RGB"
    frame = r.frame(seg.voice_at + 1.5)
    card = np.asarray(frame.crop((render.CARD_X + 40, 130, render.CARD_X + render.CARD_W - 40, 330)), dtype=float)
    assert card.mean() > 180  # thẻ chữ trắng bên phải đã hiện
    x, y = render.STAGE
    stage = np.asarray(frame.crop((x - 80, y - 260, x + 80, y - 40)), dtype=float)
    red = (stage[..., 0] > 180) & (stage[..., 1] < 120)  # chữ A màu đỏ đứng trên sân khấu
    assert red.mean() > 0.15
    # Nhân vật dẫn chuyện chỉ có ở mở đầu và kết thúc: góc dưới trái lúc dạy chữ giống hệt bản không có họ.
    q = cli.prepare(make_script(2, characters=[]), "silent")
    plain = render.Renderer(q.lesson, q.timeline, q.spoken, q.music, q.voice, render.Fonts({}), {"A": None, "Ă": None})
    box = (0, 470, 110, 640)
    assert np.array_equal(np.asarray(frame.crop(box)), np.asarray(plain.frame(seg.voice_at + 1.5).crop(box)))
    assert not np.array_equal(np.asarray(r.frame(5.0).crop(box)), np.asarray(plain.frame(5.0).crop(box)))


def test_letter_hops_down_from_its_chip_and_back(make_script):
    p = cli.prepare(make_script(2), "silent")
    r = render.Renderer(p.lesson, p.timeline, p.spoken, p.music, p.voice, render.Fonts({}), {"A": None, "Ă": None})
    seg = p.timeline.segments[2]  # chữ Ă
    chip = r.chip_center(seg.letter)
    start = render.hop(seg.start, seg.start, render.HOP_DOWN, chip, render.STAGE, r.chip_scale, 1.0, 100)
    end = render.hop(seg.start + render.HOP_DOWN, seg.start, render.HOP_DOWN, chip, render.STAGE, r.chip_scale, 1, 100)
    assert start.pos == pytest.approx(chip) and start.scale == pytest.approx(r.chip_scale)
    assert end.pos == pytest.approx(render.STAGE) and end.scale == pytest.approx(1.0)
    middle = render.hop(seg.start + 0.2, seg.start, render.HOP_DOWN, chip, render.STAGE, r.chip_scale, 1.0, 100)
    assert middle.squash < 0  # đang bay thì giãn người
    assert render.landing(0.0) > 0.4 and abs(render.landing(0.6)) == 0  # vừa tiếp đất thì bẹp, sau đó hết


def test_read_along_cue_fills_the_gap_after_the_line(make_script):
    p = cli.prepare(make_script(1), "silent")
    r = render.Renderer(p.lesson, p.timeline, p.spoken, p.music, p.voice, render.Fonts({}), {"A": None})
    seg = p.timeline.segments[1]
    window = r.repeat_window(seg)
    assert window is not None and p.spoken[1].end < window[0] < window[1] < seg.end
    x, y = config.WIDTH // 2, render.SUB_Y
    cue = np.asarray(r.frame(sum(window) / 2).crop((x - 100, y - 12, x + 100, y + 12)), dtype=float)
    # nhãn vàng "Bé đọc theo nào!" ở chỗ phụ đề
    assert ((cue[..., 0] > 200) & (cue[..., 1] > 170) & (cue[..., 2] < 120)).mean() > 0.3
    music = {"bpm": 132, "intro_bars": 4, "letter_bars": 2, "outro_bars": 4}
    fast = cli.prepare(make_script(1, music=music, intro="Xin chào các bạn!"), "silent")
    r = render.Renderer(fast.lesson, fast.timeline, fast.spoken, fast.music, fast.voice, render.Fonts({}), {"A": None})
    assert r.repeat_window(fast.timeline.segments[1]) is None  # nhịp nhanh: không còn chỗ cho bé đọc theo


def test_sprite_plays_forward_then_backward(tmp_path):
    frames = [Image.new("RGBA", (40, 80), (v, 0, 0, 255)) for v in (10, 20, 30)]
    path = tmp_path / "nhan-vat.webp"
    sprites.save_webp(frames, path)
    s = character.Sprite(path, box=(20, 100))
    assert s.size == (20, 40)  # co vừa khung, giữ tỉ lệ
    seen = [s.at(k / config.SPRITE_FPS).getpixel((10, 20))[0] for k in range(6)]
    assert [round(v / 10) for v in seen] == [1, 2, 3, 2, 1, 2]


def test_sprite_mask_keeps_details_inside_the_ring_only():
    h = w = 200
    body = np.zeros((h, w), np.float32)
    body[60:140, 60:140] = 1.0  # thân nhân vật: U²-Net chắc chắn
    detail = body.copy()
    detail[50:60, 60:140] = 1.0  # quai tai nghe mảnh: chỉ ISNet thấy
    detail[0:6, :] = 1.0  # vòng sáng ở mép: ISNet lấy nhầm
    alpha = sprites.combine(body, detail, radius=80)
    assert alpha[100, 100] == 1.0 and alpha[55, 100] == 1.0
    assert alpha[2, 100] == 0.0
    rgb = np.full((h, w, 3), (30, 50, 90), np.float32)  # nền xanh đậm
    rgb[60:140, 60:140] = (240, 240, 240)
    hole = body.copy()
    hole[20:40, 80:120] = 1.0  # U²-Net lấp cả khoảng nền giữa quai tai nghe và đầu
    alpha = sprites.combine(hole, detail, radius=80, rgb=rgb)
    assert alpha[30, 100] == 0.0 and alpha[100, 100] == 1.0


def test_vtt_files_list_every_chapter_and_line(make_script):
    p = cli.prepare(make_script(3), "silent")
    chapters = cli.chapters_vtt(p)
    assert chapters.startswith("WEBVTT") and chapters.count(" --> ") == 5
    assert "A · cái áo" in chapters and "00:00:00.000 --> " in chapters
    assert cli.subtitles_vtt(p).count(" --> ") == 5


def test_accent_aware_matching():
    assert qa.normalize("giờ") == qa.normalize("dờ") == qa.normalize("rờ")
    assert qa.normalize("sờ") == qa.normalize("xờ")
    assert qa.normalize("chữ l") == ["chữ", "lờ"]
    assert qa.contains(qa.normalize("đây là chữ y dài"), qa.normalize("i dài"))
    assert not qa.contains(qa.normalize("cục hình"), qa.normalize("cục pin"))
    assert qa.wer(["a", "b", "c"], ["a", "c"]) == pytest.approx(1 / 3)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="cần ffmpeg")
def test_render_command_writes_a_playable_mp4(make_script, tmp_path):
    out = tmp_path / "thu.mp4"
    code = cli.main(["--script", str(make_script(1)), "render", "--voice", "silent", "--end", "1.0", "--out", str(out)])
    assert code == 0 and out.stat().st_size > 1000
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert float(probe.stdout) == pytest.approx(1.0, abs=0.1)


def test_animal_call_follows_the_line_and_pops_out_of_the_card(make_script):
    letters = [
        {"letter": "B", "sound": "bờ", "phrase": "con bò", "word": "bò", "emoji": "🐄", "call": "bo",
         "call_text": "Ụm bò!"},
        {"letter": "C", "sound": "cờ", "phrase": "con cá", "word": "cá", "emoji": "🐟"},
    ]  # fmt: skip
    p = cli.prepare(make_script(0, letters=letters), "silent")
    calls = [e for e in p.events if e.cue]
    assert [(e.name, e.cue) for e in calls] == [("bo", "chu-01")]
    line = p.spoken[1]
    assert calls[0].at == pytest.approx(line.end + sfx.CALL_GAP)  # kêu sau câu đọc, không chồng lên lời
    assert sum(e.name == "boing" for e in p.events) == 2  # mỗi chữ một tiếng tiếp đất
    r = render.Renderer(p.lesson, p.timeline, p.spoken, p.music, p.voice, render.Fonts({}), {}, p.events)
    seg_b, seg_c = p.timeline.segments[1], p.timeline.segments[2]
    assert r.call_out(calls[0].at - 0.5, seg_b) == 0 and r.call_out(calls[0].at + 0.5, seg_b) == pytest.approx(1)
    assert r.repeat_window(seg_b) is None and r.repeat_window(seg_c) is not None  # có con vật kêu thì thôi đọc theo
    assert r.frame(calls[0].at + 0.5).size == (config.WIDTH, config.HEIGHT)
    effects = sfx.render(p.events, p.timeline.duration, config.SAMPLE_RATE)
    i = int(calls[0].at * config.SAMPLE_RATE)
    assert np.abs(effects[i : i + config.SAMPLE_RATE]).max() > 0.05 and np.abs(effects).max() <= 1.0
