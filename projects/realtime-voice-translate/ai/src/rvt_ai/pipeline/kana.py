"""Đổi katakana còn sót trong bản dịch tiếng Việt/Anh sang romaji (Hepburn), ví dụ tên "カカシ" → "Kakashi".

Bản dịch tiếng Việt chỉ cần còn một chữ Nhật là bị coi là hỏng và phải dịch lại (docs 09 §9). Model hay để nguyên tên
nhân vật bằng katakana, nên đổi sang chữ Latin trước khi kiểm thay vì bỏ cả câu.
"""

import re

_BASE = {
    "ア": "a", "イ": "i", "ウ": "u", "エ": "e", "オ": "o",
    "カ": "ka", "キ": "ki", "ク": "ku", "ケ": "ke", "コ": "ko",
    "ガ": "ga", "ギ": "gi", "グ": "gu", "ゲ": "ge", "ゴ": "go",
    "サ": "sa", "シ": "shi", "ス": "su", "セ": "se", "ソ": "so",
    "ザ": "za", "ジ": "ji", "ズ": "zu", "ゼ": "ze", "ゾ": "zo",
    "タ": "ta", "チ": "chi", "ツ": "tsu", "テ": "te", "ト": "to",
    "ダ": "da", "ヂ": "ji", "ヅ": "zu", "デ": "de", "ド": "do",
    "ナ": "na", "ニ": "ni", "ヌ": "nu", "ネ": "ne", "ノ": "no",
    "ハ": "ha", "ヒ": "hi", "フ": "fu", "ヘ": "he", "ホ": "ho",
    "バ": "ba", "ビ": "bi", "ブ": "bu", "ベ": "be", "ボ": "bo",
    "パ": "pa", "ピ": "pi", "プ": "pu", "ペ": "pe", "ポ": "po",
    "マ": "ma", "ミ": "mi", "ム": "mu", "メ": "me", "モ": "mo",
    "ヤ": "ya", "ユ": "yu", "ヨ": "yo",
    "ラ": "ra", "リ": "ri", "ル": "ru", "レ": "re", "ロ": "ro",
    "ワ": "wa", "ヲ": "o", "ン": "n", "ヴ": "vu",
    "ァ": "a", "ィ": "i", "ゥ": "u", "ェ": "e", "ォ": "o",
}  # fmt: skip
_SMALL_Y = {"ャ": "ya", "ュ": "yu", "ョ": "yo"}
_KATAKANA_RUN = re.compile(r"[ァ-ヺー]+")


def _romanize(run: str) -> str:
    out: list[str] = []
    i = 0
    geminate = False
    while i < len(run):
        ch = run[i]
        if ch == "ッ":
            geminate = True
            i += 1
            continue
        if ch == "ー":  # trường âm: bỏ, như cách viết tên thường gặp (ラーメン → Ramen)
            i += 1
            continue
        syl = _BASE.get(ch, "")
        nxt = run[i + 1] if i + 1 < len(run) else ""
        if nxt in _SMALL_Y and syl.endswith("i"):
            # キャ → kya, シャ → sha, チャ → cha, ジャ → ja
            stem = syl[:-1]
            y = _SMALL_Y[nxt]
            syl = stem + (y[1:] if stem in ("sh", "ch", "j") else y)
            i += 1
        elif nxt and nxt in "ァィゥェォ" and syl:
            syl = syl[:-1] + _BASE[nxt]  # ファ → fa, ティ → ti
            i += 1
        if geminate and syl:
            syl = ("t" if syl.startswith("ch") else syl[0]) + syl
            geminate = False
        out.append(syl)
        i += 1
    return "".join(out)


def katakana_to_romaji(text: str) -> str:
    """Thay mỗi cụm katakana bằng romaji viết hoa chữ đầu; phần còn lại giữ nguyên."""
    return _KATAKANA_RUN.sub(lambda m: _romanize(m.group(0)).capitalize(), text)
