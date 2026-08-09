from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest

from monthly_limit_order_review.storage import load_yaml
from monthly_limit_order_review.strategy_policy import (
    StrategyPolicyError,
    load_current_strategy,
    validate_strategy_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def test_current_strategy_pointer_loads_the_approved_strategy() -> None:
    strategy = load_current_strategy(ROOT)

    assert strategy["strategy_id"] == "husband_personal_2026-08-09"
    assert strategy["automation"]["human_approval_required_for_all_trades"] is True


def test_strategy_targets_and_rebalance_thresholds_are_consistent() -> None:
    strategy = load_current_strategy(ROOT)
    groups = strategy["allocation"]["target_groups"]

    target_sum = sum((Decimal(str(group["target_pct"])) for group in groups.values()), start=Decimal("0"))

    assert target_sum == Decimal("1.0")
    assert Decimal(str(groups["broad_core"]["rebalance_proposal_below_pct"])) == Decimal("0.65")
    assert Decimal(str(groups["active_hobby"]["rebalance_proposal_above_pct"])) == Decimal("0.35")


def test_invalid_semiconductor_threshold_order_is_rejected() -> None:
    strategy = deepcopy(load_current_strategy(ROOT))
    strategy["risk_limits"]["direct_themes"]["semiconductor"]["rebalance_proposal_above_pct"] = 0.10

    with pytest.raises(StrategyPolicyError, match="semiconductor rebalance trigger"):
        validate_strategy_policy(strategy)


def test_cash_redeployment_plan_preserves_the_approved_reserve() -> None:
    plan = load_yaml(ROOT / "plans/2026/2026-07-25_cash_redeployment.yaml")
    liquidity = plan["basis"]["liquidity_jpy"]
    reserve = plan["allocations"]["hobby_dip_buy_reserve"]["amount_jpy"]
    core_purchase = plan["allocations"]["broad_core_lump_sum"]["planned_amount_jpy"]
    projection = plan["projection_if_executed_at_basis_amounts"]

    assert liquidity - reserve == core_purchase
    assert projection["broad_core_after_jpy"] == projection["broad_core_before_jpy"] + core_purchase
    assert projection["active_hobby_after_reserve_jpy"] == (
        projection["active_hobby_before_reserve_jpy"] + reserve
    )
    assert plan["basis"]["total_assets_jpy"] == (
        projection["broad_core_before_jpy"]
        + projection["active_hobby_before_reserve_jpy"]
        + liquidity
        + projection["residual_other_jpy"]
        + projection["unreconciled_snapshot_rounding_jpy"]
    )
