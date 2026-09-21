"""Freeze per-cell learner selections from the exploratory selection table.

Reads the exploratory ``selection_table.parquet``, keeps the selected candidate
for every ``(family, sigma, stride, degree, representation)`` cell, and writes a
JSON mapping that the confirmatory stage uses to fit exactly the frozen learner
without any platform-dependent tie-break. The mapping keys match the runner's
cell key format ``family|sigma|stride|degree|representation``.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

LABEL_PATTERN = re.compile(r"^(?P<family>[A-Za-z_]+)\((?P<params>.*)\)$")


def parse_label(label: str) -> dict:
    match = LABEL_PATTERN.match(str(label))
    if not match:
        raise ValueError(f"unrecognized learner label {label!r}")
    family = match.group("family")
    params: dict[str, float] = {}
    for part in match.group("params").split(","):
        if not part.strip():
            continue
        key, value = part.split("=")
        params[key.strip()] = float(value)
    return {"learner_family": family, "params": params}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-table", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    table = pd.read_parquet(args.selection_table)
    selected = table[table["selected"].astype(bool)]
    if selected.empty:
        raise SystemExit("selection table has no selected rows")
    models: dict[str, dict] = {}
    duplicates = []
    for _, row in selected.iterrows():
        key = (
            f"{row['family']}|{float(row['sigma']):g}|{int(row['stride'])}"
            f"|{int(row['degree'])}|{row['representation']}"
        )
        if key in models:
            duplicates.append(key)
        models[key] = parse_label(str(row["learner"]))
    payload = {
        "source_selection_table": str(args.selection_table),
        "n_cells": len(models),
        "duplicates": duplicates,
        "models": dict(sorted(models.items())),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    families: dict[str, int] = {}
    for entry in models.values():
        name = str(entry["learner_family"])
        families[name] = families.get(name, 0) + 1
    print(json.dumps({"n_cells": len(models), "learner_families": families}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
