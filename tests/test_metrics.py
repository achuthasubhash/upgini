import os

import pandas as pd
import pytest
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from requests_mock.mocker import Mocker
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import get_scorer

from upgini import FeaturesEnricher, SearchKey

from .utils import (
    mock_default_requests,
    mock_get_features_meta,
    mock_get_metadata,
    mock_initial_search,
    mock_initial_summary,
    mock_raw_features,
)

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "test_data/enricher/",
)


def test_default_metric_binary(requests_mock: Mocker):
    url = "http://fake_url2"
    mock_default_requests(requests_mock, url)
    search_task_id = mock_initial_search(requests_mock, url)
    ads_search_task_id = mock_initial_summary(
        requests_mock,
        url,
        search_task_id,
        hit_rate=99.0,
        eval_set_metrics=[
            {"eval_set_index": 1, "hit_rate": 100, "auc": 0.5},
            {"eval_set_index": 2, "hit_rate": 99, "auc": 0.77},
        ],
    )
    mock_get_metadata(requests_mock, url, search_task_id)
    mock_get_features_meta(
        requests_mock,
        url,
        ads_search_task_id,
        ads_features=[{"name": "ads_feature1", "importance": 10.1, "matchedInPercent": 99.0, "valueType": "NUMERIC"}],
        etalon_features=[{"name": "feature1", "importance": 0.1, "matchedInPercent": 100.0, "valueType": "NUMERIC"}],
    )
    mock_raw_features(requests_mock, url, search_task_id, os.path.join(FIXTURE_DIR, "features.csv.gz"))

    df = pd.read_csv(os.path.join(FIXTURE_DIR, "input.csv"))
    X = df.loc[0:499, ["phone", "feature1"]]
    y = df.loc[0:499, "target"].values
    eval_X_1 = df.loc[500:749, ["phone", "feature1"]]
    eval_y_1 = df.loc[500:749, "target"].values
    eval_X_2 = df.loc[750:999, ["phone", "feature1"]]
    eval_y_2 = df.loc[750:999, "target"].values
    eval_set = [(eval_X_1, eval_y_1), (eval_X_2, eval_y_2)]
    enricher = FeaturesEnricher(
        search_keys={"phone": SearchKey.PHONE},
        endpoint=url,
    )

    with pytest.raises(Exception, match="Fit wasn't completed successfully"):
        enricher.calculate_metrics(X, y)

    enriched_X = enricher.fit_transform(X, y, eval_set)

    assert len(enriched_X) == len(X)

    assert enricher.enriched_eval_set is not None
    assert len(enricher.enriched_eval_set) == 500

    metrics_df = enricher.calculate_metrics(X, y, eval_set)
    print(metrics_df)
    assert metrics_df.loc["train", "match_rate"] == 99.0
    assert metrics_df.loc["train", "baseline roc_auc"] == approx(0.503842)
    assert metrics_df.loc["train", "enriched roc_auc"] == approx(0.507683)
    assert metrics_df.loc["train", "uplift"] == approx(0.003842)

    assert metrics_df.loc["eval 1", "match_rate"] == 100.0
    assert metrics_df.loc["eval 1", "baseline roc_auc"] == approx(0.463245)
    assert metrics_df.loc["eval 1", "enriched roc_auc"] == approx(0.467250)
    assert metrics_df.loc["eval 1", "uplift"] == approx(0.004005)

    assert metrics_df.loc["eval 2", "match_rate"] == 99.0
    assert metrics_df.loc["eval 2", "baseline roc_auc"] == approx(0.499903)
    assert metrics_df.loc["eval 2", "enriched roc_auc"] == approx(0.494628)
    assert metrics_df.loc["eval 2", "uplift"] == approx(-0.005275)


