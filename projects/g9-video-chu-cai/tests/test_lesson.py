import copy

import pytest

from chu_cai_video import lesson

ALPHABET = list("AĂÂBCDĐEÊGHIKLMNOÔƠPQRSTUƯVXY")  # mỗi chữ là một ký tự Unicode (NFC)


def test_script_covers_the_29_letters_in_order(full_lesson):
    assert [x.letter for x in full_lesson.letters] == ALPHABET
    assert [x.id for x in full_lesson.letters][:2] == ["chu-01", "chu-02"]


def test_base_letter_drops_tone_marks_only():
    assert lesson.base_letter("ế") == "ê"
    assert lesson.base_letter("ằ") == "ă"
    assert lesson.base_letter("ợ") == "ơ"
    assert lesson.base_letter("Đ") == "đ"
    assert lesson.base_letter("á") == "a"
    assert lesson.base_letter("ă") != "a"


def test_highlight_points_at_the_letter_inside_the_example_word(full_lesson):
    for x in full_lesson.letters:
        lo, hi = x.highlight()
        assert lesson.base_letter(x.phrase[lo:hi]) == x.lower, x.letter
        assert lo >= x.phrase.find(x.word), f"{x.letter}: phải tô trong '{x.word}', không phải trong cả cụm"


def test_highlight_skips_the_classifier():
    x = lesson.Letter(index=5, letter="C", sound="cờ", phrase="con cá", word="cá", emoji="🐟")
    assert x.highlight() == (4, 5)  # chữ c của "cá", không phải của "con"


def test_say_uses_template_unless_overridden(full_lesson):
    a = full_lesson.letters[0]
    assert a.say == "Đây là chữ a, như trong cái áo."
    k = next(x for x in full_lesson.letters if x.letter == "K")
    assert k.say == "Đây là chữ ca nhé, như trong cái kéo."


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"word": "bê"}, "không nằm trong"),
        ({"phrase": "con dê", "word": "dê"}, "không thấy chữ"),
        ({"emoji": ""}, "cần 'emoji' hoặc 'image'"),
    ],
)
def test_rejects_broken_letter(script_data, tmp_path, patch, message):
    data = copy.deepcopy(script_data)
    data["letters"][3].update(patch)  # chữ B
    with pytest.raises(lesson.LessonError, match=message):
        lesson.parse(data, tmp_path)


def test_rejects_duplicate_letter_and_unknown_engine(script_data, tmp_path):
    data = copy.deepcopy(script_data)
    data["character"]["image"] = str((lesson.Path(__file__).parents[1] / "assets/nhan-vat/sach-vui.png").resolve())
    data["letters"].append(copy.deepcopy(data["letters"][0]))
    with pytest.raises(lesson.LessonError, match="lặp"):
        lesson.parse(data, tmp_path)
    data["letters"].pop()
    data["voice"]["engine"] = "robot"
    with pytest.raises(lesson.LessonError, match="không hợp lệ"):
        lesson.parse(data, tmp_path)
