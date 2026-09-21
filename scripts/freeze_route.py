"""Write the frozen route record after the exploratory stage.

Turns the exploratory route recommendation into the immutable record that the
confirmatory notebooks read. The record fixes the route (superiority or
parsimony), the validation-selected incumbent, the eligible comparator set, the
confirmatory size, the per-family size split, the representation list, the
thresholds, and hashes of the frozen inputs. It refuses to write a record whose
route is unresolved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recommendation",
        default="research_review/results/g3/exploratory/route_recommendation.json",
    )
    parser.add_argument(
        "--analysis",
        default="research_review/results/g3/exploratory/analysis_degree0.json",
    )
    parser.add_argument("--config", default="configs/tk_pilot_study.yaml")
    parser.add_argument(
        "--frozen-models", default="research_review/results/g3/frozen_models.json"
    )
    parser.add_argument("--out", default="research_review/results/g3/route_freeze.json")
    parser.add_argument("--degree", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recommendation = json.loads(Path(args.recommendation).read_text(encoding="utf-8"))
    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8"))
    cfg = yaml.safe_load(open(REPO_ROOT / args.config))
    degree = int(args.degree)
    per_degree = recommendation.get("per_degree", {}).get(str(degree), {})
    route = per_degree.get("recommended_route") or recommendation.get(
        "suggested_confirmatory_block", {}
    ).get("route")
    if route not in ("superiority", "parsimony"):
        raise SystemExit(
            f"route is unresolved ({route!r}); do not open confirmatory seeds"
        )
    incumbent = per_degree.get("incumbent") or recommendation.get(
        "suggested_confirmatory_block", {}
    ).get("incumbent")
    eligible = per_degree.get("eligible_comparators") or recommendation.get(
        "suggested_confirmatory_block", {}
    ).get("eligible_comparators")
    size = per_degree.get("size_recommendation") or analysis.get("size_recommendation")
    if not size:
        raise SystemExit("no size recommendation is available")
    n_clusters = int(size["n_clusters"])
    n_per_family = int(math.ceil(n_clusters / 2.0))
    frozen_models_path = REPO_ROOT / args.frozen_models
    payload = {
        "schema_version": "1.0",
        "artifact": "route_freeze",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage": "exploratory_complete",
        "degree": degree,
        "route": str(route),
        "incumbent": str(incumbent),
        "eligible_comparators": [str(name) for name in (eligible or [])],
        "n_clusters": n_clusters,
        "n_clusters_per_family": n_per_family,
        "n_clusters_by_family": {
            "A": n_per_family,
            "B": n_clusters - n_per_family,
        },
        "size_recommendation": size,
        "families": [str(name) for name in cfg["families"]],
        "classes": [str(name) for name in cfg["classes"]],
        "representations": [str(name) for name in cfg["representations"]],
        "thresholds": dict(cfg["decision"]),
        "bootstrap": dict(cfg["bootstrap"]),
        "seed_namespaces": dict(cfg["seed_namespaces"]),
        "frozen_models_file": str(args.frozen_models),
        "frozen_models_sha256": (
            sha256_file(frozen_models_path) if frozen_models_path.is_file() else None
        ),
        "source_artifacts": {
            "recommendation": str(args.recommendation),
            "recommendation_sha256": sha256_file(Path(args.recommendation)),
            "analysis": str(args.analysis),
            "analysis_sha256": sha256_file(Path(args.analysis)),
        },
        "note": (
            "Frozen after the exploratory stage and before any confirmatory test "
            "seed was opened. The route, incumbent, eligible comparator set, and "
            "size must not change afterwards."
        ),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ("route", "incumbent", "n_clusters")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
