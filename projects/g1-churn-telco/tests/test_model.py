"""A5–A6: model LightGBM, hiệu chỉnh và quyết định theo chi phí, lý do SHAP, chấm điểm tháng mới."""

import json

import numpy as np
import pandas as pd
import pytest

from churn_telco import config, decision, explain, score, split, train
from churn_telco.features import LABEL


def test_bundle_roundtrip_gives_identical_predictions(small, tmp_path):
    path = train.save(small.bundle, tmp_path / "m")
    loaded = train.load(path)
    test = split.split(small.df)["test"]
    np.testing.assert_allclose(loaded.score(test), small.bundle.score(test))
    meta = json.loads((path / "bundle.json").read_text())
    assert {"features", "params", "best_iteration", "calibration", "valid", "trained_at", "versions"} <= set(meta)


def test_training_is_deterministic(small):
    again = train.train(small.df, "v2")
    test = split.split(small.df)["test"]
    np.testing.assert_allclose(again.score(test), small.bundle.score(test))


def test_model_beats_random_on_valid(small):
    assert small.bundle.meta["valid"]["auc"] > 0.6


def test_platt_fixes_a_miscalibrated_score():
    rng = np.random.default_rng(0)
    p_true = rng.beta(1, 30, 50_000)
    y = (rng.random(len(p_true)) < p_true).astype(int)
    inflated = np.clip(p_true * 4, 0, 0.99)  # model "tự tin thái quá", kiểu train với class weight
    cal = decision.apply_platt(inflated, **decision.fit_platt(inflated, y))
    assert decision.ece(cal, y) < decision.ece(inflated, y) / 3


def test_expected_value_and_break_even():
    value = np.array([1_620_000.0])  # cước 300.000 đ × 12 tháng × biên 45%
    p0 = decision.break_even(value)
    assert decision.expected_value(p0, value) == pytest.approx(0, abs=1e-6)
    assert decision.expected_value(p0 * 2, value) > 0 > decision.expected_value(p0 / 2, value)


def test_call_list_respects_capacity_and_positive_ev(small):
    test = split.split(small.df)["test"]
    calls = decision.call_list(test, small.bundle.proba(test), capacity=100)
    per_month = calls[calls["call"]].groupby("t").size()
    assert (per_month <= 100).all()
    assert (calls.loc[calls["call"], "ev"] > 0).all()


def test_profit_curve_columns(small):
    test = split.split(small.df)["test"]
    curve = decision.profit_curve(test, small.bundle.proba(test), ks=[50, 100, 200])
    assert list(curve["k"]) == [50, 100, 200]
    assert curve["recall"].is_monotonic_increasing


@pytest.mark.filterwarnings("ignore:LightGBM binary classifier:UserWarning")  # shap báo đổi kiểu output, không sao
def test_pred_contrib_equals_shap_library(small):
    shap = pytest.importorskip("shap")
    rows = split.split(small.df)["test"].head(200)
    ours = explain.shap_values(small.bundle, rows)
    theirs = shap.TreeExplainer(small.bundle.booster).shap_values(rows[small.bundle.features])
    np.testing.assert_allclose(ours.to_numpy(), np.asarray(theirs), atol=1e-8)


def test_shap_adds_up_to_the_log_odds(small):
    rows = split.split(small.df)["test"].head(200)
    values = explain.shap_values(small.bundle, rows)
    raw = small.bundle.booster.predict(rows[small.bundle.features], raw_score=True)
    bias = raw - values.sum(axis=1)
    assert np.allclose(bias, bias.iloc[0])  # phần còn lại là một hằng số (giá trị kỳ vọng của model)


def test_reasons_are_positive_readable_and_never_profile(small):
    test = split.split(small.df)["test"]
    top = test.assign(p=small.bundle.proba(test)).nlargest(50, "p")
    why = explain.reasons(small.bundle, top)
    assert why["reason_1"].notna().all()
    assert (why[["shap_1", "shap_2", "shap_3"]].fillna(1) > 0).all().all()
    assert (why["shap_1"] >= why["shap_2"].fillna(0)).all()
    profile_words = ("Hộ gia đình", "Doanh nghiệp", "tuổi")
    assert not why.filter(like="reason").stack().str.contains("|".join(profile_words)).any()


def test_scoring_a_future_month_without_labels(small):
    t = pd.Timestamp("2026-01-01")  # sau ngày cuối của dữ liệu: chưa ai biết nhãn
    df = score.build_features(t, small.interim, small.promos)
    assert LABEL not in df.columns and (df["t"] == t).all()
    calls = score.call_list(small.bundle, df, capacity=config.CALL_CAPACITY)
    assert 0 < len(calls) <= config.CALL_CAPACITY
    assert calls["rank"].is_monotonic_increasing
    assert {"customer_id", "p", "ev", "reason_1", "action_1"} <= set(calls.columns)
    assert not {"full_name", "phone", "email"} & set(calls.columns)
