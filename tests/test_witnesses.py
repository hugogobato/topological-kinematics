"""Tests for the machine-readable witness registry (WP-0.2)."""

import json

from tk_pilot.witnesses import CASES, WITNESS_SEED, run_all


def test_all_witnesses_pass():
    records = run_all(seed=WITNESS_SEED)
    failed = [record["case_id"] for record in records if not record["passed"]]
    assert failed == []
    assert len(records) == len(CASES)


def test_case_ids_unique_and_expected():
    ids = [case_id for case_id, _, _, _ in CASES]
    assert len(ids) == len(set(ids))
    expected = {f"W-{index:02d}" for index in range(1, len(CASES) + 1)}
    assert set(ids) == expected


def test_records_are_json_safe():
    records = run_all(seed=WITNESS_SEED)
    sanitized = _sanitize(records)
    text = json.dumps(sanitized, allow_nan=False)
    assert "case_id" in text


def test_deterministic_for_fixed_seed():
    first = run_all(seed=WITNESS_SEED)
    second = run_all(seed=WITNESS_SEED)
    assert json.dumps(_sanitize(first), sort_keys=True) == json.dumps(
        _sanitize(second), sort_keys=True
    )


def _sanitize(value):
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else None
    if hasattr(value, "tolist"):
        return _sanitize(value.tolist())
    return str(value)
