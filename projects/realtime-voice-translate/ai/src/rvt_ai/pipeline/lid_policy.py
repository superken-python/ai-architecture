import math
from typing import Literal

from pydantic import BaseModel

Lang = Literal["ja", "en", "vi"]
ALLOWED_LANGS: tuple[Lang, ...] = ("ja", "en", "vi")


class LangDecision(BaseModel):
    lang: Lang
    probs: dict[Lang, float]
    uncertain: bool


def pick_language(
    asr_probs: dict[str, float], side_prior: dict[Lang, float], prior_weight: float = 0.4, uncertain_below: float = 0.5
) -> LangDecision:
    """Giới hạn LID của Whisper về 3 tiếng rồi kết hợp với prior của nửa màn hình."""
    # Lấy xác suất của 3 tiếng, bù 1e-6 để tránh log(0)
    p = {k: max(asr_probs.get(k, 0.0), 1e-6) for k in ALLOWED_LANGS}
    z = sum(p.values())
    if z == 0:
        z = 1.0

    # Tính score log-linear
    score = {k: math.log(p[k] / z) + prior_weight * math.log(max(side_prior.get(k, 1e-6), 1e-6)) for k in ALLOWED_LANGS}

    # Softmax để ra posterior
    top = max(score.values())
    w = {k: math.exp(s - top) for k, s in score.items()}
    total = sum(w.values())
    post = {k: v / total for k, v in w.items()}

    lang: Lang = max(post, key=post.__getitem__)  # type: ignore
    return LangDecision(lang=lang, probs=post, uncertain=post[lang] < uncertain_below)


def update_side_prior(current_prior: dict[Lang, float], observed_lang: Lang, alpha: float = 0.2) -> dict[Lang, float]:
    """Cập nhật prior bằng trung bình trượt chuẩn hóa (EMA)."""
    updated = {}
    for lang in ALLOWED_LANGS:
        target = 1.0 if lang == observed_lang else 0.0
        updated[lang] = (1.0 - alpha) * current_prior.get(lang, 0.33) + alpha * target
    # Chuẩn hóa tổng bằng 1.0
    total = sum(updated.values())
    return {k: v / total for k, v in updated.items()}


# Chữ cái có dấu của tiếng Việt. Vài chữ ("é", "à") cũng gặp trong tiếng Anh vay mượn, nên phải đủ nhiều mới tính.
_VI_LETTERS = set("àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ")


def _is_japanese(ch: str) -> bool:
    return "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿"


def script_language(text: str) -> Lang | None:
    """Ngôn ngữ nhìn từ chữ viết: chữ Nhật → ja; chữ Latin có dấu tiếng Việt → vi; chữ Latin không dấu → en.

    None khi không đủ chữ để kết luận ("2", "OK"), hoặc khi chữ Nhật và chữ Latin trộn ngang nhau.
    """
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    japanese = sum(1 for c in letters if _is_japanese(c))
    if japanese >= 0.3 * len(letters):
        return "ja"
    if japanese:
        return None
    vietnamese = sum(1 for c in text.lower() if c in _VI_LETTERS)
    if vietnamese >= 2 or (vietnamese and vietnamese >= 0.1 * len(letters)):
        return "vi"
    if len(letters) >= 3 and all(c.isascii() for c in letters):
        return "en"
    return None


def correct_language(text: str, lang: Lang) -> Lang:
    """Ngôn ngữ đã khoá (hoặc LID chọn) mâu thuẫn hẳn với chữ nhận dạng thì tin vào chữ.

    Ví dụ: khoá 日本語 mà người nói tiếng Việt, Whisper vẫn chép ra tiếng Việt. Không sửa thì thẻ ghi "JA 100%" và câu
    tiếng Việt bị "dịch" sang tiếng Việt thành một câu nói lại. Chữ Latin không dấu khi khoá tiếng Việt thì giữ nguyên,
    vì có thể là tiếng Việt không dấu hoặc một từ tiếng Anh chen vào.
    """
    script = script_language(text)
    if script is None or script == lang or (script == "en" and lang == "vi"):
        return lang
    return script
