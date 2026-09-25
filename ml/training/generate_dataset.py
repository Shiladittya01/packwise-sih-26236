"""Generate Packwise's deterministic research-derived prototype dataset.

Every row is a declared condition-grid combination. There is no random sampling.
The target is a curated design label from the versioned rules below, not an
experimentally observed or commercially validated packaging decision.
"""
from __future__ import annotations

from itertools import product
from pathlib import Path
import json

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "datasets" / "processed" / "packwise_research_curated_v1.csv"
FEATURES = [
    "commodity", "moisture_content", "fat_oil_content", "ph", "respiration_rate",
    "required_shelf_life", "storage_temperature", "storage_humidity",
    "storage_condition", "transport_condition",
]
TARGET = "recommended_packaging_material"

# Nutrient centers from the five USDA FoodData Central records listed in
# docs/research_sources.json. The biscuit and frozen-vegetable values, and all
# pH centers, are retained as editable UI teaching values and are NOT claimed
# as measurements from those USDA records. pH does not assign labels.
PROFILES = {
    "tomatoes": {"moisture_content": 94.5, "fat_oil_content": 0.2, "ph": 4.3},
    "potato_chips": {"moisture_content": 1.86, "fat_oil_content": 34.0, "ph": 6.2},
    "biscuits": {"moisture_content": 4.0, "fat_oil_content": 12.0, "ph": 6.5},
    "pasteurized_milk": {"moisture_content": 88.1, "fat_oil_content": 3.2, "ph": 6.7},
    "frozen_vegetables": {"moisture_content": 80.0, "fat_oil_content": 1.0, "ph": 6.0},
    "lentils": {"moisture_content": 8.26, "fat_oil_content": 1.06, "ph": 6.4},
    "bananas": {"moisture_content": 74.91, "fat_oil_content": 0.33, "ph": 6.0},
}

# Input level grids are explicit and deterministic. Tomato respiration values
# are midpoints of the UC Davis green-ripening ranges at 10 C and 15 C.
GRID = {
    "tomatoes": {"resp_temp": [(7.5, 10.0), (13.5, 15.0)], "humidity": [90, 95], "shelf": [7, 14], "transport": ["local", "long"]},
    "potato_chips": {"temperature": [20, 25], "humidity": [40, 60, 80], "shelf": [30, 90, 180, 270], "transport": ["local", "long", "rough"]},
    "biscuits": {"temperature": [20, 25], "humidity": [40, 60, 80], "shelf": [30, 90, 180], "transport": ["local", "long", "rough"]},
    "pasteurized_milk": {"temperature": [2, 4, 8], "humidity": [60, 75], "shelf": [5, 7, 10], "transport": ["cold", "local"]},
    "frozen_vegetables": {"temperature": [-18, -12], "humidity": [60, 75, 90], "shelf": [90, 180, 365], "transport": ["cold", "rough"]},
    "lentils": {"temperature": [20, 25, 30], "humidity": [40, 60, 80], "shelf": [90, 180, 365], "transport": ["local", "long", "rough"]},
    "bananas": {"resp_temp": [(20, 13.0), (26, 15.0)], "humidity": [90, 95], "shelf": [14, 21, 28], "transport": ["local", "long", "rough"]},
}

LABEL_RULES = {
    "rule_set_version": "research-curation-1.1",
    "tomatoes": "UC Davis respiration ranges and MAP reviews establish respiration/permeability matching. Prototype curation uses breathable_pe_film for the lower listed respiration band with a 7-day target; higher respiration or a 14-day target maps to microperforated_polyolefin for a candidate requiring measured package-gas validation. The numeric boundary is a prototype rule, not a literature-validated threshold.",
    "potato_chips": "The cereal/confectionery review describes oxygen and water-vapor protection for oil-rich fried snacks. Prototype curation maps the ordinary grid to metallized_laminate and elevates long (>=180-day) targets or rough handling to foil_laminate. These choices and the 180-day boundary are curated candidates, not experimentally observed optima.",
    "biscuits": "The cereal/confectionery review documents moisture/oxygen protection needs. Prototype curation maps short/local cases to bopp_cpp_pouch and higher fat plus a >=90-day target or non-local handling to metallized_laminate. The threshold is a prototype decision rule, not a measured threshold.",
    "pasteurized_milk": "The selected demo format is an HDPE bottle candidate for pasteurized milk. The prototype does not infer food-contact compliance, barrier performance or cold-chain adequacy from that class label.",
    "frozen_vegetables": "The selected demo format is a polyethylene freezer bag candidate for frozen vegetables. No numeric cold-service or barrier performance is claimed; supplier and filled-pack verification remain necessary.",
    "lentils": "For dry bulk handling, the prototype maps higher humidity, rough handling or >=180-day targets to woven_pp_pe_liner_sack; other grid cells map to bopp_cpp_pouch. This is a curated format tradeoff, not a validated moisture/shelf-life boundary.",
    "bananas": "UC Davis reports mature-green Cavendish respiration ranges of 10–30 mL CO2/kg·h at 13 °C and 12–40 at 15 °C, 90–95% RH, and chilling injury risk below 13 °C. FAO describes hands of bananas packed in cardboard containers lined with polyethylene to reduce transport damage, and its produce-carton guidance calls for adequate vents. Each banana grid row is labeled ventilated_fiberboard_carton_with_pe_liner as one sourced composite shipping format. This is a single curated candidate class for a simplified form-factor prototype, not an experimentally compared optimum; carton grade, liner perforation, fruit maturity, box geometry and supplier performance are not inferred.",
    "pH": "pH is included as an input for future research and validation context, but is deliberately not used by these packaging-class label rules because no reviewed source supplied a defensible pH-to-class threshold for these material classes.",
    "limitations": "Synthetic, deterministic, rule-labelled design grid. A row is one constructed scenario, not an independent laboratory observation. It cannot establish accuracy on real foods or supplier packaging."
}


