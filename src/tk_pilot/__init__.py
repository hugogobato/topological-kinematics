"""Topological Kinematics pilot package.

Phase 0 artifacts freeze the diagram metric and the discrete path diagnostics.
The Phase 1 modules add synthetic trajectory generators, persistence
extraction, feature representations, learners, and the staged runner.

Importing :mod:`tk_pilot` alone stays lightweight: submodules are imported
explicitly by callers, so this package import never pulls in gudhi, persim,
scikit-learn, pandas, matplotlib, or joblib.
"""

__all__: list[str] = []
