from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from monthly_limit_order_review.storage import write_yaml
from monthly_limit_order_review.structured_review import (
    DECISION_QUALITY_CHECKS,
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
        "accessed_at": "2026-08-02T12:00:00Z",
        "source_type": "issuer_ir_or_filing",
        "claim_supported": "The stated factual claim",
    }


def quality_checks() -> list[dict]:
    return [
        {
            "check_id": check_id,
            "status": "pass",
            "evidence": "validated in final response",
            "remediation": "",
        }
        for check_id in sorted(DECISION_QUALITY_CHECKS)
    ]


def tactical_policy(*, proposed: bool = False) -> dict:
    return {
        "policy_id": "TL-2026-08",
        "status": "proposed" if proposed else "not_applicable",
        "initial_target_pct_of_total_assets": 7.5 if proposed else None,
        "target_jpy": 3_000_000 if proposed else None,
        "deployment_asset": "全世界株式" if proposed else None,
        "trigger_index": "MSCI ACWI" if proposed else None,
        "reference_high_definition": "終値ベースの過去最高値" if proposed else None,
        "price_basis": "close" if proposed else None,
        "lookback_period": "all_available_history" if proposed else None,
        "fx_treatment": "JPY unhedged total return" if proposed else None,
        "tranches": 3 if proposed else None,
        "amount_per_tranche": "target_jpy / 3" if proposed else None,
        "refill_rule": "new contributions only" if proposed else None,
        "termination_rule": "fully deployed" if proposed else None,
        "policy_allocation_treatment": "outside policy denominator while undeployed" if proposed else None,
        "rationale": "review result" if proposed else "monthly mode",
        "source_refs": [],
        "requires_user_approval": True,
    }


def deployment_review_payload(
    *,
    market_decline_status: str = "not_declining",
    considered: bool = False,
) -> dict:
    return {
        "policy_ref": CANONICAL_TACTICAL_REF,
        "reserve_status": "unknown",
        "market_decline_status": market_decline_status,
        "trigger_index_matches_deployment_target": True,
        "theme_or_sector_decline_used_as_trigger": False,
        "market_evidence": [],
        "use_option": {
            "considered": considered,
            "status": "conditional" if considered else "not_applicable",
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
        "artifact_type": "monthly_review_response",
        "review_mode": "monthly_operational_review",
        "interaction_phase": "final_review",
        "review_target_month": "2026_08",
        "portfolio_snapshot_as_of": "2026-07-26",
        "market_reference_as_of": "2026-08-02",
        "packet_generated_at": "2026-08-02T12:00:00Z",
        "research_cutoff_at": "2026-08-02T12:00:00Z",
        "decision_date": "2026-08-02",
        "strategic_policy_decision": {
            "status": "not_applicable",
            "objective": None,
            "updated_inputs": {
                "newly_confirmed": [],
                "superseded_assumptions": [],
                "decisions_now_unblocked": [],
                "decisions_still_blocked": [],
            },
            "financial_planning_model": {
                "status": "not_applicable",
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
                    "allocation_rule": None,
                    "rationale": None,
                },
                "inheritance_included_in_base_case": None,
                "inheritance_base_case_jpy": None,
                "inheritance_treatment": None,
                "terminal_asset_floor_current_jpy": None,
                "success_probability_pct": None,
                "success_probability_rationale": None,
                "target_return_pct": None,
                "target_return_formula": None,
                "sensitivity_cases": [],
                "source_refs": [],
            },
            "recommended_policy": {
                "policy_id": "SAA-2026-08",
                "investable_equity_pct": None,
                "investable_bond_pct": None,
                "investable_other_pct": None,
                "core_policy": None,
                "satellite_policy": None,
                "rebalancing_rule": None,
                "transition_deadline": None,
            },
            "policy_allocation_within_investable_portfolio": {
                "equity_pct": None,
                "bond_pct": None,
                "other_pct": None,
            },
            "household_total_asset_allocation": {
                "equity_pct": None,
                "bond_pct": None,
                "household_reserve_pct": None,
                "tactical_liquidity_pct": None,
                "excluded_other_pct": None,
            },
            "tactical_liquidity_policy": policy,
            "active_risk_policy": {
                "policy_id": "AR-2026-08",
                "satellites_allowed": None,
                "total_satellite_cap_pct": None,
                "single_theme_cap_pct": None,
                "single_security_cap_pct": None,
                "exceptions": [],
            },
            "direct_semiconductor_limit": {
                "policy_id": "SEMICON-2026-08",
                "status": "hard_constraint",
                "limit_pct": 12,
                "denominator": "household_total_assets_jpy",
                "priority": "strictest applicable cap",
                "rationale": "approved current policy",
            },
            "candidate_methodology": {},
            "candidate_comparison": [],
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
        },
        "codex_handoff": {
            "execution_checks": [],
            "prompt_feedback": [],
            "repository_changes": {"must": [], "should": [], "nice_to_have": []},
        },
        "decision_quality_checks": quality_checks(),
    }


