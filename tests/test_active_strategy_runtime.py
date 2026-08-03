from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.portfolio_metrics import (
    build_core_buy_materials,
    compute_portfolio_metrics,
)
from monthly_limit_order_review.cli import compute_monthly
from monthly_limit_order_review.prompt_renderer import render_chatgpt_prompt
from monthly_limit_order_review.rules import calculate_sox_buy_signal
from monthly_limit_order_review.snapshot_loader import load_snapshot
from monthly_limit_order_review.storage import load_yaml
from monthly_limit_order_review.strategy_policy import load_current_strategy_context


ROOT = Path(__file__).resolve().parents[1]


def active_policy() -> tuple[dict, dict]:
    context = load_current_strategy_context(ROOT)
    policy = deepcopy(load_yaml(ROOT / "config/portfolio_policy.yaml"))
    policy["classification_overrides"] = load_yaml(
        ROOT / "config/classification_overrides.yaml"
    )
    policy["active_strategy"] = context["strategy"]
    policy["active_plans"] = context["active_plans"]
    return policy, context


def test_current_snapshot_uses_strategy_groups_instead_of_legacy_bucket_targets() -> None:
    policy, _ = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")

    analysis = compute_portfolio_metrics(snapshot, policy)
    strategy_allocations = {
        allocation.bucket: allocation
        for allocation in analysis["strategy_allocations"]
    }

    assert strategy_allocations["broad_core"].actual_pct == Decimal("0.3699")
    assert strategy_allocations["broad_core"].target_pct == Decimal("0.70")
    assert strategy_allocations["active_hobby"].actual_pct == Decimal("0.2888")
    assert strategy_allocations["active_hobby"].target_pct == Decimal("0.30")
    assert analysis["strategy_metrics"]["recognized_reserved_cash_jpy"] == Decimal(
        "0"
    )
    assert analysis["strategy_metrics"]["unallocated_liquidity_jpy"] == Decimal(
        "13622664"
    )
    assert all(
        allocation.target_pct is None
        for allocation in analysis["bucket_allocations"]
    )


def test_current_snapshot_emits_new_strategy_warnings_not_legacy_bucket_warnings() -> None:
    policy, _ = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")

    analysis = compute_portfolio_metrics(snapshot, policy)
    warning_codes = {warning.code for warning in analysis["warnings"]}

    assert "broad_core_reinforcement_proposal" in warning_codes
    assert "semiconductor_rebalance_proposal" in warning_codes
    assert "active_hobby_rebalance_proposal" not in warning_codes
    assert "satellite_plus_core_limit" not in warning_codes
    assert "pltr_limit" not in warning_codes


def test_superseded_cash_plan_is_not_loaded_as_an_active_plan() -> None:
    policy, context = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_08.yaml")
    analysis = compute_portfolio_metrics(snapshot, policy)
    buy_rules = load_yaml(ROOT / "config/buy_rules.yaml")

    materials, _ = build_core_buy_materials(
        snapshot,
        analysis["bucket_allocations"],
        analysis["resolved_buckets"],
        [],
        buy_rules,
        strategy_allocations=analysis["strategy_allocations"],
        strategy_metrics=analysis["strategy_metrics"],
        active_strategy=context["strategy"],
        active_plans=context["active_plans"],
    )

    assert context["active_plans"] == []
    assert materials["strategy_id"] == "husband_personal_2026-08-02"
    assert materials["active_plan_id"] is None
    assert materials["monthly_core_budget_tier"] == "standard"
    assert materials["recommended_monthly_core_buy_budget_jpy"] == 100000
    assert materials["active_plan_basis_snapshot_date"] is None
    assert materials["active_plan_basis_liquidity_jpy"] is None
    assert materials["active_plan_basis_planned_amount_jpy"] is None
    assert materials["active_plan_current_snapshot_date"] is None
    assert materials["active_plan_current_recalculated_amount_jpy"] is None
    assert materials["active_plan_amount_delta_jpy"] is None
    assert materials["active_plan_amount_difference_expected"] is False
    assert materials["active_plan_historical_basis_must_not_be_overwritten"] is False
    assert (ROOT / "plans/2026/2026-07-25_cash_redeployment.yaml").exists()


def test_sox_signal_uses_direct_semiconductor_limit_from_active_strategy(
    buy_rules_config,
    sample_market_references,
    sample_exposure_breakdown,
) -> None:
    _, context = active_policy()

    signal = calculate_sox_buy_signal(
        buy_rules_config,
        sample_market_references,
        exposure_breakdown=sample_exposure_breakdown,
        active_strategy=context["strategy"],
    )

    assert signal["routine_additions_allowed"] is False
    assert signal["rebalance_proposal_required"] is True
    assert signal["priority_lowered_reason"] == "direct_semiconductor_above_preferred_max"
    assert signal["semiconductor_preferred_max_pct"] == Decimal("0.12")
    assert signal["semiconductor_rebalance_proposal_above_pct"] == Decimal("0.12")


