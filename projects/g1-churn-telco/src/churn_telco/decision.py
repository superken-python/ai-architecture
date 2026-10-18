"""Từ điểm số tới quyết định gọi ai (A5 · STAT-05): hiệu chỉnh xác suất, giá trị kỳ vọng, ngưỡng theo năng lực.

Một cuộc gọi giữ chân khách i có giá trị kỳ vọng
    EV_i = p_i × SAVE_RATE × (giá trị_i − OFFER_COST) − CALL_COST,   với giá trị_i = cước_i × VALUE_MONTHS × MARGIN
nên ta cần p_i là XÁC SUẤT THẬT (đã hiệu chỉnh), không chỉ là điểm xếp hạng. Gọi khi EV > 0 (ngưỡng hoà vốn), nhưng
mỗi tháng tối đa CALL_CAPACITY cuộc — khi năng lực là ràng buộc chặt, ngưỡng thực tế là EV của người thứ 500.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from churn_telco import config
from churn_telco.features import LABEL

EPS = 1e-6


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def fit_platt(p: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Hiệu chỉnh Platt: p' = sigmoid(a·logit(p) + b), học trên tập valid (KHÔNG trên tập dùng để train model)."""
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p).reshape(-1, 1), y)
    return {"a": float(lr.coef_[0, 0]), "b": float(lr.intercept_[0])}


def apply_platt(p: np.ndarray, a: float, b: float) -> np.ndarray:
    return 1 / (1 + np.exp(-(a * _logit(p) + b)))


def reliability(p: np.ndarray, y: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Bảng độ tin cậy: chia theo phân vị của p; model hiệu chỉnh tốt thì mean_pred ≈ frac_churn ở mọi nhóm."""
    frame = pd.DataFrame({"p": p, "y": y})
    frame["bin"] = pd.qcut(frame["p"].rank(method="first"), bins, labels=False)
    return frame.groupby("bin").agg(n=("y", "size"), mean_pred=("p", "mean"), frac_churn=("y", "mean")).reset_index()


def ece(p: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error: trung bình |dự đoán − thực tế| theo nhóm, có trọng số theo số dòng."""
    r = reliability(p, y, bins)
    return float(np.average((r["mean_pred"] - r["frac_churn"]).abs(), weights=r["n"]))


def customer_value(df: pd.DataFrame) -> np.ndarray:
    """Lợi nhuận gộp giữ được nếu khách ở lại: cước tháng × số tháng ở thêm × biên lợi nhuận."""
    return df["monthly_fee"].to_numpy(float) * config.VALUE_MONTHS * config.MARGIN


def expected_value(p: np.ndarray, value: np.ndarray) -> np.ndarray:
    return p * config.SAVE_RATE * (value - config.OFFER_COST) - config.CALL_COST


def break_even(value: np.ndarray) -> np.ndarray:
    """Xác suất churn tối thiểu để một cuộc gọi có lãi kỳ vọng (EV = 0)."""
    return config.CALL_COST / (config.SAVE_RATE * (value - config.OFFER_COST))


def call_list(frame: pd.DataFrame, p: np.ndarray, capacity: int = config.CALL_CAPACITY) -> pd.DataFrame:
    """Mỗi tháng: xếp theo EV giảm dần, gọi tối đa `capacity` khách có EV > 0."""
    out = frame.assign(p=p, value=customer_value(frame))
    out["ev"] = expected_value(out["p"].to_numpy(), out["value"].to_numpy())
    out["rank"] = out.groupby("t")["ev"].rank(ascending=False, method="first").astype(int)
    out["call"] = (out["rank"] <= capacity) & (out["ev"] > 0)
    return out


def profit_curve(frame: pd.DataFrame, p: np.ndarray, ks: list[int] | None = None) -> pd.DataFrame:
    """Theo số cuộc gọi mỗi tháng k: precision, recall, và lợi nhuận kỳ vọng THỰC HIỆN được (tính theo nhãn thật).

    Lợi nhuận(k) = Σ_{k khách đầu} [y · SAVE_RATE · (giá trị − OFFER_COST)] − k · CALL_COST, trung bình theo tháng.
    Đường này trả lời: tăng năng lực gọi lên bao nhiêu thì còn có lãi (coverage–precision cho bài toán gọi điện).
    """
    ks = ks or [100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000]
    ranked = call_list(frame, p, capacity=max(ks)).sort_values(["t", "rank"])
    rows = []
    for k in ks:
        top = ranked[ranked["rank"] <= k]
        gain = (top[LABEL] * config.SAVE_RATE * (top["value"] - config.OFFER_COST)).groupby(top["t"]).sum()
        months = ranked["t"].nunique()
        churners = ranked.groupby("t")[LABEL].sum()
        rows.append(
            {
                "k": k,
                "coverage": k / (len(ranked) / months),
                "precision": top[LABEL].mean(),
                "recall": (top.groupby("t")[LABEL].sum() / churners).mean(),
                "profit": (gain - k * config.CALL_COST).mean(),
                "ev_at_k": top.groupby("t")["ev"].min().mean(),  # EV của người cuối danh sách
            }
        )
    return pd.DataFrame(rows)
