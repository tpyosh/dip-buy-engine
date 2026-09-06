from __future__ import annotations

from pathlib import Path

from monthly_limit_order_review.context_records import (
    apply_holding_metadata,
    holding_metadata_by_symbol,
    load_financial_context,
    load_holding_metadata_context,
)
from monthly_limit_order_review.current_state import build_current_state_projection
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml


ROOT = Path(__file__).resolve().parents[1]


def test_financial_values_are_loaded_from_versioned_ssot() -> None:
    context = load_financial_context(ROOT)
    record = context["record"]
    regular = record["cash_flow"]["regular_month"]

    assert context["source_path"] == "financial/versions/2026-08-29-v4.yaml"
    assert regular["essential_expenses_jpy"]["value"] == 250_000
    assert regular["income_after_tax_social_insurance_mortgage_ideco_jpy"][
        "is_expense_value"
    ] is False
    assert record["cash_requirements"]["emergency_fund"]["target_jpy"] == 2_000_000
    assert record["cash_requirements"]["contingency_reserve"]["enabled"] is False
    large_expense = record["cash_requirements"]["near_term_large_expenses"]["confirmed_items"][0]
    assert large_expense["amount_jpy"] == 467_987
    assert large_expense["funding_account"] == "三菱UFJ銀行 普通預金"
    assert large_expense["investment_treatment"] == "excluded_from_investable_cash"
    assert record["dip_buy_liquidity"]["target_ratio"]["value"] == 0.0
    assert record["dip_buy_liquidity"]["target_ratio"]["status"] == (
        "confirmed_user_approved"
    )
    assert record["strategic_profile"]["objective_configuration"][
        "selection_status"
    ] == "confirmed"
    assert record["strategic_profile"]["planned_contributions"]["status"] == (
        "reviewer_to_derive"
    )
    assert "投資待機資金の目標比率" not in record["unknown_information"]
    assert not any(
        "サテライトの目標比率" in item
        for item in record["unknown_information"]
    )


def test_holding_metadata_overlays_accounts_without_rewriting_snapshot() -> None:
    context = load_holding_metadata_context(ROOT)
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")

    apply_holding_metadata(snapshot, context["record"])
    accounts = {holding.symbol: holding.account_type for holding in snapshot.holdings}

    assert context["source_path"] == "holdings/versions/2026-08-14-v4.yaml"
    assert accounts["NISSEI_SOX_1"] == "特定口座（源泉徴収あり）"
    assert accounts["NISSEI_SOX_2"] == "NISA成長投資枠"
    assert accounts["9444"] == "特定口座（源泉徴収あり）"
    assert accounts["2353"] == "一般口座"


def test_holding_intent_and_execution_answers_are_machine_readable() -> None:
    context = load_holding_metadata_context(ROOT)
    holdings = holding_metadata_by_symbol(context)
    execution = context["record"]["execution_context"]

    assert holdings["9444"]["execution_status"]["position_quantity"] == 0
    assert holdings["9444"]["execution_status"]["last_filled_quantity"] == 1500
    assert holdings["9444"]["execution_status"]["order_in_progress_quantity"] == 0
    assert holdings["2353"]["execution_status"]["position_quantity"] == 0
    assert holdings["2353"]["execution_status"]["last_filled_quantity"] == 100
    assert holdings["2353"]["execution_status"]["order_in_progress_quantity"] == 0
    assert holdings["7201"]["execution_status"]["position_quantity"] == 0
    assert holdings["7201"]["execution_status"]["last_filled_quantity"] == 100
    assert holdings["7201"]["execution_status"]["last_average_fill_price_jpy"] == 345
    assert holdings["SMH"]["execution_status"]["position_quantity"] == 0
    assert holdings["SMH"]["execution_status"]["order_in_progress_quantity"] == 0
    assert holdings["SMH"]["execution_status"]["last_filled_quantity"] == 1
    assert holdings["SMH"]["execution_status"]["last_average_fill_price_usd"] == 585.83
    assert holdings["SMH"]["execution_status"]["settlement_amount_usd"] == 582.92
    assert holdings["SMH"]["execution_status"]["last_order_number"] == "1262"
    assert holdings["SMH"]["execution_status"]["order_side"] == "sell"
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
        "unreflected_orders": True,
        "planned_withdrawals": False,
        "restricted_funds": False,
        "confirmed_at": "2026-08-14",
    }


def test_current_state_projection_replaces_confirmed_full_exits_with_proceeds() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")
    original_total = snapshot.total_assets_jpy
    original_symbols = {holding.symbol for holding in snapshot.holdings}
    context = load_holding_metadata_context(ROOT)
    ledger = load_yaml(ROOT / "transactions/ledger.yaml")

    projected, report = build_current_state_projection(
        snapshot,
        context["record"],
        ledger,
    )

    projected_symbols = {holding.symbol for holding in projected.holdings}
    assert {"7201", "9444", "2353"} <= original_symbols
    assert not {"7201", "9444", "2353", "SMH", "BTC", "ETH", "XRP"} & projected_symbols
    assert "POST_SNAPSHOT_SALE_PROCEEDS" in projected_symbols
    proceeds = next(
        holding
        for holding in projected.holdings
        if holding.symbol == "POST_SNAPSHOT_SALE_PROCEEDS"
    )
    assert proceeds.market_value_jpy == 921_785
    assert report["removed_snapshot_market_value_jpy"] == 945_952
    assert report["provisional_sale_proceeds_jpy"] == 921_785
    assert report["projected_total_assets_jpy"] == 40_027_744
    assert report["is_provisional"] is True
    assert snapshot.total_assets_jpy == original_total
    assert {holding.symbol for holding in snapshot.holdings} == original_symbols


def test_current_state_projection_does_not_treat_unknown_deductions_as_confirmed_zero() -> None:
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")
    context = load_holding_metadata_context(ROOT)
    ledger = load_yaml(ROOT / "transactions/ledger.yaml")

    _, report = build_current_state_projection(snapshot, context["record"], ledger)
    adjustments = {item["symbol"]: item for item in report["adjustments"]}

    assert adjustments["7201"]["confirmed_fees_jpy"] == 55
    assert "tax_jpy" in adjustments["7201"]["unknown_deductions"]
    assert "fee_jpy" in adjustments["9444"]["unknown_deductions"]
    assert "net_proceeds_jpy" not in adjustments["2353"]["unknown_deductions"]
    assert adjustments["9444"]["confirmed_net_proceeds_jpy"] == 459_976
    assert adjustments["2353"]["confirmed_net_proceeds_jpy"] == 25_048
    assert adjustments["SMH"]["gross_proceeds_jpy"] is None
    assert adjustments["SMH"]["provisional_proceeds_jpy"] == 91_950
    assert "snapshot market value carrying placeholder" in adjustments["SMH"][
        "provisional_amount_definition"
    ]
    crypto = adjustments["BTC_ETH_XRP_AGGREGATE"]
    assert crypto["symbols"] == ["BTC", "ETH", "XRP"]
    assert crypto["snapshot_market_value_jpy"] == 322_422
    assert crypto["provisional_proceeds_jpy"] == 310_366
    assert crypto["gross_proceeds_jpy"] is None
