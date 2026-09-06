from __future__ import annotations

from copy import deepcopy
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from monthly_limit_order_review.portfolio_metrics import (
    build_core_buy_materials,
    compute_portfolio_metrics,
)
from monthly_limit_order_review.cli import build_current_review_packet, compute_monthly
from monthly_limit_order_review.on_demand import (
    assess_snapshot_freshness,
    render_on_demand_assessment_prompt,
)
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

    assert strategy_allocations["broad_core"].actual_pct == Decimal("0.3702")
    assert strategy_allocations["broad_core"].target_pct == Decimal("0.825")
    assert strategy_allocations["active_hobby"].actual_pct == Decimal("0.2931")
    assert strategy_allocations["active_hobby"].target_pct == Decimal("0.175")
    assert analysis["strategy_metrics"]["recognized_reserved_cash_jpy"] == Decimal(
        "0"
    )
    assert analysis["strategy_metrics"]["unallocated_liquidity_jpy"] == Decimal(
        "13147713"
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
    assert "active_hobby_rebalance_proposal" in warning_codes
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

    assert [plan["plan_id"] for plan in context["active_plans"]] == ["ACT-S3"]
    assert all(
        plan["plan_id"] != "cash-redeployment-2026-07-25"
        for plan in context["active_plans"]
    )
    assert materials["strategy_id"] == "husband_personal_2026-08-09-v2"
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

    assert computation.metadata["strategy_id"] == "husband_personal_2026-08-09-v2"
    assert computation.strategy_summary["active_plan_ids"] == ["ACT-S3"]
    assert computation.core_buy_materials[
        "recommended_monthly_core_buy_budget_jpy"
    ] is None
    assert computation.core_buy_materials["active_plan_product"] is None
    assert computation.sox_buy_signal["routine_additions_allowed"] is False
    assert computation.sox_buy_signal["rebalance_proposal_required"] is True
    assert "core_recurring_plan_conflicts_with_current_strategy" not in warning_codes
    assert "legacy_candidate_heuristic_review_only" in warning_codes
    assert computation.metadata["core_recurring_contributions_source"] == (
        "plans/recurring/versions/2026-08-09.yaml"
    )
    assert computation.metadata["candidate_policy_status"] == (
        "legacy_analytical_heuristic"
    )
    assert computation.metadata["tactical_cash_policy"] == {
        "enabled": False,
        "target_pct": 0.0,
    }
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
    assert story_targets["9444"]["sell_order_available"] is False
    assert story_targets["2353"]["user_disposition"] == (
        "sell_when_at_a_loss_preferred"
    )
    accounts = {
        holding.symbol: holding.account_type
        for holding in computation.snapshot.holdings
    }
    assert accounts["NISSEI_SOX_1"] == "特定口座（源泉徴収あり）"
    assert accounts["NISSEI_SOX_2"] == "NISA成長投資枠"
    assert accounts["9444"] == "特定口座（源泉徴収あり）"
    assert accounts["2353"] == "一般口座"
    assert computation.metadata["approved_review_constraints"][0]["statement"].startswith(
        "直接半導体エクスポージャーを総資産の12.00%以下"
    )
    assert computation.metadata["holding_execution_context"]["unreflected_orders"] is True
    assert computation.quarterly_rule_review_outputs[
        "cash_normalization_months_estimate"
    ] is None

    for holding in computation.snapshot.holdings:
        if holding.asset_class in {"core", "jun_core", "satellite_core", "satellite"} and holding.account_type is None:
            holding.account_type = "特定口座（源泉徴収あり）"
    computation.snapshot.snapshot_date = date(2026, 8, 9)
    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
        review_packet=build_current_review_packet(computation, ROOT),
    )
    assert "## 2. 入力データ" in prompt
    assert "total_assets_jpy: 40051911" in prompt
    assert "active_strategy_id" not in prompt
    assert "review_mode: on_demand_operational_review" in prompt
    assert "strategy_id: husband_personal_2026-08-09-v2" in prompt
    assert "サテライト比率、具体的な銘柄" in prompt
    assert "2026-07-25_cash_redeployment" not in prompt
    assert "recommended_monthly_core_buy_budget_jpy" not in prompt
    assert "12620505" not in prompt
    assert "routine_additions_allowed" not in prompt
    assert "inherited_pending_review" in prompt
    assert "security_story_review_targets:" in prompt
    assert "sell_order_available: false" in prompt
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

    for holding in computation.snapshot.holdings:
        if holding.asset_class in {"core", "jun_core", "satellite_core", "satellite"} and holding.account_type is None:
            holding.account_type = "特定口座（源泉徴収あり）"
    computation.snapshot.snapshot_date = date(2026, 8, 9)
    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
        review_packet=build_current_review_packet(computation, ROOT),
    )
    assert "active_plan_basis_planned_amount_jpy" not in prompt
    assert "active_plan_current_recalculated_amount_jpy" not in prompt
    assert "active_plan_amount_delta_jpy" not in prompt
    assert "12620505" not in prompt
    assert "12622664" not in prompt