def test_catboost_metric_binary(requests_mock: Mocker):
    url = "http://fake_url2"
    mock_default_requests(requests_mock, url)
    search_task_id = mock_initial_search(requests_mock, url)
    ads_search_task_id = mock_initial_summary(
        requests_mock,
        url,
        search_task_id,
        hit_rate=99.0,
        eval_set_metrics=[
            {"eval_set_index": 1, "hit_rate": 100, "auc": 0.5},
            {"eval_set_index": 2, "hit_rate": 99, "auc": 0.5},
        ],
    )
    mock_get_metadata(requests_mock, url, search_task_id)
    mock_get_features_meta(
        requests_mock,
        url,
        ads_search_task_id,
        ads_features=[{"name": "ads_feature1", "importance": 10.1, "matchedInPercent": 99.0, "valueType": "NUMERIC"}],
        etalon_features=[{"name": "feature1", "importance": 0.1, "matchedInPercent": 100.0, "valueType": "NUMERIC"}],
    )
    mock_raw_features(requests_mock, url, search_task_id, os.path.join(FIXTURE_DIR, "features.csv.gz"))

    df = pd.read_csv(os.path.join(FIXTURE_DIR, "input.csv"))
    X = df.loc[0:499, ["phone", "feature1"]]
    y = df.loc[0:499, "target"].values
    eval_X_1 = df.loc[500:749, ["phone", "feature1"]]
    eval_y_1 = df.loc[500:749, "target"].values
    eval_X_2 = df.loc[750:999, ["phone", "feature1"]]
    eval_y_2 = df.loc[750:999, "target"].values
    eval_set = [(eval_X_1, eval_y_1), (eval_X_2, eval_y_2)]
    enricher = FeaturesEnricher(
        search_keys={"phone": SearchKey.PHONE},
        endpoint=url,
    )

    with pytest.raises(Exception, match="Fit wasn't completed successfully"):
        enricher.calculate_metrics(X, y)

    enriched_X = enricher.fit_transform(X, y, eval_set)

    assert len(enriched_X) == len(X)

    assert enricher.enriched_eval_set is not None
    assert len(enricher.enriched_eval_set) == 500

    estimator = CatBoostClassifier(random_seed=42, verbose=False)
    metrics_df = enricher.calculate_metrics(X, y, eval_set, estimator=estimator, scoring="roc_auc")
    print(metrics_df)
    assert metrics_df.loc["train", "match_rate"] == 99.0
    assert metrics_df.loc["train", "baseline roc_auc"] == approx(0.503201)
    assert metrics_df.loc["train", "enriched roc_auc"] == approx(0.504002)
    assert metrics_df.loc["train", "uplift"] == approx(0.000800)

    assert metrics_df.loc["eval 1", "match_rate"] == 100.0
    assert metrics_df.loc["eval 1", "baseline roc_auc"] == approx(0.472644)
    assert metrics_df.loc["eval 1", "enriched roc_auc"] == approx(0.476520)
    assert metrics_df.loc["eval 1", "uplift"] == approx(0.003876)

    assert metrics_df.loc["eval 2", "match_rate"] == 99.0
    assert metrics_df.loc["eval 2", "baseline roc_auc"] == approx(0.506015)
    assert metrics_df.loc["eval 2", "enriched roc_auc"] == approx(0.505436)
    assert metrics_df.loc["eval 2", "uplift"] == approx(-0.000579)


@pytest.mark.skip()
def test_lightgbm_metric_binary(requests_mock: Mocker):
    url = "http://fake_url2"
    mock_default_requests(requests_mock, url)
    search_task_id = mock_initial_search(requests_mock, url)
    ads_search_task_id = mock_initial_summary(
        requests_mock,
        url,
        search_task_id,
        hit_rate=99.0,
        eval_set_metrics=[
            {"eval_set_index": 1, "hit_rate": 100, "auc": 0.5},
            {"eval_set_index": 2, "hit_rate": 99, "auc": 0.77},
        ],
    )
    mock_get_metadata(requests_mock, url, search_task_id)
    mock_get_features_meta(
        requests_mock,
        url,
        ads_search_task_id,
        ads_features=[{"name": "ads_feature1", "importance": 10.1, "matchedInPercent": 99.0, "valueType": "NUMERIC"}],
        etalon_features=[{"name": "feature1", "importance": 0.1, "matchedInPercent": 100.0, "valueType": "NUMERIC"}],
    )
    mock_raw_features(requests_mock, url, search_task_id, os.path.join(FIXTURE_DIR, "features.csv.gz"))

    df = pd.read_csv(os.path.join(FIXTURE_DIR, "input.csv"))
    X = df.loc[0:499, ["phone", "feature1"]]
    y = df.loc[0:499, "target"].values
    eval_X_1 = df.loc[500:749, ["phone", "feature1"]]
    eval_y_1 = df.loc[500:749, "target"].values
    eval_X_2 = df.loc[750:999, ["phone", "feature1"]]
    eval_y_2 = df.loc[750:999, "target"].values
    eval_set = [(eval_X_1, eval_y_1), (eval_X_2, eval_y_2)]
    enricher = FeaturesEnricher(
        search_keys={"phone": SearchKey.PHONE},
        endpoint=url,
    )

    with pytest.raises(Exception, match="Fit wasn't completed successfully"):
        enricher.calculate_metrics(X, y)

    enriched_X = enricher.fit_transform(X, y, eval_set)

    assert len(enriched_X) == len(X)

    assert enricher.enriched_eval_set is not None
    assert len(enricher.enriched_eval_set) == 500

    estimator = LGBMClassifier(random_seed=42)
    metrics_df = enricher.calculate_metrics(X, y, eval_set, estimator=estimator)
    print(metrics_df)
    assert metrics_df.loc["train", "match_rate"] == 99.0
    assert metrics_df.loc["train", "baseline roc_auc"] == approx(0.502001)  # Investigate same values
    assert metrics_df.loc["train", "enriched roc_auc"] == approx(0.502001)
    assert metrics_df.loc["train", "uplift"] == approx(0.0)

    assert metrics_df.loc["eval 1", "match_rate"] == 100.0
    assert metrics_df.loc["eval 1", "baseline roc_auc"] == approx(0.532685)
    assert metrics_df.loc["eval 1", "enriched roc_auc"] == approx(0.532685)
    assert metrics_df.loc["eval 1", "uplift"] == approx(0.0)

    assert metrics_df.loc["eval 2", "match_rate"] == 99.0
    assert metrics_df.loc["eval 2", "baseline roc_auc"] == approx(0.544197)
    assert metrics_df.loc["eval 2", "enriched roc_auc"] == approx(0.544197)
    assert metrics_df.loc["eval 2", "uplift"] == approx(0.0)


