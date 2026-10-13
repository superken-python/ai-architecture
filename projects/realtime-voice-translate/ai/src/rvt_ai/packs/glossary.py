"""Glossary và bảng tra câu ngắn cho bộ dịch (docs 09 §5.2, §5.5, §9).

- `packs/glossary/<tên>.yaml`: tên riêng, thuật ngữ (`source`, `target_vi`, `target_en`, `target_ja`) và quy ước xưng hô
  theo ngôn ngữ đích (`addressing.vi`). Chọn bằng biến môi trường `RVT_GLOSSARIES` (nhiều tên cách nhau bởi dấu phẩy).
- `packs/phrasebook/<ngôn ngữ nguồn>.yaml`: câu cảm thán ngắn ("うん", "え?") dịch bằng bảng tra, không gọi model.
"""

import os
import re
from functools import cache

import yaml
from pydantic import BaseModel, Field

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.pipeline.kana import katakana_to_romaji
from rvt_contracts.messages import Lang


class GlossaryTerm(BaseModel):
    source: str
    target_ja: str | None = None
    target_vi: str | None = None
    target_en: str | None = None

    def forms(self, lang: Lang) -> list[str]:
        """Các cách viết của mục này trong một câu tiếng `lang`."""
        out = [self.source] if lang == "ja" or self.target_ja is None else []
        own = getattr(self, f"target_{lang}")
        if own:
            out.append(own)
        return [f for f in dict.fromkeys(out) if f]

    def target(self, lang: Lang) -> str:
        return getattr(self, f"target_{lang}") or self.source


class Glossary(BaseModel):
    terms: list[GlossaryTerm] = Field(default_factory=list)
    addressing: dict[str, list[str]] = Field(default_factory=dict)

    def merge(self, other: "Glossary") -> "Glossary":
        addressing = {k: list(v) for k, v in self.addressing.items()}
        for lang, notes in other.addressing.items():
            addressing.setdefault(lang, []).extend(notes)
        return Glossary(terms=[*self.terms, *other.terms], addressing=addressing)

    def match(self, text: str, source: Lang, target: Lang) -> list[tuple[str, str]]:
        """Các cặp (cách viết trong câu nguồn, bản dịch cố định) có mặt trong `text`, mục dài trước."""
        found: list[tuple[str, str]] = []
        taken: list[str] = []
        for term in sorted(self.terms, key=lambda t: -max(len(f) for f in t.forms(source) or [""])):
            for form in term.forms(source):
                # "カカシ先生" đã khớp thì không thêm "カカシ" nữa
                if form in text and not any(form in t for t in taken):
                    found.append((form, term.target(target)))
                    taken.append(form)
                    break
        return found

    def fix_leftovers(self, translation: str, target: Lang) -> str:
        """Thay tên, thuật ngữ còn để nguyên chữ Nhật trong bản dịch bằng bản dịch cố định của chúng."""
        if target == "ja":
            return translation
        pairs = [(f, t.target(target)) for t in self.terms for f in t.forms("ja") if t.target(target) != f]
        for form, repl in sorted(pairs, key=lambda p: -len(p[0])):
            translation = translation.replace(form, repl)
        return translation


class Phrasebook(BaseModel):
    entries: dict[str, dict[str, str]] = Field(default_factory=dict)  # câu nguồn đã chuẩn hoá → {ngôn ngữ: bản dịch}

    def lookup(self, text: str, target: Lang) -> str | None:
        return self.entries.get(normalize_phrase(text), {}).get(target)


_PUNCT_EDGE = re.compile(r"^[\s。、・…,.]+|[\s。、・…,.]+$")


def normalize_phrase(text: str) -> str:
    text = text.strip().replace("？", "?").replace("！", "!")
    return _PUNCT_EDGE.sub("", text)


def fix_leftovers(translation: str, source: Lang, target: Lang, glossary: Glossary) -> str:
    """Bản dịch sang tiếng Việt/Anh còn sót chữ Nhật: thay bằng bản dịch trong glossary, katakana còn lại đổi sang
    romaji ("カカシ" → "Kakashi"). Kanji không có trong glossary vẫn để bộ kiểm loại (docs 09 §9)."""
    if source != "ja" or target not in ("vi", "en"):
        return translation
    return katakana_to_romaji(glossary.fix_leftovers(translation, target))


def _packs_dir() -> str:
    path = os.path.abspath(settings.PACKS_DIR)
    if not os.path.exists(path):
        path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../packs"))
    return path


def load_glossary(names: list[str], packs_dir: str | None = None) -> Glossary:
    base = os.path.join(packs_dir or _packs_dir(), "glossary")
    glossary = Glossary()
    for name in names:
        path = os.path.join(base, f"{name}.yaml")
        if not os.path.exists(path):
            logger.warning(f"Glossary '{name}' not found at {path}")
            continue
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        glossary = glossary.merge(Glossary(terms=data.get("terms") or [], addressing=data.get("addressing") or {}))
    return glossary


def load_phrasebook(source: Lang, packs_dir: str | None = None) -> Phrasebook:
    path = os.path.join(packs_dir or _packs_dir(), "phrasebook", f"{source}.yaml")
    if not os.path.exists(path):
        return Phrasebook()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    entries: dict[str, dict[str, str]] = {}
    for item in data.get("phrases") or []:
        translations = {k: v for k, v in item.items() if k != source and isinstance(v, str)}
        for key in [item[source], *(item.get("variants") or [])]:
            entries[normalize_phrase(key)] = translations
    return Phrasebook(entries=entries)


@cache
def get_glossary() -> Glossary:
    names = [n.strip() for n in settings.GLOSSARIES.split(",") if n.strip()]
    glossary = load_glossary(names)
    logger.info(f"Loaded glossaries {names}: {len(glossary.terms)} terms")
    return glossary


@cache
def get_phrasebook(source: Lang) -> Phrasebook:
    return load_phrasebook(source)
