"""FastAPI service for Packwise's trained research-curated prototype model."""
from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Literal
from contextlib import asynccontextmanager

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "ml" / "models" / "packwise_pipeline.joblib"
METADATA_PATH = ROOT / "ml" / "models" / "model_metadata.json"
DATABASE_PATH = ROOT / "packaging_database" / "materials.json"
SOURCES_PATH = ROOT / "docs" / "research_sources.json"
FOOD_REFERENCE_PATH = ROOT / "datasets" / "reference" / "foodon_food_commodities.json"
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("packwise.api")

FOODS = {
    "tomatoes": {"name": "Fresh tomatoes", "aliases": ["tomato", "fresh tomato", "fresh tomatoes"]},
    "potato_chips": {"name": "Potato chips", "aliases": ["chips", "potato chips", "potato crisps"]},
    "biscuits": {"name": "Biscuits", "aliases": ["biscuit", "biscuits", "tea biscuits"]},
    "pasteurized_milk": {"name": "Pasteurized milk", "aliases": ["milk", "pasteurized milk"]},
    "frozen_vegetables": {"name": "Frozen vegetables", "aliases": ["frozen vegetable", "frozen vegetables", "frozen mixed vegetables"]},
    "lentils": {"name": "Dry lentils", "aliases": ["lentil", "lentils", "dry lentils"]},
    "bananas": {"name": "Mature-green bananas", "aliases": ["banana", "bananas", "mature-green banana", "mature green bananas", "cavendish banana"]},
}


def normalize_food_name(value: str) -> str:
    """Normalize punctuation, case, accents and ontology qualifiers for lookup."""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(character for character in normalized if not unicodedata.combining(character))
    normalized = re.sub(r"\([^)]*\)", " ", normalized.casefold())
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def load_foodon_reference() -> tuple[dict, frozenset[str]]:
    reference = json.loads(FOOD_REFERENCE_PATH.read_text(encoding="utf-8"))
    names = set()
    for term in reference.get("terms", []):
        for label in [term.get("label", ""), *term.get("aliases", [])]:
            normalized = normalize_food_name(label)
            if normalized:
                names.add(normalized)
    return reference, frozenset(names)


FOODON_REFERENCE, FOODON_NAMES = load_foodon_reference()
FOOD_ALIASES = {
    normalize_food_name(alias.replace("_", " ")): key
    for key, info in FOODS.items()
    for alias in [key, info["name"], *info["aliases"]]
}


def resolve_commodity(value: str) -> str:
    explicit_custom = value.casefold().startswith("custom:")
    name = value[len("custom:"):].strip() if explicit_custom else value.strip()
    normalized = normalize_food_name(name)
    if not normalized or any(ord(character) < 32 for character in name):
        raise ValueError("Please enter a valid food commodity name.")
    if not explicit_custom and normalized in FOOD_ALIASES:
        return FOOD_ALIASES[normalized]
    if normalized not in FOODON_NAMES:
        raise ValueError("Please enter a valid food commodity name.")
    # Keep a clear marker for a legitimate FoodOn term outside the prototype's
    # seven named training profiles. The classifier never receives this name.
    return f"custom:{name}"


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    commodity: str = Field(min_length=1, max_length=120)
    moisture: float = Field(ge=0, le=100, allow_inf_nan=False)
    fat: float = Field(ge=0, le=100, allow_inf_nan=False)
    ph: float = Field(ge=0, le=14, allow_inf_nan=False)
    respiration_rate: float = Field(ge=0, le=500, allow_inf_nan=False, description="mL CO2 per kg per hour; use a measured rate for respiring produce; zero means not used for this prototype food")
    shelf_life: int = Field(ge=1, le=730)
    temperature: float = Field(ge=-40, le=60, allow_inf_nan=False)
    humidity: float = Field(ge=0, le=100, allow_inf_nan=False)
    storage_condition: Literal["ambient", "chilled", "frozen"]
    transport_condition: Literal["local", "long", "rough", "cold"]

    @field_validator("commodity")
    @classmethod
    def normalize_supported_commodity(cls, value: str) -> str:
        return resolve_commodity(value)

    @model_validator(mode="after")
    def validate_composition_and_conditions(self):
        if self.moisture + self.fat > 100:
            raise ValueError("Moisture plus fat cannot exceed 100% of food mass.")
        if self.storage_condition == "frozen" and self.temperature > -12:
            raise ValueError("Frozen storage requires a temperature of −12 °C or below in this prototype.")
        if self.storage_condition == "chilled" and not -1 <= self.temperature <= 8:
            raise ValueError("Chilled storage must be between −1 and 8 °C in this prototype.")
        if self.storage_condition == "ambient" and self.temperature < 1:
            raise ValueError("Ambient storage must be at least 1 °C; use chilled or frozen storage.")
        if self.commodity == "pasteurized_milk" and self.storage_condition != "chilled":
            raise ValueError("Pasteurized milk is supported only with chilled storage in this prototype.")
        if self.commodity == "frozen_vegetables" and self.storage_condition != "frozen":
            raise ValueError("Frozen vegetables are supported only with frozen storage in this prototype.")
        if self.commodity == "tomatoes" and self.storage_condition == "frozen":
            raise ValueError("Frozen tomatoes are outside the supported tomato profile.")
        if self.commodity == "bananas" and self.temperature < 13:
            raise ValueError("Mature-green bananas are chilling-sensitive; the prototype storage/transport profile starts at 13 °C.")
        if self.commodity == "bananas" and self.storage_condition != "ambient":
            raise ValueError("The mature-green banana profile uses 13 °C or warmer storage/transport; select ambient storage in this prototype.")
        return self


