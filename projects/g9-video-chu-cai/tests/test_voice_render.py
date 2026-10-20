import shutil
import subprocess

import numpy as np
import pytest

from chu_cai_video import audio, cli, config, lesson, qa, render, timeline, voice


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
    card = np.asarray(r.frame(seg.end - 0.5).crop((640, 130, 1180, 330)), dtype=float)
    assert card.mean() > 180  # thẻ chữ trắng đã hiện


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