def assign_label(row: dict) -> str:
    food = row["commodity"]
    if food == "tomatoes":
        return "microperforated_polyolefin" if row["respiration_rate"] >= 10 or row["required_shelf_life"] > 7 else "breathable_pe_film"
    if food == "potato_chips":
        return "foil_laminate" if row["required_shelf_life"] >= 180 or row["transport_condition"] == "rough" else "metallized_laminate"
    if food == "biscuits":
        barrier_need = row["fat_oil_content"] >= 10 and (row["required_shelf_life"] >= 90 or row["transport_condition"] != "local")
        return "metallized_laminate" if barrier_need else "bopp_cpp_pouch"
    if food == "pasteurized_milk":
        return "hdpe_bottle"
    if food == "frozen_vegetables":
        return "freezer_pe_bag"
    if food == "lentils":
        bulk_need = row["required_shelf_life"] >= 180 or row["storage_humidity"] >= 80 or row["transport_condition"] == "rough"
        return "woven_pp_pe_liner_sack" if bulk_need else "bopp_cpp_pouch"
    if food == "bananas":
        return "ventilated_banana_carton"
    raise ValueError(f"No documented label policy for {food!r}")


def iter_rows():
    for food, grid in GRID.items():
        profile = PROFILES[food]
        cases = []
        if food in ("tomatoes", "bananas"):
            cases = [(rr, temp, rh, life, trip) for (rr, temp), rh, life, trip in product(grid["resp_temp"], grid["humidity"], grid["shelf"], grid["transport"])]
        else:
            cases = [(0.0, temp, rh, life, trip) for temp, rh, life, trip in product(grid["temperature"], grid["humidity"], grid["shelf"], grid["transport"])]
        for case_index, (resp, temp, rh, life, trip) in enumerate(cases):
            storage = "chilled" if food == "pasteurized_milk" else "frozen" if food == "frozen_vegetables" else "ambient"
            row = {
                "commodity": food,
                **profile,
                "respiration_rate": float(resp),
                "required_shelf_life": int(life),
                "storage_temperature": float(temp),
                "storage_humidity": float(rh),
                "storage_condition": storage,
                "transport_condition": trip,
            }
            row[TARGET] = assign_label(row)
            # Stable row provenance for audit/debug only. Current evaluation
            # is stratified by row; nearby grid cases may cross folds and this
            # does not simulate independent experimental validation.
            row["_split_group"] = f"{food}:{case_index}"
            yield row


def main():
    rows = list(iter_rows())
    frame = pd.DataFrame(rows)
    frame = frame[FEATURES + [TARGET, "_split_group"]]
    if frame.duplicated(FEATURES + [TARGET]).any():
        raise ValueError("Generated duplicate feature/target rows; revise the condition grid.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False)
    meta = {
        "dataset": OUTPUT.relative_to(ROOT).as_posix(),
        "rows": len(frame),
        "features": FEATURES,
        "target": TARGET,
        "rule_set_version": LABEL_RULES["rule_set_version"],
        "label_counts": frame[TARGET].value_counts().sort_index().to_dict(),
        "note": "Deterministic research-derived synthetic/curated data; never experimental ground truth.",
    }
    (ROOT / "datasets" / "processed" / "dataset_metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
