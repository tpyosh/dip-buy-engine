from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.models import CandidateOrder
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.validation import apply_candidate_validations, build_ocr_snapshot_validation_warnings


def build_candidate(**overrides) -> CandidateOrder:
    candidate = CandidateOrder(
        symbol="URA",
        bucket="satellite_core",
        base_price=Decimal("100"),
        avg20_base_price=Decimal("100"),
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


def test_ocr_validation_reports_category_duplicate_and_account_warnings(tmp_path: Path) -> None:
    current_path = tmp_path / "current.yaml"
    current_path.write_text(
        """snapshot_date: "2026-04-07"
currency_base: "JPY"
total_assets_jpy: 2000000
category_totals_jpy:
  core: 2500000
holdings:
  - symbol: "DUP"
    name: "Duplicate Fund"
    account_type: "特定口座"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1000000
    currency: "JPY"
  - symbol: "DUP"
    name: "Duplicate Fund"
    account_type: "特定口座"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1000000
    currency: "JPY"
  - symbol: "IDECO_FUND"
    name: "iDeCo Pension Fund"
    account_type: "iDeCo"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 0
    currency: "JPY"
""",
        encoding="utf-8",
    )

    snapshot = load_snapshot(current_path)
    warnings = build_ocr_snapshot_validation_warnings(snapshot)
    warning_codes = {warning.code for warning in warnings}

    assert "category_total_mismatch" in warning_codes
    assert "duplicate_holding_symbol" in warning_codes
    assert "possible_duplicate_holding" in warning_codes
    assert "pension_classification_check" in warning_codes


def test_ocr_validation_reports_previous_snapshot_continuity_issues(tmp_path: Path) -> None:
    previous_path = tmp_path / "previous.yaml"
    previous_path.write_text(
        """snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 1500000
holdings:
  - symbol: "OLD"
    name: "Old Asset"
    asset_class: "satellite"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 500000
    currency: "JPY"
  - symbol: "KEEP"
    name: "Keep Asset"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 1000000
    currency: "JPY"
""",
        encoding="utf-8",
    )
    current_path = tmp_path / "current.yaml"
    current_path.write_text(
        """snapshot_date: "2026-04-07"
currency_base: "JPY"
total_assets_jpy: 2500000
holdings:
  - symbol: "KEEP"
    name: "Keep Asset"
    asset_class: "satellite"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 2500000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    previous_snapshot = load_snapshot(previous_path)
    current_snapshot = load_snapshot(current_path)
    warnings = build_ocr_snapshot_validation_warnings(
        current_snapshot,
        previous_snapshot=previous_snapshot,
    )
    warning_codes = {warning.code for warning in warnings}

    assert "previous_holding_disappeared" in warning_codes
    assert "asset_class_changed_from_previous_snapshot" in warning_codes
    assert "large_month_over_month_change" in warning_codes
