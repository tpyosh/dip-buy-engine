from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from monthly_limit_order_review.storage import write_yaml
from monthly_limit_order_review.structured_review import (
    DECISION_QUALITY_CHECKS,
    REQUIRED_CAPABILITIES,
    SEMANTIC_VALIDATION_CHECKS,
    STATIC_REFERENCE_CHECKS,
    load_health_check_response,
    load_monthly_review_response,
)


CANONICAL_TACTICAL_REF = "strategic_policy_decision.tactical_liquidity_policy"


def source_payload() -> dict:
    return {
        "title": "Primary source",
        "publisher": "Example Publisher",
        "url": "https://example.com/source",
        "publication_date": "2026-08-01",
        "data_as_of": "2026-07-31",
        "accessed_at": "2026-08-02T12:00:00Z",
        "cutoff_compliance_status": "compliant",
        "source_type": "issuer_ir_or_filing",
        "claim_supported": "The stated factual claim",
    }


def quality_checks() -> list[dict]:
    return [
        {
            "check_id": check_id,
            "status": "pass",
            "evidence": f"decision_quality_checks[{check_id}] path and value validated",
            "reason": "validated",
            "remediation": "",
        }
        for check_id in sorted(DECISION_QUALITY_CHECKS)
    ]


def static_checks() -> list[dict]:
    return [
        {
            "check_id": check_id,
            "status": "pass",
            "evidence": f"static_reference_checks[{check_id}] path validated",
            "reason": "validated",
            "remediation": "",
        }
        for check_id in sorted(STATIC_REFERENCE_CHECKS)
    ]


def tactical_policy(*, proposed: bool = False) -> dict:
    return {
        "policy_id": "TL-2026-08",
        "status": "proposed" if proposed else "not_applicable",
        "reason": "review result" if proposed else "monthly mode",
        "remediation": "",
        "policy_basis_as_of": "2026-08-02" if proposed else None,
        "locked_before_market_evaluation": True if proposed else None,
        "initial_target_pct_of_total_assets": 7.5 if proposed else None,
        "target_jpy": 3_000_000 if proposed else None,
        "deployment_asset": "全世界株式" if proposed else None,
        "trigger_index": "MSCI ACWI" if proposed else None,
        "reference_high_definition": "終値ベースの過去最高値" if proposed else None,
        "decline_threshold_pct": 20 if proposed else None,
        "price_basis": "close" if proposed else None,
        "lookback_period": "all_available_history" if proposed else None,
        "fx_treatment": "JPY unhedged total return" if proposed else None,
        "tranches": 3 if proposed else None,
        "amount_per_tranche": "target_jpy / 3" if proposed else None,
        "minimum_balance_jpy": 0 if proposed else None,
        "refill_rule": "new contributions only" if proposed else None,
        "termination_rule": "fully deployed" if proposed else None,
        "policy_allocation_treatment": "outside policy denominator while undeployed" if proposed else None,
        "rationale": "review result" if proposed else "monthly mode",
        "source_refs": [],
        "requires_user_approval": True,
    }


def capability_gate() -> dict:
    return {
        "gate_status": "all_available",
        "evaluated_before_calculations": True,
        "capabilities": [
            {
                "capability_id": capability_id,
                "status": "available",
                "evidence": f"runtime verified for {capability_id}",
                "reason": "available",
                "missing_capability": [],
                "remediation": "",
            }
            for capability_id in sorted(REQUIRED_CAPABILITIES)
        ],
    }


def semantic_checks() -> list[dict]:
    return [
        {
            "check_id": check_id,
            "status": "pass",
            "evidence": f"semantic value reconciliation for {check_id}",
            "reason": "validated",
            "remediation": "",
            "observed_value": "verified",
            "expected_value": "verified",
            "difference": 0,
            "tolerance": 0,
        }
        for check_id in sorted(SEMANTIC_VALIDATION_CHECKS)
    ]


def deployment_review_payload(
    *,
    market_decline_status: str = "not_declining",
    considered: bool = False,
) -> dict:
    return {
        "policy_ref": CANONICAL_TACTICAL_REF,
        "policy_locked_before_market_evaluation": True,
        "reserve_status": "unknown",
        "market_decline_status": market_decline_status,
        "trigger_index_matches_deployment_target": True,
        "theme_or_sector_decline_used_as_trigger": False,
        "market_evidence": [],
        "use_option": {
            "considered": considered,
            "status": "conditional" if considered else "not_applicable",
            "reason": "comparison required" if considered else "not declining",
            "remediation": "",
            "target": "全世界株式" if considered else None,
            "amount_jpy": None,
            "formula": "available reserve / 3" if considered else "",
            "timing": "next trading day" if considered else None,
            "rationale": "comparison required" if considered else "not declining",
        },
        "selected_action": "hold" if considered else "not_applicable",
        "selection_rationale": "current comparison",
        "reserve_maintenance_is_objective": False,
    }


