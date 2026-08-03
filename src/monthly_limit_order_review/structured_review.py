from __future__ import annotations

from decimal import Decimal

import yaml

from .models import ReviewFeedback, ReviewOrderProposal
from .storage import load_yaml


DECISION_QUALITY_CHECKS = {
    "target_equity_ratio_is_not_cash_residual",
    "strategic_cash_and_tactical_cash_are_separated",
    "one_primary_policy_is_selected",
    "policy_is_derived_from_stated_objective",
    "age_and_horizon_are_considered_when_relevant",
    "age_is_not_replaced_by_an_unexamined_rule_of_thumb",
    "empirical_rules_have_verifiable_support",
    "statistical_average_is_not_presented_as_a_certain_outcome",
    "no_persona_generated_investment_lore",
    "no_numeric_threshold_is_based_only_on_expert_sounding_language",
    "subjective_axes_are_used_only_when_explicitly_authorized",
    "no_unrequested_psychological_or_lifestyle_axes",
    "no_ad_hoc_concentration_limit",
    "no_arbitrary_partial_sale",
    "every_general_statement_supports_a_decision",
    "transition_plan_matches_policy_portfolio",
    "prior_recommendations_are_explicitly_superseded_when_changed",
    "delegated_financial_planning_inputs_are_derived_not_reasked",
    "derived_financial_planning_values_have_evidence_and_sensitivity",
}


def load_monthly_review_response(
    path,
    *,
    expected_month: str,
    expected_security_symbols: set[str],
    expected_thematic_member_symbols: set[str] | None = None,
    expected_cash_context: dict | None = None,
    expected_date_context: dict | None = None,
    total_assets_jpy: Decimal | int | None = None,
) -> tuple[dict, ReviewFeedback]:
    payload = load_yaml(path)
    _validate_monthly_review_response(
        payload,
        expected_month=expected_month,
        expected_security_symbols=expected_security_symbols,
        expected_thematic_member_symbols=expected_thematic_member_symbols or set(),
        expected_cash_context=expected_cash_context,
        expected_date_context=expected_date_context,
        total_assets_jpy=total_assets_jpy,
    )
    decisions = payload["decisions"]
    repository_changes = payload["codex_handoff"]["repository_changes"]
    feedback = ReviewFeedback(
        raw_text=yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        sections={},
        order_proposals=[
            ReviewOrderProposal(
                symbol=item["symbol"],
                recommended_price=(
                    Decimal(str(item["recommended_price"]))
                    if item.get("recommended_price") is not None
                    else None
                ),
                recommended_shares=(
                    int(item["quantity"])
                    if item.get("quantity") is not None
                    and Decimal(str(item["quantity"]))
                    == Decimal(str(item["quantity"])).to_integral()
                    else None
                ),
                reason=item["rationale"],
            )
            for item in decisions["order_proposals"]
        ],
        sox_decision=next(
            (
                item.get("decision")
                for item in payload.get("thematic_fund_reviews", [])
                if any(
                    str(symbol).startswith("NISSEI_SOX_")
                    for symbol in item.get("member_symbols", [])
                )
            ),
            None,
        ),
        portfolio_diagnosis=list(decisions["portfolio_diagnosis"]),
        rule_review=list(decisions["rule_refs"]),
        must=list(repository_changes["must"]),
        should=list(repository_changes["should"]),
        nice_to_have=list(repository_changes["nice_to_have"]),
        parser_warnings=[],
    )
    return payload, feedback


def load_health_check_response(
    path,
    *,
    expected_security_symbols: set[str],
) -> dict:
    payload = load_yaml(path)
    if payload.get("schema_version") != 1:
        raise ValueError("health_check_response.yaml schema_version must be 1")
    if payload.get("artifact_type") != "portfolio_health_check_response":
        raise ValueError(
            "health_check_response.yaml artifact_type must be portfolio_health_check_response"
        )
    for field in (
        "completed_at",
        "coverage_start",
        "coverage_end",
        "human_summary",
        "dip_buy_liquidity_deployment_review",
        "security_story_reviews",
        "cross_holding_themes",
        "alerts",
        "next_check_triggers",
        "codex_handoff",
    ):
        if field not in payload:
            raise ValueError(f"health_check_response.yaml missing {field}")
    _validate_security_story_coverage(
        payload["security_story_reviews"],
        expected_security_symbols=expected_security_symbols,
        source_name="health_check_response.yaml",
    )
    _validate_dip_buy_liquidity_deployment_review(
        payload["dip_buy_liquidity_deployment_review"],
        source_name="health_check_response.yaml",
    )
    return payload


