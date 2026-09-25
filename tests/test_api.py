from pathlib import Path

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
    assert first["confidence"] is None
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
    assert body["recommended_material"]["references"]
    assert body["suitability"]["status"] == "preliminary_candidate"


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
    assert body["suitability"]["status"] == "preliminary_candidate"
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


def test_missing_and_invalid_fields_return_422():
    payload = tomato_payload()
    del payload["humidity"]
    assert client.post("/api/recommend", json=payload).status_code == 422
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
        assert "property-only" in body["explanation"]
        assert body["confidence"] is None
        assert body["alternatives"] == []


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
    assert body["confidence"] is None
    assert body["suitability"]["status"] == "review_required"
    assert body["alternatives"] == []
    assert any("no named training profile" in warning for warning in body["warnings"])
    assert "not one of the named training profiles" in body["explanation"]
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
    assert any("outside the global training-data span" in warning for warning in response.json()["warnings"])


def test_cors_allows_local_vite_origin():
    response = client.options(
        "/api/recommend",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_model_artifact_failure_returns_503(monkeypatch, tmp_path):
    monkeypatch.setattr(api, "_pipeline", None)
    monkeypatch.setattr(api, "PIPELINE_PATH", Path(tmp_path) / "missing-model.joblib")
    health = client.get("/api/health")
    recommendation = client.post("/api/recommend", json=tomato_payload())
    assert health.status_code == 503
    assert health.json()["detail"]["model_loaded"] is False
    assert recommendation.status_code == 503


def test_inference_error_returns_structured_500(monkeypatch):
    class BrokenPipeline:
        def predict(self, _frame):
            raise RuntimeError("inference failure")

    monkeypatch.setattr(api, "_pipeline", BrokenPipeline())
    response = client.post("/api/recommend", json=tomato_payload())
    assert response.status_code == 500
    assert response.json()["detail"] == "The model could not complete this recommendation."


def test_material_database_does_not_claim_unsourced_numeric_properties():
    response = client.get("/api/materials")
    assert response.status_code == 200
    profiles = response.json()["materials"]
    assert len(profiles) == 9
    assert all(profile["otr"] is None and profile["wvtr"] is None for profile in profiles)