def configured_origins():
    origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
    origins.extend(origin.strip() for origin in os.getenv("PACKWISE_ALLOWED_ORIGINS", "").split(",") if origin.strip())
    return list(dict.fromkeys(origins))


@asynccontextmanager
async def lifespan(_app):
    load_artifacts()
    yield


app = FastAPI(title="Packwise Recommendation API", version="2.0.0", description="Prototype food packaging classification with research-derived synthetic training data.", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_origin_regex=os.getenv("PACKWISE_ALLOWED_ORIGIN_REGEX") or None,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

_pipeline = None
_load_error: str | None = None
_metadata = None
_materials: dict | None = None
_sources: dict | None = None


def load_artifacts(force: bool = False):
    global _pipeline, _metadata, _materials, _sources, _load_error
    if _pipeline is not None and not force:
        return
    try:
        if not PIPELINE_PATH.is_file():
            raise FileNotFoundError(f"Trained model not found at {PIPELINE_PATH}")
        if not METADATA_PATH.is_file():
            raise FileNotFoundError(f"Model metadata not found at {METADATA_PATH}")
        if not DATABASE_PATH.is_file():
            raise FileNotFoundError(f"Packaging database not found at {DATABASE_PATH}")
        if not SOURCES_PATH.is_file():
            raise FileNotFoundError(f"Research source registry not found at {SOURCES_PATH}")
        if not FOOD_REFERENCE_PATH.is_file():
            raise FileNotFoundError(f"Food commodity reference not found at {FOOD_REFERENCE_PATH}")
        _pipeline = joblib.load(PIPELINE_PATH)
        _metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        if "commodity" in _metadata.get("input_features", []):
            raise ValueError("The saved model uses commodity names as features; retrain the property-only model before serving.")
        _materials = json.loads(DATABASE_PATH.read_text(encoding="utf-8"))
        _sources = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
        _load_error = None
    except Exception as exc:
        _pipeline = None
        _sources = None
        _load_error = f"Model or required data could not be loaded: {exc}"
        logger.exception("Packwise model artifact load failed")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content=jsonable_encoder({"error": "invalid_request", "detail": exc.errors()}))


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled Packwise API failure", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "server_error", "detail": "The recommendation service encountered an internal error."})


@app.get("/api/health")
def health():
    load_artifacts()
    if _pipeline is None:
        raise HTTPException(status_code=503, detail={"status": "unavailable", "model_loaded": False, "reason": _load_error})
    return {
        "status": "ok",
        "model_loaded": True,
        "model_name": _metadata.get("model_name"),
        "model_version": _metadata.get("model_version"),
        "training_data_type": "synthetic/curated research-derived prototype data",
        "training_rows": _metadata.get("dataset_rows"),
        "model_features": _metadata.get("input_features", []),
        "commodity_name_used_by_model": False,
        "food_reference_terms": FOODON_REFERENCE.get("term_count", len(FOODON_NAMES)),
    }