def _validate_monthly_review_response(
    payload: dict,
    *,
    expected_month: str,
    expected_security_symbols: set[str],
    expected_thematic_member_symbols: set[str],
    expected_cash_context: dict | None,
    expected_date_context: dict | None,
    total_assets_jpy: Decimal | int | None,
) -> None:
    if payload.get("schema_version") != 2:
        raise ValueError("review_response.yaml schema_version must be 2")
    if payload.get("artifact_type") != "monthly_review_response":
        raise ValueError("review_response.yaml artifact_type must be monthly_review_response")
    if payload.get("review_target_month") != expected_month:
        raise ValueError(
            "review_response.yaml review_target_month does not match the snapshot month"
        )
    required = {
        "review_mode",
        "interaction_phase",
        "portfolio_snapshot_as_of",
        "market_reference_as_of",
        "packet_generated_at",
        "research_cutoff_at",
        "decision_date",
        "strategic_policy_decision",
        "decision_axes",
        "empirical_evidence",
        "human_summary",
        "cash_assessment",
        "dip_buy_liquidity_deployment_review",
        "security_story_reviews",
        "thematic_fund_reviews",
        "before_after_allocation",
        "account_tax_comparisons",
        "decisions",
        "codex_handoff",
        "decision_quality_checks",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError("review_response.yaml missing fields: " + ", ".join(missing))
    if expected_date_context:
        for field in (
            "portfolio_snapshot_as_of",
            "market_reference_as_of",
            "packet_generated_at",
            "research_cutoff_at",
        ):
            expected = expected_date_context.get(field)
            if expected is not None and str(payload.get(field)) != str(expected):
                raise ValueError(
                    f"review_response.yaml {field} conflicts with review packet; "
                    f"expected={expected!r}, actual={payload.get(field)!r}"
                )

    _validate_strategic_policy_decision(
        payload["strategic_policy_decision"],
        review_mode=payload["review_mode"],
    )
    if payload["interaction_phase"] != "final_review":
        raise ValueError("review_response.yaml interaction_phase must be final_review")
    _validate_updated_inputs(payload["strategic_policy_decision"]["updated_inputs"])
    _validate_decision_axes(payload["decision_axes"])
    if not isinstance(payload["empirical_evidence"], list):
        raise ValueError("empirical_evidence must be a list")
    _validate_empirical_evidence(payload["empirical_evidence"])
    _validate_decision_quality_checks(payload["decision_quality_checks"])

    _validate_security_story_coverage(
        payload["security_story_reviews"],
        expected_security_symbols=expected_security_symbols,
        source_name="review_response.yaml",
    )
    _validate_thematic_fund_coverage(
        payload["thematic_fund_reviews"],
        expected_member_symbols=expected_thematic_member_symbols,
    )
    _validate_before_after_allocation(payload["before_after_allocation"])
    _validate_account_tax_comparisons(payload["account_tax_comparisons"])
    _validate_cash_assessment(
        payload["cash_assessment"],
        expected_cash_context=expected_cash_context,
    )
    _validate_dip_buy_liquidity_deployment_review(
        payload["dip_buy_liquidity_deployment_review"],
        source_name="review_response.yaml",
    )

    decisions = payload["decisions"]
    decision_fields = {
        "policy_refs",
        "portfolio_diagnosis",
        "rule_refs",
        "order_proposals",
        "actions",
    }
    unexpected_decision_fields = sorted(set(decisions) - decision_fields)
    if unexpected_decision_fields:
        raise ValueError(
            "decisions contains non-canonical fields: "
            + ", ".join(unexpected_decision_fields)
        )
    for field in decision_fields:
        if field not in decisions:
            raise ValueError(f"decisions missing {field}")
    _validate_canonical_tactical_liquidity_policy(
        payload["strategic_policy_decision"]["tactical_liquidity_policy"],
        cash_assessment=payload["cash_assessment"],
        deployment_review=payload["dip_buy_liquidity_deployment_review"],
        policy_refs=decisions["policy_refs"],
    )
    _validate_actions(decisions["actions"], total_assets_jpy=total_assets_jpy)
    _validate_order_proposals(decisions["order_proposals"])
    handoff = payload["codex_handoff"]
    if "repository_changes" not in handoff:
        raise ValueError("codex_handoff missing repository_changes")
    if "prompt_feedback" not in handoff:
        raise ValueError("codex_handoff missing prompt_feedback")
    if not isinstance(handoff["prompt_feedback"], list):
        raise ValueError("codex_handoff.prompt_feedback must be a list")
    _validate_execution_checks(handoff.get("execution_checks"))
    _validate_prompt_feedback(handoff["prompt_feedback"])
    for priority in ("must", "should", "nice_to_have"):
        if priority not in handoff["repository_changes"]:
            raise ValueError(f"codex_handoff.repository_changes missing {priority}")


def _validate_strategic_policy_decision(decision, *, review_mode: str) -> None:
    if review_mode not in {
        "monthly_operational_review",
        "strategic_policy_second_opinion",
    }:
        raise ValueError("review_response.yaml review_mode is invalid")
    if not isinstance(decision, dict):
        raise ValueError("strategic_policy_decision must be an object")
    required = {
        "status",
        "objective",
        "updated_inputs",
        "financial_planning_model",
        "recommended_policy",
        "policy_allocation_within_investable_portfolio",
        "household_total_asset_allocation",
        "tactical_liquidity_policy",
        "active_risk_policy",
        "direct_semiconductor_limit",
        "candidate_methodology",
        "candidate_comparison",
    }
    missing = sorted(required - set(decision))
    if missing:
        raise ValueError(
            "strategic_policy_decision missing fields: " + ", ".join(missing)
        )
    expected_status = (
        "not_applicable"
        if review_mode == "monthly_operational_review"
        else "proposed"
    )
    if decision["status"] != expected_status:
        raise ValueError(
            "strategic_policy_decision.status conflicts with review_mode; "
            f"expected={expected_status}"
        )
    _validate_financial_planning_model(
        decision["financial_planning_model"],
        strategic=review_mode == "strategic_policy_second_opinion",
    )
    policy = decision["recommended_policy"]
    policy_fields = {
        "policy_id",
        "investable_equity_pct",
        "investable_bond_pct",
        "investable_other_pct",
        "core_policy",
        "satellite_policy",
        "rebalancing_rule",
        "transition_deadline",
    }
    if not isinstance(policy, dict) or policy_fields - set(policy):
        missing_policy = sorted(policy_fields - set(policy or {}))
        raise ValueError(
            "strategic_policy_decision.recommended_policy missing fields: "
            + ", ".join(missing_policy)
        )
    if review_mode == "strategic_policy_second_opinion":
        if not decision["objective"]:
            raise ValueError("strategic policy response requires an objective")
        equity = policy["investable_equity_pct"]
        bonds = policy["investable_bond_pct"]
        other = policy["investable_other_pct"]
        if (
            equity is None
            or bonds is None
            or other is None
            or Decimal(str(equity)) + Decimal(str(bonds)) + Decimal(str(other))
            != 100
        ):
            raise ValueError(
                "strategic policy response requires valid investable equity and bond weights"
            )
        if not decision["candidate_comparison"]:
            raise ValueError("strategic policy response requires candidate_comparison")
        investable = decision["policy_allocation_within_investable_portfolio"]
        _require_mapping_fields(
            investable,
            {"equity_pct", "bond_pct", "other_pct"},
            name="policy_allocation_within_investable_portfolio",
        )


        investable_values = [investable[key] for key in ("equity_pct", "bond_pct", "other_pct")]
        if any(value is None for value in investable_values) or sum(
            Decimal(str(value)) for value in investable_values
        ) != 100:
            raise ValueError("investable policy allocation must total 100")
        household = decision["household_total_asset_allocation"]
        household_fields = {
            "equity_pct",
            "bond_pct",
            "household_reserve_pct",
            "tactical_liquidity_pct",
            "excluded_other_pct",
        }
        _require_mapping_fields(
            household,
            household_fields,
            name="household_total_asset_allocation",
        )
        household_values = [household[key] for key in household_fields]
        if any(value is None for value in household_values) or sum(
            Decimal(str(value)) for value in household_values
        ) != 100:
            raise ValueError("household total asset allocation must total 100")
        tactical = decision["tactical_liquidity_policy"]
        _require_mapping_fields(
            tactical,
            {
                "policy_id",
                "status",
                "initial_target_pct_of_total_assets",
                "target_jpy",
                "deployment_asset",
                "trigger_index",
                "reference_high_definition",
                "price_basis",
                "lookback_period",
                "fx_treatment",
                "tranches",
                "amount_per_tranche",
                "refill_rule",
                "termination_rule",
                "policy_allocation_treatment",
                "rationale",
                "source_refs",
                "requires_user_approval",
            },
            name="tactical_liquidity_policy",
        )
        tactical_required_values = (
            "initial_target_pct_of_total_assets",
            "target_jpy",
            "deployment_asset",
            "trigger_index",
            "reference_high_definition",
            "price_basis",
            "lookback_period",
            "fx_treatment",
            "tranches",
            "amount_per_tranche",
            "refill_rule",
            "termination_rule",
            "policy_allocation_treatment",
        )
        if any(tactical[field] is None for field in tactical_required_values):
            raise ValueError("strategic tactical_liquidity_policy must be complete")
        active_risk = decision["active_risk_policy"]
        _require_mapping_fields(
            active_risk,
            {
                "policy_id",
                "satellites_allowed",
                "total_satellite_cap_pct",
                "single_theme_cap_pct",
                "single_security_cap_pct",
                "exceptions",
            },
            name="active_risk_policy",
        )
        if active_risk["satellites_allowed"] is True and any(
            active_risk[field] is None
            for field in (
                "total_satellite_cap_pct",
                "single_theme_cap_pct",
                "single_security_cap_pct",
            )
        ):
            raise ValueError("strategic active_risk_policy caps must be complete")
        if not isinstance(decision["candidate_methodology"], dict):
            raise ValueError("strategic candidate_methodology must be an object")
        _validate_candidate_comparison(decision)
        direct_limit = decision["direct_semiconductor_limit"]
        _require_mapping_fields(
            direct_limit,
            {"policy_id", "status", "limit_pct", "denominator", "priority", "rationale"},
            name="direct_semiconductor_limit",
        )


def _validate_financial_planning_model(model: dict, *, strategic: bool) -> None:
    required = {
        "status",
        "return_basis",
        "current_age",
        "withdrawal_start_age",
        "planning_end_age",
        "retirement_spending_current_jpy_per_month",
        "retirement_spending_derivation",
        "public_pension_annual_current_jpy",
        "public_pension_estimation_method",
        "long_term_contribution_policy",
        "inheritance_included_in_base_case",
        "inheritance_base_case_jpy",
        "inheritance_treatment",
        "terminal_asset_floor_current_jpy",
        "success_probability_pct",
        "success_probability_rationale",
        "target_return_pct",
        "target_return_formula",
        "sensitivity_cases",
        "source_refs",
    }
    _require_mapping_fields(model, required, name="financial_planning_model")
    contribution = model["long_term_contribution_policy"]
    contribution_fields = {
        "annual_net_contribution_jpy",
        "contribution_end_age",
        "allocation_rule",
        "rationale",
    }
    _require_mapping_fields(
        contribution,
        contribution_fields,
        name="financial_planning_model.long_term_contribution_policy",
    )
    if not strategic:
        if model["status"] != "not_applicable":
            raise ValueError("monthly financial_planning_model must be not_applicable")
        return
    if model["status"] != "derived":
        raise ValueError("strategic financial_planning_model must be derived")
    required_values = {
        "return_basis",
        "current_age",
        "withdrawal_start_age",
        "planning_end_age",
        "retirement_spending_current_jpy_per_month",
        "retirement_spending_derivation",
        "public_pension_annual_current_jpy",
        "public_pension_estimation_method",
        "inheritance_included_in_base_case",
        "inheritance_treatment",
        "terminal_asset_floor_current_jpy",
        "success_probability_pct",
        "success_probability_rationale",
        "target_return_pct",
        "target_return_formula",
    }
    if any(model[field] is None for field in required_values):
        raise ValueError("strategic financial_planning_model must be complete")
    if any(contribution[field] is None for field in contribution_fields):
        raise ValueError("strategic long_term_contribution_policy must be complete")
    if not model["sensitivity_cases"] or not model["source_refs"]:
        raise ValueError(
            "strategic financial_planning_model requires sensitivity cases and sources"
        )


def _validate_candidate_comparison(decision: dict) -> None:
    methodology_fields = {
        "global_equity_index",
        "bond_index",
        "bond_instrument_type",
        "estimation_period",
        "assumptions_as_of",
        "inflation_assumption_pct",
        "return_basis",
        "tax_cost_treatment",
        "major_drawdown_definition",
        "rebalancing_frequency",
        "range_rationale",
        "boundary_extension_applied",
    }
    methodology = decision["candidate_methodology"]
    missing_methodology = sorted(methodology_fields - set(methodology))
    if missing_methodology:
        raise ValueError(
            "strategic candidate_methodology missing fields: "
            + ", ".join(missing_methodology)
        )
    if any(
        methodology[field] in (None, "")
        for field in methodology_fields - {"boundary_extension_applied"}
    ):
        raise ValueError("strategic candidate_methodology must be complete")
    candidate_fields = {
        "candidate_id",
        "global_equity_pct",
        "bonds_pct",
        "expected_nominal_return_pct",
        "expected_real_return_pct",
        "expected_volatility_pct",
        "equity_bond_correlation",
        "estimated_major_drawdown_pct",
        "primary_objective_fit_value",
        "primary_objective_fit_formula",
        "assumptions_ref",
        "selected",
    }
    candidates = decision["candidate_comparison"]
    candidate_ids: set[str] = set()
    selected: list[dict] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or candidate_fields - set(candidate):
            raise ValueError(f"candidate_comparison[{index}] is incomplete")
        if (
            Decimal(str(candidate["global_equity_pct"]))
            + Decimal(str(candidate["bonds_pct"]))
            != 100
        ):
            raise ValueError(f"candidate_comparison[{index}] weights must total 100")
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in candidate_ids:
            raise ValueError("candidate_comparison contains duplicate candidate_id")
        candidate_ids.add(candidate_id)
        if candidate["selected"] is True:
            selected.append(candidate)
    required_ids = {"GE100_B0", "GE90_B10", "GE80_B20", "GE70_B30"}
    if not required_ids.issubset(candidate_ids):
        raise ValueError("candidate_comparison must include the standard 100/0 through 70/30 range")
    if len(selected) != 1:
        raise ValueError("candidate_comparison must select exactly one candidate")
    if (
        decision["objective"] == "minimize_risk_for_required_return"
        and selected[0]["candidate_id"] == "GE70_B30"
        and "GE60_B40" not in candidate_ids
    ):
        raise ValueError(
            "minimum-risk optimum at the 70/30 boundary requires one 60/40 extension"
        )


def _require_mapping_fields(value, fields: set[str], *, name: str) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    missing = sorted(fields - set(value))
    if missing:
        raise ValueError(f"{name} missing fields: " + ", ".join(missing))


def _validate_decision_axes(axes) -> None:
    required = {
        "user_confirmed_facts",
        "packet_confirmed_facts",
        "empirical_market_evidence",
        "mathematically_derived_constraints",
        "reviewer_assumptions",
    }
    if not isinstance(axes, dict):
        raise ValueError("decision_axes must be an object")
    missing = sorted(required - set(axes))
    if missing:
        raise ValueError("decision_axes missing fields: " + ", ".join(missing))


def _validate_updated_inputs(updated) -> None:
    required = {
        "newly_confirmed",
        "superseded_assumptions",
        "decisions_now_unblocked",
        "decisions_still_blocked",
    }
    if not isinstance(updated, dict):
        raise ValueError("updated_inputs must be an object")
    missing = sorted(required - set(updated))
    if missing:
        raise ValueError("updated_inputs missing fields: " + ", ".join(missing))


def _validate_decision_quality_checks(checks) -> None:
    if not isinstance(checks, list):
        raise ValueError("decision_quality_checks must be a list")
    required_fields = {"check_id", "status", "evidence", "remediation"}
    by_id: dict[str, dict] = {}
    for index, check in enumerate(checks):
        if not isinstance(check, dict) or required_fields - set(check):
            raise ValueError(
                f"decision_quality_checks[{index}] must contain check_id, status, evidence, remediation"
            )
        if check["status"] not in {"pass", "fail", "not_applicable"}:
            raise ValueError(f"decision_quality_checks[{index}].status is invalid")
        if check["check_id"] in by_id:
            raise ValueError("decision_quality_checks contains duplicate check_id")
        by_id[check["check_id"]] = check
    missing = sorted(DECISION_QUALITY_CHECKS - set(by_id))
    if missing:
        raise ValueError("decision_quality_checks missing fields: " + ", ".join(missing))
    failed = sorted(
        name
        for name in DECISION_QUALITY_CHECKS
        if by_id[name]["status"] != "pass"
    )
    if failed:
        raise ValueError(
            "decision_quality_checks must all pass in final_review: "
            + ", ".join(failed)
        )


def _validate_cash_assessment(
    cash: dict,
    *,
    expected_cash_context: dict | None,
) -> None:
    required = {
        "emergency_fund_target_jpy",
        "emergency_fund_status",
        "monthly_essential_expenses_jpy",
        "spending_months",
        "near_term_confirmed_expenses_jpy",
        "contingency_reserve_jpy",
        "tactical_liquidity_policy_ref",
        "dip_buy_liquidity_status",
        "minimum_confirmed_cash_jpy",
        "maximum_calculable_cash_jpy",
        "total_cash_target_status",
        "total_cash_target_jpy",
        "derivation_notes",
    }
    if not isinstance(cash, dict):
        raise ValueError("cash_assessment must be an object")
    missing = sorted(required - set(cash))
    if missing:
        raise ValueError("cash_assessment missing fields: " + ", ".join(missing))
    if cash["emergency_fund_status"] not in {
        "confirmed_user_target",
        "calculated",
        "not_calculable",
    }:
        raise ValueError("cash_assessment.emergency_fund_status is invalid")
    if cash["dip_buy_liquidity_status"] not in {
        "configured",
        "target_calculated_deployment_unconfigured",
        "unconfigured",
        "pending_independent_second_opinion",
        "proposal_requested_from_current_review",
    }:
        raise ValueError("cash_assessment.dip_buy_liquidity_status is invalid")
    if (
        cash["tactical_liquidity_policy_ref"]
        != "strategic_policy_decision.tactical_liquidity_policy"
    ):
        raise ValueError("cash_assessment tactical_liquidity_policy_ref is invalid")
    if cash["total_cash_target_status"] not in {
        "fully_calculable",
        "confirmed_minimum_only",
        "not_calculable",
    }:
        raise ValueError("cash_assessment.total_cash_target_status is invalid")
    if (
        cash["monthly_essential_expenses_jpy"] is None
        and cash["spending_months"] is not None
    ):
        raise ValueError(
            "cash_assessment.spending_months must be null when monthly essential expenses are unknown"
        )
    if (
        cash["total_cash_target_status"] != "fully_calculable"
        and cash["total_cash_target_jpy"] is not None
    ):
        raise ValueError(
            "cash_assessment.total_cash_target_jpy must be null unless fully calculable"
        )
    if (
        cash["total_cash_target_status"] == "fully_calculable"
        and cash["total_cash_target_jpy"] is None
    ):
        raise ValueError(
            "cash_assessment.total_cash_target_jpy is required when fully calculable"
        )
    if expected_cash_context is None:
        return

    emergency = expected_cash_context["emergency_fund"]
    near_term = expected_cash_context["near_term_confirmed_expenses"]
    contingency = expected_cash_context["contingency_reserve"]
    dip = expected_cash_context["dip_buy_liquidity"]
    result = expected_cash_context["result"]
    expected_values = {
        "emergency_fund_target_jpy": emergency.get("target_jpy"),
        "emergency_fund_status": emergency.get("status"),
        "monthly_essential_expenses_jpy": emergency.get(
            "monthly_essential_expenses_jpy"
        ),
        "spending_months": emergency.get("spending_months"),
        "near_term_confirmed_expenses_jpy": near_term.get("amount_jpy"),
        "contingency_reserve_jpy": contingency.get("amount_jpy"),
        "dip_buy_liquidity_status": dip.get("status"),
        "minimum_confirmed_cash_jpy": result.get("minimum_confirmed_cash_jpy"),
        "maximum_calculable_cash_jpy": result.get("maximum_cash_target_jpy"),
        "total_cash_target_status": result.get("cash_target_status"),
        "total_cash_target_jpy": result.get("total_cash_target_jpy"),
    }
    for field, expected in expected_values.items():
        actual = cash.get(field)
        if not values_equal(actual, expected):
            raise ValueError(
                f"cash_assessment.{field} conflicts with review packet; "
                f"expected={expected!r}, actual={actual!r}"
            )


def _validate_dip_buy_liquidity_deployment_review(
    review,
    *,
    source_name: str,
) -> None:
    if not isinstance(review, dict):
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review must be an object"
        )
    required = {
        "reserve_status",
        "market_decline_status",
        "market_evidence",
        "use_option",
        "selected_action",
        "selection_rationale",
        "reserve_maintenance_is_objective",
    }
    if source_name == "review_response.yaml":
        required.update(
            {
                "policy_ref",
                "trigger_index_matches_deployment_target",
                "theme_or_sector_decline_used_as_trigger",
            }
        )
    missing = sorted(required - set(review))
    if missing:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review missing fields: "
            + ", ".join(missing)
        )
    if review["reserve_status"] not in {"available", "unavailable", "unknown"}:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.reserve_status is invalid"
        )
    if review["market_decline_status"] not in {
        "declining",
        "not_declining",
        "unclear",
    }:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.market_decline_status is invalid"
        )
    if source_name == "review_response.yaml":
        if review["theme_or_sector_decline_used_as_trigger"] is not False:
            raise ValueError(
                f"{source_name} must not use a theme or sector decline as the market trigger"
            )
        if (
            review["trigger_index_matches_deployment_target"] is False
            and review["market_decline_status"] != "unclear"
        ):
            raise ValueError(
                f"{source_name} market_decline_status must be unclear when the trigger index does not match the deployment target"
            )
        for index, source in enumerate(review["market_evidence"]):
            _validate_source(
                source,
                path=f"dip_buy_liquidity_deployment_review.market_evidence[{index}]",
            )
    if not isinstance(review["market_evidence"], list):
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.market_evidence must be a list"
        )
    if review["reserve_maintenance_is_objective"] is not False:
        raise ValueError(
            f"{source_name} must not treat reserve maintenance as the review objective"
        )
    if review["selected_action"] not in {
        "use",
        "hold",
        "not_applicable",
        "not_calculable",
    }:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.selected_action is invalid"
        )

    use_option = review["use_option"]
    use_required = {
        "considered",
        "status",
        "target",
        "amount_jpy",
        "formula",
        "timing",
        "rationale",
    }
    if not isinstance(use_option, dict):
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.use_option must be an object"
        )
    use_missing = sorted(use_required - set(use_option))
    if use_missing:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.use_option missing fields: "
            + ", ".join(use_missing)
        )
    if use_option["status"] not in {
        "executable",
        "conditional",
        "not_calculable",
        "not_applicable",
    }:
        raise ValueError(
            f"{source_name} dip_buy_liquidity_deployment_review.use_option.status is invalid"
        )

    declining_with_possible_reserve = (
        review["market_decline_status"] == "declining"
        and review["reserve_status"] != "unavailable"
    )
    if not declining_with_possible_reserve:
        return
    if use_option["considered"] is not True:
        raise ValueError(
            f"{source_name} must consider a dip-buy reserve use option in a declining market"
        )
    if use_option["status"] == "not_applicable":
        raise ValueError(
            f"{source_name} cannot mark the dip-buy reserve use option not_applicable "
            "in a declining market"
        )
    if not str(use_option.get("target") or "").strip():
        raise ValueError(
            f"{source_name} dip-buy reserve use option must identify a target"
        )
    if not str(use_option.get("timing") or "").strip():
        raise ValueError(
            f"{source_name} dip-buy reserve use option must identify timing"
        )
    if use_option.get("amount_jpy") is None and not str(
        use_option.get("formula") or ""
    ).strip():
        raise ValueError(
            f"{source_name} dip-buy reserve use option must provide an amount or formula"
        )
    if not str(use_option.get("rationale") or "").strip():
        raise ValueError(
            f"{source_name} dip-buy reserve use option must provide rationale"
        )


