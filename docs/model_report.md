# Prototype ML model report

Generated: 2026-09-25T01:35:54.888593+00:00

## Dataset and target

- Dataset: `datasets/processed/packwise_research_curated_v1.csv` (331 deterministic synthetic/curated rows).
- Inputs: `moisture_content`, `fat_oil_content`, `respiration_rate`, `required_shelf_life`, `storage_temperature`, `storage_humidity`, `storage_condition`, `transport_condition`.
- Target: `recommended_packaging_material`.
- Label source: documented curation rules in `ml/training/generate_dataset.py`; no target is an experimental observation.
- Class imbalance: majority class share 0.218; macro metrics are used alongside accuracy.

| Curated target class | Rows |
|---|---:|
| `bopp_cpp_pouch` | 18 |
| `breathable_pe_film` | 4 |
| `foil_laminate` | 48 |
| `freezer_pe_bag` | 36 |
| `hdpe_bottle` | 36 |
| `metallized_laminate` | 72 |
| `microperforated_polyolefin` | 12 |
| `ventilated_banana_carton` | 36 |
| `woven_pp_pe_liner_sack` | 69 |

## Preprocessing and leakage checks

The classifier uses six measured numeric inputs plus storage and transport conditions. It does not receive the commodity name or pH. Numeric inputs use median imputation and standard scaling; categorical conditions use most-frequent imputation and one-hot encoding. These are inside a scikit-learn `Pipeline`, so each cross-validation fold fits preprocessing only on its training partition. The dataset retains the commodity and pH for provenance and API validation, but neither reaches the classifier. Generated data was checked for missing values, exact duplicate request/target records, impossible composition sums, pH/RH bounds, and train/test index overlap. The split/helper column is not a model input.

The rows are a structured scenario grid derived from a fixed label policy. The evaluation therefore measures rule-grid reproduction, not generalization to independent experiments. Neighboring grid points can be correlated; high scores must not be presented as real-world packaging accuracy.

## Candidate model comparison

Stratified 4-fold cross-validation; mean ± standard deviation. Selection uses mean macro-F1, with CV accuracy as a tie-breaker. No model was chosen from the holdout score.

| Model | Accuracy | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|
| logistic_regression | 0.936 ± 0.043 | 0.881 ± 0.070 | 0.905 ± 0.070 | 0.876 ± 0.078 |
| random_forest | 0.994 ± 0.011 | 0.985 ± 0.027 | 0.984 ± 0.028 | 0.980 ± 0.034 |
| gradient_boosting | 0.991 ± 0.010 | 0.996 ± 0.005 | 0.981 ± 0.023 | 0.985 ± 0.018 |

Selected model: **gradient_boosting** (`GradientBoostingClassifier`).

## Held-out synthetic-grid metrics

- Train rows: 258; held-out rows: 73.
- Accuracy: 1.000
- Macro precision: 1.000
- Macro recall: 1.000
- Macro F1: 1.000

Confusion matrix uses this class order: `bopp_cpp_pouch`, `breathable_pe_film`, `foil_laminate`, `freezer_pe_bag`, `hdpe_bottle`, `metallized_laminate`, `microperforated_polyolefin`, `ventilated_banana_carton`, `woven_pp_pe_liner_sack`.

```json
[
  [
    4,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0
  ],
  [
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0
  ],
  [
    0,
    0,
    10,
    0,
    0,
    0,
    0,
    0,
    0
  ],
  [
    0,
    0,
    0,
    8,
    0,
    0,
    0,
    0,
    0
  ],
  [
    0,
    0,
    0,
    0,
    8,
    0,
    0,
    0,
    0
  ],
  [
    0,
    0,
    0,
    0,
    0,
    16,
    0,
    0,
    0
  ],
  [
    0,
    0,
    0,
    0,
    0,
    0,
    3,
    0,
    0
  ],
  [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    8,
    0
  ],
  [
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    15
  ]
]
```

These figures are **not estimates of real-world predictive performance**. They quantify how well a conventional model recovers curated labels from their own generated design grid.

## Unseen commodity and support handling

The commodity name is not a model feature. The API validates it against the bundled FoodOn vocabulary, then sends the same eight measured/storage features to the fitted pipeline for a known or valid unseen name. Invalid names are rejected before inference. This demonstrates inference for an unseen name in the model's feature space; it does not establish real-world food or packaging generalization because the labels are synthetic/curated and there is no independent commodity trial set. The API warns when a numeric model input falls outside its global training-data min/max range. That simple per-feature check does not detect every unsupported combination within those bounds.

## Explainability and confidence

Feature importance method: tree impurity importance aggregated by source feature. The API labels these as global model importance, not causal effects for a specific food. SHAP was not needed for this small, rule-labelled prototype. The result shows the estimator's raw predicted-class probability separately from suitability; that probability is not calibrated against experimental package outcomes and is not a scientific certainty.

## Limitations

- All target labels are deterministic research-derived curation rules, not experimentally observed packaging decisions.
- Metrics quantify how well candidate estimators reproduce this synthetic rule grid; they are not real-food accuracy or scientific validation.
- The structured grid contains one demonstration nutrient/pH center for several commodities; changed real measurements may be outside the training distribution.
- Mature-green bananas have one curated target class in the current grid, so the model does not compare competing banana package classes or learn banana-specific material tradeoffs.
- The API displays the estimator's raw predicted-class probability when available; it is not calibrated against experimental package outcomes.