@app.get("/api/materials")
def materials_catalog():
    if _materials is None:
        load_artifacts()
    if _materials is None:
        raise HTTPException(status_code=503, detail="Packaging database is not available.")
    return {"evidence_policy": _materials["evidence_policy"], "materials": [with_references(item) for item in _materials["materials"]]}


@app.get("/api/model-card")
def model_card():
    load_artifacts()
    if _pipeline is None or _metadata is None:
        raise HTTPException(status_code=503, detail="Model report is not available.")
    return _metadata


def with_references(material: dict) -> dict:
    source_rows = (_sources or {}).get("sources", [])
    references = [
        {"id": source["id"], "name": source["name"], "url": source.get("url") or source.get("data_url", "")}
        for source in source_rows if source["id"] in material.get("source_ids", [])
    ]
    return {**material, "references": references}


def make_model_row(request: RecommendationRequest):
    values = request.model_dump()
    return {
        "commodity": values["commodity"],
        "moisture_content": values["moisture"],
        "fat_oil_content": values["fat"],
        "ph": values["ph"],
        "respiration_rate": values["respiration_rate"],
        "required_shelf_life": values["shelf_life"],
        "storage_temperature": values["temperature"],
        "storage_humidity": values["humidity"],
        "storage_condition": values["storage_condition"],
        "transport_condition": values["transport_condition"],
    }


def model_feature_explanations(row):
    importance = (_metadata or {}).get("feature_importance", {})
    feature_map = {
        "moisture_content": ("Moisture content", f"{row['moisture_content']:g}%"),
        "fat_oil_content": ("Fat / oil content", f"{row['fat_oil_content']:g}%"),
        "ph": ("pH", f"{row['ph']:g}"),
        "respiration_rate": ("Respiration rate", f"{row['respiration_rate']:g} mL CO2/kg·h"),
        "required_shelf_life": ("Shelf-life target", f"{row['required_shelf_life']} days"),
        "storage_temperature": ("Storage temperature", f"{row['storage_temperature']:g} °C"),
        "storage_humidity": ("Storage humidity", f"{row['storage_humidity']:g}% RH"),
        "storage_condition": ("Storage condition", row["storage_condition"]),
        "transport_condition": ("Transport condition", row["transport_condition"]),
    }
    order = sorted(importance, key=importance.get, reverse=True)[:5]
    return [
        {"feature": key, "label": feature_map[key][0], "value": feature_map[key][1], "global_importance": round(float(importance[key]), 4), "scope": "global model importance; not a causal or per-case attribution"}
        for key in order if key in feature_map
    ]


def domain_warnings(row):
    warnings = []
    is_unseen = row["commodity"].startswith("custom:")
    if is_unseen:
        warnings.append("This is a valid food commodity name with no named training profile. The commodity name is excluded from the classifier; the prediction uses the submitted measurable and storage features.")
    if row["commodity"] == "bananas":
        warnings.append("Banana evidence note: the cited UC Davis fact sheet lists 13–14 °C and 90–95% RH for storage/transport, with chilling-injury risk below 13 °C. This prototype label is a ventilated, PE-lined fiberboard carton candidate; confirm ventilation, cushioning, carton strength and liner construction for your banana maturity and route.")
        warnings.append("The banana training grid contains only this one curated target class. The model does not compare alternative banana package classes yet, so changing banana conditions may not change the material class.")
    model_ranges = (_metadata or {}).get("input_ranges_global", {})
    commodity_ranges = (_metadata or {}).get("input_ranges_by_commodity", {}).get(row["commodity"], {})
    for feature, value in row.items():
        bounds = commodity_ranges.get(feature) or model_ranges.get(feature)
        if bounds and (value < bounds[0] or value > bounds[1]):
            warnings.append(f"{feature}={value} is outside the {('commodity' if feature in commodity_ranges else 'global')} training-data span {bounds[0]}–{bounds[1]}; the model is extrapolating for this input.")
    return warnings


def predict_packaging(row: dict):
    """Run the saved fitted preprocessing-and-classification pipeline."""
    if _pipeline is None or _metadata is None:
        raise RuntimeError("The trained property-only model is not loaded.")
    model_features = _metadata.get("input_features", [])
    model_input = pd.DataFrame([{feature: row[feature] for feature in model_features}])
    return str(_pipeline.predict(model_input)[0]), model_input


