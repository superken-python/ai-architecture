import copy
from pathlib import Path

import numpy as np
import pytest
from PIL import ImageFont

from chu_cai_video import actor, config, lesson, sfx


@pytest.fixture(scope="module")
def font() -> ImageFont.FreeTypeFont:
    """Font có dấu tiếng Việt của máy (test chạy offline, không tải Baloo 2); không có thì font mặc định của Pillow."""
    found = next((p for p in config.FALLBACK_FONTS if Path(p).exists()), None)
    return ImageFont.truetype(found, 400) if found else ImageFont.load_default(400)


def test_base_shape_strips_every_mark():
    assert [actor.base_shape(ch) for ch in "ĂÂÊÔƠƯĐB"] == ["A", "A", "E", "O", "O", "U", "Đ", "B"]


def test_letter_actor_has_a_face_on_its_body(font):
    b = actor.LetterActor("B", (232, 65, 79), font, height=200)
    img, feet = b.draw(actor.Pose())
    assert img.mode == "RGBA" and 0 < feet[0] < img.width and 0 < feet[1] <= img.height
    x0, y0, x1, y1 = b.body
    for ex, ey in b.eyes:  # mắt nằm trên thân, ở nửa trên
        assert x0 - 20 < ex < x1 + 20 and y0 < ey < (y0 + y1) / 2
    white = np.asarray(img)[..., :3].min(axis=2) > 245
    assert white.sum() > 200  # lòng trắng mắt, găng tay
    hat = actor.LetterActor("Ă", (232, 65, 79), font, height=200)
    plain = actor.LetterActor("A", (232, 65, 79), font, height=200)
    if hat.size[1] > plain.size[1]:  # font có dấu á: dấu nằm trên thân như chiếc mũ, mặt đặt dưới dấu
        assert hat.body[1] - hat.origin[1] > 10 and hat.eyes[0][1] > hat.body[1]


def test_poses_change_the_drawing(font):
    g = actor.LetterActor("G", (242, 124, 30), font, height=160)
    idle = np.asarray(g.draw(actor.Pose())[0], dtype=float)
    for pose in (actor.Pose(talk=1.0), actor.Pose(blink=1.0), actor.Pose(cheer=1.0), actor.Pose(run=0.25, stride=1)):
        assert np.abs(np.asarray(g.draw(pose)[0], dtype=float) - idle).mean() > 0.01, pose


@pytest.mark.parametrize("name", sfx.NAMES)
def test_sounds_are_clean_and_repeatable(name):
    x = sfx.sound(name, config.SAMPLE_RATE)
    assert x.dtype == np.float32 and np.isfinite(x).all()
    assert 0.1 < x.size / config.SAMPLE_RATE < 2.5
    assert 0.5 < np.abs(x).max() <= 0.91
    if name in sfx.CALLS:  # dựng lại từ công thức ra đúng y hệt
        call = sfx.CALLS[name]
        assert np.array_equal(sfx.synth(call, config.SAMPLE_RATE, call.seed), x)


def test_vocal_tract_formants_get_denser_with_a_longer_neck():
    cow, cat = sfx.tract(0.45, 3), sfx.tract(0.1, 3)
    assert cow[0] < cat[0] and cow[1] - cow[0] < cat[1] - cat[0]
    assert sfx.tract(0.45, 3, open_=0.5)[0] < cow[0]  # ngậm miệng: formant thấp xuống


def test_unknown_animal_call_is_rejected(script_data, tmp_path):
    data = copy.deepcopy(script_data)
    data["characters"] = []
    data["letters"][3]["call"] = "khung-long"  # chữ B
    with pytest.raises(lesson.LessonError, match="không có tiếng"):
        lesson.parse(data, tmp_path)