def test_rf_metric_binary(requests_mock: Mocker):
    url = "http://fake_url2"
    mock_default_requests(requests_mock, url)
    search_task_id = mock_initial_search(requests_mock, url)
    ads_search_task_id = mock_initial_summary(
        requests_mock,
        url,
        search_task_id,
        hit_rate=99.0,
        eval_set_metrics=[
            {"eval_set_index": 1, "hit_rate": 100, "auc": 0.5},
            {"eval_set_index": 2, "hit_rate": 99, "auc": 0.77},
        ],
    )
    mock_get_metadata(requests_mock, url, search_task_id)
    mock_get_features_meta(
        requests_mock,
        url,
        ads_search_task_id,
        ads_features=[{"name": "ads_feature1", "importance": 10.1, "matchedInPercent": 99.0, "valueType": "NUMERIC"}],
        etalon_features=[{"name": "feature1", "importance": 0.1, "matchedInPercent": 100.0, "valueType": "NUMERIC"}],
    )
    mock_raw_features(requests_mock, url, search_task_id, os.path.join(FIXTURE_DIR, "features.csv.gz"))

    df = pd.read_csv(os.path.join(FIXTURE_DIR, "input.csv"))
    X = df.loc[0:499, ["phone", "feature1"]]
    y = df.loc[0:499, "target"].values
    eval_X_1 = df.loc[500:749, ["phone", "feature1"]]
    eval_y_1 = df.loc[500:749, "target"].values
    eval_X_2 = df.loc[750:999, ["phone", "feature1"]]
    eval_y_2 = df.loc[750:999, "target"].values
    eval_set = [(eval_X_1, eval_y_1), (eval_X_2, eval_y_2)]
    enricher = FeaturesEnricher(
        search_keys={"phone": SearchKey.PHONE},
        endpoint=url,
    )

    with pytest.raises(Exception, match="Fit wasn't completed successfully"):
        enricher.calculate_metrics(X, y)

    enriched_X = enricher.fit_transform(X, y, eval_set)

    assert len(enriched_X) == len(X)

    assert enricher.enriched_eval_set is not None
    assert len(enricher.enriched_eval_set) == 500

    estimator = RandomForestClassifier(random_state=42)
    scoring = get_scorer("neg_mean_squared_error")
    metrics_df = enricher.calculate_metrics(X, y, eval_set, estimator=estimator, scoring=scoring)
    print(metrics_df)
    baseline_metric = "baseline make_scorer(mean_squared_error, greater_is_better=False)"
    enriched_metric = "enriched make_scorer(mean_squared_error, greater_is_better=False)"
    assert metrics_df.loc["train", "match_rate"] == 99.0
    assert metrics_df.loc["train", baseline_metric] == approx(-0.516)  # Investigate same values
    assert metrics_df.loc["train", enriched_metric] == approx(-0.516)
    assert metrics_df.loc["train", "uplift"] == approx(0.0)

    assert metrics_df.loc["eval 1", "match_rate"] == 100.0
    assert metrics_df.loc["eval 1", baseline_metric] == approx(-0.52)
    assert metrics_df.loc["eval 1", enriched_metric] == approx(-0.52)
    assert metrics_df.loc["eval 1", "uplift"] == approx(0.0)

    assert metrics_df.loc["eval 2", "match_rate"] == 99.0
    assert metrics_df.loc["eval 2", baseline_metric] == approx(-0.456)
    assert metrics_df.loc["eval 2", enriched_metric] == approx(-0.456)
    assert metrics_df.loc["eval 2", "uplift"] == approx(0.0)


def approx(value: float):
    return pytest.approx(value, abs=0.000001)