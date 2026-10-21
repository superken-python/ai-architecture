import copy
import os
from pathlib import Path

import pytest
import yaml

from chu_cai_video import config, lesson

# Test không bao giờ tải gì: font dự phòng của máy, hình thay thế, giọng `silent`.
os.environ["CHU_CAI_OFFLINE"] = "1"


@pytest.fixture(scope="session")
def script_data() -> dict:
    with open(config.DEFAULT_SCRIPT, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def full_lesson() -> lesson.Lesson:
    return lesson.load(config.DEFAULT_SCRIPT)


@pytest.fixture
def make_script(tmp_path: Path, script_data: dict):
    """Ghi một kịch bản rút gọn ra thư mục tạm (đường dẫn ảnh động nhân vật đổi sang tuyệt đối)."""

    def _make(n_letters: int = 3, **changes) -> Path:
        data = copy.deepcopy(script_data)
        data["letters"] = data["letters"][:n_letters]
        for c in data["characters"]:
            c["sprite"] = str((config.DEFAULT_SCRIPT.parent / c["sprite"]).resolve())
            c.pop("source", None)  # video gốc chỉ cần cho `make sprites`
        data["voice"]["recordings"] = str(tmp_path / "giong-thu-am")
        data["voice"]["engine"] = "silent"
        for key, value in changes.items():
            data[key] = value
        path = tmp_path / "kich-ban.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        return path

    return _make
