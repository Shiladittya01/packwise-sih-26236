"""Train, compare and report prototype material-class classifiers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import warnings

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "datasets" / "processed" / "packwise_research_curated_v1.csv"
MODEL_DIR = ROOT / "ml" / "models"
TARGET = "recommended_packaging_material"
FEATURES = [
    "moisture_content", "fat_oil_content", "respiration_rate",
    "required_shelf_life", "storage_temperature", "storage_humidity",
    "storage_condition", "transport_condition",
]
DATASET_INPUTS = [
    "commodity", "moisture_content", "fat_oil_content", "ph", "respiration_rate",
    "required_shelf_life", "storage_temperature", "storage_humidity",
    "storage_condition", "transport_condition",
]
NUMERIC = [
    "moisture_content", "fat_oil_content", "respiration_rate",
    "required_shelf_life", "storage_temperature", "storage_humidity",
]
CATEGORICAL = ["storage_condition", "transport_condition"]
API_TO_DATASET = {
    "commodity": "commodity", "moisture": "moisture_content", "fat": "fat_oil_content",
    "ph": "ph", "respiration_rate": "respiration_rate", "shelf_life": "required_shelf_life",
    "temperature": "storage_temperature", "humidity": "storage_humidity",
    "storage_condition": "storage_condition", "transport_condition": "transport_condition",
}


def make_preprocessor():
    numeric = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scale", StandardScaler())])
    categorical = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERIC),
        ("categorical", categorical, CATEGORICAL),
    ], remainder="drop")


def new_pipeline(classifier):
    return Pipeline([("preprocessor", make_preprocessor()), ("classifier", classifier)])


def metric_scorers(class_labels):
    # Fixed class list makes macro metrics comparable when one fold has no
    # examples of a rare curated class.
    from sklearn.metrics import make_scorer
    return {
        "accuracy": "accuracy",
        "precision_macro": make_scorer(precision_score, labels=class_labels, average="macro", zero_division=0),
        "recall_macro": make_scorer(recall_score, labels=class_labels, average="macro", zero_division=0),
        "f1_macro": make_scorer(f1_score, labels=class_labels, average="macro", zero_division=0),
    }


def choose_holdout(X, y, seed=42):
    labels = set(y)
    # Stratified deterministic holdout. The input lattice is deduplicated below;
    # the report explicitly limits these metrics to reproducing its own labels.
    for offset in range(100):
        split = StratifiedShuffleSplit(n_splits=1, test_size=0.22, random_state=seed + offset)
        train_ix, test_ix = next(split.split(X, y))
        if set(y.iloc[train_ix]) == labels and set(y.iloc[test_ix]) == labels:
            return train_ix, test_ix, seed + offset
    raise RuntimeError("Could not find a holdout split containing every curated class.")


def aggregate_importances(pipeline):
    prep = pipeline.named_steps["preprocessor"]
    classifier = pipeline.named_steps["classifier"]
    names = prep.get_feature_names_out()
    if hasattr(classifier, "feature_importances_"):
        raw = np.asarray(classifier.feature_importances_, dtype=float)
        method = "tree impurity importance aggregated by source feature"
    elif hasattr(classifier, "coef_"):
        raw = np.abs(np.asarray(classifier.coef_, dtype=float)).mean(axis=0)
        method = "mean absolute coefficient aggregated by source feature"
    else:
        return {}, "not exposed by selected estimator"
    grouped = {name: 0.0 for name in FEATURES}
    for transformed_name, value in zip(names, raw):
        clean = transformed_name.split("__", 1)[-1]
        # Match the longest source feature first to keep names containing
        # underscores intact.
        source = next((f for f in sorted(FEATURES, key=len, reverse=True) if clean == f or clean.startswith(f + "_")), None)
        if source:
            grouped[source] += float(value)
    total = sum(grouped.values())
    if total:
        grouped = {key: value / total for key, value in grouped.items()}
    return grouped, method


def main():
    warnings.filterwarnings("ignore", category=UserWarning)
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Missing curated dataset: {DATA_PATH}. Run generate_dataset.py first.")
    frame = pd.read_csv(DATA_PATH)
    required = DATASET_INPUTS + [TARGET, "_split_group"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Dataset columns are missing: {missing}")
    if frame[required].isna().any().any():
        raise ValueError("Generated data unexpectedly contains missing cells; inspect the generator.")
    if frame.duplicated(DATASET_INPUTS + [TARGET]).any():
        raise ValueError("Duplicate feature/target rows detected.")
    if not frame["moisture_content"].between(0, 100).all() or not frame["fat_oil_content"].between(0, 100).all():
        raise ValueError("Composition values fall outside 0–100%.")
    if (frame["moisture_content"] + frame["fat_oil_content"] > 100).any():
        raise ValueError("Water plus fat exceeds 100% for at least one row.")
    if not frame["ph"].between(0, 14).all() or not frame["storage_humidity"].between(0, 100).all():
        raise ValueError("pH or relative humidity range validation failed.")
    if frame[FEATURES].duplicated().any():
        raise ValueError("Duplicate model-feature vectors detected (including rows that differ only by excluded pH).")

    X, y = frame[FEATURES], frame[TARGET].astype(str)
    classes = sorted(y.unique())
    class_counts = y.value_counts().sort_index()
    n_splits = min(5, int(class_counts.min()))
    if n_splits < 2:
        raise ValueError("Each target class needs at least two examples for cross-validation.")
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    scoring = metric_scorers(classes)
    candidates = {
        "logistic_regression": LogisticRegression(max_iter=3000, class_weight="balanced", random_state=42),
        "random_forest": RandomForestClassifier(
            n_estimators=300, min_samples_leaf=2, class_weight="balanced_subsample",
            random_state=42, n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=100, learning_rate=0.04, max_depth=2, random_state=42,
        ),
    }
    cv_results = {}
    for name, estimator in candidates.items():
        result = cross_validate(new_pipeline(estimator), X, y, scoring=scoring, cv=cv, n_jobs=1, error_score="raise")
        cv_results[name] = {
            metric: {"mean": float(np.mean(result[f"test_{metric}"])), "std": float(np.std(result[f"test_{metric}"]))}
            for metric in scoring
        }
    # Model choice uses grouped-by-class-preserving stratified CV macro-F1,
    # with CV accuracy only as a deterministic tie breaker. Holdout scores are
    # reported afterward and never used to select the estimator.
    selected_name = max(candidates, key=lambda name: (cv_results[name]["f1_macro"]["mean"], cv_results[name]["accuracy"]["mean"]))
    train_ix, test_ix, used_seed = choose_holdout(X, y)
    X_train, X_test = X.iloc[train_ix], X.iloc[test_ix]
    y_train, y_test = y.iloc[train_ix], y.iloc[test_ix]
    if set(X_train.index).intersection(X_test.index) or set(y_train.index).intersection(y_test.index):
        raise AssertionError("Train/test index leakage detected.")
    # Preprocessing is part of a Pipeline, so imputers/scalers/encoders fit only
    # on train-fold records during CV and on the holdout training portion here.
    holdout_pipeline = new_pipeline(candidates[selected_name]).fit(X_train, y_train)
    heldout_predictions = holdout_pipeline.predict(X_test)
    holdout = {
        "accuracy": float(accuracy_score(y_test, heldout_predictions)),
        "precision_macro": float(precision_score(y_test, heldout_predictions, labels=classes, average="macro", zero_division=0)),
        "recall_macro": float(recall_score(y_test, heldout_predictions, labels=classes, average="macro", zero_division=0)),
        "f1_macro": float(f1_score(y_test, heldout_predictions, labels=classes, average="macro", zero_division=0)),
        "test_rows": int(len(test_ix)),
        "train_rows": int(len(train_ix)),
        "split_seed": used_seed,
        "confusion_matrix_labels": classes,
        "confusion_matrix": confusion_matrix(y_test, heldout_predictions, labels=classes).tolist(),
    }
    final_pipeline = new_pipeline(candidates[selected_name]).fit(X, y)
    preprocessor = final_pipeline.named_steps["preprocessor"]
    importance, importance_method = aggregate_importances(final_pipeline)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, MODEL_DIR / "packwise_pipeline.joblib")
    joblib.dump(preprocessor, MODEL_DIR / "preprocessing_pipeline.joblib")
    feature_config = {
        "features": FEATURES,
        "accepted_request_fields": DATASET_INPUTS,
        "validated_but_not_used_by_model": {
            "commodity": "Used only for dataset provenance and application validation; the classifier cannot use food names, so an unseen validated food follows the same measured-feature pipeline.",
            "ph": "No defensible pH-to-material-class label rule was found for these curated classes; pH is validated, stored in the dataset and echoed by the API but excluded from the classifier.",
        },
        "numeric_features": NUMERIC,
        "categorical_features": CATEGORICAL,
        "target": TARGET,
        "api_field_mapping": API_TO_DATASET,
        "encoding": "OneHotEncoder(handle_unknown='ignore')",
        "numeric_preprocessing": "median imputation then StandardScaler, fitted inside cross-validation/training pipeline",
        "missing_values_in_generated_data": 0,
        "target_is_experimental_ground_truth": False,
        "label_rules": "ml/training/generate_dataset.py::LABEL_RULES / assign_label",
    }
    metadata = {
        "model_name": selected_name,
        "model_type": type(final_pipeline.named_steps["classifier"]).__name__,
        "model_version": "prototype-2.0",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_path": DATA_PATH.relative_to(ROOT).as_posix(),
        "dataset_rows": int(len(frame)),
        "input_features": FEATURES,
        "accepted_request_fields": DATASET_INPUTS,
        "validated_but_not_used_by_model": ["ph"],
        "target": TARGET,
        "classes": classes,
        "class_counts": {str(k): int(v) for k, v in class_counts.items()},
        "input_ranges_by_commodity": {
            str(food): {
                column: [float(frame.loc[frame.commodity == food, column].min()), float(frame.loc[frame.commodity == food, column].max())]
                for column in ["moisture_content", "fat_oil_content", "respiration_rate", "required_shelf_life", "storage_temperature", "storage_humidity"]
            }
            for food in sorted(frame.commodity.unique())
        },
        "input_ranges_global": {
            column: [float(frame[column].min()), float(frame[column].max())]
            for column in NUMERIC
        },
        "supported_categories": {
            column: sorted(frame[column].astype(str).unique().tolist())
            for column in CATEGORICAL
        },
        "majority_class_baseline": float(class_counts.max() / len(frame)),
        "cv_folds": n_splits,
        "cross_validation": cv_results,
        "holdout": holdout,
        "feature_importance_method": importance_method,
        "feature_importance": importance,
        "scikit_learn_version": sklearn.__version__,
        "limitations": [
            "All target labels are deterministic research-derived curation rules, not experimentally observed packaging decisions.",
            "Metrics quantify how well candidate estimators reproduce this synthetic rule grid; they are not real-food accuracy or scientific validation.",
            "The structured grid contains one demonstration nutrient/pH center for several commodities; changed real measurements may be outside the training distribution.",
            "Mature-green bananas have one curated target class in the current grid, so the model does not compare competing banana package classes or learn banana-specific material tradeoffs.",
            "No confidence percentage is displayed because class probabilities are not calibrated against experimental outcomes.",
        ],
    }
    (MODEL_DIR / "feature_config.json").write_text(json.dumps(feature_config, indent=2), encoding="utf-8")
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (ROOT / "docs" / "model_report.md").write_text(render_report(metadata), encoding="utf-8")
    print(json.dumps({"selected_model": selected_name, "holdout": holdout, "cv": cv_results, "feature_importance": importance}, indent=2))


def render_report(meta):
    counts = "\n".join(f"| `{label}` | {count} |" for label, count in meta["class_counts"].items())
    cv_table = "\n".join(
        f"| {name} | {values['accuracy']['mean']:.3f} ± {values['accuracy']['std']:.3f} | {values['precision_macro']['mean']:.3f} ± {values['precision_macro']['std']:.3f} | {values['recall_macro']['mean']:.3f} ± {values['recall_macro']['std']:.3f} | {values['f1_macro']['mean']:.3f} ± {values['f1_macro']['std']:.3f} |"
        for name, values in meta["cross_validation"].items()
    )
    return f"""# Prototype ML model report

