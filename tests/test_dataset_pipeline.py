import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"


def test_dataset_is_deterministic_and_valid():
    dataset = ROOT / "datasets" / "processed" / "packwise_research_curated_v1.csv"
    before = hashlib.sha256(dataset.read_bytes()).hexdigest()
    subprocess.run([str(PYTHON), str(ROOT / "ml" / "training" / "generate_dataset.py")], check=True, capture_output=True, text=True)
    after = hashlib.sha256(dataset.read_bytes()).hexdigest()
    frame = pd.read_csv(dataset)
    metadata = json.loads((ROOT / "datasets" / "processed" / "dataset_metadata.json").read_text(encoding="utf-8"))
    assert before == after
    assert len(frame) == 331 == metadata["rows"]
    assert set(frame.loc[frame.commodity == "bananas", "recommended_packaging_material"]) == {"ventilated_banana_carton"}
    assert not frame.isna().any().any()
    assert not frame.duplicated([column for column in frame.columns if column != "_split_group"]).any()
    assert (frame.moisture_content + frame.fat_oil_content <= 100).all()


def test_saved_pipeline_and_feature_config_are_reproducible_artifacts():
    models = ROOT / "ml" / "models"
    assert (models / "packwise_pipeline.joblib").is_file()
    assert (models / "preprocessing_pipeline.joblib").is_file()
    config = json.loads((models / "feature_config.json").read_text(encoding="utf-8"))
    metadata = json.loads((models / "model_metadata.json").read_text(encoding="utf-8"))
    assert len(config["features"]) == 8
    assert "commodity" not in config["features"]
    assert "ph" in config["accepted_request_fields"]
    assert "ph" in config["validated_but_not_used_by_model"]
    assert "commodity" in config["validated_but_not_used_by_model"]
    assert "commodity" not in metadata["input_features"]
    assert metadata["dataset_rows"] == 331
    assert metadata["holdout"]["confusion_matrix"]


def test_foodon_reference_snapshot_is_bundled_and_broad():
    reference = json.loads((ROOT / "datasets" / "reference" / "foodon_food_commodities.json").read_text(encoding="utf-8"))
    assert reference["source"] == "FoodOn"
    assert reference["term_count"] > 10_000
    labels = {term["label"].casefold() for term in reference["terms"]}
    assert any("dragon fruit" in label for label in labels)
