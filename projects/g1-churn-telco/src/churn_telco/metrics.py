"""Metric xếp hạng khi năng lực xử lý có hạn + khoảng tin cậy bootstrap theo khách (A3 · STAT-02, A5 · ML-03).

- AUC: xác suất một khách churn được xếp trên một khách không churn — đo cả bảng xếp hạng.
- PR-AUC (average precision): tập trung vào phần đầu bảng, nhạy với dữ liệu mất cân bằng hơn AUC.
- precision@k / recall@k: mỗi tháng CSKH gọi được k = 500 khách — trong 500 người đó bao nhiêu người thật sự sắp rời
  (precision), và bắt được bao nhiêu phần trong số người sắp rời (recall). Tính TỪNG THÁNG rồi lấy trung bình.

Bootstrap theo cụm: một khách xuất hiện ở nhiều tháng trong tập test nên các dòng không độc lập. Mỗi vòng bootstrap
rút lại KHÁCH (có hoàn lại); khách được rút n lần thì mọi dòng của khách đó có trọng số n. Thứ tự xếp hạng của mỗi
model chỉ tính một lần, mỗi vòng chỉ đổi trọng số — nên 1.000 vòng chạy trong vài giây.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from churn_telco import config
from churn_telco.features import LABEL

METRICS = ["auc", "pr_auc", "p@k", "r@k", "f1@k"]


@dataclass(frozen=True)
class Ranked:
    """Một model trên một tập đánh giá: xếp hạng tính một lần, dùng lại cho mọi vòng bootstrap."""

    y: np.ndarray  # nhãn theo thứ tự dòng gốc
    order: np.ndarray  # chỉ số dòng theo điểm giảm dần (cả tập)
    last: np.ndarray  # vị trí cuối của mỗi nhóm điểm bằng nhau trong `order` — điểm hoà là một ngưỡng
    by_t: tuple[np.ndarray, ...]  # từng tháng: chỉ số dòng theo điểm giảm dần


def rank(score: np.ndarray, y: np.ndarray, t: np.ndarray) -> Ranked:
    score, y, t = np.asarray(score, float), np.asarray(y, int), np.asarray(t)
    order = np.argsort(-score, kind="stable")
    s = score[order]
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    by_t = tuple(np.flatnonzero(t == m)[np.argsort(-score[t == m], kind="stable")] for m in np.unique(t))
    return Ranked(y, order, last, by_t)


def evaluate(r: Ranked, w: np.ndarray | None = None, k: int = config.CALL_CAPACITY) -> dict[str, float]:
    """Mọi metric của một model với trọng số dòng w (mặc định 1 = không bootstrap)."""
    w = np.ones(len(r.y)) if w is None else np.asarray(w, float)
    ys, ws = r.y[r.order], w[r.order]
    tps = np.cumsum(ws * ys)[r.last]  # số ca churn được bắt khi hạ ngưỡng xuống từng mức điểm
    fps = np.cumsum(ws * (1 - ys))[r.last]
    tpr, fpr = np.r_[0, tps] / tps[-1], np.r_[0, fps] / fps[-1]
    precision = np.divide(tps, tps + fps, out=np.ones_like(tps), where=(tps + fps) > 0)
    per_month = []
    for idx in r.by_t:
        yt, wt = r.y[idx], w[idx]
        take = np.clip(k - (np.cumsum(wt) - wt), 0, wt)  # phần trọng số của mỗi dòng lọt vào top-k
        hit = (take * yt).sum()
        p, rc = hit / take.sum(), hit / max((wt * yt).sum(), 1e-12)
        per_month.append((p, rc, 2 * p * rc / (p + rc) if p + rc else 0.0))
    p_k, r_k, f1_k = np.mean(per_month, axis=0)
    return {
        "auc": float(np.trapezoid(tpr, fpr)),
        "pr_auc": float(np.sum(np.diff(tpr) * precision)),
        "p@k": float(p_k),
        "r@k": float(r_k),
        "f1@k": float(f1_k),
    }


def bootstrap(
    scores: dict[str, np.ndarray],
    frame: pd.DataFrame,
    n_boot: int = 1000,
    k: int = config.CALL_CAPACITY,
    reference: str | None = None,
    cluster: str | None = "customer_id",
    seed: int = config.SEED,
) -> pd.DataFrame:
    """Khoảng tin cậy 95% cho mọi metric của mọi model, cộng chênh lệch CẶP so với model `reference`.

    Chênh lệch cặp: hai model được đo trên CÙNG một mẫu bootstrap ở mỗi vòng, nên phần dao động do mẫu triệt tiêu —
    khoảng tin cậy của chênh lệch hẹp hơn nhiều so với việc so hai khoảng tin cậy riêng lẻ.
    """
    y, t = frame[LABEL].to_numpy(), frame["t"].to_numpy()
    ranked = {name: rank(s, y, t) for name, s in scores.items()}
    codes = pd.factorize(frame[cluster])[0] if cluster else np.arange(len(frame))
    n = codes.max() + 1
    rng = np.random.default_rng(seed)
    draws: dict[str, list[dict]] = {name: [] for name in ranked}
    for _ in range(n_boot):
        w = np.bincount(rng.integers(0, n, n), minlength=n)[codes]
        for name, r in ranked.items():
            draws[name].append(evaluate(r, w, k))
    point = {name: evaluate(r, k=k) for name, r in ranked.items()}
    boot = {name: pd.DataFrame(d) for name, d in draws.items()}
    rows = []
    for name in ranked:
        for m in METRICS:
            row = {"model": name, "metric": m, "value": point[name][m]}
            row |= {"lo": boot[name][m].quantile(0.025), "hi": boot[name][m].quantile(0.975)}
            if reference and name != reference:
                delta = boot[name][m] - boot[reference][m]
                row |= {"delta": point[name][m] - point[reference][m], "p_better": float((delta > 0).mean())}
                row |= {"delta_lo": delta.quantile(0.025), "delta_hi": delta.quantile(0.975)}
            rows.append(row)
    return pd.DataFrame(rows)


def table(results: pd.DataFrame, k: int = config.CALL_CAPACITY) -> str:
    """Bảng markdown: mỗi model một dòng, mỗi ô "giá trị [KTC 95%]"; cột cuối là chênh lệch P@k so với tham chiếu."""
    names = {"auc": "AUC", "pr_auc": "PR-AUC", "p@k": f"P@{k}", "r@k": f"R@{k}", "f1@k": f"F1@{k}"}
    lines = ["| Model | " + " | ".join(names.values()) + f" | Δ P@{k} so với tham chiếu |", "|---" * 7 + "|"]
    for model, g in results.groupby("model", sort=False):
        g = g.set_index("metric")
        cells = [f"{g.at[m, 'value']:.3f} [{g.at[m, 'lo']:.3f}–{g.at[m, 'hi']:.3f}]" for m in METRICS]
        if "delta" in g and pd.notna(g.at["p@k", "delta"]):
            d = g.loc["p@k"]
            cells.append(f"{d.delta:+.3f} [{d.delta_lo:+.3f}…{d.delta_hi:+.3f}]")
        else:
            cells.append("—")
        lines.append(f"| {model} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