def test_monthly_cli_records_current_strategy_and_user_conditions(
    monkeypatch,
    sample_market_references,
) -> None:
    monkeypatch.setattr(
        "monthly_limit_order_review.cli.fetch_market_references",
        lambda requests: sample_market_references,
    )

    computation = compute_monthly(
        ROOT / "data/normalized/snapshot_2026_08.yaml",
        project_root=ROOT,
    )
    warning_codes = {warning.code for warning in computation.warnings}

    assert computation.metadata["strategy_id"] == "husband_personal_2026-08-02"
    assert computation.strategy_summary["active_plan_ids"] == []
    assert computation.core_buy_materials[
        "recommended_monthly_core_buy_budget_jpy"
    ] is None
    assert computation.core_buy_materials["active_plan_product"] is None
    assert computation.sox_buy_signal["routine_additions_allowed"] is False
    assert computation.sox_buy_signal["rebalance_proposal_required"] is True
    assert "core_recurring_plan_conflicts_with_current_strategy" in warning_codes
    assert "legacy_candidate_heuristic_review_only" in warning_codes
    assert computation.metadata["core_recurring_contributions_source"] == (
        "plans/recurring/versions/2026-03-01.yaml"
    )
    assert computation.metadata["candidate_policy_status"] == (
        "legacy_analytical_heuristic"
    )
    assert computation.core_buy_materials["monthly_core_budget_policy"] == {}
    assert {
        target["thesis_status"]
        for target in computation.long_term_thesis_targets
    } == {"active", "inherited_pending_review"}
    story_targets = {
        target["symbol"]: target for target in computation.security_story_targets
    }
    assert set(story_targets) == {
        "7203",
        "9444",
        "2353",
        "7201",
        "SMH",
        "PLTR",
        "CIBR",
        "MSFT",
        "URA",
    }
    assert story_targets["SMH"]["thesis_status"] == "active"
    assert story_targets["7203"]["thesis_status"] == "missing"
    assert story_targets["9444"]["user_disposition"] == "sell_requested"
    assert story_targets["9444"]["sell_order_available"] is True
    assert story_targets["2353"]["user_disposition"] == (
        "sell_when_at_a_loss_preferred"
    )
    accounts = {
        holding.symbol: holding.account_type
        for holding in computation.snapshot.holdings
    }
    assert accounts["NISSEI_SOX_1"] == "特定口座（源泉徴収あり）"
    assert accounts["NISSEI_SOX_2"] == "NISA（2024年以降・枠区分未確認）"
    assert accounts["9444"] == "特定口座（源泉徴収あり）"
    assert accounts["2353"] == "一般口座"
    assert computation.metadata["approved_review_constraints"][0]["statement"].startswith(
        "直接半導体エクスポージャーを総資産の12.00%以下"
    )
    assert computation.metadata["holding_execution_context"]["unreflected_orders"] is False
    assert computation.quarterly_rule_review_outputs[
        "cash_normalization_months_estimate"
    ] is None

    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
    )
    assert "## 2. 入力データ" in prompt
    assert "total_assets_jpy: 39969688" in prompt
    assert "active_strategy_id" not in prompt
    assert "review_mode: monthly_operational_review" in prompt
    assert "husband_personal_2026-08-02" in prompt
    assert "この承認済み政策からの乖離点検にだけ使い" in prompt
    assert "2026-07-25_cash_redeployment" not in prompt
    assert "recommended_monthly_core_buy_budget_jpy" not in prompt
    assert "12620505" not in prompt
    assert "routine_additions_allowed" not in prompt
    assert "inherited_pending_review" in prompt
    assert "security_story_review_targets:" in prompt
    assert "sell_order_available: true" in prompt
    assert "未反映注文、出金予定、拘束資金はいずれもない" in prompt
    assert "Pythonがルールから生成した候補注文" in prompt


def test_current_snapshot_does_not_reactivate_superseded_cash_plan(
    monkeypatch,
    sample_market_references,
) -> None:
    monkeypatch.setattr(
        "monthly_limit_order_review.cli.fetch_market_references",
        lambda requests: sample_market_references,
    )

    computation = compute_monthly(
        ROOT / "data/normalized/snapshot_2026_08.yaml",
        project_root=ROOT,
    )
    materials = computation.core_buy_materials

    assert materials["active_plan_basis_snapshot_date"] is None
    assert materials["active_plan_basis_planned_amount_jpy"] is None
    assert materials["active_plan_current_snapshot_date"] is None
    assert materials["active_plan_current_recalculated_amount_jpy"] is None
    assert materials["active_plan_amount_delta_jpy"] is None
    assert materials["active_plan_amount_difference_expected"] is False
    assert materials["active_plan_historical_basis_must_not_be_overwritten"] is False

    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
    )
    assert "active_plan_basis_planned_amount_jpy" not in prompt
    assert "active_plan_current_recalculated_amount_jpy" not in prompt
    assert "active_plan_amount_delta_jpy" not in prompt
    assert "12620505" not in prompt
    assert "12622664" not in prompt
