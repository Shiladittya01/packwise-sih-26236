from pathlib import Path
import math

import pytest

from fastapi.testclient import TestClient

import backend.packwise_api as api

client = TestClient(api.app)


def tomato_payload(**updates):
    payload = {
        "commodity": "tomatoes", "moisture": 94.5, "fat": 0.2, "ph": 4.3,
        "respiration_rate": 7.5, "shelf_life": 7, "temperature": 10,
        "humidity": 90, "storage_condition": "ambient", "transport_condition": "local",
    }
    payload.update(updates)
    return payload


def estimate_payload(commodity, **updates):
    payload = {
        "commodity": commodity, "moisture": 78, "fat": 2, "ph": 5.5,
        "respiration_rate": 0, "shelf_life": 30, "temperature": 22,
        "humidity": 60, "storage_condition": "ambient", "transport_condition": "local",
    }
    payload.update(updates)
    return payload


def test_health_and_model_card_are_loaded():
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["model_loaded"] is True
    assert health.json()["training_rows"] == 331
    assert health.json()["commodity_name_used_by_model"] is False
    assert len(health.json()["model_features"]) == 8
    assert health.json()["food_reference_terms"] == 12655
    report = client.get("/api/model-card")
    assert report.status_code == 200
    assert report.json()["model_name"] in {"logistic_regression", "random_forest", "gradient_boosting"}
    assert "commodity" not in report.json()["input_features"]
    assert "ph" not in report.json()["input_features"]
    assert set(report.json()["cross_validation"]) == {"logistic_regression", "random_forest", "gradient_boosting"}


def test_inputs_reach_model_and_change_prediction():
    lower_respiration = client.post("/api/recommend", json=tomato_payload())
    higher_respiration = client.post("/api/recommend", json=tomato_payload(respiration_rate=13.5, shelf_life=14, temperature=15))
    assert lower_respiration.status_code == higher_respiration.status_code == 200
    first = lower_respiration.json()
    second = higher_respiration.json()
    assert first["recommended_material"]["id"] == "breathable_pe_film"
    assert second["recommended_material"]["id"] == "microperforated_polyolefin"
    assert first["input_echo"]["respiration_rate"] == 7.5
    assert second["input_echo"]["shelf_life"] == 14
    assert 0 <= first["confidence"] <= 1
    assert first["target_shelf_life_days"] == 7
    assert 0 <= first["suitability"]["score"] <= 100
    assert 0 <= first["data_coverage_percent"] <= 100
    assert first["suitability"]["assessment_type"] == "estimated"
    assert first["suitability"]["key_factors"]
    assert first["model_prediction"]["material"]["id"] == "breathable_pe_film"
    assert first["suitability"]["score"] != second["suitability"]["score"] or first["recommended_material"]["id"] != second["recommended_material"]["id"]
    assert first["important_features"]


def test_chips_shelf_life_changes_candidate():
    common = {
        "commodity": "potato_chips", "moisture": 1.86, "fat": 34, "ph": 6.2,
        "respiration_rate": 0, "temperature": 25, "humidity": 60,
        "storage_condition": "ambient", "transport_condition": "long",
    }
    short = client.post("/api/recommend", json={**common, "shelf_life": 120}).json()
    long = client.post("/api/recommend", json={**common, "shelf_life": 200}).json()
    assert short["recommended_material"]["id"] == "metallized_laminate"
    assert long["recommended_material"]["id"] == "foil_laminate"


