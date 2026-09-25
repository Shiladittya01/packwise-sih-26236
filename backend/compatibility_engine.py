"""Property-based packaging compatibility estimates for the Packwise prototype.

Material capability bands summarize qualitative catalog descriptions. They are
ordinal design inputs, not converted supplier specifications or test results.
"""
from __future__ import annotations

from typing import Any


LEVEL = {"very_low": 0.1, "low": 0.25, "limited": 0.25, "moderate": 0.5, "high": 0.75, "very_high": 0.9}
SUSTAINABILITY_BAND = {"constrained": "low", "mixed_or_context_dependent": "moderate", "favorable_if_collected": "high"}


def _food_name(commodity: str) -> str:
    return commodity.removeprefix("custom:").replace("_", " ").casefold()


def infer_food_category(commodity: str, row: dict[str, Any]) -> str:
    """Infer a broad packaging archetype from recognizable name cues and inputs."""
    name = _food_name(commodity)
    tokens = set(name.split())
    if row.get("storage_condition") == "frozen" or "frozen" in tokens:
        return "frozen_food"
    if tokens.intersection({"pickle", "pickles", "pickled", "preserve", "preserved", "fermented", "jam", "chutney"}):
        return "acidic_preserve"
    if tokens.intersection({"milk", "dairy", "juice", "beverage", "drink", "liquid", "yogurt", "yoghurt", "sauce"}):
        return "chilled_liquid" if row.get("storage_condition") == "chilled" else "liquid_food"
    if tokens.intersection({"biscuit", "biscuits", "cookie", "cookies", "chip", "chips", "crisp", "crisps", "cracker", "crackers", "snack", "bar", "cereal"}):
        return "dry_snack"
    if tokens.intersection({"fruit", "fruits", "vegetable", "vegetables", "produce", "tomato", "tomatoes", "banana", "bananas", "apple", "apples", "grape", "grapes", "mango", "mangoes", "potato", "potatoes", "onion", "onions"}):
        return "fresh_produce"
    if tokens.intersection({"rice", "grain", "grains", "lentil", "lentils", "pulse", "pulses", "bean", "beans", "legume", "legumes", "flour", "dal"}):
        return "dry_commodity"
    moisture = row.get("moisture_content")
    if moisture is not None and moisture <= 15:
        return "dry_food"
    if row.get("respiration_rate") is not None and row["respiration_rate"] > 0 and (moisture is None or moisture >= 50):
        return "fresh_produce"
    return "general_food"


def _requirement(key: str, category: str, row: dict[str, Any]) -> tuple[str, float]:
    """Return required ordinal band and input-evidence quality (0..1)."""
    moisture = row.get("moisture_content")
    fat = row.get("fat_oil_content")
    shelf_life = row.get("required_shelf_life")
    ph = row.get("ph")
    if key == "water_vapor_barrier":
        humidity = row.get("storage_humidity")
        if moisture is not None:
            level = "high" if moisture <= 15 or moisture >= 75 or (humidity is not None and humidity >= 80) else "moderate"
            return level, 1.0 if humidity is not None else 0.88
        if humidity is not None:
            return ("high" if humidity >= 80 else "moderate"), 0.55
        return ("high" if category in {"fresh_produce", "chilled_liquid", "liquid_food", "dry_food", "dry_commodity", "dry_snack", "acidic_preserve"} else "moderate"), 0.0
    if key == "oxygen_barrier":
        if fat is not None or shelf_life is not None:
            high = (fat is not None and fat >= 10) or (shelf_life is not None and shelf_life >= 90)
            moderate = (fat is not None and fat >= 3) or (shelf_life is not None and shelf_life >= 30) or category in {"dry_snack", "dry_commodity"}
            return ("high" if high else "moderate" if moderate else "low"), 1.0
        return ("moderate" if category in {"dry_snack", "dry_commodity"} else "low"), 0.0
    if key == "gas_exchange":
        respiration = row.get("respiration_rate")
        if respiration is not None:
            if category == "fresh_produce":
                return ("high" if respiration >= 20 else "moderate"), 1.0
            return ("high" if respiration >= 20 else "moderate" if respiration >= 5 else "low"), 1.0
        return "moderate", 0.0
    if key == "sealability":
        if ph is not None:
            return ("high" if ph <= 4.6 or category == "acidic_preserve" else "moderate"), 1.0
        return ("high" if category == "acidic_preserve" else "moderate"), 0.45
    if key == "fat_resistance":
        return ("high" if fat >= 10 else "moderate"), 1.0
    if key == "acid_compatibility":
        return "high", 1.0 if ph is not None else 0.45
    if key == "mechanical_protection":
        transport = row.get("transport_condition")
        return ("high" if transport == "rough" else "moderate"), 1.0 if transport is not None else 0.0
    if key == "light_barrier":
        return "high", 1.0
    if key == "temperature_tolerance":
        temperature = row.get("storage_temperature")
        if temperature is not None or row.get("storage_condition") is not None:
            return ("high" if row.get("storage_condition") == "frozen" or (temperature is not None and temperature <= -12) else "moderate"), 1.0
        return "moderate", 0.0
    if key == "shelf_life_barrier":
        if shelf_life is None:
            return "moderate", 0.0
        return ("high" if shelf_life >= 90 else "moderate" if shelf_life >= 30 else "low"), 1.0
    return "moderate", 0.5