def _validate_canonical_tactical_liquidity_policy(
    policy,
    *,
    cash_assessment: dict,
    deployment_review: dict,
    policy_refs: list,
) -> None:
    if not isinstance(policy, dict):
        raise ValueError(
            "strategic_policy_decision.tactical_liquidity_policy must be an object"
        )
    required = {
        "policy_id",
        "status",
        "initial_target_pct_of_total_assets",
        "target_jpy",
        "deployment_asset",
        "trigger_index",
        "reference_high_definition",
        "price_basis",
        "lookback_period",
        "fx_treatment",
        "tranches",
        "amount_per_tranche",
        "refill_rule",
        "termination_rule",
        "policy_allocation_treatment",
        "rationale",
        "source_refs",
        "requires_user_approval",
    }
    missing = sorted(required - set(policy))
    if missing:
        raise ValueError(
            "strategic_policy_decision.tactical_liquidity_policy missing fields: "
            + ", ".join(missing)
        )
    if policy["requires_user_approval"] is not True:
        raise ValueError("tactical liquidity policy requires user approval")
    ratio = policy["initial_target_pct_of_total_assets"]
    if ratio is not None and not 0 <= Decimal(str(ratio)) <= 100:
        raise ValueError("tactical liquidity target percentage must be between 0 and 100")
    canonical_ref = "strategic_policy_decision.tactical_liquidity_policy"
    if cash_assessment.get("tactical_liquidity_policy_ref") != canonical_ref:
        raise ValueError("cash_assessment must reference the canonical tactical policy")
    if deployment_review.get("policy_ref") != canonical_ref:
        raise ValueError("deployment review must reference the canonical tactical policy")
    if policy["policy_id"] not in policy_refs:
        raise ValueError("decisions.policy_refs must reference tactical_liquidity_policy.policy_id")