def test_other_supported_food_reaches_model_and_catalog():
    payload = {
        "commodity": "Pasteurized milk", "moisture": 88.1, "fat": 3.2, "ph": 6.7,
        "respiration_rate": 0, "shelf_life": 7, "temperature": 4,
        "humidity": 65, "storage_condition": "chilled", "transport_condition": "cold",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["recommended_material"]["id"] == "hdpe_bottle"
    assert body["packaging_properties"]["otr"] is None
    assert body["recommended_material"]["image_asset"] == "/materials/hdpe-bottle.svg"
    assert body["recommended_material"]["references"]
    assert 0 <= body["suitability"]["score"] <= 100
    assert body["sustainability"]["assessment_type"] == "estimated_index"
    assert body["model_prediction"]["material"]["id"] == "hdpe_bottle"


def test_bananas_return_the_sourced_carton_candidate():
    payload = {
        "commodity": "banana", "moisture": 74.91, "fat": 0.33, "ph": 6,
        "respiration_rate": 20, "shelf_life": 21, "temperature": 13.5,
        "humidity": 90, "storage_condition": "ambient", "transport_condition": "long",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["input_echo"]["commodity"] == "bananas"
    assert body["recommended_material"]["id"] == "ventilated_banana_carton"
    assert 0 <= body["suitability"]["score"] <= 100
    assert {ref["id"] for ref in body["recommended_material"]["references"]} == {"fao_banana_packaging", "ucdavis_banana"}
    assert any("13–14 °C" in warning for warning in body["warnings"])
    assert any("only this one curated target class" in warning for warning in body["warnings"])


def test_banana_chilling_conditions_are_rejected():
    payload = {
        "commodity": "banana", "moisture": 74.91, "fat": 0.33, "ph": 6,
        "respiration_rate": 20, "shelf_life": 21, "temperature": 4,
        "humidity": 90, "storage_condition": "chilled", "transport_condition": "long",
    }
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 422
    assert "chilling-sensitive" in str(response.json())


def test_missing_fields_are_ignored_but_out_of_range_values_are_rejected():
    payload = tomato_payload()
    del payload["humidity"]
    partial = client.post("/api/recommend", json=payload)
    assert partial.status_code == 200
    assert partial.json()["input_echo"]["humidity"] is None
    assert partial.json()["suitability"]["score"] is not None
    blank_fields = tomato_payload(**{key: "" for key in ["moisture", "fat", "ph", "respiration_rate", "shelf_life", "temperature", "humidity", "storage_condition", "transport_condition"]})
    blank_response = client.post("/api/recommend", json=blank_fields)
    assert blank_response.status_code == 200
    assert blank_response.json()["suitability"]["score"] is not None
    assert blank_response.json()["target_shelf_life_days"] is None
    assert client.post("/api/recommend", json=tomato_payload(moisture=80, fat=30)).status_code == 422
    assert client.post("/api/recommend", json=tomato_payload(ph=15)).status_code == 422
    assert client.post("/api/recommend", json=tomato_payload(humidity=150)).status_code == 422
    assert client.post("/api/recommend", json=tomato_payload(storage_condition="frozen", temperature=-18)).status_code == 422


def test_valid_food_reference_accepts_unseen_apple_and_dragon_fruit():
    apple = {
        "commodity": "APPLE", "moisture": 85, "fat": 0.2, "ph": 3.6,
        "respiration_rate": 3, "shelf_life": 30, "temperature": 4,
        "humidity": 90, "storage_condition": "chilled", "transport_condition": "long",
    }
    dragon_fruit = {
        "commodity": "Dragon Fruit", "moisture": 85, "fat": 0.2, "ph": 4.5,
        "respiration_rate": 12, "shelf_life": 14, "temperature": 10,
        "humidity": 90, "storage_condition": "ambient", "transport_condition": "long",
    }
    for payload in [apple, dragon_fruit]:
        response = client.post("/api/recommend", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["prediction_scope"] == "valid_unseen_commodity"
        assert body["recommended_material"]["id"]
        assert 0 <= body["confidence"] <= 1
        assert "model probability" in body["confidence_note"].casefold()
        assert body["target_shelf_life_days"] == payload["shelf_life"]
        assert 0 <= body["suitability"]["score"] <= 100
        assert 0 <= body["sustainability"]["score"] <= 100
        assert 0 <= body["data_coverage_percent"] <= 100
        assert body["suitability"]["key_factors"]
        assert body["recommended_material"]["image_asset"].startswith("/materials/")
        assert body["explanation"].strip()
        assert len(body["alternatives"]) == 3


@pytest.mark.parametrize("payload", [
    estimate_payload("Rice", moisture=11, fat=1, ph=6.2, shelf_life=180, humidity=55),
    estimate_payload("Milk", moisture=88.1, fat=3.2, ph=6.7, shelf_life=7, temperature=4, humidity=65, storage_condition="chilled", transport_condition="cold"),
    estimate_payload("Apple", moisture=85, fat=0.2, ph=3.6, respiration_rate=3, shelf_life=30, temperature=4, humidity=90, storage_condition="chilled", transport_condition="long"),
    estimate_payload("Potato", moisture=79, fat=0.1, ph=6.2, respiration_rate=10, shelf_life=30),
    estimate_payload("Pickle", moisture=65, fat=10, ph=3.5, shelf_life=30),
    estimate_payload("Biscuits", moisture=4, fat=12, ph=6.5, shelf_life=90),
    estimate_payload("Fresh vegetables", moisture=90, fat=0.2, ph=6, respiration_rate=12, shelf_life=14),
    estimate_payload("Kelp Crisps", moisture=8, fat=15, ph=6, shelf_life=90),
    estimate_payload("Homemade Pickle", moisture=65, fat=10, ph=3.5, respiration_rate=None, shelf_life=None, temperature=None, humidity=None, storage_condition=None, transport_condition=None),
    estimate_payload("Homemade Pickle", moisture=65, fat=10, ph=3.5, respiration_rate=0, shelf_life=30, temperature=25, humidity=60, storage_condition="ambient", transport_condition="long"),
])
def test_requested_food_cases_always_return_complete_estimates(payload):
    response = client.post("/api/recommend", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert math.isfinite(body["suitability"]["score"])
    assert 0 <= body["suitability"]["score"] <= 100
    assert 0 <= body["sustainability"]["score"] <= 100
    assert 0 <= body["data_coverage_percent"] <= 100
    assert body["recommended_material"]["id"]
    assert body["recommended_material"]["structure"]
    assert body["explanation"].strip()
    assert body["suitability"]["key_factors"]
    assert body["suitability"]["assessment_type"] == "estimated"


def test_storage_and_property_changes_can_change_fit_and_coverage():
    lower_humidity = client.post("/api/recommend", json=estimate_payload(
        "Fresh produce", moisture=55, fat=1, ph=6, respiration_rate=8,
        shelf_life=14, temperature=10, humidity=40, storage_condition="ambient",
    )).json()
    higher_humidity = client.post("/api/recommend", json=estimate_payload(
        "Fresh produce", moisture=55, fat=1, ph=6, respiration_rate=8,
        shelf_life=14, temperature=10, humidity=95, storage_condition="ambient",
    )).json()
    partial = client.post("/api/recommend", json=estimate_payload(
        "Fresh produce", moisture=55, fat=1, ph=6, respiration_rate=None,
        shelf_life=None, temperature=None, humidity=None, storage_condition=None,
        transport_condition=None,
    )).json()
    assert (lower_humidity["suitability"]["score"], lower_humidity["recommended_material"]["id"]) != (higher_humidity["suitability"]["score"], higher_humidity["recommended_material"]["id"])
    assert partial["data_coverage_percent"] < lower_humidity["data_coverage_percent"]


def test_inference_uses_only_saved_property_features(monkeypatch):
    api.load_artifacts(force=True)
    seen = {}

    class InspectPipeline:
        def predict(self, frame):
            seen["columns"] = list(frame.columns)
            return ["microperforated_polyolefin"]

    monkeypatch.setattr(api, "_pipeline", InspectPipeline())
    response = client.post("/api/recommend", json=tomato_payload(commodity="Dragon Fruit"))
    assert response.status_code == 200
    assert seen["columns"] == api._metadata["input_features"]
    assert "commodity" not in seen["columns"]
    assert "ph" not in seen["columns"]
    assert response.json()["confidence"] is None


def test_invalid_food_names_are_rejected_before_model_inference(monkeypatch):
    def inference_must_not_run(_row):
        raise AssertionError("invalid commodity reached model inference")

    monkeypatch.setattr(api, "predict_packaging", inference_must_not_run)
    for name in ["jjjgjghghg", "abcxyz123", "qwertyfood999", "asdfghjkl", "custom:jjjgjghghg"]:
        response = client.post("/api/recommend", json=tomato_payload(commodity=name))
        assert response.status_code == 422
        assert "Please enter a valid food commodity name" in str(response.json())
        assert "recommended_material" not in response.json()


def test_prefixed_valid_food_is_still_accepted_for_compatibility():
    response = client.post("/api/recommend", json=tomato_payload(commodity="custom:Mango"))
    assert response.status_code == 200
    body = response.json()
    assert body["input_echo"]["commodity"] == "custom:Mango"
    assert body["prediction_scope"] == "valid_unseen_commodity"
    assert 0 <= body["confidence"] <= 1
    assert 0 <= body["suitability"]["score"] <= 100
    assert 0 <= body["sustainability"]["score"] <= 100
    assert body["alternatives"]
    assert any("new to the catalog" in warning for warning in body["warnings"])
    assert "not one of the named training profiles" not in body["explanation"]
    assert all(feature["feature"] != "commodity" for feature in body["important_features"])


def test_custom_food_prefix_requires_a_name():
    response = client.post("/api/recommend", json=tomato_payload(commodity="custom:"))
    assert response.status_code == 422
    assert "Please enter a valid food commodity name" in str(response.json())


def test_extreme_but_physical_custom_values_return_support_warning():
    response = client.post("/api/recommend", json=tomato_payload(
        commodity="Dragon Fruit", moisture=99, respiration_rate=100,
        shelf_life=400, temperature=25, humidity=99,
        storage_condition="ambient", transport_condition="rough",
    ))
    assert response.status_code == 200
    assert any("outside the range used in model training" in warning for warning in response.json()["warnings"])


def test_cors_allows_local_vite_origin():
    response = client.options(
        "/api/recommend",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_model_artifact_failure_returns_503(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "_pipeline", None)
    monkeypatch.setattr(api, "_materials", None)
    monkeypatch.setattr(api, "_sources", None)
    monkeypatch.setattr(api, "PIPELINE_PATH", Path(tmp_path) / "missing-model.joblib")
    health = client.get("/api/health")
    recommendation = client.post("/api/recommend", json=tomato_payload())
    assert health.status_code == 503
    assert health.json()["detail"]["model_loaded"] is False
    assert recommendation.status_code == 200
    assert recommendation.json()["suitability"]["score"] is not None


def test_inference_error_uses_property_fallback(monkeypatch):
    class BrokenPipeline:
        def predict(self, _frame):
            raise RuntimeError("inference failure")

    monkeypatch.setattr(api, "_pipeline", BrokenPipeline())
    response = client.post("/api/recommend", json=tomato_payload())
    assert response.status_code == 200
    assert response.json()["suitability"]["score"] is not None
    assert any("model prediction was unavailable" in warning.casefold() for warning in response.json()["warnings"])


def test_material_database_does_not_claim_unsourced_numeric_properties():
    response = client.get("/api/materials")
    assert response.status_code == 200
    profiles = response.json()["materials"]
    assert len(profiles) == 9
    assert all(profile["otr"] is None and profile["wvtr"] is None for profile in profiles)
    for profile in profiles:
        asset = profile["image_asset"]
        assert asset.startswith("/materials/")
        assert (api.ROOT / "frontend" / "public" / asset.lstrip("/")).is_file()
        compatibility = profile["compatibility_profile"]
        assert compatibility["profile_kind"] == "qualitative_design_bands"
        assert {"oxygen_barrier", "water_vapor_barrier", "sealability"}.issubset(compatibility["ratings"])
        assert compatibility["profile_note"].startswith("Ordinal compatibility inputs")
