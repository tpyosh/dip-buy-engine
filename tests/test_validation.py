from __future__ import annotations

from decimal import Decimal

from monthly_limit_order_review.models import CandidateOrder
from monthly_limit_order_review.validation import apply_candidate_validations


def build_candidate(**overrides) -> CandidateOrder:
    candidate = CandidateOrder(
        symbol="URA",
        bucket="satellite_core",
        base_price=Decimal("100"),
        current_price=Decimal("90"),
        limit_price=Decimal("85"),
        shares=2,
        estimated_cost=Decimal("170"),
        estimated_cost_jpy=Decimal("26780"),
        currency="USD",
        drawdown_pct=Decimal("-15"),
        drawdown_rule="-15% x 2",
        reference_method="mean_close_30d",
    )
    for key, value in overrides.items():
        setattr(candidate, key, value)
    return candidate


def test_limit_price_above_current_is_suppressed(buy_rules_config) -> None:
    candidates, warnings = apply_candidate_validations(
        [build_candidate(limit_price=Decimal("95"), estimated_cost=Decimal("190"), estimated_cost_jpy=Decimal("29925"))],
        buy_rules_config,
    )

    candidate = candidates[0]
    assert candidate.suppressed is True
    assert candidate.suppressed_reason_code == "limit_above_current"
    assert candidate.suppressed_reason_text == "Calculated limit price is not below the current price."
    assert warnings[0].code == "limit_above_current"


def test_missing_current_price_is_reported_as_calculation_blocker(buy_rules_config) -> None:
    candidates, warnings = apply_candidate_validations(
        [build_candidate(current_price=None)],
        buy_rules_config,
    )

    candidate = candidates[0]
    assert candidate.suppressed is True
    assert candidate.suppressed_reason_code == "missing_current_price"
    assert candidate.suppression_reasons == ["Current price is unavailable."]
    assert warnings[0].code == "missing_current_price"
