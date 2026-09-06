from __future__ import annotations

from copy import deepcopy
from datetime import date
from decimal import Decimal
from pathlib import Path

import yaml
import pytest

from monthly_limit_order_review.context_records import load_financial_context
from monthly_limit_order_review.models import Holding
from monthly_limit_order_review.prompt_renderer import (
    render_chatgpt_prompt,
    render_review_generation_blocker,
)
from monthly_limit_order_review.review_packet import (
    build_cash_requirement_inputs,
    build_structured_cash_requirement_inputs,
    build_review_packet,
    extract_financial_review_context,
    extract_structured_financial_review_context,
)
from monthly_limit_order_review.utils import to_serializable

ROOT = Path(__file__).resolve().parents[1]


def complete_strategic_financial_context() -> dict:
    financial = deepcopy(load_financial_context(ROOT)["record"])
    financial["mortgage"]["household_total"]["fixed_or_variable"] = "variable"
    financial["strategic_profile"] = {
        "user_age": 40,
        "tax_residency": "Japan",
        "investment_horizon_years": 25,
        "planning_end_age": 90,
        "expected_withdrawal_start": "2051-01-01",
        "earliest_possible_asset_use_date": "2046-01-01",
        "planned_contributions": [{"amount_jpy": 100000, "frequency": "monthly"}],
        "expected_future_cash_flows": [{"type": "salary", "status": "expected"}],
        "human_capital_assumptions": {"employment_income_until_age": 65},
        "pension_and_other_future_assets": [{"type": "public_pension", "amount_status": "unknown"}],
        "objective_configuration": {
            "primary_objective": None,
            "objective_models": {
                "maximize_terminal_wealth": {
                    "horizon_years": 25,
                    "planned_contributions": [{"amount_jpy": 100000, "frequency": "monthly"}],
                    "return_basis": "real",
                    "statistic": "median",
                    "downside_quantile_pct": None,
                    "leverage_allowed": False,
                },
                "minimize_risk_for_required_return": {
                    "target_return_pct": 3,
                    "return_basis": "real",
                    "horizon_years": 25,
                    "success_probability_pct": 80,
                },
                "maximize_ex_ante_sharpe_ratio": {
                    "risk_free_rate_definition": "JPY 3-month government bill",
                    "return_basis": "nominal",
                    "horizon_years": 25,
                },
            },
        },
    }
    return financial


def test_review_packet_matches_closed_root_schema(sample_computation) -> None:
    packet = build_review_packet(
        sample_computation,
        financial_assumptions_text=(
            ROOT / "FINANCIAL_ASSUMPTIONS.md"
        ).read_text(encoding="utf-8"),
    )
    payload = to_serializable(packet)
    schema = yaml.safe_load(
        (ROOT / "schemas/review-packet.schema.yaml").read_text(encoding="utf-8")
    )

    assert set(payload) == set(schema["required"])
    assert schema["additionalProperties"] is False
    assert packet.packet_type == "on_demand_independent_review"
    assert packet.review_cadence == "on_demand"
    assert packet.review_mode == "on_demand_operational_review"
    assert packet.generation_status == "ready"
    assert packet.interaction_phase == "final_review"
    assert packet.approved_policy is not None
    assert packet.approved_policy["target_groups"]
    assert packet.output_contract["final_review"]["required_sections"][0] == "【推奨方針】"
    assert packet.capital_layers["prohibited_residual_rule"]
    assert packet.strategic_decision_objective["primary_objective"] is None
    assert packet.user_decision_preferences == {
        "wants_concrete_policy_recommendation": True,
        "wants_decision_based_on_investment_theory": True,
        "does_not_want_unrequested_evaluation_axes": True,
        "does_not_want_generic_theory_without_decision": True,
        "expects_independent_reviewer_to_select_one_base_case": True,
    }
    assert len(packet.output_contract["final_review"]["required_sections"]) == 7
    assert packet.output_contract["final_review"]["required_sections"][-1] == (
        "【次回レビュー時期】"
    )
    assert packet.output_contract["final_review"]["delivery"]["preferred"] == (
        "attach_review_response_yaml"
    )
    assert "thematic_fund_review" in packet.output_contract["inline_response_schema"]["$defs"]
    assert "array_schemas" not in packet.output_contract
    assert "response_skeleton" not in packet.output_contract
    assert any(rule["rule_id"] == "R-ID-001" for rule in packet.rule_registry)


