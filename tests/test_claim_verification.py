from __future__ import annotations

from autoresearch.experiments.ledger import LedgerEntry
from autoresearch.paper.claims import verify_numeric_claims


def test_verify_numeric_claims_accepts_ledger_metrics() -> None:
    ledger = [
        LedgerEntry("baseline", 1.0, "ok", "keep", "", "", "runs/baseline/metrics.json"),
        LedgerEntry("regularized", 0.95, "ok", "keep", "", "", "runs/regularized/metrics.json"),
    ]

    result = verify_numeric_claims("The metric improved from 1.0 to 0.95.", ledger)

    assert result.ok
    assert result.verified_numbers == (1.0, 0.95)


def test_verify_numeric_claims_rejects_fabricated_numbers() -> None:
    ledger = [
        LedgerEntry("baseline", 1.0, "ok", "keep", "", "", "runs/baseline/metrics.json"),
    ]

    result = verify_numeric_claims("The metric was 0.123.", ledger)

    assert not result.ok
    assert result.unsupported_numbers == (0.123,)