Generated: {meta['trained_at_utc']}

## Dataset and target

- Dataset: `{meta['dataset_path']}` ({meta['dataset_rows']} deterministic synthetic/curated rows).
- Inputs: {', '.join(f'`{name}`' for name in meta['input_features'])}.
- Target: `{meta['target']}`.
- Label source: documented curation rules in `ml/training/generate_dataset.py`; no target is an experimental observation.
- Class imbalance: majority class share {meta['majority_class_baseline']:.3f}; macro metrics are used alongside accuracy.

| Curated target class | Rows |
|---|---:|
{counts}

## Preprocessing and leakage checks

The classifier uses six measured numeric inputs plus storage and transport conditions. It does not receive the commodity name or pH. Numeric inputs use median imputation and standard scaling; categorical conditions use most-frequent imputation and one-hot encoding. These are inside a scikit-learn `Pipeline`, so each cross-validation fold fits preprocessing only on its training partition. The dataset retains the commodity and pH for provenance and API validation, but neither reaches the classifier. Generated data was checked for missing values, exact duplicate request/target records, impossible composition sums, pH/RH bounds, and train/test index overlap. The split/helper column is not a model input.

The rows are a structured scenario grid derived from a fixed label policy. The evaluation therefore measures rule-grid reproduction, not generalization to independent experiments. Neighboring grid points can be correlated; high scores must not be presented as real-world packaging accuracy.

