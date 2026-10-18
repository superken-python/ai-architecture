"""Baseline (A3 · BIZ-02, ML-01): con số phải vượt TRƯỚC khi nói tới model "xịn".

Bốn mức, từ rẻ tới đắt:
1. Ngẫu nhiên — sàn: precision@500 ≈ tỷ lệ churn nền. Thấp hơn mức này là có lỗi.
2. Luật CSKH hiện tại — cách đang làm: gọi khách sắp hết hợp đồng, rồi khách hay báo lỗi mạng (framing A1).
3. Luật giảm sử dụng — luật của người phân tích sau EDA (A2): khách dùng ít đi nhiều nhất xếp trước.
4. Logistic regression trong một Pipeline — model tuyến tính đơn giản nhất dùng mọi feature.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from churn_telco import config
from churn_telco.features import CATEGORICAL, LABEL, NUMERIC


def _jitter(df: pd.DataFrame, seed: int = config.SEED) -> np.ndarray:
    """Nhiễu rất nhỏ để phá hoà điểm một cách ngẫu nhiên (luật cho rất nhiều khách cùng điểm)."""
    return np.random.default_rng(seed).random(len(df)) * 1e-6


def random_scores(df: pd.DataFrame) -> np.ndarray:
    return _jitter(df)


def rule_cskh(df: pd.DataFrame) -> np.ndarray:
    points = (
        4 * (df["days_to_contract_end"] <= 30)  # sắp hết hợp đồng: đội gia hạn vẫn gọi nhóm này
        + 2 * (df["network_tickets_60d"] >= 1)  # vừa phàn nàn về mạng
        + 1 * (df["contract_months"] == 0)  # không kỳ hạn: rời lúc nào cũng được
        + 1 * (df["late_or_unpaid_90d"] >= 1)  # trả cước trễ
    )
    return points.to_numpy(float) + _jitter(df)


def rule_usage_drop(df: pd.DataFrame) -> np.ndarray:
    ratio = df["usage_ratio"].fillna(1.0).to_numpy()  # data tháng trước / trung bình 3 tháng trước đó
    return -ratio + _jitter(df)  # dùng ít đi nhiều nhất thì xếp trước


def make_logistic(numeric: list[str] = NUMERIC, categorical: list[str] = CATEGORICAL) -> Pipeline:
    """Mọi bước tiền xử lý nằm TRONG Pipeline: imputer/scaler chỉ học từ tập train khi gọi fit — không rò rỉ."""
    pre = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical),
            ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), numeric),
        ]
    )
    return Pipeline([("pre", pre), ("model", LogisticRegression(C=0.5, max_iter=2000))])


def fit_logistic(train: pd.DataFrame) -> Pipeline:
    return make_logistic().fit(train[CATEGORICAL + NUMERIC], train[LABEL])


RULES = {"Ngẫu nhiên": random_scores, "Luật CSKH hiện tại": rule_cskh, "Luật giảm sử dụng": rule_usage_drop}