def test_missing_account_type_blocks_prompt_and_emits_only_a_blocker(
    sample_computation,
) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.snapshot.holdings[1].account_type = None

    packet = build_review_packet(sample_computation)

    assert packet.generation_status == "blocked_missing_account_types"
    assert packet.account_type_gate["status"] == "blocked"
    with pytest.raises(ValueError, match="blocked_missing_account_types"):
        render_chatgpt_prompt(
            sample_computation,
            (ROOT / "prompts/templates/monthly_review_template.md").read_text(
                encoding="utf-8"
            ),
            review_packet=packet,
        )
    blocker = render_review_generation_blocker(packet)
    assert "ChatGPTへ渡すプロンプトではありません" in blocker
    assert sample_computation.snapshot.holdings[1].symbol in blocker


def test_review_packet_contains_only_observed_or_calculated_current_inputs(
    sample_computation,
) -> None:
    packet = build_review_packet(sample_computation)
    serialized = yaml.safe_dump(
        to_serializable(packet),
        allow_unicode=True,
        sort_keys=False,
    )

    assert "portfolio_totals" in serialized
    assert "market_references" in serialized
    assert "unknown_information" in serialized
    assert "active_strategy" not in serialized
    assert "active_plan" not in serialized
    assert "candidate_orders" not in serialized
    assert "recommended_monthly_core_buy_budget_jpy" not in serialized
    assert "screenshot_paths" not in serialized


def test_complete_strategic_inputs_enable_objective_confirmation_phase(
    sample_computation,
) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.metadata["review_mode"] = "strategic_policy_second_opinion"
    sample_computation.snapshot.snapshot_date = date(2026, 8, 9)
    financial = complete_strategic_financial_context()
    packet = build_review_packet(
        sample_computation,
        financial_context=financial,
        financial_context_source="financial/versions/test-complete.yaml",
    )

    assert packet.review_mode == "strategic_policy_second_opinion"
    assert packet.generation_status == "ready"
    assert packet.interaction_phase == "objective_confirmation"
    assert packet.missing_strategic_inputs == []
    prompt = render_chatgpt_prompt(
        sample_computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
        review_packet=packet,
    )
    assert "required_first_response:" in prompt
    assert "forbidden_in_first_response:" in prompt
    assert "web_research" in prompt
    assert "after_user_answer:" in prompt


def test_birth_date_is_used_to_calculate_age_at_snapshot(sample_computation) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.snapshot.snapshot_date = date(2026, 8, 9)
    financial = complete_strategic_financial_context()
    financial["strategic_profile"]["date_of_birth"] = "1992-01-07"

    packet = build_review_packet(
        sample_computation,
        financial_context=financial,
        financial_context_source="financial/versions/test-complete.yaml",
    )

    assert packet.strategic_required_inputs["date_of_birth"] == "1992-01-07"
    assert packet.strategic_required_inputs["user_age"] == 34
    assert packet.strategic_required_inputs["user_age_as_of"] == "2026-08-09"


def test_undecided_contribution_horizon_blocks_strategic_packet(
    sample_computation,
) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.metadata["review_mode"] = "strategic_policy_second_opinion"
    sample_computation.snapshot.snapshot_date = date(2026, 8, 9)
    financial = complete_strategic_financial_context()
    financial["strategic_profile"]["planned_contributions"] = {
        "status": "continuation_horizon_undecided",
        "observed_commitments_ref": "plans/recurring/current.yaml",
        "continuation_until": None,
    }

    packet = build_review_packet(
        sample_computation,
        financial_context=financial,
        financial_context_source="financial/versions/test-complete.yaml",
    )

    assert packet.generation_status == "blocked_missing_strategic_inputs"
    assert "planned_contributions" in packet.missing_strategic_inputs


def test_selected_objective_enables_final_review_phase(sample_computation) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.snapshot.snapshot_date = date(2026, 8, 9)
    financial = complete_strategic_financial_context()
    financial["strategic_profile"]["objective_configuration"][
        "primary_objective"
    ] = "maximize_ex_ante_sharpe_ratio"
    packet = build_review_packet(
        sample_computation,
        financial_context=financial,
        financial_context_source="financial/versions/test-complete.yaml",
    )

    assert packet.generation_status == "ready"
    assert packet.interaction_phase == "final_review"
    assert packet.strategic_decision_objective["primary_objective"] == (
        "maximize_ex_ante_sharpe_ratio"
    )