def response_payload() -> dict:
    policy = tactical_policy()
    return {
        "schema_version": 2,
        "artifact_type": "investment_review_response",
        "review_cadence": "on_demand",
        "review_mode": "on_demand_operational_review",
        "interaction_phase": "final_review",
        "review_target_month": "2026_08",
        "portfolio_snapshot_as_of": "2026-07-26",
        "market_reference_as_of": "2026-08-02",
        "packet_generated_at": "2026-08-02T12:00:00Z",
        "research_cutoff_at": "2026-08-02T12:00:00Z",
        "decision_date": "2026-08-02",
        "recommendation_window": {
            "start_at": "2026-08-02T12:00:00Z",
            "end_at": "2026-08-30T12:00:00Z",
            "window_length": 4,
            "window_unit": "weeks",
            "selection_rationale": "現在のデータ鮮度と実行可能性から4週間を選択",
            "confidence_boundary": "重大イベント発生時は早期再レビューする",
        },
        "next_review_recommendation": {
            "review_after_at": "2026-08-30",
            "interval_value": 4,
            "interval_unit": "weeks",
            "rationale": "推奨行動ウィンドウ終了時に再評価する",
            "early_review_triggers": ["重大な決算または制度変更"],
            "closing_sentence": "また4週間後（2026-08-30）に最新のスナップショットをもとにレビュー依頼を出してください。",
        },
        "review_completion_status": "complete",
        "execution_capability_gate": capability_gate(),
        "strategic_policy_decision": {
            "stage": "strategic_policy_stage",
            "status": "not_applicable",
            "reason": "monthly operational mode",
            "remediation": "",
            "objective": None,
            "updated_inputs": {
                "newly_confirmed": [],
                "superseded_assumptions": [],
                "decisions_now_unblocked": [],
                "decisions_still_blocked": [],
            },
            "financial_planning_model": {
                "status": "not_applicable",
                "reason": "monthly mode",
                "remediation": "",
                "return_basis": None,
                "current_age": None,
                "withdrawal_start_age": None,
                "planning_end_age": None,
                "retirement_spending_current_jpy_per_month": None,
                "retirement_spending_derivation": None,
                "public_pension_annual_current_jpy": None,
                "public_pension_estimation_method": None,
                "long_term_contribution_policy": {
                    "annual_net_contribution_jpy": None,
                    "contribution_end_age": None,
                    "contribution_end_date": None,
                    "allocation_rule": None,
                    "rationale": None,
                },
                "contribution_reconciliation": [],
                "planning_timeline": None,
                "liability_cash_flows": [],
                "inheritance_included_in_base_case": None,
                "inheritance_base_case_jpy": None,
                "inheritance_treatment": None,
                "terminal_asset_floor_current_jpy": None,
                "success_probability_pct": None,
                "success_probability_rationale": None,
                "target_return_pct": None,
                "target_return_formula": None,
                "required_return_calculation": {"status": "not_applicable", "reason": "monthly mode", "missing_capability": [], "remediation": ""},
                "success_probability_calculation": {"status": "not_applicable", "reason": "monthly mode", "missing_capability": [], "remediation": ""},
                "sensitivity_cases": [],
                "source_refs": [],
            },
            "recommended_policy": None,
            "policy_allocation_within_investable_portfolio": None,
            "household_total_asset_allocation": None,
            "tactical_liquidity_policy": policy,
            "active_risk_policy": None,
            "direct_semiconductor_limit": {
                "current_approved_constraint": {
                    "policy_id": "approved_direct_semiconductor_max_pct",
                    "status": "hard_constraint",
                    "limit_pct": 12,
                    "denominator": "household_total_assets_jpy",
                    "approved": True,
                    "rationale": "approved current policy",
                },
                "proposed_future_policy": {
                    "policy_id": None,
                    "status": "not_applicable",
                    "limit_pct": None,
                    "denominator": "household_total_assets_jpy",
                    "approved": False,
                    "rationale": "monthly mode",
                },
                "priority": "strictest applicable cap",
            },
            "tactical_liquidity_candidate_comparison": [],
            "crypto_contribution_option_comparison": [],
            "other_allocation_candidate_comparison": [],
            "candidate_methodology": None,
            "candidate_comparison": [],
        },
        "implementation_decision": {
            "stage": "implementation_stage",
            "status": "complete",
            "reason": "monthly implementation review completed",
            "remediation": "",
            "strategic_policy_ref": "strategic_policy_decision.recommended_policy",
            "strategic_policy_status_at_start": "not_applicable",
            "strategy_locked_before_market_evaluation": True,
            "product_decision_refs": [],
            "tactical_deployment_ref": "dip_buy_liquidity_deployment_review",
            "before_after_allocation_ref": "before_after_allocation",
        },
        "account_lot_execution": {
            "status": "complete",
            "reason": "no proposed account-lot orders",
            "remediation": "",
            "implementation_decision_ref": "implementation_decision",
            "missing_information": [],
            "executable_order_proposal_ids": [],
            "blocked_order_proposal_ids": [],
        },
        "decision_axes": {
            "user_confirmed_facts": [],
            "packet_confirmed_facts": [],
            "empirical_market_evidence": [],
            "mathematically_derived_constraints": [],
            "reviewer_assumptions": [],
        },
        "empirical_evidence": [],
        "human_summary": {"overall_assessment": "watch", "priority_actions": []},
        "cash_assessment": {
            "emergency_fund_target_jpy": 2_000_000,
            "emergency_fund_status": "confirmed_user_target",
            "monthly_essential_expenses_jpy": None,
            "spending_months": None,
            "near_term_confirmed_expenses_jpy": None,
            "contingency_reserve_jpy": None,
            "tactical_liquidity_policy_ref": CANONICAL_TACTICAL_REF,
            "dip_buy_liquidity_status": "unconfigured",
            "minimum_confirmed_cash_jpy": 2_000_000,
            "maximum_calculable_cash_jpy": None,
            "total_cash_target_status": "confirmed_minimum_only",
            "total_cash_target_jpy": None,
            "calculation_reason": "tactical target unknown",
            "remediation": "derive tactical policy",
            "derivation_notes": [],
        },
        "dip_buy_liquidity_deployment_review": deployment_review_payload(),
        "security_story_reviews": [
            {
                "symbol": "MSFT",
                "evaluated": True,
                "thesis_status": "inherited_pending_review",
                "provisional_story": None,
                "material_facts": [],
                "story_health": "watch",
                "invalidation_signals": [],
                "decision": "hold",
                "decision_rationale": "primary sources checked",
                "next_review_triggers": [],
                "sources": [],
            }
        ],
        "thematic_fund_reviews": [],
        "before_after_allocation": [],
        "account_tax_comparisons": [],
        "decisions": {
            "policy_refs": [policy["policy_id"]],
            "portfolio_diagnosis": [],
            "rule_refs": ["R-CASH-001"],
            "order_proposals": [],
            "actions": [],
            "new_asset_purchase_conclusion": {
                "status": "no_new_asset_purchase",
                "rationale": "no new asset purchase is proposed in the base fixture",
                "action_ids": [],
            },
        },
        "codex_handoff": {
            "execution_checks": [],
            "prompt_feedback": [],
            "repository_changes": {"must": [], "should": [], "nice_to_have": []},
        },
        "decision_quality_checks": quality_checks(),
        "static_reference_checks": static_checks(),
        "validation_tolerances": {
            "rounding_tolerance_jpy": 10,
            "rounding_tolerance_pct_points": 0.02,
            "monte_carlo_probability_tolerance_pct_points": 0.01,
            "return_volatility_tolerance_pct_points": 0.01,
        },
        "rounding_reconciliation": {
            "rounding_tolerance_jpy": 10,
            "rounding_tolerance_pct_points": 0.02,
            "rounding_residual_jpy": 3,
            "rounding_residual_pct_points": 0.01,
            "rounding_residual_treatment": "within_tolerance_recorded",
            "evidence": "snapshot holding sum differs by 3 JPY",
        },
        "semantic_validation_checks": semantic_checks(),
    }


