"""Chia theo thời gian và đóng băng bộ đánh giá (A3 · BIZ-02, ML-01).

- train ≤ 2025-06 (học) · valid 2025-07..09 (early stopping, hiệu chỉnh, chọn ngưỡng) · test 2025-10..12 (đóng băng).
- Chia theo THỜI GIAN chứ không ngẫu nhiên: model sẽ chấm điểm tháng sau bằng dữ liệu tháng trước, nên đánh giá cũng
  phải "học quá khứ, đoán tương lai".
- "Đóng băng" = ghi manifest (danh sách tháng, số dòng, số ca churn, mã băm của khoá + nhãn) vào eval/manifest.json và
  commit. Lần đánh giá nào cũng kiểm tra lại mã băm: ai sửa pipeline làm đổi tập test thì `make eval` báo lỗi ngay.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from churn_telco import config
from churn_telco.features import KEYS, LABEL

MANIFEST = config.EVAL_DIR / "manifest.json"


def split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    t = df["t"]
    return {
        "train": df[t <= config.TRAIN_END],
        "valid": df[(t > config.TRAIN_END) & (t <= config.VALID_END)],
        "test": df[t > config.VALID_END],
    }


def fingerprint(df: pd.DataFrame) -> str:
    """Mã băm SHA-256 của (t, customer_id, nhãn) đã sắp xếp — đổi một dòng hay một nhãn là đổi mã."""
    rows = df[[*KEYS, LABEL]].sort_values(KEYS)
    payload = rows.assign(t=rows["t"].dt.strftime("%Y-%m-%d")).to_csv(index=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def describe(test: pd.DataFrame) -> dict:
    return {
        "rule": f"t > {config.VALID_END:%Y-%m-%d} (3 tháng cuối có nhãn)",
        "snapshots": sorted(test["t"].dt.strftime("%Y-%m-%d").unique().tolist()),
        "rows": len(test),
        "customers": int(test["customer_id"].nunique()),
        "positives": int(test[LABEL].sum()),
        "sha256": fingerprint(test),
    }


def freeze(df: pd.DataFrame, path: Path = MANIFEST, force: bool = False) -> dict:
    """Ghi manifest của tập test. Đã có thì KHÔNG ghi đè (trừ khi force=True — tức là bạn cố ý đổi bộ đánh giá)."""
    if path.exists() and not force:
        raise FileExistsError(f"{path} đã có — bộ đánh giá đã đóng băng; dùng force=True nếu thật sự muốn đổi")
    manifest = describe(split(df)["test"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def frozen_test(df: pd.DataFrame, path: Path = MANIFEST) -> pd.DataFrame:
    """Tập test đã kiểm tra khớp manifest — mọi con số báo cáo đều đi qua hàm này."""
    test = split(df)["test"]
    expected = json.loads(path.read_text(encoding="utf-8"))
    actual = describe(test)
    if actual["sha256"] != expected["sha256"]:
        diff = {k: (expected[k], actual[k]) for k in ("rows", "customers", "positives") if expected[k] != actual[k]}
        raise ValueError(
            f"Tập test không khớp {path.name} (manifest, hiện tại): {diff or 'cùng số dòng, khác nội dung'}"
        )
    return test
