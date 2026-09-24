# Prototype ML model report

Generated: 2026-09-24T15:32:16.906974+00:00

## Dataset and target

- Dataset: `datasets/processed/packwise_research_curated_v1.csv` (295 deterministic synthetic/curated rows).
- Inputs: `commodity`, `moisture_content`, `fat_oil_content`, `respiration_rate`, `required_shelf_life`, `storage_temperature`, `storage_humidity`, `storage_condition`, `transport_condition`.
- Target: `recommended_packaging_material`.
- Label source: documented curation rules in `ml/training/generate_dataset.py`; no target is an experimental observation.
- Class imbalance: majority class share 0.244; macro metrics are used alongside accuracy.

| Curated target class | Rows |
|---|---:|
| `bopp_cpp_pouch` | 18 |
| `breathable_pe_film` | 4 |
| `foil_laminate` | 48 |
| `freezer_pe_bag` | 36 |
| `hdpe_bottle` | 36 |
| `metallized_laminate` | 72 |
| `microperforated_polyolefin` | 12 |
| `woven_pp_pe_liner_sack` | 69 |

## Preprocessing and leakage checks

Categorical inputs use most-frequent imputation and one-hot encoding. Numeric inputs use median imputation and standard scaling. Both are inside a scikit-learn `Pipeline`, so each cross-validation fold fits preprocessing only on its training partition. The dataset contains pH and the API validates and echoes it, but pH is excluded from the classifier: the label rules have no defensible pH-to-material threshold, and fixed pH centers could leak commodity identity. Generated data was checked for missing values, exact duplicate request/target records, impossible composition sums, pH/RH bounds, and train/test index overlap. The split/helper column is not a model input.

The rows are a structured scenario grid derived from a fixed label policy. The evaluation therefore measures rule-grid reproduction, not generalization to independent experiments. Neighboring grid points can be correlated; high scores must not be presented as real-world packaging accuracy.

## Candidate model comparison

Stratified 4-fold cross-validation; mean ± standard deviation. Selection uses mean macro-F1, with CV accuracy as a tie-breaker. No model was chosen from the holdout score.

| Model | Accuracy | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|
| logistic_regression | 0.942 ± 0.034 | 0.901 ± 0.058 | 0.929 ± 0.051 | 0.894 ± 0.070 |
| random_forest | 0.993 ± 0.012 | 0.991 ± 0.016 | 0.990 ± 0.017 | 0.990 ± 0.017 |
| gradient_boosting | 0.993 ± 0.012 | 0.979 ± 0.036 | 0.979 ± 0.036 | 0.969 ± 0.054 |

Selected model: **random_forest** (`RandomForestClassifier`).

## Held-out synthetic-grid metrics

- Train rows: 230; held-out rows: 65.
- Accuracy: 0.985
- Macro precision: 0.938
- Macro recall: 0.958
- Macro F1: 0.933

Confusion matrix uses this class order: `bopp_cpp_pouch`, `breathable_pe_film`, `foil_laminate`, `freezer_pe_bag`, `hdpe_bottle`, `metallized_laminate`, `microperforated_polyolefin`, `woven_pp_pe_liner_sack`.

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
    0
  ],
  [
    0,
    1,
    0,
    0,
    0,
    0,
    2,
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
    15
  ]
]
```

These figures are **not estimates of real-world predictive performance**. They quantify how well a conventional model recovers curated labels from their own generated design grid.

## Explainability and confidence

Feature importance method: tree impurity importance aggregated by source feature. The API labels these as global model importance, not causal effects for a specific food. SHAP was not needed for this small, rule-labelled prototype. Probabilities are intentionally not shown as user confidence because the class labels are synthetic and no experimental calibration set exists.

## Limitations

- All target labels are deterministic research-derived curation rules, not experimentally observed packaging decisions.
- Metrics quantify how well candidate estimators reproduce this synthetic rule grid; they are not real-food accuracy or scientific validation.
- The structured grid contains one demonstration nutrient/pH center for several commodities; changed real measurements may be outside the training distribution.
- No confidence percentage is displayed because class probabilities are not calibrated against experimental outcomes.
