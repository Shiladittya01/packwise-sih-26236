# SIH judge notes — factual prototype answers

## Where is the AI?

The supervised model lives in `ml/models/packwise_pipeline.joblib`. `backend/packwise_api.py` loads it and calls its trained `predict()` method after validating and mapping the request. The preprocessing transformer, model and training metadata are under `ml/models/`. The suitability check after prediction is an explicit database rule and is not called machine learning.

## Where did the data come from? How many samples?

The reviewed public sources did not provide the complete experimental food/condition → recommended-material label table needed for this classifier. Packwise uses 295 deterministically generated, research-derived synthetic/curated scenario rows. This is a prototype dataset, not experimentally collected data or 295 independent tests. Its ingredient composition anchors and tomato respiration anchors are sourced and documented; label assignment is by versioned documented curation rules.

## Why this model, and what are the metrics?

The trainer compared Logistic Regression, Random Forest and Gradient Boosting. The Random Forest won on four-fold stratified cross-validation macro-F1. The generated model report gives accuracy, macro precision, macro recall, macro-F1, fold standard deviations and confusion matrix. Those values measure how well the model reconstructs the curated grid labels, not real-world package-selection accuracy.

## How do you prevent overfitting?

Preprocessing stays inside the cross-validation pipeline, exact duplicate input rows are rejected, bookkeeping fields are excluded from model features, classes and class balance are reported, and the selected model is evaluated on a separate holdout. The dataset is still small, structured and rule-labeled; these steps do not replace external experimental validation.

## How does the result respond to inputs? Is this only rules?

The frontend submits the current form values to `/api/recommend`. The API runs the fitted classifier; it does not run the dataset's label-generation rules to make each prediction. Several inputs (such as shelf target, respiration and route) can move a row across learned class boundaries. Since the training labels were curated rules, the model is a genuine supervised ML implementation but not evidence that it outperforms a transparent rule system. This distinction should be stated plainly.

## Can it be used to choose a production pack?

No. It is an SIH prototype shortlist. It does not calculate a package design, certify contact compliance, determine migration, predict microbial safety or shelf life, or validate supplier-specific performance. Real use requires trained food-packaging review and trials.

## What comes next?

Collect independent trial records with commodity/formulation, measured food properties, package structure and gauge, conditioned OTR/WVTR, seal/integrity results, filled-package geometry, storage/transport history, and measured quality/shelf-life outcomes. Have subject-matter experts define recommendation labels; split evaluation by commodity/supplier/study; validate and calibrate on a genuinely independent data collection before making performance claims.
