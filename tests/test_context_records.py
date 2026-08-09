from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.context_records import (
    apply_holding_metadata,
    holding_metadata_by_symbol,
    load_financial_context,
    load_holding_metadata_context,
)
from monthly_limit_order_review.snapshot_loader import load_snapshot


ROOT = Path(__file__).resolve().parents[1]


def test_financial_values_are_loaded_from_versioned_ssot() -> None:
    context = load_financial_context(ROOT)
    record = context["record"]
    regular = record["cash_flow"]["regular_month"]

    assert context["source_path"] == "financial/versions/2026-08-09.yaml"
    assert regular["essential_expenses_jpy"]["value"] == 250_000
    assert regular["income_after_tax_social_insurance_mortgage_ideco_jpy"][
        "is_expense_value"
    ] is False
    assert record["cash_requirements"]["emergency_fund"]["target_jpy"] == 2_000_000
    assert record["cash_requirements"]["contingency_reserve"]["enabled"] is False
    assert record["dip_buy_liquidity"]["target_ratio"]["value"] is None
    assert record["dip_buy_liquidity"]["target_ratio"]["status"] == (
        "proposal_requested_from_current_monthly_independent_review"
    )
    assert record["strategic_profile"]["objective_configuration"][
        "selection_status"
    ] == "confirmed"
    assert record["strategic_profile"]["planned_contributions"]["status"] == (
        "reviewer_to_derive"
    )


def test_holding_metadata_overlays_accounts_without_rewriting_snapshot() -> None:
    context = load_holding_metadata_context(ROOT)
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")

    apply_holding_metadata(snapshot, context["record"])
    accounts = {holding.symbol: holding.account_type for holding in snapshot.holdings}

    assert context["source_path"] == "holdings/versions/2026-08-02.yaml"
    assert accounts["NISSEI_SOX_1"] == "特定口座（源泉徴収あり）"
    assert accounts["NISSEI_SOX_2"] == "NISA（2024年以降・枠区分未確認）"
    assert accounts["9444"] == "特定口座（源泉徴収あり）"
    assert accounts["2353"] == "一般口座"


def test_holding_intent_and_execution_answers_are_machine_readable() -> None:
    context = load_holding_metadata_context(ROOT)
    holdings = holding_metadata_by_symbol(context)
    execution = context["record"]["execution_context"]

    assert holdings["9444"]["execution_status"]["sell_order_available"] is True
    assert holdings["9444"]["user_intent"]["disposition"] == "sell_requested"
    assert holdings["2353"]["user_intent"]["disposition"] == (
        "sell_when_at_a_loss_preferred"
    )
    assert holdings["7201"]["user_intent"]["disposition"] == "sell_allowed"
    assert holdings["7203"]["user_intent"]["disposition"] == (
        "sell_if_rationally_justified"
    )
    assert execution == {
        "scope": "portfolio",
        "unreflected_orders": False,
        "planned_withdrawals": False,
        "restricted_funds": False,
        "confirmed_at": "2026-08-02",
    }