def _validate_actions(
    actions,
    *,
    total_assets_jpy: Decimal | int | None,
) -> None:
    if not isinstance(actions, list):
        raise ValueError("decisions.actions must be a list")
    required = {
        "action_id",
        "status",
        "description",
        "source",
        "destination",
        "amount_jpy",
        "formula",
        "inputs",
        "assumption_independent_direction",
        "confirmed_conditions_consistent",
        "max_impact_if_assumptions_wrong_jpy",
        "timing",
        "rationale",
        "requires_user_approval",
    }
    valid_statuses = {"executable", "conditional", "on_hold"}
    valid_source_types = {
        "confirmed_user_condition",
        "observed_packet_fact",
        "machine_calculation",
        "evidence_based_inference",
        "explicit_assumption",
    }
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError(f"decisions.actions[{index}] must be an object")
        missing = sorted(required - set(action))
        if missing:
            raise ValueError(
                f"decisions.actions[{index}] missing audit fields: "
                + ", ".join(missing)
            )
        status = action["status"]
        if status not in valid_statuses:
            raise ValueError(f"decisions.actions[{index}] has invalid status {status!r}")
        if status == "executable" and not action["confirmed_conditions_consistent"]:
            raise ValueError(
                f"decisions.actions[{index}] cannot be executable when confirmed conditions conflict"
            )
        inputs = action["inputs"]
        if not isinstance(inputs, list):
            raise ValueError(f"decisions.actions[{index}].inputs must be a list")
        if not str(action["formula"]).strip() or not inputs:
            raise ValueError(
                f"decisions.actions[{index}] must show a formula and typed inputs"
            )
        for input_index, item in enumerate(inputs):
            if not isinstance(item, dict) or not {
                "name",
                "value",
                "source_type",
                "source_ref",
            }.issubset(item):
                raise ValueError(
                    f"decisions.actions[{index}].inputs[{input_index}] is incomplete"
                )
            if item["source_type"] not in valid_source_types:
                raise ValueError(
                    f"decisions.actions[{index}].inputs[{input_index}] has invalid source_type"
                )
        has_assumption = any(
            isinstance(item, dict)
            and item.get("source_type") == "explicit_assumption"
            for item in inputs
        )
        if action["requires_user_approval"] is not True:
            raise ValueError(
                f"decisions.actions[{index}] requires explicit user approval"
            )
        if status == "executable" and action["max_impact_if_assumptions_wrong_jpy"] is None:
            raise ValueError(
                f"decisions.actions[{index}] cannot be executable without maximum impact"
            )
        if status == "executable" and has_assumption:
            raise ValueError(
                f"decisions.actions[{index}] relies on an explicit assumption; mark it conditional"
            )


