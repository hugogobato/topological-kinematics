#!/usr/bin/env python3
"""Run the Phase 0 (G0) witness suite and write machine-readable artifacts.

Usage:
    python3 scripts/run_witness_suite.py [--out DIR] [--seed N]

Outputs (default DIR = research_review/results/phase0/witness):
    witness_results.json   machine-readable case results
    witness_summary.txt    human-readable summary
    environment.json       frozen environment and input hashes
    run.log                raw stdout/stderr transcript
    figures/*.png          correctness figures

The suite is a correctness artifact. Passing it does not establish novelty,
predictive value, or application utility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tk_pilot import witness_figures  # noqa: E402
from tk_pilot.witnesses import WITNESS_SEED, run_all  # noqa: E402

HASHED_INPUTS = [
    "research_review/Topological_Kinematics_Research_Plan.md",
    "research_review/Pilot_Experiment_Specification.md",
    "research_review/assumption_ledger.yaml",
    "research_review/metric_interface.md",
    "research_review/preregistration_draft.md",
    "research_review/witness_note.md",
    "research_review/results/phase0/G0_decision.md",
    "research_review/topological_kinematics_witness.py",
    "src/tk_pilot/diagram_metrics.py",
    "src/tk_pilot/path_diagnostics.py",
    "src/tk_pilot/witnesses.py",
    "src/tk_pilot/witness_figures.py",
    "scripts/run_witness_suite.py",
    "tests/test_diagram_metrics.py",
    "tests/test_path_diagnostics.py",
    "tests/test_witnesses.py",
]


class Tee:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("w", encoding="utf-8")

    def write(self, text: str) -> None:
        sys.stdout.write(text)
        self.handle.write(text)

    def flush(self) -> None:
        sys.stdout.flush()
        self.handle.flush()

    def close(self) -> None:
        self.handle.close()


def display_path(path: Path) -> str:
    """Render a path relative to the project root when possible."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def sanitize(value):
    if isinstance(value, dict):
        return {str(key): sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    if isinstance(value, (bool, str)) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            return value
        return None
    if hasattr(value, "tolist"):
        return sanitize(value.tolist())
    if hasattr(value, "item"):
        return sanitize(value.item())
    return str(value)


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def package_version(name: str):
    try:
        module = __import__(name)
        return getattr(module, "__version__", "unknown")
    except Exception:
        return None


def environment_record() -> dict:
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": None,
        "packages": {
            "numpy": package_version("numpy"),
            "scipy": package_version("scipy"),
            "matplotlib": package_version("matplotlib"),
            "gudhi": package_version("gudhi"),
            "persim": package_version("persim"),
            "pytest": package_version("pytest"),
            "yaml": package_version("yaml"),
            "ripser": package_version("ripser"),
        },
    }


def cpu_count() -> int | None:
    try:
        import os

        return os.cpu_count()
    except Exception:
        return None


def summarize(records: list[dict]) -> dict:
    per_category = {}
    for record in records:
        bucket = per_category.setdefault(
            record["category"], {"cases": 0, "passed": 0, "failed": 0}
        )
        bucket["cases"] += 1
        if record["passed"]:
            bucket["passed"] += 1
        else:
            bucket["failed"] += 1
    n_passed = sum(1 for r in records if r["passed"])
    return {
        "n_cases": len(records),
        "n_passed": n_passed,
        "n_failed": len(records) - n_passed,
        "all_passed": n_passed == len(records),
        "per_category": per_category,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "research_review" / "results" / "phase0" / "witness",
        help="output directory",
    )
    parser.add_argument("--seed", type=int, default=WITNESS_SEED)
    args = parser.parse_args()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    tee = Tee(out_dir / "run.log")
    started = time.perf_counter()
    try:
        tee.write(f"Phase 0 witness suite (seed {args.seed})\n")
        tee.write(f"started {datetime.now(timezone.utc).isoformat()}\n")
        records = run_all(seed=args.seed)
        summary = summarize(records)
        environment = environment_record()
        environment["cpu_count"] = cpu_count()
        environment["input_sha256"] = {
            relative: sha256_file(ROOT / relative) for relative in HASHED_INPUTS
        }
        environment["wall_seconds"] = time.perf_counter() - started
        environment["seed"] = args.seed

        for record in records:
            status = "PASS" if record["passed"] else "FAIL"
            tee.write(f"[{status}] {record['case_id']} {record['description']}\n")
            for check in record["checks"]:
                check_status = "ok" if check["passed"] else "FAILED"
                detail = {
                    key: value
                    for key, value in check.items()
                    if key not in {"name", "passed"}
                }
                tee.write(f"    - {check_status}: {check['name']} {detail}\n")
        tee.write(
            f"summary: {summary['n_passed']}/{summary['n_cases']} cases passed; "
            f"wall {environment['wall_seconds']:.2f} s\n"
        )

        payload = {
            "suite": "tk_pilot_phase0_witness",
            "gate": "G0",
            "scope": (
                "Operational correctness of the frozen finite-metric definitions "
                "only; not novelty, not extraction correctness, not utility."
            ),
            "seed": args.seed,
            "summary": summary,
            "cases": records,
        }
        with (out_dir / "witness_results.json").open("w", encoding="utf-8") as handle:
            json.dump(sanitize(payload), handle, indent=2, allow_nan=False)
        with (out_dir / "environment.json").open("w", encoding="utf-8") as handle:
            json.dump(sanitize(environment), handle, indent=2, allow_nan=False)
        with (out_dir / "witness_summary.txt").open("w", encoding="utf-8") as handle:
            handle.write(
                "Phase 0 witness suite summary\n"
                f"seed: {args.seed}\n"
                f"cases passed: {summary['n_passed']}/{summary['n_cases']}\n"
                f"all passed: {summary['all_passed']}\n"
                "verdict: operational correctness only\n"
            )
        try:
            figures = witness_figures.make_all_figures(out_dir / "figures", records)
            for figure in figures:
                tee.write(f"figure: {display_path(figure)}\n")
        except Exception as error:  # figure rendering must not hide results
            tee.write(f"figure generation failed: {type(error).__name__}: {error}\n")
        return 0 if summary["all_passed"] else 1
    finally:
        tee.close()


if __name__ == "__main__":
    raise SystemExit(main())