def test_operational_review_projection_excludes_confirmed_post_snapshot_exits(
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
        project_current_state=True,
    )

    symbols = {holding.symbol for holding in computation.snapshot.holdings}
    story_symbols = {
        target["symbol"] for target in computation.security_story_targets
    }
    assert not {"7201", "9444", "2353", "SMH", "BTC", "ETH", "XRP"} & symbols
    assert not {"7201", "9444", "2353", "SMH"} & story_symbols
    assert "POST_SNAPSHOT_SALE_PROCEEDS" in symbols
    assert computation.snapshot.total_assets_jpy == Decimal("40027744")
    projection = computation.metadata["current_state_projection"]
    assert projection["provisional_sale_proceeds_jpy"] == 921_785
    assert projection["is_provisional"] is True


def test_current_operational_packet_does_not_reopen_approved_allocation_policy(
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
        project_current_state=True,
    )
    packet = build_current_review_packet(computation, ROOT)

    unknown_reasons = [
        str(item["reason"])
        for item in packet.unknown_information
    ]
    confirmed_statements = [
        str(item["statement"])
        for item in packet.confirmed_user_conditions
    ]

    assert packet.review_mode == "on_demand_operational_review"
    assert packet.approved_policy is not None
    approved_targets = {
        item["group"]: item["target_pct"]
        for item in packet.approved_policy["target_groups"]
    }
    assert approved_targets["broad_core"] == Decimal("0.825")
    assert approved_targets["active_hobby"] == Decimal("0.175")
    assert packet.allowed_quantitative_facts["cash_requirement_inputs"]["dip_buy_liquidity"] == {
        "status": "configured",
        "target_jpy": 0,
        "target_ratio": 0.0,
        "amount_calculation_policy": "none",
        "decision_owner": "user_confirmed_policy",
        "purchase_target": None,
        "activation_condition": None,
        "tranche_amount_jpy": 0,
        "tranche_count": 0,
        "minimum_balance_jpy": 0,
        "replenishment_method": None,
        "unknown_reason": "",
    }
    assert "戦術的な投資待機資金は設けない" in confirmed_statements
    assert "投資待機資金は市場下落時に使う手段であり、残高維持自体を目的にしない" not in confirmed_statements
    assert not any("投資待機資金" in reason for reason in unknown_reasons)
    assert not any("目標コア・サテライト比率" in reason for reason in unknown_reasons)
    assert not any("サテライトの目標比率" in reason for reason in unknown_reasons)

    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
        review_packet=packet,
    )
    assert "strategy_id: husband_personal_2026-08-09-v2" in prompt
    assert "group: broad_core\n    target_pct: 0.825" in prompt
    assert "group: active_hobby\n    target_pct: 0.175" in prompt
    assert "戦術的な投資待機資金は設けない" in prompt
    assert "未承認の投資待機資金比率" not in prompt
    assert "サテライトの目標比率、対象銘柄" not in prompt

    freshness = assess_snapshot_freshness(
        computation.snapshot.snapshot_date,
        requested_at=datetime(2026, 8, 10, 12, 0, tzinfo=UTC),
    )
    health_prompt = render_on_demand_assessment_prompt(
        computation,
        (ROOT / "prompts/templates/on_demand_assessment_template.md").read_text(
            encoding="utf-8"
        ),
        inventory_freshness=freshness,
    )
    assert "tactical_cash_policy_status: disabled" in health_prompt
    assert "reserve_status: unavailable" in health_prompt
    assert "selected_action: not_applicable" in health_prompt
    assert "市場下落時も使用案、発動条件、投入額を再提案しない" in health_prompt
    assert "使用案を必ず記録する" not in health_prompt
