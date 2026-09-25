# SIH judge notes — factual prototype answers

## Where is the AI?

The supervised model lives in `ml/models/packwise_pipeline.joblib`. `backend/packwise_api.py` loads it and calls its trained `predict()` method after validating and mapping the request. The preprocessing transformer, model and training metadata are under `ml/models/`. The suitability check after prediction is an explicit database rule and is not called machine learning.

## Where did the data come from? How many samples?

The reviewed public sources did not provide the complete experimental food/condition → recommended-material label table needed for this classifier. Packwise uses 331 deterministically generated, research-derived synthetic/curated scenario rows across seven commodity profiles. This is a prototype dataset, not experimentally collected data or 331 independent tests. Banana composition and respiration anchors and its carton/liner design context are sourced and documented; label assignment is by versioned documented curation rules. The banana grid has only one curated package class, so it does not compare banana packaging alternatives.

Food names are checked separately against a pinned FoodOn product-term snapshot bundled for offline use. The current snapshot has 12,655 terms. It rejects unmatched strings such as `jjjgjghghg`; it does not provide measured properties or packaging labels.

## What happens for a banana?

Select **Mature-green bananas**. For the prototype profile, the model returns a ventilated fiberboard carton with a polyethylene liner, based on FAO banana-packing guidance. UC Davis postharvest guidance supplies the respiration and handling context: 13–14 °C and 90–95% RH for storage/transport, with chilling-injury risk below 13 °C. The UI defaults are illustrative and should be replaced with measured product/route data. This is a research-curated prototype candidate, not experimental proof of the best banana pack. The current banana training grid contains one target class, so the model does not choose among competing banana package designs.

## Why this model, and what are the metrics?

The trainer compared Logistic Regression, Random Forest and Gradient Boosting. Gradient Boosting won on four-fold stratified cross-validation macro-F1 for the current artifact. The generated model report gives accuracy, macro precision, macro recall, macro-F1, fold standard deviations and confusion matrix. Those values measure how well the model reconstructs the curated grid labels, not real-world package-selection accuracy.

## How do you prevent overfitting?

Preprocessing stays inside the cross-validation pipeline, exact duplicate input rows are rejected, bookkeeping fields are excluded from model features, classes and class balance are reported, and the selected model is evaluated on a separate holdout. The dataset is still small, structured and rule-labeled; these steps do not replace external experimental validation.

## How does the result respond to inputs? Is this only rules?

The frontend submits the current form values to `/api/recommend`. The classifier receives eight measured/storage fields; it never receives commodity name or pH. A valid unseen food such as Dragon Fruit runs through the same saved preprocessing and model pipeline as a training profile. The API marks the name as unseen and checks numeric inputs against training ranges. It does not run the dataset's label-generation rules during inference. Since the training labels were curated rules, this is a supervised ML prototype and not evidence that it outperforms a transparent rule system or generalizes to experimentally verified packaging choices.

## Can it be used to choose a production pack?

No. It is an SIH prototype shortlist. It does not calculate a package design, certify contact compliance, determine migration, predict microbial safety or shelf life, or validate supplier-specific performance. Real use requires trained food-packaging review and trials.

## What comes next?

Collect independent trial records with commodity/formulation, measured food properties, package structure and gauge, conditioned OTR/WVTR, seal/integrity results, filled-package geometry, storage/transport history, and measured quality/shelf-life outcomes. Have subject-matter experts define recommendation labels; split evaluation by commodity/supplier/study; validate and calibrate on a genuinely independent data collection before making performance claims.
