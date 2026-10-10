from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from monthly_limit_order_review.models import CandidateOrder
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.validation import apply_candidate_validations, build_snapshot_validation_warnings


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


@pytest.mark.parametrize("primary_source", ["broker_csv", "structured_asset_records"])
def test_snapshot_validation_accepts_non_image_sources(
    sample_snapshot_path: Path, primary_source: str
) -> None:
    snapshot = load_snapshot(sample_snapshot_path)
    snapshot.source_evidence = {"primary_source": primary_source}

    warnings = build_snapshot_validation_warnings(snapshot)

    assert "primary_evidence_not_screenshot" not in {warning.code for warning in warnings}


def test_snapshot_validation_reports_category_duplicate_and_account_warnings(tmp_path: Path) -> None:
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
    warnings = build_snapshot_validation_warnings(snapshot)
    warning_codes = {warning.code for warning in warnings}

    assert "category_total_mismatch" in warning_codes
    assert "duplicate_holding_symbol" in warning_codes
    assert "possible_duplicate_holding" in warning_codes
    assert "pension_classification_check" in warning_codes


def test_category_gap_below_point_one_percent_of_total_assets_is_ignored(
    tmp_path: Path,
) -> None:
    current_path = tmp_path / "category_relative_tolerance.yaml"
    current_path.write_text(
        """snapshot_date: "2026-08-09"
currency_base: "JPY"
total_assets_jpy: 40000000
category_totals_jpy:
  core: 20000000
holdings:
  - symbol: "CORE"
    name: "Core Fund"
    source_category: "core"
    account_type: "特定口座"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 19960001
    currency: "JPY"
  - symbol: "CASH"
    name: "Cash"
    source_category: "liquidity"
    account_type: null
    asset_class: "liquidity"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 20039999
    currency: "JPY"
""",
        encoding="utf-8",
    )

    warnings = build_snapshot_validation_warnings(load_snapshot(current_path))

    assert "category_total_mismatch" not in {warning.code for warning in warnings}


def test_category_gap_at_point_one_percent_of_total_assets_is_reported(
    tmp_path: Path,
) -> None:
    current_path = tmp_path / "category_relative_tolerance_boundary.yaml"
    current_path.write_text(
        """snapshot_date: "2026-08-09"
currency_base: "JPY"
total_assets_jpy: 40000000
category_totals_jpy:
  core: 20000000
holdings:
  - symbol: "CORE"
    name: "Core Fund"
    source_category: "core"
    account_type: "特定口座"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 19960000
    currency: "JPY"
  - symbol: "CASH"
    name: "Cash"
    source_category: "liquidity"
    account_type: null
    asset_class: "liquidity"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 20040000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    warnings = build_snapshot_validation_warnings(load_snapshot(current_path))

    assert "category_total_mismatch" in {warning.code for warning in warnings}


def test_snapshot_validation_reports_previous_snapshot_continuity_issues(tmp_path: Path) -> None:
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
    warnings = build_snapshot_validation_warnings(
        current_snapshot,
        previous_snapshot=previous_snapshot,
    )
    warning_codes = {warning.code for warning in warnings}

    assert "previous_holding_disappeared" in warning_codes
    assert "asset_class_changed_from_previous_snapshot" in warning_codes
    assert "large_month_over_month_change" in warning_codes


def test_same_product_cross_account_rows_are_not_treated_as_redundant(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "cross-account.yaml"
    snapshot_path.write_text(
        """snapshot_date: "2026-07-26"
currency_base: "JPY"
total_assets_jpy: 3000000
holdings:
  - symbol: "NISSEI_SOX_1"
    name: "ニッセイSOX指数インデックスファンド"
    account_type: "NISA成長投資枠"
    asset_class: "satellite_core"
    quantity: 100
    avg_cost: 10000
    current_price: 20000
    market_value_jpy: 2000000
    currency: "JPY"
  - symbol: "NISSEI_SOX_2"
    name: "ニッセイSOX指数インデックスファンド"
    account_type: "特定口座（源泉徴収あり）"
    asset_class: "satellite_core"
    quantity: 50
    avg_cost: 10000
    current_price: 20000
    market_value_jpy: 1000000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    warnings = build_snapshot_validation_warnings(load_snapshot(snapshot_path))
    warning_codes = {warning.code for warning in warnings}

    assert "same_product_cross_account_split" in warning_codes
    assert "account_separation_unverified" not in warning_codes
    assert "possible_duplicate_holding" not in warning_codes


def test_unknown_account_blocks_same_product_consolidation(tmp_path: Path) -> None:
    snapshot_path = tmp_path / "unknown-account.yaml"
    snapshot_path.write_text(
        """snapshot_date: "2026-07-26"
currency_base: "JPY"
total_assets_jpy: 3000000
holdings:
  - symbol: "SOX_1"
    name: "SOX Fund"
    account_type: null
    asset_class: "satellite_core"
    quantity: 100
    avg_cost: 10000
    current_price: 20000
    market_value_jpy: 2000000
    currency: "JPY"
  - symbol: "SOX_2"
    name: "SOX Fund"
    account_type: "特定口座（源泉徴収あり）"
    asset_class: "satellite_core"
    quantity: 50
    avg_cost: 10000
    current_price: 20000
    market_value_jpy: 1000000
    currency: "JPY"
""",
        encoding="utf-8",
    )

    warnings = build_snapshot_validation_warnings(load_snapshot(snapshot_path))
    warning_codes = {warning.code for warning in warnings}

    assert "missing_account_type" in warning_codes
    assert "account_separation_unverified" in warning_codes
