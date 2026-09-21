"""Figures for the Phase 0 witness suite.

These figures visualize correctness witnesses only. They are not evidence of
novelty, predictive value, or application utility.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

from .diagram_metrics import bottleneck_bruteforce, bottleneck_gudhi
from .path_diagnostics import compute_path_diagnostics

__all__ = ["make_all_figures"]


def _singleton(s: float, lifespan: float = 10.0) -> np.ndarray:
    return np.array([[float(s), float(s) + lifespan]])


def _euclidean(p, q) -> float:
    return float(np.linalg.norm(np.asarray(p, dtype=float) - np.asarray(q, dtype=float)))


def _finish(fig, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def figure_singleton_bottleneck(out_dir: Path) -> Path:
    shifts = np.linspace(0.0, 9.0, 91)
    base = _singleton(0.0)
    gudhi = np.array([bottleneck_gudhi(base, _singleton(s)) for s in shifts])
    brute = np.array([bottleneck_bruteforce(base, _singleton(s)) for s in shifts])
    analytic = np.minimum(shifts, 5.0)
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.plot(shifts, analytic, color="black", linewidth=2.0, label="analytic min(|ds|, M/2)")
    ax.plot(shifts, gudhi, color="tab:blue", linewidth=1.0, linestyle="--", label="gudhi")
    ax.plot(
        shifts,
        brute,
        color="tab:orange",
        linewidth=0.0,
        marker="x",
        markersize=4,
        markevery=6,
        label="brute force",
    )
    ax.axvline(5.0, color="tab:red", linestyle=":", linewidth=1.2)
    ax.annotate(
        "diagonal matching takes over at M/2 = 5",
        xy=(5.0, 2.5),
        xytext=(5.6, 1.4),
        arrowprops={"arrowstyle": "->", "color": "tab:red"},
        color="tab:red",
        fontsize=9,
    )
    ax.set_xlabel("birth-coordinate shift |ds| for singleton diagrams {(s, s+10)}")
    ax.set_ylabel("bottleneck distance")
    ax.set_title("W-01: singleton bottleneck distance and the diagonal transition")
    ax.legend(loc="lower right", fontsize=9)
    path = out_dir / "fig_singleton_bottleneck.png"
    _finish(fig, path)
    return path


def figure_equal_speed_paths(out_dir: Path) -> Path:
    timestamps = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    path_a = [0.0, 1.0, 2.0, 1.0, 0.0]
    path_b = [0.0, 1.0, 0.0, 1.0, 0.0]
    pd_a = compute_path_diagnostics(
        [_singleton(s) for s in path_a], timestamps
    )
    pd_b = compute_path_diagnostics(
        [_singleton(s) for s in path_b], timestamps
    )
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    axes[0].plot(timestamps, path_a, marker="o", label="path A", color="tab:blue")
    axes[0].plot(timestamps, path_b, marker="s", label="path B", color="tab:orange")
    axes[0].set_xlabel("physical time")
    axes[0].set_ylabel("singleton birth coordinate s_t")
    axes[0].set_title("Equal speed, length, and endpoints")
    axes[0].legend(fontsize=9)
    angle_times = pd_a.interval_speed_times[1:]
    axes[1].step(angle_times, pd_a.comparison_angles, where="mid", color="tab:blue", label="path A")
    axes[1].step(angle_times, pd_b.comparison_angles, where="mid", color="tab:orange", label="path B")
    axes[1].set_yticks([0.0, np.pi / 2.0, np.pi])
    axes[1].set_yticklabels(["0", "pi/2", "pi"])
    axes[1].set_xlabel("physical time")
    axes[1].set_ylabel("comparison angle theta_t")
    axes[1].set_title("Angle sequences differ (L = 4, R = 0, speed = 4)")
    axes[1].legend(fontsize=9)
    path = out_dir / "fig_equal_speed_paths.png"
    _finish(fig, path)
    return path


def figure_angle_instability(out_dir: Path) -> Path:
    epsilons = np.logspace(-12, -2, 60)
    plus = []
    minus = []
    for eps in epsilons:
        plus.append(
            compute_path_diagnostics(
                [(0.0, 0.0), (1.0, 0.0), (1.0 + eps, 0.0)], [0.0, 1.0, 2.0], _euclidean
            ).comparison_angles[0]
        )
        minus.append(
            compute_path_diagnostics(
                [(0.0, 0.0), (1.0, 0.0), (1.0 - eps, 0.0)], [0.0, 1.0, 2.0], _euclidean
            ).comparison_angles[0]
        )
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ax.semilogx(epsilons, plus, color="tab:blue", linewidth=2.0, label="delta = +eps (continuation)")
    ax.semilogx(epsilons, minus, color="tab:orange", linewidth=2.0, label="delta = -eps (reversal)")
    ax.set_ylim(-0.15, np.pi + 0.15)
    ax.set_yticks([0.0, np.pi / 2.0, np.pi])
    ax.set_yticklabels(["0", "pi/2", "pi"])
    ax.set_xlabel("step perturbation magnitude |delta| (log scale)")
    ax.set_ylabel("comparison angle theta at the middle point")
    ax.set_title("W-09: angle jump at a near-zero step (perturbation 2|delta|)")
    ax.legend(loc="center right", fontsize=9)
    path = out_dir / "fig_angle_instability.png"
    _finish(fig, path)
    return path


def figure_random_path_checks(out_dir: Path, results: list[dict]) -> Path:
    rng = np.random.default_rng(20260920)
    lengths = []
    displacements = []
    etas = []
    for _ in range(200):
        dim = int(rng.choice([1, 2, 3, 5, 8]))
        n_points = int(rng.integers(5, 13))
        points = rng.normal(size=(n_points, dim))
        pd = compute_path_diagnostics(points, np.arange(n_points, dtype=float), _euclidean)
        lengths.append(pd.length)
        displacements.append(pd.displacement)
        etas.append(pd.efficiency)
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    axes[0].scatter(lengths, displacements, s=12, alpha=0.6, color="tab:blue")
    upper = max(max(lengths), max(displacements))
    axes[0].plot([0, upper], [0, upper], color="black", linestyle="--", linewidth=1.0, label="R = L")
    axes[0].set_xlabel("path length L")
    axes[0].set_ylabel("endpoint displacement R")
    axes[0].set_title("Random metric paths satisfy R <= L")
    axes[0].legend(fontsize=9)
    perturbation_case = next(r for r in results if r["case_id"] == "W-12")
    ratios = perturbation_case["details"]["max_observed_over_bound"]
    names = ["length", "displacement", "speed", "speed change"]
    values = [ratios["length"], ratios["displacement"], ratios["speed"], ratios["speed_change"]]
    axes[1].bar(names, values, color="tab:green")
    axes[1].axhline(1.0, color="tab:red", linestyle="--", linewidth=1.2, label="bound")
    axes[1].set_ylabel("max observed error / bound")
    axes[1].set_title("Perturbation bounds are respected")
    axes[1].legend(fontsize=9)
    path = out_dir / "fig_random_path_checks.png"
    _finish(fig, path)
    return path


def make_all_figures(out_dir: Path, results: list[dict]) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [
        figure_singleton_bottleneck(out_dir),
        figure_equal_speed_paths(out_dir),
        figure_angle_instability(out_dir),
        figure_random_path_checks(out_dir, results),
    ]