SOURCE_FIELDS = {
    "title",
    "publisher",
    "url",
    "publication_date",
    "accessed_at",
    "source_type",
    "claim_supported",
}


def _validate_source(source, *, path: str) -> None:
    if not isinstance(source, dict):
        raise ValueError(f"{path} must be an object")
    missing = sorted(SOURCE_FIELDS - set(source))
    if missing:
        raise ValueError(f"{path} missing fields: " + ", ".join(missing))
    if not str(source.get("url") or "").startswith(("https://", "http://")):
        raise ValueError(f"{path}.url must be an absolute web URL")


def _validate_empirical_evidence(items) -> None:
    required = {
        "evidence_id",
        "claim",
        "source",
        "observed_market_or_population",
        "observation_period",
        "result",
        "limitations",
        "decision_supported",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"empirical_evidence[{index}] is incomplete")
        _validate_source(item["source"], path=f"empirical_evidence[{index}].source")


def _validate_before_after_allocation(items) -> None:
    if not isinstance(items, list):
        raise ValueError("before_after_allocation must be a list")
    required = {
        "view",
        "category",
        "before_pct",
        "after_pct",
        "target_pct",
        "calculation_status",
    }
    grouped: dict[str, list[dict]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"before_after_allocation[{index}] is incomplete")
        grouped.setdefault(str(item["view"]), []).append(item)
    for view, rows in grouped.items():
        calculated = [row for row in rows if row["calculation_status"] == "calculated"]
        if calculated and all(row["after_pct"] is not None for row in calculated):
            total = sum(Decimal(str(row["after_pct"])) for row in calculated)
            if total != 100:
                raise ValueError(f"before_after_allocation {view} after_pct must total 100")