def make_strategic(payload: dict) -> dict:
    payload = deepcopy(payload)
    payload["review_mode"] = "strategic_policy_second_opinion"
    decision = payload["strategic_policy_decision"]
    decision["status"] = "proposed"
    decision["objective"] = "maximize_ex_ante_sharpe_ratio"
    decision["financial_planning_model"] = {
        "status": "derived",
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
            "allocation_rule": "tax-advantaged core first",
            "rationale": "cash-flow-based sustainable contribution",
        },
        "inheritance_included_in_base_case": False,
        "inheritance_base_case_jpy": 0,
        "inheritance_treatment": "excluded due timing and share uncertainty",
        "terminal_asset_floor_current_jpy": 10000000,
        "success_probability_pct": 90,
        "success_probability_rationale": "retirement planning evidence",
        "target_return_pct": 2.5,
        "target_return_formula": "real IRR of modeled contributions and withdrawals",
        "sensitivity_cases": ["lower pension", "higher spending"],
        "source_refs": ["E-FP-001"],
    }
    decision["recommended_policy"].update(
        {
            "investable_equity_pct": 80,
            "investable_bond_pct": 20,
            "investable_other_pct": 0,
            "core_policy": "global equity core",
            "satellite_policy": "allowed within caps",
            "rebalancing_rule": "annual",
            "transition_deadline": "2027-03-31",
        }
    )
    decision["policy_allocation_within_investable_portfolio"].update(
        {"equity_pct": 80, "bond_pct": 20, "other_pct": 0}
    )
    decision["household_total_asset_allocation"].update(
        {
            "equity_pct": 70,
            "bond_pct": 17.5,
            "household_reserve_pct": 5,
            "tactical_liquidity_pct": 7.5,
            "excluded_other_pct": 0,
        }
    )
    decision["tactical_liquidity_policy"] = tactical_policy(proposed=True)
    payload["decisions"]["policy_refs"] = [
        decision["tactical_liquidity_policy"]["policy_id"]
    ]
    decision["active_risk_policy"].update(
        {
            "satellites_allowed": True,
            "total_satellite_cap_pct": 20,
            "single_theme_cap_pct": 10,
            "single_security_cap_pct": 5,
        }
    )
    decision["candidate_methodology"] = {
        "global_equity_index": "MSCI ACWI",
        "bond_index": "Bloomberg Global Aggregate JPY Hedged",
        "bond_instrument_type": "JPY-hedged investment-grade aggregate bonds",
        "estimation_period": "2000-01-01/2025-12-31",
        "assumptions_as_of": "2026-08-02",
        "inflation_assumption_pct": 2,
        "return_basis": "pre-tax after-cost nominal and real",
        "tax_cost_treatment": "pre-tax returns net of fund costs",
        "major_drawdown_definition": "monthly peak-to-trough total return",
        "rebalancing_frequency": "annual",
        "range_rationale": "standard equity-dominant range for this comparison",
        "boundary_extension_applied": False,
    }
    decision["candidate_comparison"] = [
        {
            "candidate_id": candidate_id,
            "global_equity_pct": equity,
            "bonds_pct": 100 - equity,
            "expected_nominal_return_pct": 5,
            "expected_real_return_pct": 3,
            "expected_volatility_pct": 10,
            "equity_bond_correlation": 0,
            "estimated_major_drawdown_pct": -30,
            "primary_objective_fit_value": 0.3,
            "primary_objective_fit_formula": "(return-risk_free)/volatility",
            "assumptions_ref": "candidate_methodology",
            "selected": candidate_id == "GE80_B20",
        }
        for candidate_id, equity in (
            ("GE100_B0", 100),
            ("GE90_B10", 90),
            ("GE80_B20", 80),
            ("GE70_B30", 70),
        )
    ]
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


def test_strategic_mode_requires_one_complete_policy(tmp_path: Path) -> None:
    payload, _ = load(write_yaml(tmp_path / "review_response.yaml", make_strategic(response_payload())))
    assert payload["strategic_policy_decision"]["status"] == "proposed"


def test_strategic_investable_allocation_must_total_100(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    payload["strategic_policy_decision"]["policy_allocation_within_investable_portfolio"]["bond_pct"] = 10
    with pytest.raises(ValueError, match="must total 100"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_minimum_risk_boundary_requires_one_60_40_extension(tmp_path: Path) -> None:
    payload = make_strategic(response_payload())
    decision = payload["strategic_policy_decision"]
    decision["objective"] = "minimize_risk_for_required_return"
    for candidate in decision["candidate_comparison"]:
        candidate["selected"] = candidate["candidate_id"] == "GE70_B30"
    with pytest.raises(ValueError, match="requires one 60/40 extension"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


def test_final_review_quality_checks_must_all_pass(tmp_path: Path) -> None:
    payload = response_payload()
    payload["decision_quality_checks"][0]["status"] = "fail"
    with pytest.raises(ValueError, match="must all pass"):
        load(write_yaml(tmp_path / "review_response.yaml", payload))


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
        "status": status,
        "description": "cash to global equity",
        "source": "cash",
        "destination": "global equity",
        "amount_jpy": 1,
        "formula": "assumed ratio",
        "inputs": [{"name": "ratio", "value": 1, "source_type": "explicit_assumption", "source_ref": "reviewer assumption"}],
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
        {"view": "household_total_asset_allocation", "category": "equity", "before_pct": 70, "after_pct": 70, "target_pct": 70, "calculation_status": "calculated"},
        {"view": "household_total_asset_allocation", "category": "cash", "before_pct": 20, "after_pct": 20, "target_pct": 20, "calculation_status": "calculated"},
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