def test_review_packet_does_not_backfill_future_financial_assumptions(
    sample_computation,
) -> None:
    financial = deepcopy(load_financial_context(ROOT)["record"])
    financial["effective_from"] = "2027-01-01"
    packet = build_review_packet(
        sample_computation,
        financial_context=financial,
        financial_context_source="financial/versions/future-test.yaml",
    )

    assert not any(
        item["source"] == "financial/versions/future-test.yaml"
        for item in packet.confirmed_user_conditions
    )
    assert any(
        item["item"] == "financial_assumptions_at_review_date"
        for item in packet.unknown_information
    )


def test_review_packet_preserves_cross_account_same_product_meaning(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)
    computation.snapshot.holdings.extend(
        [
            Holding(
                symbol="NISSEI_SOX_1",
                name="ニッセイSOX指数インデックスファンド",
                account_type="NISA成長投資枠",
                asset_class="satellite_core",
                quantity=Decimal("100"),
                avg_cost=Decimal("10000"),
                current_price=Decimal("20000"),
                market_value_jpy=Decimal("2000000"),
                profit_loss_jpy=Decimal("1000000"),
                currency="JPY",
            ),
            Holding(
                symbol="NISSEI_SOX_2",
                name="ニッセイSOX指数インデックスファンド",
                account_type="特定口座（源泉徴収あり）",
                asset_class="satellite_core",
                quantity=Decimal("50"),
                avg_cost=Decimal("10000"),
                current_price=Decimal("20000"),
                market_value_jpy=Decimal("1000000"),
                profit_loss_jpy=Decimal("500000"),
                currency="JPY",
            ),
        ]
    )

    packet = build_review_packet(computation)
    groups = packet.allowed_quantitative_facts["same_product_account_groups"]
    sox_group = next(
        group
        for group in groups
        if group["symbols"] == ["NISSEI_SOX_1", "NISSEI_SOX_2"]
    )

    assert sox_group["account_separation_status"] == "separate_accounts_confirmed"
    assert sox_group["human_label"] == "ニッセイSOX指数インデックスファンド"
    assert all(member["human_label"] for member in sox_group["members"])
    thematic = packet.allowed_quantitative_facts["thematic_fund_review_targets"]
    assert thematic[0]["member_symbols"] == ["NISSEI_SOX_1", "NISSEI_SOX_2"]
    assert thematic[0]["story_review_scope"] == "product_and_underlying_index_once"


def test_cash_case_a_preserves_confirmed_minimum_without_inventing_expenses() -> None:
    financial = load_financial_context(ROOT)
    _, _, unknowns = extract_structured_financial_review_context(
        financial["record"],
        source=financial["source_path"],
    )

    cash = build_structured_cash_requirement_inputs(
        financial["record"],
        unknowns,
        portfolio_snapshot_total_assets_jpy=40_000_000,
    )

    assert cash["monthly_cash_flow"] == {
        "after_tax_social_insurance_mortgage_ideco_income_jpy": 374_171,
        "nisa_monthly_contribution_jpy": 100_000,
        "effective_monthly_disposable_income_jpy": 274_171,
        "monthly_essential_expenses_jpy": 250_000,
        "ordinary_month_balance": "approximately_zero",
        "bonus_income": {
            "take_home_reference_jpy": 2_000_000,
            "amount_qualifier": "approximately_slightly_below_reference",
            "annual_frequency": 1,
            "payment_months": [1],
            "certainty": "rough_user_estimate",
        },
        "income_values_are_not_expense_values": True,
    }
    assert cash["emergency_fund"]["target_jpy"] == 2_000_000
    assert cash["emergency_fund"]["status"] == "confirmed_user_target"
    assert cash["emergency_fund"]["spending_months"] == 8
    assert cash["dip_buy_liquidity"]["status"] == "configured"
    assert cash["dip_buy_liquidity"]["target_jpy"] == 0
    assert cash["dip_buy_liquidity"]["amount_calculation_policy"] == "none"
    assert cash["dip_buy_liquidity"]["decision_owner"] == "user_confirmed_policy"
    assert cash["result"]["minimum_confirmed_cash_jpy"] == 2_467_987
    assert cash["result"]["cash_target_status"] == "fully_calculable"
    assert cash["result"]["total_cash_target_jpy"] == 2_467_987


