from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from monthly_limit_order_review.models import Holding, PortfolioSnapshot
from monthly_limit_order_review.review_readiness import (
    build_account_type_gate,
    classify_review_account_type,
    require_complete_account_type_gate,
)


def holding(symbol: str, asset_class: str, account_type: str | None) -> Holding:
    return Holding(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        quantity=Decimal("1"),
        avg_cost=Decimal("1"),
        current_price=Decimal("1"),
        market_value_jpy=Decimal("1"),
        currency="JPY",
        account_type=account_type,
    )


def snapshot(*holdings: Holding) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        snapshot_date=date(2026, 8, 9),
        currency_base="JPY",
        total_assets_jpy=Decimal("4"),
        liquidity_target_jpy=None,
        holdings=list(holdings),
    )


@pytest.mark.parametrize(
    ("account_type", "expected"),
    [
        ("NISA（成長投資枠）", "NISA"),
        ("特定口座（源泉徴収あり）", "特定口座"),
        ("一般口座", "一般口座"),
        (None, None),
        ("未確認", None),
    ],
)
def test_account_type_is_classified_for_the_review_gate(
    account_type: str | None,
    expected: str | None,
) -> None:
    assert classify_review_account_type(account_type) == expected


def test_non_tradable_cash_does_not_block_a_complete_account_gate() -> None:
    gate = build_account_type_gate(
        snapshot(
            holding("CORE", "core", "NISA（つみたて投資枠）"),
            holding("STOCK", "satellite", "特定口座（源泉徴収あり）"),
            holding("CASH", "liquidity", None),
        )
    )

    assert gate["status"] == "complete"
    assert gate["checked_holding_count"] == 2
    assert gate["missing_or_unclassified_holdings"] == []


def test_missing_tradable_account_type_blocks_review_generation() -> None:
    portfolio = snapshot(
        holding("CORE", "core", "NISA"),
        holding("UNKNOWN", "satellite", None),
    )

    gate = build_account_type_gate(portfolio)
    assert gate["status"] == "blocked"
    assert gate["missing_or_unclassified_holdings"] == [
        {
            "symbol": "UNKNOWN",
            "name": "UNKNOWN",
            "observed_account_type": None,
        }
    ]
    with pytest.raises(ValueError, match="blocked_missing_account_types: UNKNOWN"):
        require_complete_account_type_gate(portfolio)