def build_food_requirements(commodity: str, row: dict[str, Any], model_available: bool = True) -> dict[str, Any]:
    """Build a relevant, weighted factor list for the food and available inputs."""
    category = infer_food_category(commodity, row)
    specs: list[dict[str, Any]] = [
        {"key": "water_vapor_barrier", "label": "Moisture protection", "weight": 0.18},
        {"key": "oxygen_barrier", "label": "Oxygen barrier", "weight": 0.16},
        {"key": "sealability", "label": "Sealability", "weight": 0.10},
        {"key": "shelf_life_barrier", "label": "Target duration support", "weight": 0.10},
    ]
    fat, ph = row.get("fat_oil_content"), row.get("ph")
    respiration, transport = row.get("respiration_rate"), row.get("transport_condition")
    temperature = row.get("storage_temperature")
    storage = row.get("storage_condition")
    if fat is not None and fat >= 2:
        specs.append({"key": "fat_resistance", "label": "Fat / oil compatibility", "weight": 0.10})
    if (ph is not None and ph <= 5.0) or category == "acidic_preserve":
        specs.append({"key": "acid_compatibility", "label": "Acid contact compatibility", "weight": 0.10})
    if category == "fresh_produce" or (respiration is not None and respiration > 0):
        specs.append({"key": "gas_exchange", "label": "Produce gas exchange", "weight": 0.18})
    if storage is not None or temperature is not None:
        specs.append({"key": "temperature_tolerance", "label": "Temperature use", "weight": 0.08})
    specs.append({"key": "mechanical_protection", "label": "Transport protection", "weight": 0.08})
    if fat is not None and fat >= 10:
        specs.append({"key": "light_barrier", "label": "Light protection", "weight": 0.06})
    if category != "general_food":
        specs.append({"key": "food_group_fit", "label": "Food type fit", "weight": 0.32})
    if not commodity.startswith("custom:"):
        specs.append({"key": "application_match", "label": "Recorded food application", "weight": 0.10})
    if model_available:
        specs.append({"key": "model_alignment", "label": "Model class support", "weight": 0.06})
    if storage:
        specs.append({"key": "storage_compatibility", "label": "Storage compatibility", "weight": 0.10})
    for spec in specs:
        if spec["key"] == "storage_compatibility":
            spec["requirement"] = storage
            spec["input_quality"] = 1.0
        elif spec["key"] == "food_group_fit":
            spec["requirement"] = category
            spec["input_quality"] = 0.55
        else:
            level, quality = _requirement(spec["key"], category, row)
            spec["requirement"] = level
            spec["input_quality"] = quality
    return {"category": category, "requirements": specs}


def _compatibility(requirement: str, capability: str) -> float | None:
    needed, offered = LEVEL.get(requirement), LEVEL.get(capability)
    if needed is None or offered is None:
        return None
    # Give full credit to a close match, a gentle over-specification penalty,
    # and a larger penalty when capability falls short of the requirement.
    difference = offered - needed
    score = 100.0 - max(0.0, difference) * 35.0 - max(0.0, -difference) * 140.0
    return max(0.0, min(100.0, score))


