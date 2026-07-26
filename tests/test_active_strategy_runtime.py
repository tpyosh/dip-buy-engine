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


def test_latest_snapshot_uses_strategy_groups_instead_of_legacy_bucket_targets() -> None:
    policy, _ = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_07.yaml")

    analysis = compute_portfolio_metrics(snapshot, policy)
    strategy_allocations = {
        allocation.bucket: allocation
        for allocation in analysis["strategy_allocations"]
    }

    assert strategy_allocations["broad_core"].actual_pct == Decimal("0.3462")
    assert strategy_allocations["broad_core"].target_pct == Decimal("0.70")
    assert strategy_allocations["active_hobby"].actual_pct == Decimal("0.3328")
    assert strategy_allocations["active_hobby"].target_pct == Decimal("0.30")
    assert analysis["strategy_metrics"]["recognized_reserved_cash_jpy"] == Decimal(
        "1000000"
    )
    assert analysis["strategy_metrics"]["unallocated_liquidity_jpy"] == Decimal(
        "12620505"
    )
    assert all(
        allocation.target_pct is None
        for allocation in analysis["bucket_allocations"]
    )


def test_latest_snapshot_emits_new_strategy_warnings_not_legacy_bucket_warnings() -> None:
    policy, _ = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_07.yaml")

    analysis = compute_portfolio_metrics(snapshot, policy)
    warning_codes = {warning.code for warning in analysis["warnings"]}

    assert "broad_core_reinforcement_proposal" in warning_codes
    assert "semiconductor_routine_additions_paused" in warning_codes
    assert "active_hobby_rebalance_proposal" not in warning_codes
    assert "satellite_plus_core_limit" not in warning_codes
    assert "pltr_limit" not in warning_codes


def test_approved_cash_plan_overrides_legacy_monthly_core_budget() -> None:
    policy, context = active_policy()
    snapshot = load_snapshot(ROOT / "data/normalized/snapshot_2026_07.yaml")
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

    assert materials["strategy_id"] == "husband_personal_2026-07-25"
    assert materials["active_plan_id"] == "2026-07-25_cash_redeployment"
    assert materials["monthly_core_budget_tier"] == "approved_lump_sum_plan"
    assert materials["recommended_monthly_core_buy_budget_jpy"] == 12620505
    assert materials["active_plan_basis_snapshot_date"] == "2026-06-28"
    assert materials["active_plan_basis_liquidity_jpy"] == 13620505
    assert materials["active_plan_basis_planned_amount_jpy"] == 12620505
    assert materials["active_plan_current_snapshot_date"].isoformat() == "2026-06-28"
    assert materials["active_plan_current_recalculated_amount_jpy"] == 12620505
    assert materials["active_plan_amount_delta_jpy"] == 0
    assert materials["active_plan_amount_difference_expected"] is False
    assert materials["active_plan_historical_basis_must_not_be_overwritten"] is True
    assert materials["active_plan_requires_pretrade_balance_confirmation"] is True


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
    assert signal["rebalance_proposal_required"] is False
    assert signal["priority_lowered_reason"] == "direct_semiconductor_above_preferred_max"
    assert signal["semiconductor_preferred_max_pct"] == Decimal("0.15")
    assert signal["semiconductor_rebalance_proposal_above_pct"] == Decimal("0.20")


def test_monthly_cli_records_current_strategy_and_approved_plan(
    monkeypatch,
    sample_market_references,
) -> None:
    monkeypatch.setattr(
        "monthly_limit_order_review.cli.fetch_market_references",
        lambda requests: sample_market_references,
    )

    computation = compute_monthly(
        ROOT / "data/normalized/snapshot_2026_07.yaml",
        project_root=ROOT,
    )
    warning_codes = {warning.code for warning in computation.warnings}

    assert computation.metadata["strategy_id"] == "husband_personal_2026-07-25"
    assert computation.strategy_summary["active_plan_ids"] == [
        "2026-07-25_cash_redeployment"
    ]
    assert computation.core_buy_materials[
        "recommended_monthly_core_buy_budget_jpy"
    ] == 12620505
    assert computation.core_buy_materials["active_plan_product"] == (
        "楽天・プラス・オールカントリー株式インデックス・ファンド"
    )
    assert computation.core_buy_materials[
        "active_plan_product_allocation_pct"
    ] == 1
    assert computation.core_buy_materials["active_plan_execution_method"] == "lump_sum"
    assert computation.core_buy_materials[
        "active_plan_user_executes_order_manually"
    ] is True
    assert computation.sox_buy_signal["routine_additions_allowed"] is False
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
    } == {"inherited_pending_review"}
    assert computation.quarterly_rule_review_outputs[
        "cash_normalization_months_estimate"
    ] is None

    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
    )
    assert "active_strategy_id: husband_personal_2026-07-25" in prompt
    assert "| broad_core | 13629542 | 34.62% | 70.00% | -35.38% |" in prompt
    assert "| active_hobby | 13104152 | 33.28% | 30.00% | 3.28% |" in prompt
    assert "recommended_monthly_core_buy_budget_jpy: 12620505" in prompt
    assert (
        "active_plan_product: 楽天・プラス・オールカントリー株式インデックス・ファンド"
        in prompt
    )
    assert "active_plan_product_allocation_pct: 100.00%" in prompt
    assert "active_plan_execution_method: lump_sum" in prompt
    assert "active_plan_user_executes_order_manually: True" in prompt
    assert "core_spot_buy_allocation_rule: {'source_role': 'approved_active_plan'" in prompt
    assert "baseline_total_core_deployment_target_jpy: 1380000" not in prompt
    assert "rebalance_mode_core_spot_buy_reference_jpy: 1280000" not in prompt
    assert "external_files_required: false" in prompt
    assert "routine_additions_allowed: False" in prompt
    assert "inherited_pending_review" in prompt


def test_current_snapshot_keeps_active_plan_basis_separate_from_recalculation(
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

    assert materials["active_plan_basis_snapshot_date"] == "2026-06-28"
    assert materials["active_plan_basis_planned_amount_jpy"] == 12620505
    assert materials["active_plan_current_snapshot_date"].isoformat() == "2026-07-26"
    assert materials["active_plan_current_recalculated_amount_jpy"] == 12622664
    assert materials["active_plan_amount_delta_jpy"] == 2159
    assert materials["active_plan_amount_difference_expected"] is True
    assert materials["active_plan_historical_basis_must_not_be_overwritten"] is True

    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
    )
    assert "active_plan_basis_planned_amount_jpy: 12620505" in prompt
    assert "active_plan_current_recalculated_amount_jpy: 12622664" in prompt
    assert "active_plan_amount_delta_jpy: 2159" in prompt
    assert "active_plan_amount_difference_expected: true" in prompt
    assert "active_plan_historical_basis_must_not_be_overwritten: true" in prompt