def _validate_account_tax_comparisons(items) -> None:
    if not isinstance(items, list):
        raise ValueError("account_tax_comparisons must be a list")
    required = {
        "comparison_id",
        "symbol",
        "account_type",
        "cost_basis_jpy",
        "unrealized_gain_loss_jpy",
        "tax_treatment",
        "nisa_impact",
        "estimated_after_tax_proceeds_jpy",
        "decision",
        "sources",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"account_tax_comparisons[{index}] is incomplete")
        for source_index, source in enumerate(item["sources"]):
            _validate_source(
                source,
                path=f"account_tax_comparisons[{index}].sources[{source_index}]",
            )


def _validate_order_proposals(items) -> None:
    if not isinstance(items, list):
        raise ValueError("decisions.order_proposals must be a list")
    required = {
        "proposal_id",
        "symbol",
        "account_type",
        "side",
        "status",
        "quantity",
        "amount_jpy",
        "formula",
        "inputs",
        "tax_and_account_analysis_ref",
        "rationale",
        "requires_user_approval",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"decisions.order_proposals[{index}] is incomplete")
        if item["requires_user_approval"] is not True:
            raise ValueError(
                f"decisions.order_proposals[{index}] requires explicit user approval"
            )


def _validate_execution_checks(items) -> None:
    if not isinstance(items, list):
        raise ValueError("codex_handoff.execution_checks must be a list")
    required = {"check_id", "status", "evidence", "blocking_action_ids"}
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"codex_handoff.execution_checks[{index}] is incomplete")