def _score_factor(spec: dict[str, Any], material: dict[str, Any], commodity: str,
                  category: str, model_probabilities: dict[str, float]) -> tuple[float | None, str, str, float]:
    profile = material.get("compatibility_profile", {})
    ratings = profile.get("ratings", {})
    key = spec["key"]
    if spec.get("input_quality", 0.0) <= 0 and key not in {"food_group_fit", "application_match", "model_alignment"}:
        return None, "", "", 0.0
    if key == "model_alignment":
        probability = model_probabilities.get(material["id"])
        if probability is not None:
            return max(0.0, min(100.0, probability * 100)), "raw class probability from the trained prototype model", "model_output", 0.45
        return None, "", "", 0.0
    if key == "application_match":
        if commodity in material.get("typical_applications", []):
            return _compatibility("high", "high"), "catalog application mapping", "catalog_mapping", 0.8
        return None, "", "", 0.0
    if key == "food_group_fit":
        groups = profile.get("food_groups", [])
        if not groups:
            return None, "", "", 0.0
        band = "high" if category in groups else "low"
        return _compatibility("high", band), "qualitative material-format group", "qualitative_group", 0.55
    if key == "storage_compatibility":
        rating = profile.get("storage_support", {}).get(spec["requirement"])
        if rating is None:
            return None, "", "", 0.0
        if isinstance(rating, str):
            score = _compatibility("high", rating)
        else:
            score = float(rating)
        return score, "explicit catalog storage-use note", "qualitative_source", 0.75
    capability = ratings.get(key)
    if capability in (None, "unknown"):
        return None, "", "", 0.0
    score = _compatibility(spec["requirement"], capability)
    if score is None:
        return None, "", "", 0.0
    basis = profile.get("rating_basis", {}).get(key, "qualitative packaging profile").strip()
    return score, basis, "qualitative_source", 0.65


def _level(score: float) -> str:
    if score >= 80:
        return "Highly Suitable"
    if score >= 65:
        return "Suitable"
    if score >= 45:
        return "Moderate Fit"
    return "Limited Fit"


def _factor_reason(factor: dict[str, Any]) -> str:
    score, label, requirement = factor["score"], factor["label"], factor["requirement"].replace("_", " ")
    if factor["key"] == "food_group_fit":
        if score >= 75:
            return f"The material format aligns with the {requirement} food group."
        return f"The material profile does not directly cover the {requirement} food group."
    if factor["key"] == "model_alignment":
        return f"The trained classifier assigns this material a {score:.1f}% class probability."
    if factor["key"] == "application_match":
        return "This food appears in the material's recorded typical applications."
    if factor["key"] == "storage_compatibility":
        return f"The catalog lists this package format for {requirement} storage."
    if score >= 80:
        return f"{label} is a strong match for the {requirement} need in this profile."
    if score >= 60:
        return f"{label} is a partial match for the {requirement} need in this profile."
    return f"{label} may not meet the {requirement} need in this profile."


def calculate_suitability(material: dict[str, Any], commodity: str, row: dict[str, Any],
                           model_probabilities: dict[str, float]) -> dict[str, Any]:
    requirements = build_food_requirements(commodity, row, model_available=bool(model_probabilities))["requirements"]
    scored: list[dict[str, Any]] = []
    for spec in requirements:
        value, basis, evidence, profile_quality = _score_factor(spec, material, commodity,
                                                                  infer_food_category(commodity, row), model_probabilities)
        if value is None:
            continue
        scored.append({
            "key": spec["key"], "label": spec["label"], "score": round(value, 1),
            "weight": spec["weight"], "requirement": spec["requirement"], "basis": basis,
            "evidence": evidence, "input_quality": round(spec["input_quality"], 2),
        })
    if not scored:
        # Catalog capability profiles are required to include at least moisture,
        # oxygen and sealability bands, so a valid food always has scored factors.
        raise ValueError(f"Material {material.get('id')!r} has no usable compatibility profile.")
    total_weight = sum(item["weight"] for item in scored)
    estimate = sum(item["score"] * item["weight"] for item in scored) / total_weight
    relevant_weight = sum(spec["weight"] for spec in requirements)
    evidenced_weight = sum(item["weight"] * item["input_quality"] * (0.65 if item["evidence"] == "qualitative_source" else 1.0 if item["evidence"] == "catalog_mapping" else 0.45 if item["evidence"] == "model_output" else 0.75) for item in scored)
    coverage = round(100 * evidenced_weight / max(relevant_weight, 0.01))
    reasons = [_factor_reason(item) for item in sorted(scored, key=lambda item: (item["weight"], item["score"]), reverse=True)[:5]]
    category = infer_food_category(commodity, row)
    return {
        "score": round(max(0.0, min(100.0, estimate))),
        "level": _level(estimate),
        "assessment_type": "estimated",
        "summary": f"Estimated for a {category.replace('_', ' ')} profile from submitted properties and qualitative packaging capability bands.",
        "data_coverage_percent": max(0, min(100, coverage)),
        "coverage": {"available_factors": len(scored), "relevant_factors": len(requirements)},
        "calculation": {
            "score": "Weighted mean of scored compatibility factors; missing factors are excluded from the score denominator.",
            "factor_fit": "Ordinal band values are 0.10, 0.25, 0.50, 0.75 and 0.90. Fit is clamp(100 - 140 × band shortfall - 35 × excess band, 0, 100).",
            "special_factors": "Model support uses its raw class probability × 100; catalog application and food-group matches use the same ordinal band-fit rule.",
            "data_coverage": "Evidence quality and input support across all relevant factors, including factors excluded from the score.",
        },
        "food_category": category,
        "factors": scored,
        "key_factors": reasons,
        "limitations": ["Capability bands summarize qualitative catalog evidence; they are not measured package performance."],
    }


