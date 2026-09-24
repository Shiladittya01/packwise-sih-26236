# Dataset and label methodology

## Why the training data is curated

Searches found datasets and studies for separate pieces of the problem, including food composition, produce respiration, packaging permeability/composition, MAP design and food/package shelf-life studies. The inspected sources did not expose an experimentally observed row schema covering the complete desired feature set and a selected recommended-material class. Re-labeling those unrelated data as material recommendations would be misleading.

The prototype therefore trains on a **synthetic/curated research-derived scenario grid**. It is a transparent demonstration dataset, not real collected food/packaging trials. Rows are emitted by `ml/training/generate_dataset.py`; the CSV is deterministic across runs. There are no random features, no repeated copies used as extra samples, and no external dataset is used as the target.

## Size and schema

- 295 generated scenarios across six supported commodity archetypes.
- Ten recorded request features: `commodity`, `moisture_content`, `fat_oil_content`, `ph`, `respiration_rate`, `required_shelf_life`, `storage_temperature`, `storage_humidity`, `storage_condition`, `transport_condition`.
- Target `recommended_packaging_material` with eight classes.
- `_split_group` is generator bookkeeping only; it is not a feature.
- The classifier uses nine features. pH is recorded, validated and echoed, but deliberately excluded from model fitting because the curated class rules do not establish a scientifically defensible pH-to-material mapping. Fixed pH anchors could let it proxy a commodity category.

## Sources and anchor values

The complete source/dataset inventory is [`research_sources.json`](research_sources.json). USDA FoodData Central anchors used in the generator are four individual records: raw tomato (FDC 170457), plain salted potato chips (169677), whole milk (746782) and raw lentils (172420). UC Davis's tomato produce fact sheet supplies two green-ripening respiration anchors (midpoints 7.5 mL CO₂/kg·h at 10 °C and 13.5 at 15 °C). These are source-referenced composition/respiration values, not package recommendations. Biscuit and frozen vegetable composition centers and the pH centers are retained demonstration inputs and are labeled as such.

Other researched sources include 50-article packaging permeability/composition annotations, a 295-point material permeability compilation, an open CC0 produce MAP supplementary dataset and a 2026 snack shelf-life simulation workbook. Their row/schema/rights limitations are recorded individually. None supplies the full ground-truth target, and none is incorporated as if it did.

## Label assignment

Every row is a Cartesian product of explicitly listed levels in `GRID`; the target is assigned by `assign_label`. The complete per-commodity rationale and uncertainty is in the `LABEL_RULES` dictionary in the generator.

| Commodity | Prototype curation rule | Target class(es) |
|---|---|---|
| Tomatoes | UC Davis respiration ranges and MAP literature support matching produce respiration with gas exchange. The prototype maps lower listed respiration with the shorter target to a breathable PE candidate; higher listed respiration or the longer target to a micro-perforated candidate. The cutoffs are not published validated thresholds. | `breathable_pe_film`, `microperforated_polyolefin` |
| Potato chips | Literature notes oxygen/moisture protection for oil-rich fried snacks. The grid maps standard cases to metallized laminate; ≥180-day targets or rough freight to foil laminate. The threshold is a prototype assumption. | `metallized_laminate`, `foil_laminate` |
| Biscuits | Dry-food moisture/oxygen protection informs a short/local BOPP/CPP candidate; high-fat with ≥90-day target or non-local route maps to metallized laminate. This cutoff is not a literature-derived numeric threshold. | `bopp_cpp_pouch`, `metallized_laminate` |
| Pasteurized milk | A bottle is the curated format candidate. This label does not validate food contact, barrier, pasteurization or cold chain. | `hdpe_bottle` |
| Frozen vegetables | A polyethylene freezer-bag format is the curated candidate. No numeric freezer service property is inferred. | `freezer_pe_bag` |
| Lentils | A dry pouch is the local/shorter/lower-humidity candidate; rough handling, higher humidity or ≥180-day targets map to a lined woven bulk-sack candidate. This is an unvalidated format tradeoff. | `bopp_cpp_pouch`, `woven_pp_pe_liner_sack` |

The material classes in `packaging_database/materials.json` are generic structures. No class implies a supplier grade, universal barrier value, exact gauge or tested performance.

## Cleaning, preprocessing, evaluation

The generator and trainer fail on missing cells, exact duplicate request/target rows, duplicate model-feature vectors (including rows that differ only by excluded pH), water+fat above 100%, moisture/fat outside 0–100%, pH outside 0–14, and humidity outside 0–100%. The trainer records class counts/majority baseline. Numeric imputation (median) and scaling, categorical imputation (most frequent) and one-hot encoding are composed inside a scikit-learn Pipeline; they are fit within each CV fold. The API rejects raw unsupported commodity names. Its explicit `custom:<name>` path is for exploratory use only: the encoder ignores this unseen category and the response flags it as outside the training scope, with no confidence or curated alternatives.

Logistic Regression, Random Forest and Gradient Boosting are compared with four-fold stratified CV. The selected model is chosen by CV macro-F1, then CV accuracy. A separate stratified holdout is reported after selection. The deterministic grid is structured and neighboring conditions are related, so metrics are internal rule-reproduction scores—not external validity. No production accuracy claim is made.