@app.post("/api/recommend")
def recommend(request: RecommendationRequest):
    load_artifacts()
    if _pipeline is None:
        raise HTTPException(status_code=503, detail={"error": "model_unavailable", "reason": _load_error})
    if _materials is None:
        raise HTTPException(status_code=503, detail={"error": "database_unavailable"})
    row = make_model_row(request)
    try:
        prediction, model_input = predict_packaging(row)
        candidates = []
        is_custom_food = row["commodity"].startswith("custom:")
        if hasattr(_pipeline, "predict_proba"):
            classes = list(_pipeline.classes_)
            raw_probabilities = _pipeline.predict_proba(model_input)[0]
            for class_name, _probability in sorted(zip(classes, raw_probabilities), key=lambda pair: pair[1], reverse=True):
                profile = next((item for item in _materials["materials"] if item["id"] == str(class_name)), None)
                if not is_custom_food and profile and row["commodity"] in profile["typical_applications"] and profile["id"] != prediction:
                    candidates.append(with_references(profile))
                if len(candidates) == 2:
                    break
        material = next((item for item in _materials["materials"] if item["id"] == prediction), None)
        if material is None:
            raise RuntimeError(f"Predicted target {prediction!r} is not in the packaging database.")
        material = with_references(material)
        supported_application = not is_custom_food and row["commodity"] in material["typical_applications"]
        suitability = {
            "status": "preliminary_candidate" if supported_application else "review_required",
            "summary": "The model-selected class appears in this prototype's curated application list. This is a shortlist for expert review, not a validated packaging specification." if supported_application else "The food name is valid, but this commodity has no named training profile or curated application mapping. The property-only model generated a preliminary candidate; expert assessment and testing are required.",
            "basis": "Deterministic post-prediction application check against the packaging database; no commodity-specific application entry exists for this unseen food.",
        }
        important = model_feature_explanations(row)
        lead = ", ".join(f"{item['label']} ({item['global_importance']:.0%} global importance)" for item in important[:3]) or "no exposed feature-importance data"
        if is_custom_food:
            display_name = row["commodity"][len("custom:"):]
            explanation = (
                f"The trained {(_metadata or {}).get('model_name', 'classifier')} returned {material['name']} for the valid food name {display_name!r}. "
                "This name was not one of the named training profiles and was not sent to the property-only classifier; the prediction uses the submitted measurable and storage features. "
                f"Across supported training profiles, the highest global feature importances were {lead}. These are global associations, not causal evidence or a per-case explanation."
            )
        else:
            explanation = (
                f"The trained {(_metadata or {}).get('model_name', 'classifier')} model predicts {material['name']} for {FOODS[row['commodity']]['name']} from the submitted food and handling inputs. "
                f"Across the training grid, the highest global feature importances were {lead}. "
                "Those values describe overall model behavior, not causal evidence for this individual package. The class label comes from a research-derived synthetic/curated prototype dataset, not measured package trials."
            )
        warnings = domain_warnings(row)
        if row["commodity"] in ("tomatoes", "pasteurized_milk", "frozen_vegetables", "bananas"):
            warnings.append("Packaging does not establish food safety or a use-by date. Maintain the commodity's validated handling and temperature controls.")
        warnings.append("Thickness, OTR, WVTR, sealability and mechanical-strength values are omitted because this generic material class has no verified complete supplier/test specification in the database.")
        if not candidates:
            alternatives_note = "No second material in the current database has a curated application entry for this commodity."
        else:
            alternatives_note = "Alternatives are other model-ranked classes with a curated application entry for this commodity; no probability or confidence is shown."
        return {
            "recommended_material": material,
            "confidence": None,
            "confidence_note": "Not reported: the model is trained on synthetic/curated labels and has no experimental calibration data.",
            "suitability": suitability,
            "packaging_properties": material,
            "important_features": important,
            "explanation": explanation,
            "alternatives": candidates,
            "alternatives_note": alternatives_note,
            "warnings": warnings,
            "input_echo": request.model_dump(),
            "prediction_source": "trained supervised classifier; target labels are synthetic/curated research-derived rules",
            "prediction_scope": "valid_unseen_commodity" if is_custom_food else "supported_prototype_commodity",
            "model": {"name": (_metadata or {}).get("model_name"), "version": (_metadata or {}).get("model_version")},
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Packwise recommendation failed")
        raise HTTPException(status_code=500, detail="The model could not complete this recommendation.") from exc