def test_current_policy_request_switches_packet_to_strategic_mode(
    sample_computation,
) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.snapshot.snapshot_date = date(2026, 8, 9)
    sample_computation.metadata["core_recurring_contributions_source"] = (
        "plans/recurring/versions/2026-03-01.yaml"
    )
    sample_computation.metadata["satellite_review_policy"] = {
        "satellites_allowed": True,
        "positive_satellite_allocation_required": True,
        "all_country_only_baseline_required": True,
        "target_pct": {"value": None, "status": "reviewer_to_propose"},
        "securities": {"value": None, "status": "reviewer_to_propose"},
    }
    financial = load_financial_context(ROOT)
    packet = build_review_packet(
        sample_computation,
        financial_context=financial["record"],
        financial_context_source=financial["source_path"],
    )

    assert packet.review_mode == "strategic_policy_second_opinion"
    assert packet.generation_status == "ready"
    assert packet.interaction_phase == "final_review"
    assert packet.missing_strategic_inputs == []
    assert packet.strategic_required_inputs["planning_end_age"] == 100
    assert packet.strategic_decision_objective["objective_models"][
        "minimize_risk_for_required_return"
    ]["offered"] is True
    assert packet.approved_policy is None
    assert packet.candidate_methodology["candidate_grid"][
        "equity_share_of_equity_bond_sleeve_pct"
    ] == list(range(0, 101, 10))
    assert packet.active_risk_policy["satellites_allowed"] is True
    assert packet.active_risk_policy["satellite_target_pct"]["status"] == (
        "reviewer_to_propose"
    )
    assert packet.active_risk_policy["satellite_securities"]["status"] == (
        "reviewer_to_propose"
    )
    assert "user_age" not in packet.missing_strategic_inputs
    assert packet.direct_semiconductor_limit["current_approved_constraint"][
        "limit_pct"
    ] == 12
    assert packet.direct_semiconductor_limit["proposed_future_policy"][
        "status"
    ] == "reviewer_to_propose"
    strategic_inputs = packet.strategic_required_inputs
    assert strategic_inputs["planned_contributions"]["observed_commitments_ref"] == (
        "plans/recurring/versions/2026-03-01.yaml"
    )
    assert not any(
        "750000" in str(item)
        for item in strategic_inputs["planned_contributions"]["constraints"]
    )
    assert strategic_inputs["planning_timeline"] == {
        **strategic_inputs["planning_timeline"],
        "model_start_date": "2026-08-09",
        "contribution_end_date": "2057-01-06",
        "first_withdrawal_date": "2057-01-07",
        "planned_retirement_date": "2057-01-07",
        "mortgage_repayment_end_date": "2064-09-27",
        "planning_end_date": "2092-01-07",
    }
    liability = strategic_inputs["liability_cash_flows"][0]
    assert liability["retirement_period"]["ends_on"] == "2064-09-27"
    assert liability["current_asset_offset_prohibited"] is True
    contribution_types = {
        row["contribution_type"]
        for row in strategic_inputs["contribution_reconciliation"]["rows"]
    }
    assert contribution_types == {
        "nisa_broad_equity_core",
        "ideco_broad_equity_core",
        "crypto_btc_eth",
    }
    assert packet.market_decline_rule["policy_design_sequence"][-1] == (
        "then_apply_locked_rule_to_market_data_at_research_cutoff"
    )
    assert all(
        item["status"] == "reviewer_to_derive"
        for item in packet.candidate_methodology["assumption_delegations"].values()
    )
    inline_schema = packet.output_contract["inline_response_schema"]
    candidate_required = set(inline_schema["$defs"]["candidate"]["required"])
    assert {
        "estimated_success_probability_pct",
        "required_success_probability_pct",
        "candidate_feasible",
        "constraint_failures",
        "calculation_status",
        "reason",
        "remediation",
    }.issubset(candidate_required)
    assert "static_reference_checks" in inline_schema["required"]
    assert inline_schema["$defs"]["quality_check"]["properties"]["status"][
        "enum"
    ] == ["pass", "fail", "not_verifiable", "not_applicable"]
    assert packet.candidate_methodology["tactical_liquidity_candidates_pct"] == [
        0,
        2.5,
        5,
        7.5,
        10,
    ]
    assert packet.candidate_methodology["other_pct_candidates"] == [0, 1, 2, 3, 5]
    assert packet.decision_stage_contract["required_order"] == [
        "strategic_policy_stage",
        "implementation_stage",
    ]
    assert packet.execution_capability_contract["fabrication_prohibited"] is True
    assert packet.validation_contract["numeric_tolerances"] == {
        "amount_jpy": 10,
        "percentage_points": 0.02,
        "monte_carlo_probability_pct_points": 0.01,
        "return_and_volatility_pct_points": 0.01,
    }
    assert {
        "data_as_of",
        "cutoff_compliance_status",
    }.issubset(inline_schema["$defs"]["source"]["required"])
    assert packet.validation_contract["semantic_validation_check_ids"]