def calculate_sustainability(material: dict[str, Any], suitability: dict[str, Any]) -> dict[str, Any]:
    """Estimate a limited material-design index from known structure evidence."""
    profile = material.get("compatibility_profile", {})
    factors: list[dict[str, Any]] = []
    component_groups = profile.get("component_groups")
    if component_groups:
        count = len(set(component_groups))
        unspecified = profile.get("additional_components_unspecified")
        band = "high" if count == 1 and not unspecified else "moderate" if count == 1 or (count == 2 and not unspecified) else "low"
        score = LEVEL[band] * 100
        factors.append({"key": "material_simplicity", "label": "Material simplicity proxy", "score": score, "weight": 0.25, "basis": f"{count} known material group(s); ordinal band {band}"})
    recycling_status = profile.get("recycling_status")
    if recycling_status in SUSTAINABILITY_BAND:
        band = SUSTAINABILITY_BAND[recycling_status]
        factors.append({"key": "recycling_pathway", "label": "Recycling pathway note", "score": LEVEL[band] * 100, "weight": 0.25, "basis": f"Ordinal band {band}: {profile.get('recycling_basis', 'catalog note')}"})
    score_value = suitability.get("score")
    if isinstance(score_value, (int, float)):
        factors.append({"key": "protection_fit", "label": "Estimated compatibility proxy", "score": float(score_value), "weight": 0.20, "basis": "Compatibility estimate only; no measured shelf-life extension or food-loss reduction"})
    total_weight = sum(item["weight"] for item in factors)
    if total_weight <= 0:
        raise ValueError(f"Material {material.get('id')!r} has no sustainability evidence.")
    score = sum(item["score"] * item["weight"] for item in factors) / total_weight
    max_evidence_weight = 0.25 + 0.25 + 0.20 + 0.15 + 0.15
    return {
        "score": round(max(0.0, min(100.0, score))),
        "assessment_type": "estimated_index",
        "label": "Estimated Sustainability",
        "data_coverage_percent": round(100 * total_weight / max_evidence_weight),
        "coverage": {"available_factors": len(factors), "relevant_factors": 5},
        "calculation": "Weighted mean of the ordinal material-simplicity band, documented recycling note and suitability compatibility score. Missing factors are excluded; the normalized index is not a verified environmental percentage.",
        "factors": factors,
        "summary": "A limited design proxy from known material-group count, documented recycling notes and compatibility fit; this is not a life-cycle assessment.",
        "missing_factors": ["package mass and thickness", "regional collection, recycling or composting outcome", "reuse route", "measured food-loss reduction"],
    }


def rank_materials(materials: list[dict[str, Any]], commodity: str, row: dict[str, Any],
                   model_probabilities: dict[str, float]) -> list[dict[str, Any]]:
    ranked = []
    for material in materials:
        assessment = calculate_suitability(material, commodity, row, model_probabilities)
        ranked.append({"material": material, "suitability": assessment})
    ranked.sort(key=lambda item: (
        item["suitability"]["score"],
        item["suitability"]["data_coverage_percent"],
        model_probabilities.get(item["material"]["id"], 0.0),
    ), reverse=True)
    return ranked
