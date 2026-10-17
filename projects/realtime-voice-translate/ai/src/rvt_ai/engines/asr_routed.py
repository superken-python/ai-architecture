"""Một model nhận dạng cho mỗi ngôn ngữ của phiên (docs 10 §10.3, §11.1).

Chế độ chỉ nghe khoá ngôn ngữ theo phiên, nên mỗi lượt nhận dạng đã biết ngôn ngữ: tiếng Việt đi qua model chuyên tiếng
Việt (PhoWhisper-large đã chuyển sang CTranslate2), tiếng Anh và lượt chưa biết ngôn ngữ đi qua model mặc định
(large-v3-turbo). Mọi model được nạp lúc khởi động, để lượt đầu tiên không phải chờ nạp model.
"""

import os
from collections.abc import Callable
from typing import Any

from rvt_ai.core.config import settings
from rvt_ai.core.logging import logger
from rvt_ai.engines.ports import AsrEngine
from rvt_contracts.messages import Lang


def resolve_model(model: str, models_dir: str | None = None) -> str | None:
    """Đường dẫn hoặc tên model để nạp; None nếu là thư mục cục bộ chưa có.

    Thư mục trong models/ (hoặc đường dẫn tuyệt đối) được dùng nếu có. Tên có hậu tố "-ct2" là model phải chuẩn bị trước
    bằng scripts/prepare_listen_models.sh, nên không có thì trả None thay vì để faster-whisper đi tải một thứ không tồn
    tại. Tên khác (large-v3-turbo, repo Hugging Face) để faster-whisper tự tải.
    """
    base = models_dir or settings.MODELS_DIR
    for path in (model, os.path.join(base, model)):
        if os.path.isdir(path):
            return path
    if model.endswith("-ct2") or os.path.isabs(model):
        return None
    return model


class LanguageRoutedAsrEngine:
    def __init__(
        self,
        default_model: str,
        models: dict[str, str],
        factory: Callable[[str], AsrEngine],
        models_dir: str | None = None,
    ):
        self.default = factory(default_model)
        self.default_name = default_model
        self.engines: dict[str, AsrEngine] = {}
        self.names: dict[str, str] = {}
        for lang, model in models.items():
            if model == default_model:
                self.engines[lang] = self.default
                self.names[lang] = default_model
                continue
            resolved = resolve_model(model, models_dir)
            if resolved is None:
                logger.warning(
                    f"ASR model for '{lang}' not found: {model}. Using {default_model} instead; "
                    "run scripts/prepare_listen_models.sh to prepare it."
                )
                self.engines[lang] = self.default
                self.names[lang] = default_model
                continue
            logger.info(f"Loading ASR model for '{lang}': {resolved}")
            self.engines[lang] = factory(resolved)
            self.names[lang] = model

    def model_for(self, language: Lang | None) -> str:
        return self.names.get(language or "", self.default_name)

    def transcribe(
        self, audio: bytes, language: Lang | None = None, **kwargs: Any
    ) -> tuple[str, Lang, dict[Lang, float]]:
        engine = self.engines.get(language or "", self.default)
        return engine.transcribe(audio, language, **kwargs)