def _validate_prompt_feedback(items) -> None:
    required = {
        "feedback_id",
        "category",
        "severity",
        "problem",
        "recommended_change",
        "affected_path",
    }
    for index, item in enumerate(items):
        if not isinstance(item, dict) or required - set(item):
            raise ValueError(f"codex_handoff.prompt_feedback[{index}] is incomplete")


def values_equal(actual, expected) -> bool:
    if actual is None or expected is None:
        return actual is None and expected is None
    if isinstance(actual, (int, float, Decimal)) and isinstance(
        expected, (int, float, Decimal)
    ):
        return Decimal(str(actual)) == Decimal(str(expected))
    return actual == expected


def _validate_security_story_coverage(
    reviews,
    *,
    expected_security_symbols: set[str],
    source_name: str,
) -> None:
    if not isinstance(reviews, list):
        raise ValueError("security_story_reviews must be a list")
    symbols = [str(item.get("symbol")) for item in reviews if isinstance(item, dict)]
    duplicate_symbols = sorted({symbol for symbol in symbols if symbols.count(symbol) > 1})
    if duplicate_symbols:
        raise ValueError(
            f"{source_name} security_story_reviews contains duplicate symbols: "
            + ", ".join(duplicate_symbols)
        )
    actual_symbols = set(symbols)
    if actual_symbols != expected_security_symbols:
        missing_symbols = sorted(expected_security_symbols - actual_symbols)
        extra_symbols = sorted(actual_symbols - expected_security_symbols)
        raise ValueError(
            f"{source_name} security_story_reviews coverage mismatch; "
            f"missing={missing_symbols}, extra={extra_symbols}"
        )
    for review in reviews:
        for field in (
            "evaluated",
            "story_health",
            "decision",
            "decision_rationale",
            "next_review_triggers",
            "sources",
        ):
            if field not in review:
                raise ValueError(
                    f"security_story_reviews[{review.get('symbol')}] missing {field}"
                )
        if source_name == "review_response.yaml":
            for index, source in enumerate(review["sources"]):
                _validate_source(
                    source,
                    path=(
                        f"security_story_reviews[{review.get('symbol')}].sources[{index}]"
                    ),
                )


