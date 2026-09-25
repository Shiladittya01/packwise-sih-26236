"""Build the bundled English FoodOn product-term reference snapshot.

The generated file is a name-validation vocabulary, not a source of food
composition values or packaging labels. Runtime API validation is offline.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "datasets" / "reference" / "foodon_food_commodities.json"
FOODON_COMMIT = "cd73540243a84bcd511a500d9a497d12d7dc02f6"
SOURCE_URL = (
    "https://raw.githubusercontent.com/FoodOntology/foodon/"
    f"{FOODON_COMMIT}/src/ontology/foodon-synonyms.tsv"
)
FOOD_PRODUCT_ROOT = "http://purl.obolibrary.org/obo/FOODON_00001002"


def english_text(value: str) -> str | None:
    value = value.strip()
    if "@" in value:
        text, language = value.rsplit("@", 1)
        if language.lower() not in {"en", "en-us", "en-gb"}:
            return None
        value = text
    value = value.strip().strip('"')
    return value or None


def build() -> dict:
    with urlopen(SOURCE_URL, timeout=60) as response:
        rows = csv.DictReader(response.read().decode("utf-8").splitlines(), delimiter="\t")
        classes: dict[str, dict] = {}
        children: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            class_iri = row["?class"].strip().strip("<>")
            if not class_iri.startswith("http://purl.obolibrary.org/obo/FOODON_"):
                continue
            record = classes.setdefault(class_iri, {"id": class_iri.rsplit("/", 1)[-1], "parents": set(), "labels": [], "aliases": set()})
            parent = row["?parent"].strip().strip("<>")
            if parent.startswith("http://purl.obolibrary.org/obo/FOODON_"):
                record["parents"].add(parent)
                children[parent].add(class_iri)
            term = english_text(row["?label"])
            if not term:
                continue
            kind = row["?type"].strip()
            if kind == "label":
                record["labels"].append(term)
            elif kind in {"synonym", "synonym (exact)", "synonym (narrow)"}:
                record["aliases"].add(term)

    product_terms = {FOOD_PRODUCT_ROOT}
    queue = [FOOD_PRODUCT_ROOT]
    while queue:
        parent = queue.pop()
        for child in children.get(parent, ()):
            if child not in product_terms:
                product_terms.add(child)
                queue.append(child)

    terms = []
    for iri in sorted(product_terms):
        source = classes.get(iri)
        if not source or not source["labels"]:
            continue
        label = sorted(set(source["labels"]), key=lambda value: (len(value), value.casefold()))[0]
        aliases = sorted(
            {value for value in source["aliases"] if value.casefold() != label.casefold()},
            key=str.casefold,
        )
        terms.append({
            "id": source["id"],
            "label": label,
            "aliases": aliases,
            "parents": sorted(parent.rsplit("/", 1)[-1] for parent in source["parents"]),
        })

    return {
        "name": "FoodOn food product terminology snapshot",
        "source": "FoodOn",
        "source_commit": FOODON_COMMIT,
        "source_url": SOURCE_URL,
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "attribution": "FoodOn project contributors",
        "retrieved_on": date.today().isoformat(),
        "root_term": "FOODON_00001002 (food product)",
        "term_count": len(terms),
        "purpose": "Offline commodity-name validation only; not food composition data, packaging labels, or ML training data.",
        "terms": terms,
    }


if __name__ == "__main__":
    database = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(database, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {database['term_count']} FoodOn terms to {OUTPUT}")