## Candidate model comparison

Stratified {meta['cv_folds']}-fold cross-validation; mean ± standard deviation. Selection uses mean macro-F1, with CV accuracy as a tie-breaker. No model was chosen from the holdout score.

| Model | Accuracy | Macro precision | Macro recall | Macro F1 |
|---|---:|---:|---:|---:|
{cv_table}

Selected model: **{meta['model_name']}** (`{meta['model_type']}`).

## Held-out synthetic-grid metrics

- Train rows: {meta['holdout']['train_rows']}; held-out rows: {meta['holdout']['test_rows']}.
- Accuracy: {meta['holdout']['accuracy']:.3f}
- Macro precision: {meta['holdout']['precision_macro']:.3f}
- Macro recall: {meta['holdout']['recall_macro']:.3f}
- Macro F1: {meta['holdout']['f1_macro']:.3f}

Confusion matrix uses this class order: {', '.join(f'`{name}`' for name in meta['holdout']['confusion_matrix_labels'])}.

```json
{json.dumps(meta['holdout']['confusion_matrix'], indent=2)}
```

These figures are **not estimates of real-world predictive performance**. They quantify how well a conventional model recovers curated labels from their own generated design grid.

## Unseen commodity and support handling

The commodity name is not a model feature. The API validates it against the bundled FoodOn vocabulary, then sends the same eight measured/storage features to the fitted pipeline for a known or valid unseen name. Invalid names are rejected before inference. This demonstrates inference for an unseen name in the model's feature space; it does not establish real-world food or packaging generalization because the labels are synthetic/curated and there is no independent commodity trial set. The API warns when a numeric model input falls outside its global training-data min/max range. That simple per-feature check does not detect every unsupported combination within those bounds.

## Explainability and confidence

Feature importance method: {meta['feature_importance_method']}. The API labels these as global model importance, not causal effects for a specific food. SHAP was not needed for this small, rule-labelled prototype. Probabilities are intentionally not shown as user confidence because the class labels are synthetic and no experimental calibration set exists.

## Limitations

""" + "\n".join(f"- {item}" for item in meta["limitations"]) + "\n"


if __name__ == "__main__":
    main()