def _validate_thematic_fund_coverage(
    reviews,
    *,
    expected_member_symbols: set[str],
) -> None:
    if not isinstance(reviews, list):
        raise ValueError("thematic_fund_reviews must be a list")
    actual_members: list[str] = []
    for index, review in enumerate(reviews):
        if not isinstance(review, dict):
            raise ValueError(f"thematic_fund_reviews[{index}] must be an object")
        required = {
            "theme_review_id",
            "product_name",
            "member_symbols",
            "index_story",
            "material_facts",
            "story_health",
            "decision",
            "decision_rationale",
            "sources",
            "account_lot_reviews",
        }
        missing = sorted(required - set(review))
        if missing:
            raise ValueError(
                f"thematic_fund_reviews[{index}] missing fields: "
                + ", ".join(missing)
            )
        members = [str(item) for item in review["member_symbols"]]
        actual_members.extend(members)
        lot_symbols = {
            str(item.get("symbol"))
            for item in review["account_lot_reviews"]
            if isinstance(item, dict)
        }
        if lot_symbols != set(members):
            raise ValueError(
                f"thematic_fund_reviews[{index}] account lot coverage mismatch"
            )
        for source_index, source in enumerate(review["sources"]):
            _validate_source(
                source,
                path=f"thematic_fund_reviews[{index}].sources[{source_index}]",
            )
    duplicates = sorted(
        {symbol for symbol in actual_members if actual_members.count(symbol) > 1}
    )
    if duplicates:
        raise ValueError(
            "thematic_fund_reviews contains duplicate member symbols: "
            + ", ".join(duplicates)
        )
    if set(actual_members) != expected_member_symbols:
        raise ValueError(
            "thematic_fund_reviews coverage mismatch; "
            f"missing={sorted(expected_member_symbols - set(actual_members))}, "
            f"extra={sorted(set(actual_members) - expected_member_symbols)}"
        )
