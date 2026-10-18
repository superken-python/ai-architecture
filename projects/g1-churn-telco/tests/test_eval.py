"""A3: chia theo thời gian, bộ đánh giá đóng băng, metric khớp sklearn, bootstrap và baseline."""

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, roc_auc_score

from churn_telco import baselines, config, evaluate, metrics, split
from churn_telco.features import CATEGORICAL, LABEL, NUMERIC


def test_time_split_has_no_overlap(small):
    parts = split.split(small.df)
    assert parts["train"]["t"].max() < parts["valid"]["t"].min()
    assert parts["valid"]["t"].max() < parts["test"]["t"].min()
    assert sum(len(p) for p in parts.values()) == len(small.df)


def test_frozen_test_detects_any_change(small):
    manifest = small.root / "eval" / "manifest.json"
    assert len(split.frozen_test(small.df, manifest)) == json.loads(manifest.read_text())["rows"]
    tampered = small.df.copy()
    row = tampered.index[tampered["t"] == tampered["t"].max()][0]
    tampered.loc[row, LABEL] = 1 - tampered.loc[row, LABEL]  # đổi đúng MỘT nhãn
    with pytest.raises(ValueError, match="không khớp"):
        split.frozen_test(tampered, manifest)


def test_freeze_refuses_to_overwrite(small):
    with pytest.raises(FileExistsError):
        split.freeze(small.df, small.root / "eval" / "manifest.json")


@pytest.fixture(scope="module")
def scored(small):
    test = split.split(small.df)["test"]
    rng = np.random.default_rng(0)
    score = test[LABEL] * rng.random(len(test)) + rng.random(len(test))  # điểm có tín hiệu, không hoà
    return test, score.to_numpy()


def test_metrics_match_sklearn(scored):
    test, score = scored
    m = metrics.evaluate(metrics.rank(score, test[LABEL], test["t"]))
    assert m["auc"] == pytest.approx(roc_auc_score(test[LABEL], score))
    assert m["pr_auc"] == pytest.approx(average_precision_score(test[LABEL], score))


def test_metrics_handle_ties_and_weights_like_sklearn(scored):
    test, _ = scored
    ties = (test["contract_months"] == 0).to_numpy(float)  # chỉ 2 mức điểm: rất nhiều điểm hoà
    w = np.random.default_rng(1).integers(0, 3, len(test))
    m = metrics.evaluate(metrics.rank(ties, test[LABEL], test["t"]), w)
    assert m["auc"] == pytest.approx(roc_auc_score(test[LABEL], ties, sample_weight=w))
    assert m["pr_auc"] == pytest.approx(average_precision_score(test[LABEL], ties, sample_weight=w))


def test_precision_at_k_per_month(scored):
    test, score = scored
    k = 50
    expected = np.mean([g.assign(s=score[test["t"] == t]).nlargest(k, "s")[LABEL].mean() for t, g in test.groupby("t")])
    assert metrics.evaluate(metrics.rank(score, test[LABEL], test["t"]), k=k)["p@k"] == pytest.approx(expected)


def test_bootstrap_interval_and_paired_delta(scored):
    test, score = scored
    res = metrics.bootstrap({"a": score, "b": score.copy()}, test, n_boot=200, k=50, reference="b")
    row = res.set_index(["model", "metric"]).loc[("a", "auc")]
    assert row.lo <= row.value <= row.hi
    assert row.delta == 0 and row.delta_lo == 0 and row.delta_hi == 0  # cùng một model: chênh lệch cặp đúng bằng 0


def test_cluster_bootstrap_is_wider_than_row_bootstrap(scored):
    """Một khách xuất hiện nhiều tháng → các dòng tương quan → rút theo dòng làm KTC hẹp giả tạo."""
    test, score = scored
    width = {}
    for cluster in ("customer_id", None):
        r = metrics.bootstrap({"m": score}, test, n_boot=300, k=50, cluster=cluster).set_index("metric")
        width[cluster] = (r["hi"] - r["lo"]).loc[["auc", "pr_auc"]].mean()
    assert width["customer_id"] >= width[None] * 0.9


def test_random_baseline_hits_base_rate(small):
    test = split.split(small.df)["test"]
    m = metrics.evaluate(metrics.rank(baselines.random_scores(test), test[LABEL], test["t"]), k=200)
    assert m["auc"] == pytest.approx(0.5, abs=0.06)


def test_logistic_pipeline_learns_only_from_train(small):
    parts = split.split(small.df)
    model = baselines.fit_logistic(parts["train"])
    imputer = model.named_steps["pre"].named_transformers_["num"].named_steps["simpleimputer"]
    expected = parts["train"][NUMERIC].median().to_numpy()
    np.testing.assert_allclose(imputer.statistics_, expected)  # median của TRAIN, không phải của cả bảng
    assert list(model.feature_names_in_) == CATEGORICAL + NUMERIC


def test_harness_compares_everything_on_the_frozen_set(small):
    res = evaluate.run(
        "test",
        n_boot=50,
        processed=small.processed,
        manifest=small.root / "eval" / "manifest.json",
        models_dir=small.root / "models",
    )
    models = list(res["model"].unique())
    assert models[:4] == [*baselines.RULES, evaluate.REFERENCE] and "LightGBM v2" in models  # baseline trước, model sau
    assert set(res["metric"]) == set(metrics.METRICS)
    table = metrics.table(res, k=config.CALL_CAPACITY)
    assert table.count("\n") == len(models) + 1
    assert isinstance(res, pd.DataFrame)