def make_strategic(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload["review_mode"] = "strategic_policy_second_opinion"
    decision = payload["strategic_policy_decision"]
    decision["status"] = "complete"
    decision["reason"] = "completed strategic policy comparison"
    decision["remediation"] = ""
    payload["review_completion_status"] = "complete_with_execution_blocks"
    payload["implementation_decision"].update(
        {
            "status": "complete",
            "reason": "mapped from completed strategic policy",
            "strategic_policy_status_at_start": "complete",
            "strategy_locked_before_market_evaluation": True,
        }
    )
    payload["account_lot_execution"].update(
        {
            "status": "blocked",
            "reason": "lot details missing",
            "remediation": "confirm lots",
            "missing_information": ["account lot details"],
        }
    )
    decision["objective"] = "maximize_ex_ante_sharpe_ratio"
    decision["financial_planning_model"] = {
        "status": "complete",
        "reason": "derived from packet and primary sources",
        "remediation": "",
        "return_basis": "real",
        "current_age": 34,
        "withdrawal_start_age": 65,
        "planning_end_age": 100,
        "retirement_spending_current_jpy_per_month": 300000,
        "retirement_spending_derivation": "current spending with cited adjustment",
        "public_pension_annual_current_jpy": 1800000,
        "public_pension_estimation_method": "official formula estimate",
        "long_term_contribution_policy": {
            "annual_net_contribution_jpy": 1800000,
            "contribution_end_age": 65,
            "contribution_end_date": "2057-01-06",
            "allocation_rule": "tax-advantaged core first",
            "rationale": "cash-flow-based sustainable contribution",
        },
        "contribution_reconciliation": [
            {
                "contribution_type": "nisa",
                "periodic_amount_jpy": 100000,
                "period": "monthly",
                "annualized_amount_jpy": 1200000,
                "funding_source": "salary",
                "already_deducted_from_reported_current_income": False,
                "included_in_model": True,
                "capital_source_classification": "new_savings",
                "continuation_end_date": "2057-01-06",
                "uncertainty_status": "observed_setting",
                "rationale": "reconciled",
            }
        ],
        "planning_timeline": {
            "model_start_date": "2026-07-26",
            "contribution_end_date": "2057-01-06",
            "first_withdrawal_date": "2057-01-07",
            "planned_retirement_date": "2057-01-07",
            "public_pension_start_date": "2057-01-07",
            "mortgage_repayment_end_date": "2064-09-27",
            "planning_end_date": "2092-01-07",
            "model_period": "monthly",
            "overlap_check": "pass",
        },
        "liability_cash_flows": [
            {
                "liability_id": "mortgage",
                "treatment": "future_repayment_cash_flows",
                "bank_document_values_are_authoritative": True,
                "generic_amortization_recalculation_performed": False,
                "arithmetic_mismatch_used_for_warning_or_block": False,
                "balance_as_of": "2026-07-27",
                "outstanding_principal_jpy": 31260343,
                "first_payment_date": "2026-08-27",
                "last_payment_date": "2064-09-27",
                "base_case_monthly_payment_jpy": 74171,
                "base_case_annual_interest_rate": 0.0112,
                "active_period_double_count_rule": "do not subtract from after-mortgage income",
                "retirement_period_treatment": "separate cash flow until maturity",
                "rate_sensitivity": ["+1pp", "+2pp"],
                "source_refs": ["packet mortgage schedule"],
            }
        ],
        "inheritance_included_in_base_case": False,
        "inheritance_base_case_jpy": 0,
        "inheritance_treatment": "excluded due timing and share uncertainty",
        "terminal_asset_floor_current_jpy": 10000000,
        "success_probability_pct": 90,
        "success_probability_rationale": "retirement planning evidence",
        "target_return_pct": 2.5,
        "target_return_formula": "real IRR of modeled contributions and withdrawals",
        "required_return_calculation": {
            "status": "calculated",
            "reason": "root found",
            "missing_capability": [],
            "remediation": "",
            "currency_and_price_basis": "snapshot_date_current_JPY",
            "tax_cost_basis": "product_cost_in_return_personal_tax_in_cash_flows",
            "period": "monthly",
            "cash_flow_timing": "end of month",
            "formula": "B_t=B_(t-1)*(1+r)^(1/12)+F_t",
            "root_finding_method": "bisection",
            "search_interval_pct": [-99, 100],
            "tolerance_pct_points": 0.0001,
            "required_real_return_pct": 2.5,
        },
        "success_probability_calculation": {
            "status": "calculated",
            "reason": "simulation complete",
            "missing_capability": [],
            "remediation": "",
            "method": "parametric_multivariate_monthly_log_return_monte_carlo",
            "period": "monthly",
            "trials": 50000,
            "random_seed": 20260802,
            "return_distribution": "correlated log returns",
            "expected_returns_pct": {"total_equity": 5, "bond": 2, "other": 0},
            "volatilities_pct": {"total_equity": 15, "bond": 5, "other": 0},
            "correlation_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "inflation_treatment": "current JPY",
            "cash_flow_timing": "end of month",
            "rebalancing": "annual",
            "terminal_floor_jpy": 10000000,
            "success_definition": "never negative and terminal floor met",
            "estimated_probability_pct": 90,
        },
        "sensitivity_cases": ["lower pension", "higher spending"],
        "source_refs": ["E-FP-001"],
    }
    decision["recommended_policy"] = {
        "policy_id": "SAA-2026-08",
        "investable_equity_pct": 80,
        "investable_bond_pct": 20,
        "investable_other_pct": 0,
        "core_policy": "global equity core",
        "satellite_policy": "allowed within caps",
        "rebalancing_rule": "annual",
        "transition_deadline": "2027-03-31",
    }
    decision["policy_allocation_within_investable_portfolio"] = {
        "equity_pct": 80,
        "bond_pct": 20,
        "other_pct": 0,
    }
    decision["household_total_asset_allocation"] = {
        "equity_pct": 70,
        "bond_pct": 17.5,
        "household_reserve_pct": 5,
        "tactical_liquidity_pct": 7.5,
        "excluded_other_pct": 0,
    }
    decision["tactical_liquidity_policy"] = tactical_policy(proposed=True)
    decision["tactical_liquidity_candidate_comparison"] = [
        {
            "candidate_id": f"TL-{ratio}",
            "target_pct_of_household_total_assets": ratio,
            "denominator": "household_total_assets_jpy",
            "household_reserve_separate": True,
            "long_term_investable_asset_reduction_jpy": ratio * 400_000,
            "required_real_return_impact_pct_points": ratio * 0.01,
            "success_probability_impact_pct_points": -ratio * 0.02,
            "deployable_amount_jpy": ratio * 400_000,
            "expected_return_drag_pct_points": ratio * 0.01,
            "implementation_complexity": "low" if ratio == 0 else "moderate",
            "replenishment_feasibility": "feasible from realized surplus",
            "candidate_feasible": True,
            "calculation_status": "calculated",
            "reason": "finite-grid comparison completed",
            "missing_capability": [],
            "remediation": "",
            "selected": ratio == 7.5,
        }
        for ratio in [0, 2.5, 5, 7.5, 10]
    ]
    crypto_options = [
        "stop_new_contributions_and_exclude_unknown_existing_balance",
        "continue_only_within_realized_surplus_such_as_bonus",
        "continue_current_contributions_and_disclose_cash_flow_and_success_probability_impact",
    ]
    decision["crypto_contribution_option_comparison"] = [
        {
            "option_id": f"CRYPTO-{index}",
            "policy": option,
            "current_crypto_balance_jpy": None,
            "ordinary_month_cash_flow_impact_jpy": 0 if index < 2 else -17333.33,
            "success_probability_impact_pct_points": 0 if index == 0 else -0.1 * index,
            "funding_source_treatment": "does not treat unknown funding as confirmed savings",
            "calculation_status": "calculated",
            "reason": "cash-flow comparison completed",
            "missing_capability": [],
            "remediation": "",
            "selected": index == 0,
        }
        for index, option in enumerate(crypto_options)
    ]
    decision["other_allocation_candidate_comparison"] = [
        {
            "candidate_id": f"OTHER-{ratio}",
            "other_pct": ratio,
            "crypto_contribution_option_ref": "CRYPTO-0",
            "current_crypto_balance_jpy": None,
            "ordinary_month_cash_flow_consistent": True,
            "required_success_probability_maintained": True,
            "success_probability_impact_pct_points": -ratio * 0.01,
            "expected_return_impact_pct_points": ratio * 0.01,
            "diversification_benefit": "estimated on common assumptions",
            "incremental_risk": "estimated on common assumptions",
            "funding_source_consistency": "no unknown funding counted as savings",
            "candidate_feasible": True,
            "calculation_status": "calculated",
            "reason": "finite-grid comparison completed",
            "missing_capability": [],
            "remediation": "",
            "selected": ratio == 0,
        }
        for ratio in [0, 1, 2, 3, 5]
    ]
    payload["decisions"]["policy_refs"] = [
        decision["tactical_liquidity_policy"]["policy_id"]
    ]
    decision["active_risk_policy"] = {
        "policy_id": "AR-2026-08",
        "satellites_allowed": True,
        "satellite_target_pct_of_investable_portfolio": 20,
        "selected_satellite_securities": [
            {
                "symbol": "CIBR",
                "asset_name": "First Trust Nasdaq Cybersecurity ETF",
                "role": "cybersecurity satellite",
                "target_pct_of_investable_portfolio": 20,
                "rationale": "test fixture",
            }
        ],
        "all_country_only_baseline_compared": True,
        "selection_rationale": "positive satellite allocation selected after baseline comparison",
        "total_satellite_cap_pct": 20,
        "single_theme_cap_pct": 10,
        "single_security_cap_pct": 20,
        "exceptions": [],
    }
    decision["candidate_methodology"] = {
        "selection_sequence": [
            "compare_and_select_tactical_liquidity",
            "compare_crypto_contribution_options_and_select_other_pct",
            "compare_all_11_equity_bond_sleeve_candidates",
            "run_sensitivity_around_selected_results",
        ],
        "tactical_liquidity_candidate_grid": [0, 2.5, 5, 7.5, 10],
        "other_pct_candidate_grid": [0, 1, 2, 3, 5],
        "crypto_contribution_option_grid": crypto_options,
        "global_equity_index": "MSCI ACWI",
        "bond_index": "Bloomberg Global Aggregate JPY Hedged",
        "bond_instrument_type": "JPY-hedged investment-grade aggregate bonds",
        "bond_currency": "JPY",
        "bond_fx_hedge_policy": "hedged to JPY",
        "estimation_period": "2000-01-01/2025-12-31",
        "assumptions_as_of": "2026-08-02",
        "inflation_assumption_pct": 2,
        "return_basis": "pre-tax after-cost nominal and real",
        "tax_cost_treatment": "pre-tax returns net of fund costs",
        "major_drawdown_definition": "monthly peak-to-trough total return",
        "rebalancing_frequency": "annual",
        "candidate_grid": list(range(0, 101, 10)),
        "other_pct_common_base_case": 0,
        "assumption_derivations": [
            {
                "parameter_id": f"P-{index}",
                "status": "derived",
                "value": "base case",
                "decision_owner": "independent_on_demand_reviewer",
                "selection_criteria": "common basis",
                "source_refs": ["E-FP-001"],
                "base_case": "selected",
                "sensitivity": "documented",
            }
            for index in range(11)
        ],
        "required_return_method": "monthly current-JPY bisection",
        "success_probability_method": "50,000-trial seeded monthly Monte Carlo",
        "range_rationale": "standard equity-dominant range for this comparison",
    }
    decision["candidate_comparison"] = [
        {
            "candidate_id": f"SLEEVE_EQ{equity}",
            "sleeve_equity_pct": equity,
            "total_equity_pct": equity,
            "bond_pct": 100 - equity,
            "other_pct": 0,
            "expected_nominal_return_pct": 5,
            "expected_real_return_pct": 3,
            "expected_volatility_pct": 10,
            "equity_bond_correlation": 0,
            "estimated_major_drawdown_pct": -30,
            "estimated_success_probability_pct": 90,
            "required_success_probability_pct": 85,
            "candidate_feasible": True,
            "constraint_failures": [],
            "primary_objective_fit_value": 0.3,
            "primary_objective_fit_formula": "(return-risk_free)/volatility",
            "assumptions_ref": "candidate_methodology",
            "calculation_status": "calculated",
            "reason": "calculated",
            "missing_capability": [],
            "remediation": "",
            "selected": equity == 80,
        }
        for equity in range(0, 101, 10)
    ]
    decision["direct_semiconductor_limit"]["proposed_future_policy"].update(
        {
            "policy_id": "SEMICON-PROPOSED-2026-08",
            "status": "proposed",
            "limit_pct": 10,
            "rationale": "future proposal, not approved",
        }
    )
    return payload


def make_blocked_strategic(payload: dict) -> dict:
    payload = make_strategic(payload)
    decision = payload["strategic_policy_decision"]
    decision["status"] = "blocked"
    decision["reason"] = "candidate calculations could not be completed before submission"
    decision["remediation"] = "provide cutoff-compliant capital market inputs and rerun"
    payload["review_completion_status"] = "blocked"
    payload["implementation_decision"].update(
        {
            "status": "not_applicable",
            "reason": "strategic policy is blocked",
            "remediation": "complete the strategic policy first",
            "strategic_policy_status_at_start": "blocked",
            "strategy_locked_before_market_evaluation": None,
        }
    )
    payload["account_lot_execution"].update(
        {
            "status": "not_applicable",
            "reason": "implementation stage did not start",
            "remediation": "complete the strategic policy first",
            "missing_information": [],
        }
    )
    blocked_component = {
        "status": "blocked",
        "reason": decision["reason"],
        "remediation": decision["remediation"],
    }
    decision["financial_planning_model"] = deepcopy(
        response_payload()["strategic_policy_decision"]["financial_planning_model"]
    )
    decision["financial_planning_model"].update(blocked_component)
    decision["recommended_policy"] = deepcopy(blocked_component)
    decision["policy_allocation_within_investable_portfolio"] = deepcopy(
        blocked_component
    )
    decision["household_total_asset_allocation"] = deepcopy(blocked_component)
    decision["active_risk_policy"] = deepcopy(blocked_component)
    decision["candidate_methodology"] = deepcopy(blocked_component)
    decision["candidate_comparison"] = [
        {
            "candidate_id": f"SLEEVE_EQ{equity}",
            "sleeve_equity_pct": equity,
            "total_equity_pct": None,
            "bond_pct": None,
            "other_pct": None,
            "expected_nominal_return_pct": None,
            "expected_real_return_pct": None,
            "expected_volatility_pct": None,
            "equity_bond_correlation": None,
            "estimated_major_drawdown_pct": None,
            "estimated_success_probability_pct": None,
            "required_success_probability_pct": None,
            "candidate_feasible": None,
            "constraint_failures": ["cutoff-compliant assumptions unavailable"],
            "primary_objective_fit_value": None,
            "primary_objective_fit_formula": None,
            "assumptions_ref": None,
            "calculation_status": "not_calculable",
            "reason": decision["reason"],
            "missing_capability": ["multivariate_monthly_monte_carlo"],
            "remediation": decision["remediation"],
            "selected": False,
        }
        for equity in range(0, 101, 10)
    ]
    payload["decision_quality_checks"][0] = {
        "check_id": sorted(DECISION_QUALITY_CHECKS)[0],
        "status": "fail",
        "evidence": decision["reason"],
        "reason": decision["reason"],
        "remediation": decision["remediation"],
    }
    return payload


def load(path: Path, *, expected_themes: set[str] | None = None):
    return load_monthly_review_response(
        path,
        expected_month="2026_08",
        expected_security_symbols={"MSFT"},
        expected_thematic_member_symbols=expected_themes,
    )


def test_monthly_yaml_is_machine_readable_codex_input(tmp_path: Path) -> None:
    payload, feedback = load(write_yaml(tmp_path / "review_response.yaml", response_payload()))
    assert payload["schema_version"] == 2
    assert feedback.portfolio_diagnosis == []


def test_recommendation_window_must_start_at_request_time(tmp_path: Path) -> None:
    payload = response_payload()
    payload["recommendation_window"]["start_at"] = "2026-08-03T12:00:00Z"

    with pytest.raises(
        ValueError,
        match="recommendation_window.start_at must equal packet_generated_at",
    ):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_next_review_cannot_precede_recommendation_window_end(tmp_path: Path) -> None:
    payload = response_payload()
    payload["next_review_recommendation"].update(
        {
            "review_after_at": "2026-08-23",
            "interval_value": 3,
            "closing_sentence": "また3週間後（2026-08-23）に最新のスナップショットをもとにレビュー依頼を出してください。",
        }
    )

    with pytest.raises(
        ValueError,
        match="next_review_recommendation.review_after_at must not be before",
    ):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_strategic_mode_requires_one_complete_policy(tmp_path: Path) -> None:
    payload, _ = load(write_yaml(tmp_path / "review_response.yaml", make_strategic(response_payload())))
    assert payload["strategic_policy_decision"]["status"] == "complete"


def test_strategic_satellite_security_weights_must_match_target(
    tmp_path: Path,
) -> None:
    payload = make_strategic(response_payload())
    payload["strategic_policy_decision"]["active_risk_policy"][
        "selected_satellite_securities"
    ][0]["target_pct_of_investable_portfolio"] = 10

    with pytest.raises(ValueError, match="weights must reconcile"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_blocked_strategic_response_is_schema_valid_and_does_not_fabricate_candidates(
    tmp_path: Path,
) -> None:
    payload, _ = load(
        write_yaml(
            tmp_path / "blocked_review_response.yaml",
            make_blocked_strategic(response_payload()),
        )
    )
    decision = payload["strategic_policy_decision"]
    assert decision["status"] == "blocked"
    assert decision["recommended_policy"]["status"] == "blocked"
    assert len(decision["candidate_comparison"]) == 11
    assert not any(item["selected"] for item in decision["candidate_comparison"])


def test_blocked_response_does_not_force_quality_checks_to_fail(tmp_path: Path) -> None:
    payload = make_blocked_strategic(response_payload())
    payload["decision_quality_checks"] = quality_checks()
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["review_completion_status"] == "blocked"


def test_strategic_investable_allocation_must_total_100(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    payload["strategic_policy_decision"]["policy_allocation_within_investable_portfolio"]["bond_pct"] = 10
    with pytest.raises(ValueError, match="must total 100"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_minimum_risk_requires_exhaustive_zero_to_one_hundred_grid(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    decision = payload["strategic_policy_decision"]
    decision["objective"] = "minimize_risk_for_required_return"
    decision["candidate_comparison"].pop(0)
    with pytest.raises(ValueError, match="exhaustive 0-100 grid"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_candidate_ids_must_be_unique(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    candidates = payload["strategic_policy_decision"]["candidate_comparison"]
    candidates[1]["candidate_id"] = candidates[0]["candidate_id"]
    with pytest.raises(ValueError, match="duplicate candidate_id"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_candidate_comparison_rejects_multiple_selected_rows(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    candidates = payload["strategic_policy_decision"]["candidate_comparison"]
    candidates[7]["selected"] = True
    with pytest.raises(ValueError, match="must not select multiple"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_candidate_other_pct_must_match_common_base_case(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    candidate = payload["strategic_policy_decision"]["candidate_comparison"][5]
    candidate.update({"total_equity_pct": 49.5, "bond_pct": 49.5, "other_pct": 1})
    with pytest.raises(ValueError, match="other_pct must equal"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_candidate_weights_must_match_canonical_formulas(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    candidate = payload["strategic_policy_decision"]["candidate_comparison"][5]
    candidate.update({"total_equity_pct": 40, "bond_pct": 60, "other_pct": 0})
    with pytest.raises(ValueError, match="total_equity_pct violates"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_final_review_quality_check_can_be_not_verifiable(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decision_quality_checks"][0].update(
        {
            "status": "not_verifiable",
            "evidence": "",
            "reason": "source data unavailable",
            "remediation": "provide the source data",
        }
    )
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["decision_quality_checks"][0]["status"] == "not_verifiable"


def test_quality_check_pass_requires_concrete_evidence(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decision_quality_checks"][0]["evidence"] = ""
    with pytest.raises(ValueError, match="pass requires concrete evidence"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_strategy_must_be_complete_before_strategic_implementation(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    payload["strategic_policy_decision"]["status"] = "blocked"
    payload["strategic_policy_decision"]["remediation"] = "rerun calculations"
    with pytest.raises(ValueError, match="implementation cannot precede"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_tactical_liquidity_grid_must_be_complete(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    payload["strategic_policy_decision"][
        "tactical_liquidity_candidate_comparison"
    ].pop()
    with pytest.raises(ValueError, match="complete finite candidate grid"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_rounding_residual_within_tolerance_is_not_failed(tmp_path: Path) -> None:
    payload = response_payload()
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert (
        loaded["rounding_reconciliation"]["rounding_residual_treatment"]
        == "within_tolerance_recorded"
    )


def test_rounding_residual_over_tolerance_cannot_be_marked_within(tmp_path: Path) -> None:
    payload = response_payload()
    payload["rounding_reconciliation"]["rounding_residual_jpy"] = 11
    with pytest.raises(ValueError, match="exceeds the explicit tolerance"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_mortgage_values_are_not_generically_revalidated(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    liability = payload["strategic_policy_decision"]["financial_planning_model"][
        "liability_cash_flows"
    ][0]
    liability["generic_amortization_recalculation_performed"] = True
    with pytest.raises(ValueError, match="revalidation is prohibited"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_semantic_check_ids_must_be_unique(tmp_path: Path) -> None:
    payload = response_payload()
    payload["semantic_validation_checks"][1]["check_id"] = payload[
        "semantic_validation_checks"
    ][0]["check_id"]
    with pytest.raises(ValueError, match="duplicate check_id"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_partial_capability_gate_does_not_abandon_unrelated_review(tmp_path: Path) -> None:
    payload = response_payload()
    monte_carlo = next(
        item
        for item in payload["execution_capability_gate"]["capabilities"]
        if item["capability_id"] == "multivariate_monthly_monte_carlo"
    )
    monte_carlo.update(
        {
            "status": "unavailable",
            "evidence": "runtime check failed",
            "reason": "simulation runtime unavailable",
            "missing_capability": ["multivariate_monthly_monte_carlo"],
            "remediation": "rerun in a numerical environment",
        }
    )
    payload["execution_capability_gate"]["gate_status"] = "partial"
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["human_summary"]["overall_assessment"] == "watch"


def test_missing_security_story_trace_is_rejected(tmp_path: Path) -> None:
    payload = response_payload()
    payload["security_story_reviews"] = []
    with pytest.raises(ValueError, match="coverage mismatch"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_cash_values_cannot_override_confirmed_packet(tmp_path: Path) -> None:
    payload = response_payload()
    payload["cash_assessment"]["emergency_fund_target_jpy"] = 8_000_000
    context = {
        "emergency_fund": {"target_jpy": 2_000_000, "status": "confirmed_user_target", "monthly_essential_expenses_jpy": None, "spending_months": None},
        "near_term_confirmed_expenses": {"amount_jpy": None},
        "contingency_reserve": {"amount_jpy": None},
        "dip_buy_liquidity": {"status": "unconfigured", "target_jpy": None},
        "result": {"minimum_confirmed_cash_jpy": 2_000_000, "maximum_cash_target_jpy": None, "cash_target_status": "confirmed_minimum_only", "total_cash_target_jpy": None},
    }
    path = write_yaml(tmp_path / "review_response.yaml", payload)
    with pytest.raises(ValueError, match="emergency_fund_target_jpy conflicts"):
        load_monthly_review_response(path, expected_month="2026_08", expected_security_symbols={"MSFT"}, expected_cash_context=context)


def test_spending_months_requires_essential_expenses(tmp_path: Path) -> None:
    payload = response_payload()
    payload["cash_assessment"]["spending_months"] = 8
    with pytest.raises(ValueError, match="spending_months"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def action_payload(*, status: str) -> dict:
    return {
        "action_id": "A-1",
        "action_scope": "existing_holding",
        "action_level": "account_lot_order",
        "symbol": "MSFT",
        "asset_name": "Microsoft",
        "holding_status": "held",
        "side": "hold",
        "account_type": "特定口座（源泉徴収あり）",
        "execution_method": "retain the current lot without placing an order",
        "status": status,
        "reason": "assumption dependent",
        "remediation": "confirm inputs",
        "description": "cash to global equity",
        "source": "cash",
        "destination": "global equity",
        "quantity": 1,
        "amount_jpy": 1,
        "formula": "assumed ratio",
        "inputs": [{"name": "ratio", "value": 1, "source_type": "explicit_assumption", "source_ref": "reviewer assumption"}],
        "policy_refs": ["approved_direct_semiconductor_max_pct"],
        "assumption_independent_direction": False,
        "confirmed_conditions_consistent": True,
        "max_impact_if_assumptions_wrong_jpy": 1,
        "timing": "this month",
        "rationale": "assumption-dependent",
        "requires_user_approval": True,
    }


def test_any_assumption_dependent_executable_trade_is_rejected(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decisions"]["actions"] = [action_payload(status="executable")]
    with pytest.raises(ValueError, match="explicit assumption"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_assumption_dependent_trade_may_be_conditional(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decisions"]["actions"] = [action_payload(status="conditional")]
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["decisions"]["actions"][0]["status"] == "conditional"


def test_review_actions_must_cover_every_current_holding(tmp_path: Path) -> None:
    payload = response_payload()
    with pytest.raises(ValueError, match="existing holding coverage mismatch"):
        load_monthly_review_response(
            write_yaml(tmp_path / "review_response.yaml", payload),
            expected_month="2026_08",
            expected_security_symbols={"MSFT"},
            expected_current_holding_symbols={"MSFT"},
        )


def test_existing_holding_action_must_use_the_confirmed_account_category(
    tmp_path: Path,
) -> None:
    payload = response_payload()
    action = action_payload(status="conditional")
    action["account_type"] = "NISA（成長投資枠）"
    payload["decisions"]["actions"] = [action]

    with pytest.raises(ValueError, match="confirmed holding account"):
        load_monthly_review_response(
            write_yaml(tmp_path / "review_response.yaml", payload),
            expected_month="2026_08",
            expected_security_symbols={"MSFT"},
            expected_current_holding_accounts={
                "MSFT": "特定口座（源泉徴収あり）"
            },
        )


def test_new_asset_purchase_requires_matching_conclusion(tmp_path: Path) -> None:
    payload = response_payload()
    existing = action_payload(status="conditional")
    new_asset = deepcopy(existing)
    new_asset.update(
        {
            "action_id": "A-2",
            "action_scope": "new_asset",
            "symbol": "NEW_FUND",
            "asset_name": "New Fund",
            "holding_status": "not_held",
            "side": "buy",
            "account_type": "NISA（成長投資枠）",
            "execution_method": "buy once after user approval",
        }
    )
    payload["decisions"]["actions"] = [existing, new_asset]

    with pytest.raises(ValueError, match="action_ids do not match"):
        load_monthly_review_response(
            write_yaml(tmp_path / "review_response.yaml", payload),
            expected_month="2026_08",
            expected_security_symbols={"MSFT"},
            expected_current_holding_symbols={"MSFT"},
        )

    payload["decisions"]["new_asset_purchase_conclusion"] = {
        "status": "buy_proposed",
        "rationale": "The reviewed satellite parameters select this new asset.",
        "action_ids": ["A-2"],
    }
    loaded, _ = load_monthly_review_response(
        write_yaml(tmp_path / "review_response.yaml", payload),
        expected_month="2026_08",
        expected_security_symbols={"MSFT"},
        expected_current_holding_symbols={"MSFT"},
    )
    assert loaded["decisions"]["new_asset_purchase_conclusion"]["status"] == (
        "buy_proposed"
    )


def test_declining_market_requires_use_option(tmp_path: Path) -> None:
    payload = response_payload()
    payload["dip_buy_liquidity_deployment_review"] = deployment_review_payload(market_decline_status="declining", considered=False)
    with pytest.raises(ValueError, match="must consider"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_hold_is_allowed_after_use_option_comparison(tmp_path: Path) -> None:
    payload = response_payload()
    payload["dip_buy_liquidity_deployment_review"] = deployment_review_payload(market_decline_status="declining", considered=True)
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["dip_buy_liquidity_deployment_review"]["selected_action"] == "hold"


def test_mismatched_trigger_index_forces_unclear(tmp_path: Path) -> None:
    payload = response_payload()
    review = payload["dip_buy_liquidity_deployment_review"]
    review["trigger_index_matches_deployment_target"] = False
    with pytest.raises(ValueError, match="must be unclear"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_theme_decline_cannot_be_market_trigger(tmp_path: Path) -> None:
    payload = response_payload()
    payload["dip_buy_liquidity_deployment_review"]["theme_or_sector_decline_used_as_trigger"] = True
    with pytest.raises(ValueError, match="must not use a theme"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def thematic_review() -> dict:
    return {
        "theme_review_id": "nissei_sox_index_fund",
        "product_name": "ニッセイSOX指数インデックスファンド",
        "member_symbols": ["NISSEI_SOX_1", "NISSEI_SOX_2"],
        "index_story": "single product/index review",
        "material_facts": [],
        "story_health": "watch",
        "decision": "hold",
        "decision_rationale": "primary source review",
        "sources": [],
        "account_lot_reviews": [
            {"symbol": "NISSEI_SOX_1", "account_type": "taxable", "execution_decision": "hold", "tax_analysis_ref": None, "rationale": "lot review"},
            {"symbol": "NISSEI_SOX_2", "account_type": "NISA", "execution_decision": "hold", "tax_analysis_ref": None, "rationale": "lot review"},
        ],
    }


def test_thematic_product_story_and_account_lots_are_both_required(tmp_path: Path) -> None:
    payload = response_payload()
    payload["thematic_fund_reviews"] = [thematic_review()]
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload), expected_themes={"NISSEI_SOX_1", "NISSEI_SOX_2"})
    assert len(loaded["thematic_fund_reviews"][0]["account_lot_reviews"]) == 2


def test_missing_thematic_lot_is_rejected(tmp_path: Path) -> None:
    payload = response_payload()
    review = thematic_review()
    review["account_lot_reviews"].pop()
    payload["thematic_fund_reviews"] = [review]
    with pytest.raises(ValueError, match="account lot coverage mismatch"):
        load(write_yaml(tmp_path / "review_response.yaml", payload), expected_themes={"NISSEI_SOX_1", "NISSEI_SOX_2"})


def test_cash_assessment_must_reference_canonical_policy(tmp_path: Path) -> None:
    payload = response_payload()
    payload["cash_assessment"]["tactical_liquidity_policy_ref"] = "decisions.some_copy"
    with pytest.raises(ValueError, match="tactical_liquidity_policy_ref"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_duplicate_tactical_policy_under_decisions_is_rejected(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decisions"]["dip_buy_liquidity_policy_proposal"] = tactical_policy(
        proposed=True
    )
    with pytest.raises(ValueError, match="non-canonical fields"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_before_after_calculated_view_must_total_100(tmp_path: Path) -> None:
    payload = response_payload()
    payload["before_after_allocation"] = [
        {"view": "household_total_asset_allocation", "category": "equity", "before_jpy": 28_000_000, "after_jpy": 28_000_000, "target_jpy": 28_000_000, "before_pct": 70, "after_pct": 70, "target_pct": 70, "calculation_status": "calculated", "reason": "calculated", "remediation": ""},
        {"view": "household_total_asset_allocation", "category": "cash", "before_jpy": 8_000_000, "after_jpy": 8_000_000, "target_jpy": 8_000_000, "before_pct": 20, "after_pct": 20, "target_pct": 20, "calculation_status": "calculated", "reason": "calculated", "remediation": ""},
    ]
    with pytest.raises(ValueError, match="after_pct must total 100"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_source_schema_requires_publisher_and_claim(tmp_path: Path) -> None:
    payload = response_payload()
    evidence_source = source_payload()
    evidence_source.pop("publisher")
    payload["empirical_evidence"] = [{"evidence_id": "E-1", "claim": "claim", "source": evidence_source, "observed_market_or_population": "market", "observation_period": "2000-2025", "result": "result", "limitations": "limits", "decision_supported": "decision"}]
    with pytest.raises(ValueError, match="publisher"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_source_accessed_after_cutoff_is_allowed(tmp_path: Path) -> None:
    payload = response_payload()
    source = source_payload()
    source["accessed_at"] = "2026-08-04T12:00:00Z"
    payload["empirical_evidence"] = [
        {
            "evidence_id": "E-1",
            "claim": "claim",
            "source": source,
            "observed_market_or_population": "market",
            "observation_period": "2000-2025",
            "result": "result",
            "limitations": "limits",
            "decision_supported": "decision",
        }
    ]
    loaded, _ = load(write_yaml(tmp_path / "review_response.yaml", payload))
    assert loaded["empirical_evidence"][0]["source"]["accessed_at"].startswith(
        "2026-08-04"
    )


def test_source_published_after_cutoff_is_rejected_even_for_earlier_data(
    tmp_path: Path,
) -> None:
    payload = response_payload()
    source = source_payload()
    source["publication_date"] = "2026-08-03"
    source["data_as_of"] = "2026-07-31"
    payload["empirical_evidence"] = [
        {
            "evidence_id": "E-1",
            "claim": "claim",
            "source": source,
            "observed_market_or_population": "market",
            "observation_period": "2000-2025",
            "result": "result",
            "limitations": "limits",
            "decision_supported": "decision",
        }
    ]
    with pytest.raises(ValueError, match="publication_date is after"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_source_data_as_of_after_cutoff_is_rejected(tmp_path: Path) -> None:
    payload = response_payload()
    source = source_payload()
    source["data_as_of"] = "2026-08-03"
    payload["empirical_evidence"] = [
        {
            "evidence_id": "E-1",
            "claim": "claim",
            "source": source,
            "observed_market_or_population": "market",
            "observation_period": "2000-2025",
            "result": "result",
            "limitations": "limits",
            "decision_supported": "decision",
        }
    ]
    with pytest.raises(ValueError, match="data_as_of is after"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_dynamic_source_without_verifiable_publication_date_is_rejected(
    tmp_path: Path,
) -> None:
    payload = response_payload()
    source = source_payload()
    source["publication_date"] = None
    source["cutoff_compliance_status"] = "not_verifiable"
    payload["empirical_evidence"] = [
        {
            "evidence_id": "E-1",
            "claim": "claim",
            "source": source,
            "observed_market_or_population": "market",
            "observation_period": "2000-2025",
            "result": "result",
            "limitations": "limits",
            "decision_supported": "decision",
        }
    ]
    with pytest.raises(ValueError, match="cutoff_compliance_status is compliant"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_external_research_cannot_revalue_portfolio_snapshot(tmp_path: Path) -> None:
    payload = response_payload()
    payload["portfolio_snapshot_as_of"] = "2026-08-02"
    path = write_yaml(tmp_path / "review_response.yaml", payload)
    with pytest.raises(ValueError, match="portfolio_snapshot_as_of conflicts"):
        load_monthly_review_response(
            path,
            expected_month="2026_08",
            expected_security_symbols={"MSFT"},
            expected_date_context={
                "portfolio_snapshot_as_of": "2026-07-26",
                "market_reference_as_of": "2026-08-02",
                "packet_generated_at": "2026-08-02T12:00:00Z",
                "research_cutoff_at": "2026-08-02T12:00:00Z",
            },
        )


def test_health_check_contract_remains_compatible(tmp_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "artifact_type": "portfolio_health_check_response",
        "completed_at": "2026-08-02T12:00:00Z",
        "coverage_start": "2026-07-03",
        "coverage_end": "2026-08-02",
        "human_summary": {"overall_status": "watch", "urgent_items": []},
        "dip_buy_liquidity_deployment_review": {key: value for key, value in deployment_review_payload().items() if key not in {"policy_ref", "trigger_index_matches_deployment_target", "theme_or_sector_decline_used_as_trigger"}},
        "security_story_reviews": response_payload()["security_story_reviews"],
        "cross_holding_themes": [],
        "alerts": [],
        "next_check_triggers": [],
        "codex_handoff": {"thesis_updates_proposed": [], "data_gaps": []},
    }
    result = load_health_check_response(write_yaml(tmp_path / "health.yaml", payload), expected_security_symbols={"MSFT"})
    assert result["completed_at"] == "2026-08-02T12:00:00Z"