def test_unset_satellite_parameters_alone_require_strategic_review(
    sample_computation,
) -> None:
    sample_computation = deepcopy(sample_computation)
    sample_computation.metadata["satellite_review_policy"] = {
        "target_pct": {"value": None, "status": "reviewer_to_propose"},
        "securities": {"value": None, "status": "reviewer_to_propose"},
    }

    packet = build_review_packet(sample_computation)

    assert packet.review_mode == "strategic_policy_second_opinion"


def test_cash_case_b_calculates_target_only_from_complete_inputs() -> None:
    statements = [
        "月間必須支出: 300,000円",
        "必要生活防衛月数: 6か月",
        "2年以内の確定支出: 1,000,000円",
        "相場下落時の買い増し用流動資金の目標額: 2,000,000円",
        "買付対象: 全世界株式",
        "発動条件: 株式市場が直近高値から20%下落",
        "各回の投入額: 500,000円",
        "投入回数: 4回",
        "最低残高: 1,800,000円",
        "補充方法: ボーナスから補充",
    ]
    conditions = [{"statement": statement} for statement in statements]

    cash = build_cash_requirement_inputs(conditions, [])

    assert cash["emergency_fund"]["target_jpy"] == 1_800_000
    assert cash["emergency_fund"]["spending_months"] == 6
    assert cash["near_term_confirmed_expenses"]["amount_jpy"] == 1_000_000
    assert cash["dip_buy_liquidity"]["status"] == "configured"
    assert cash["dip_buy_liquidity"]["target_jpy"] == 2_000_000
    assert cash["result"]["minimum_confirmed_cash_jpy"] == 2_800_000
    assert cash["result"]["cash_target_status"] == "fully_calculable"
    assert cash["result"]["total_cash_target_jpy"] == 4_800_000


def test_cash_target_can_be_calculated_before_deployment_rules_are_complete() -> None:
    statements = [
        "月間必須支出: 300,000円",
        "必要生活防衛月数: 6か月",
        "2年以内の確定支出: 1,000,000円",
        "相場下落時の買い増し用流動資金の目標額: 2,000,000円",
    ]
    conditions = [{"statement": statement} for statement in statements]

    cash = build_cash_requirement_inputs(conditions, [])

    assert cash["dip_buy_liquidity"]["status"] == (
        "target_calculated_deployment_unconfigured"
    )
    assert cash["dip_buy_liquidity"]["target_jpy"] == 2_000_000
    assert cash["result"]["cash_target_status"] == "fully_calculable"
    assert cash["result"]["total_cash_target_jpy"] == 4_800_000


def test_prompt_defines_unknown_as_a_valid_result_and_requests_feedback(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)
    computation.snapshot.snapshot_date = date(2026, 8, 9)
    financial = load_financial_context(ROOT)
    packet = build_review_packet(
        computation,
        financial_context=financial["record"],
        financial_context_source=financial["source_path"],
    )
    assert packet.generation_status == "ready"
    prompt = render_chatgpt_prompt(
        computation,
        (ROOT / "prompts/templates/monthly_review_template.md").read_text(
            encoding="utf-8"
        ),
        review_packet=packet,
    )
    assert "reviewer_to_derive" in prompt
    assert "financial_planning_model" in prompt
    assert "同じ値をユーザーへ再質問しない" in prompt
