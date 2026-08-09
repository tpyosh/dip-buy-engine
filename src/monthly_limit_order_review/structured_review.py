from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .models import ReviewFeedback, ReviewOrderProposal
from .review_readiness import classify_review_account_type
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
    "date_timeline_is_canonical_and_cash_flows_do_not_overlap",
    "retirement_mortgage_cash_flows_are_included_without_double_counting",
    "recurring_contributions_are_reconciled_before_policy_derivation",
    "capital_market_assumptions_are_complete_and_common_to_all_candidates",
    "required_return_calculation_is_reproducible",
    "success_probability_calculation_is_reproducible",
    "candidate_grid_is_exhaustive_and_not_stopped_at_a_selected_boundary",
    "equity_bond_other_and_core_satellite_denominators_are_consistent",
    "approved_and_proposed_semiconductor_limits_are_separated",
    "strategic_policy_implementation_and_account_lot_statuses_are_separated",
    "strategic_policy_precedes_implementation",
    "tactical_liquidity_candidates_follow_finite_grid_and_selection_rule",
    "other_pct_and_crypto_options_follow_finite_grids_and_selection_rule",
    "tactical_liquidity_policy_is_locked_before_current_market_evaluation",
    "execution_capability_gate_prevents_fabricated_calculations",
    "rounding_residuals_use_explicit_tolerances",
    "mortgage_source_values_are_used_without_generic_revalidation",
    "recommendation_window_is_reviewer_selected_and_actionable",
    "next_review_recommendation_matches_the_window",
}
STATIC_REFERENCE_CHECKS = {
    "no_undefined_packet_reference",
    "no_deprecated_date_alias",
    "no_unapproved_material_trade_threshold",
    "one_canonical_tactical_liquidity_policy",
    "allocation_percentages_total_100",
    "no_machine_ids_in_human_sections",
    "no_external_response_schema_reference",
    "selected_recurring_source_is_versioned",
    "no_inactive_750000_monthly_constraint",
    "all_root_arrays_have_inline_schema",
}
SEMANTIC_VALIDATION_CHECKS = {
    "candidate_id_values_are_unique",
    "check_id_values_are_unique",
    "tactical_liquidity_grid_has_5_required_rows",
    "other_pct_grid_has_5_required_rows",
    "crypto_option_grid_has_3_required_rows",
    "equity_bond_candidate_grid_has_11_required_rows",
    "allocation_weights_total_100_within_tolerance",
    "exactly_one_policy_candidate_is_selected",
    "selected_policy_candidate_is_feasible",
    "all_review_targets_appear_exactly_once",
    "holding_values_reconcile_to_total_assets",
    "before_after_amounts_reconcile",
    "purchase_amounts_reconcile_to_funding_sources",
    "sale_amounts_reconcile_to_sale_details",
    "strategic_policy_precedes_implementation",
    "recommendation_window_starts_at_request_and_has_positive_duration",
    "next_review_date_is_not_before_recommendation_window_end",
}
REQUIRED_CAPABILITIES = {
    "monthly_cash_flow_calculation",
    "bisection_required_return_calculation",
    "multivariate_monthly_monte_carlo",
    "fixed_random_seed",
    "complete_11_candidate_comparison",
    "interest_rate_sensitivity_calculation",
    "candidate_allocation_order_arithmetic_reconciliation",
    "yaml_or_json_schema_validation",
}
ROUNDING_TOLERANCE_JPY = Decimal("10")
ROUNDING_TOLERANCE_PCT_POINTS = Decimal("0.02")


@lru_cache(maxsize=1)
def _monthly_response_schema_validator() -> Draft202012Validator:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas/monthly-review-response.schema.yaml"
    )
    schema = load_yaml(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate_against_monthly_response_schema(payload: dict) -> None:
    errors = sorted(
        _monthly_response_schema_validator().iter_errors(payload),
        key=lambda error: tuple(str(item) for item in error.absolute_path),
    )
    if not errors:
        return
    error = errors[0]
    location = ".".join(str(item) for item in error.absolute_path) or "<root>"
    raise ValueError(
        "review_response.yaml JSON Schema validation failed at "
        f"{location}: {error.message}"
    )


def load_monthly_review_response(
    path,
    *,
    expected_month: str,
    expected_security_symbols: set[str],
    expected_thematic_member_symbols: set[str] | None = None,
    expected_cash_context: dict | None = None,
    expected_date_context: dict | None = None,
    total_assets_jpy: Decimal | int | None = None,
    expected_current_holding_symbols: set[str] | None = None,
    expected_current_holding_accounts: dict[str, str] | None = None,
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
        expected_current_holding_symbols=(
            expected_current_holding_symbols
            or set((expected_current_holding_accounts or {}).keys())
        ),
        expected_current_holding_accounts=expected_current_holding_accounts or {},
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
    expected_current_holding_symbols: set[str],
    expected_current_holding_accounts: dict[str, str],
) -> None:
    if payload.get("schema_version") != 2:
        raise ValueError("review_response.yaml schema_version must be 2")
    if payload.get("artifact_type") != "investment_review_response":
        raise ValueError("review_response.yaml artifact_type must be investment_review_response")
    if payload.get("review_cadence") != "on_demand":
        raise ValueError("review_response.yaml review_cadence must be on_demand")
    if payload.get("review_target_month") != expected_month:
        raise ValueError(
            "review_response.yaml review_target_month does not match the snapshot month"
        )
    required = {
        "review_cadence",
        "review_mode",
        "interaction_phase",
        "portfolio_snapshot_as_of",
        "market_reference_as_of",
        "packet_generated_at",
        "research_cutoff_at",
        "decision_date",
        "recommendation_window",
        "next_review_recommendation",
        "review_completion_status",
        "execution_capability_gate",
        "strategic_policy_decision",
        "implementation_decision",
        "account_lot_execution",
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
        "static_reference_checks",
        "validation_tolerances",
        "rounding_reconciliation",
        "semantic_validation_checks",
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

    _validate_review_timing_contract(
        payload["recommendation_window"],
        payload["next_review_recommendation"],
        packet_generated_at=payload["packet_generated_at"],
    )

    _validate_execution_capability_gate(payload["execution_capability_gate"])
    _validate_strategic_policy_decision(
        payload["strategic_policy_decision"],
        review_mode=payload["review_mode"],
    )
    _validate_decision_stages(
        strategic=payload["strategic_policy_decision"],
        implementation=payload["implementation_decision"],
        account_lot=payload["account_lot_execution"],
        review_completion_status=payload["review_completion_status"],
    )
    if payload["interaction_phase"] != "final_review":
        raise ValueError("review_response.yaml interaction_phase must be final_review")
    _validate_updated_inputs(payload["strategic_policy_decision"]["updated_inputs"])
    _validate_decision_axes(payload["decision_axes"])
    if not isinstance(payload["empirical_evidence"], list):
        raise ValueError("empirical_evidence must be a list")
    research_cutoff_at = payload["research_cutoff_at"]
    _validate_empirical_evidence(
        payload["empirical_evidence"],
        research_cutoff_at=research_cutoff_at,
    )
    _validate_decision_quality_checks(
        payload["decision_quality_checks"],
    )
    _validate_required_checks(
        payload["static_reference_checks"],
        required_ids=STATIC_REFERENCE_CHECKS,
        name="static_reference_checks",
    )
    _validate_tolerances_and_rounding(
        payload["validation_tolerances"],
        payload["rounding_reconciliation"],
    )
    _validate_semantic_validation_checks(payload["semantic_validation_checks"])

    _validate_security_story_coverage(
        payload["security_story_reviews"],
        expected_security_symbols=expected_security_symbols,
        source_name="review_response.yaml",
        research_cutoff_at=research_cutoff_at,
    )
    _validate_thematic_fund_coverage(
        payload["thematic_fund_reviews"],
        expected_member_symbols=expected_thematic_member_symbols,
        research_cutoff_at=research_cutoff_at,
    )
    _validate_before_after_allocation(payload["before_after_allocation"])
    _validate_account_tax_comparisons(
        payload["account_tax_comparisons"],
        research_cutoff_at=research_cutoff_at,
    )
    _validate_cash_assessment(
        payload["cash_assessment"],
        expected_cash_context=expected_cash_context,
    )
    _validate_dip_buy_liquidity_deployment_review(
        payload["dip_buy_liquidity_deployment_review"],
        source_name="review_response.yaml",
        research_cutoff_at=research_cutoff_at,
    )

    decisions = payload["decisions"]
    decision_fields = {
        "policy_refs",
        "portfolio_diagnosis",
        "rule_refs",
        "order_proposals",
        "actions",
        "new_asset_purchase_conclusion",
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
    _validate_actions(
        decisions["actions"],
        total_assets_jpy=total_assets_jpy,
        expected_current_holding_symbols=expected_current_holding_symbols,
        expected_current_holding_accounts=expected_current_holding_accounts,
        new_asset_purchase_conclusion=decisions["new_asset_purchase_conclusion"],
    )
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
    _validate_against_monthly_response_schema(payload)


def _validate_execution_capability_gate(gate) -> None:
    _require_mapping_fields(
        gate,
        {"gate_status", "evaluated_before_calculations", "capabilities"},
        name="execution_capability_gate",
    )
    if gate["evaluated_before_calculations"] is not True:
        raise ValueError("execution capability gate must run before calculations")
    capabilities = gate["capabilities"]
    if not isinstance(capabilities, list):
        raise ValueError("execution_capability_gate.capabilities must be a list")
    by_id: dict[str, dict] = {}
    for index, capability in enumerate(capabilities):
        _require_mapping_fields(
            capability,
            {
                "capability_id",
                "status",
                "evidence",
                "reason",
                "missing_capability",
                "remediation",
            },
            name=f"execution_capability_gate.capabilities[{index}]",
        )
        capability_id = str(capability["capability_id"])
        if capability_id in by_id:
            raise ValueError("execution capability gate contains duplicate capability_id")
        if capability["status"] not in {"available", "partial", "unavailable"}:
            raise ValueError("execution capability status is invalid")
        if capability["status"] == "available":
            if not str(capability["evidence"]).strip():
                raise ValueError("available capability requires evidence")
            if capability["missing_capability"]:
                raise ValueError("available capability cannot list missing_capability")
        elif (
            not str(capability["reason"]).strip()
            or not capability["missing_capability"]
            or not str(capability["remediation"]).strip()
        ):
            raise ValueError(
                "partial or unavailable capability requires reason, missing_capability, and remediation"
            )
        by_id[capability_id] = capability
    if set(by_id) != REQUIRED_CAPABILITIES:
        raise ValueError("execution capability gate must cover all required capabilities exactly once")
    statuses = {item["status"] for item in capabilities}
    expected_gate_status = (
        "all_available"
        if statuses == {"available"}
        else "unavailable"
        if statuses == {"unavailable"}
        else "partial"
    )
    if gate["gate_status"] != expected_gate_status:
        raise ValueError("execution_capability_gate.gate_status conflicts with capability rows")


def _validate_decision_stages(
    *,
    strategic: dict,
    implementation: dict,
    account_lot: dict,
    review_completion_status: str,
) -> None:
    if strategic.get("stage") != "strategic_policy_stage":
        raise ValueError("strategic_policy_decision.stage must be strategic_policy_stage")
    _require_mapping_fields(
        implementation,
        {
            "stage",
            "status",
            "reason",
            "remediation",
            "strategic_policy_ref",
            "strategic_policy_status_at_start",
            "strategy_locked_before_market_evaluation",
            "product_decision_refs",
            "tactical_deployment_ref",
            "before_after_allocation_ref",
        },
        name="implementation_decision",
    )
    if implementation["stage"] != "implementation_stage":
        raise ValueError("implementation_decision.stage must be implementation_stage")
    if implementation["status"] not in {"complete", "partial", "blocked", "not_applicable"}:
        raise ValueError("implementation_decision.status is invalid")
    if implementation["status"] in {"complete", "partial"}:
        if strategic["status"] not in {"complete", "not_applicable"}:
            raise ValueError("implementation cannot precede an available strategic or approved policy")
        if implementation["strategic_policy_status_at_start"] != strategic["status"]:
            raise ValueError("implementation must record the strategic policy status at stage start")
        if implementation["strategy_locked_before_market_evaluation"] is not True:
            raise ValueError("implementation must lock strategy before market evaluation")
    _require_mapping_fields(
        account_lot,
        {
            "status",
            "reason",
            "remediation",
            "implementation_decision_ref",
            "missing_information",
            "executable_order_proposal_ids",
            "blocked_order_proposal_ids",
        },
        name="account_lot_execution",
    )
    if account_lot["status"] not in {"complete", "blocked", "not_calculable", "not_applicable"}:
        raise ValueError("account_lot_execution.status is invalid")
    if account_lot["status"] in {"blocked", "not_calculable"} and (
        not str(account_lot["reason"]).strip()
        or not str(account_lot["remediation"]).strip()
        or not account_lot["missing_information"]
    ):
        raise ValueError(
            "blocked account-lot execution requires reason, remediation, and missing_information"
        )
    if review_completion_status == "invalid":
        raise ValueError("invalid review_completion_status cannot be ingested")
    if strategic["status"] == "blocked":
        expected = "blocked"
    elif implementation["status"] in {"partial", "blocked"} or account_lot["status"] in {
        "blocked",
        "not_calculable",
    }:
        expected = "complete_with_execution_blocks"
    else:
        expected = "complete"
    if review_completion_status != expected:
        raise ValueError(
            "review_completion_status conflicts with strategic, implementation, and account-lot statuses"
        )


def _validate_tolerances_and_rounding(tolerances, rounding) -> None:
    _require_mapping_fields(
        tolerances,
        {
            "rounding_tolerance_jpy",
            "rounding_tolerance_pct_points",
            "monte_carlo_probability_tolerance_pct_points",
            "return_volatility_tolerance_pct_points",
        },
        name="validation_tolerances",
    )
    expected = {
        "rounding_tolerance_jpy": ROUNDING_TOLERANCE_JPY,
        "rounding_tolerance_pct_points": ROUNDING_TOLERANCE_PCT_POINTS,
        "monte_carlo_probability_tolerance_pct_points": Decimal("0.01"),
        "return_volatility_tolerance_pct_points": Decimal("0.01"),
    }
    for field, value in expected.items():
        if Decimal(str(tolerances[field])) != value:
            raise ValueError(f"validation_tolerances.{field} must equal {value}")
    _require_mapping_fields(
        rounding,
        {
            "rounding_tolerance_jpy",
            "rounding_tolerance_pct_points",
            "rounding_residual_jpy",
            "rounding_residual_pct_points",
            "rounding_residual_treatment",
            "evidence",
        },
        name="rounding_reconciliation",
    )
    residual_jpy = abs(Decimal(str(rounding["rounding_residual_jpy"])))
    residual_pct_raw = rounding["rounding_residual_pct_points"]
    residual_pct = (
        abs(Decimal(str(residual_pct_raw))) if residual_pct_raw is not None else Decimal("0")
    )
    within = (
        residual_jpy <= ROUNDING_TOLERANCE_JPY
        and residual_pct <= ROUNDING_TOLERANCE_PCT_POINTS
    )
    if within and rounding["rounding_residual_treatment"] != "within_tolerance_recorded":
        raise ValueError("within-tolerance rounding residual must be recorded, not failed")
    if not within and rounding["rounding_residual_treatment"] == "within_tolerance_recorded":
        raise ValueError("rounding residual exceeds the explicit tolerance")


def _validate_semantic_validation_checks(checks) -> None:
    _validate_required_checks(
        checks,
        required_ids=SEMANTIC_VALIDATION_CHECKS,
        name="semantic_validation_checks",
        additional_required_fields={
            "observed_value",
            "expected_value",
            "difference",
            "tolerance",
        },
    )
    failed_ids = [
        str(check["check_id"])
        for check in checks
        if check["status"] == "fail"
    ]
    if failed_ids:
        raise ValueError(
            "semantic validation failed: " + ", ".join(sorted(failed_ids))
        )


def _validate_review_timing_contract(
    recommendation_window,
    next_review_recommendation,
    *,
    packet_generated_at: str,
) -> None:
    _require_mapping_fields(
        recommendation_window,
        {
            "start_at",
            "end_at",
            "window_length",
            "window_unit",
            "selection_rationale",
            "confidence_boundary",
        },
        name="recommendation_window",
    )
    _require_mapping_fields(
        next_review_recommendation,
        {
            "review_after_at",
            "interval_value",
            "interval_unit",
            "rationale",
            "early_review_triggers",
            "closing_sentence",
        },
        name="next_review_recommendation",
    )
    requested_at = _parse_datetime(
        packet_generated_at,
        path="packet_generated_at",
    )
    start_at = _parse_datetime(
        recommendation_window["start_at"],
        path="recommendation_window.start_at",
    )
    end_at = _parse_datetime(
        recommendation_window["end_at"],
        path="recommendation_window.end_at",
    )
    if start_at.astimezone(UTC) != requested_at.astimezone(UTC):
        raise ValueError(
            "recommendation_window.start_at must equal packet_generated_at"
        )
    if end_at <= start_at:
        raise ValueError("recommendation_window.end_at must be after start_at")

    review_after_at = date.fromisoformat(
        str(next_review_recommendation["review_after_at"])
    )
    tokyo_end_date = end_at.astimezone(ZoneInfo("Asia/Tokyo")).date()
    if review_after_at < tokyo_end_date:
        raise ValueError(
            "next_review_recommendation.review_after_at must not be before "
            "recommendation_window.end_at"
        )
    japanese_units = {"days": "日", "weeks": "週間", "months": "か月"}
    expected_closing = (
        f"また{next_review_recommendation['interval_value']}"
        f"{japanese_units[next_review_recommendation['interval_unit']]}後"
        f"（{review_after_at.isoformat()}）に最新のスナップショットをもとに"
        "レビュー依頼を出してください。"
    )
    if next_review_recommendation["closing_sentence"] != expected_closing:
        raise ValueError(
            "next_review_recommendation.closing_sentence does not match its interval and date"
        )


def _validate_strategic_policy_decision(decision, *, review_mode: str) -> None:
    if review_mode not in {
        "on_demand_operational_review",
        "strategic_policy_second_opinion",
    }:
        raise ValueError("review_response.yaml review_mode is invalid")
    if not isinstance(decision, dict):
        raise ValueError("strategic_policy_decision must be an object")
    required = {
        "stage",
        "status",
        "reason",
        "remediation",
        "objective",
        "updated_inputs",
        "financial_planning_model",
        "recommended_policy",
        "policy_allocation_within_investable_portfolio",
        "household_total_asset_allocation",
        "tactical_liquidity_policy",
        "active_risk_policy",
        "direct_semiconductor_limit",
        "tactical_liquidity_candidate_comparison",
        "crypto_contribution_option_comparison",
        "other_allocation_candidate_comparison",
        "candidate_methodology",
        "candidate_comparison",
    }
    missing = sorted(required - set(decision))
    if missing:
        raise ValueError(
            "strategic_policy_decision missing fields: " + ", ".join(missing)
        )
    status = decision["status"]
    allowed_statuses = (
        {"not_applicable"}
        if review_mode == "on_demand_operational_review"
        else {"complete", "blocked"}
    )
    if status not in allowed_statuses:
        raise ValueError(
            "strategic_policy_decision.status conflicts with review_mode; "
            f"allowed={sorted(allowed_statuses)}"
        )
    if status == "blocked" and (
        not str(decision["reason"]).strip()
        or not str(decision["remediation"]).strip()
    ):
        raise ValueError(
            "blocked strategic_policy_decision requires reason and remediation"
        )
    _validate_financial_planning_model(
        decision["financial_planning_model"],
        strategic=review_mode == "strategic_policy_second_opinion",
        allow_blocked=status == "blocked",
    )
    if review_mode == "on_demand_operational_review":
        if any(
            decision[field]
            for field in (
                "tactical_liquidity_candidate_comparison",
                "crypto_contribution_option_comparison",
                "other_allocation_candidate_comparison",
                "candidate_comparison",
            )
        ):
            raise ValueError(
                "on-demand operational strategic policy candidate comparisons must be empty"
            )
        return

    direct_limit = decision["direct_semiconductor_limit"]
    _require_mapping_fields(
        direct_limit,
        {"current_approved_constraint", "proposed_future_policy", "priority"},
        name="direct_semiconductor_limit",
    )
    current_limit = direct_limit["current_approved_constraint"]
    proposed_limit = direct_limit["proposed_future_policy"]
    _require_mapping_fields(
        current_limit,
        {"policy_id", "status", "limit_pct", "denominator", "approved", "rationale"},
        name="direct_semiconductor_limit.current_approved_constraint",
    )
    _require_mapping_fields(
        proposed_limit,
        {"policy_id", "status", "limit_pct", "denominator", "approved", "rationale"},
        name="direct_semiconductor_limit.proposed_future_policy",
    )
    if current_limit["approved"] is not True or proposed_limit["approved"] is not False:
        raise ValueError("approved and proposed semiconductor limits must remain separate")

    _validate_policy_precursor_comparisons(decision, allow_unselected=status == "blocked")
    if status == "blocked":
        _validate_candidate_comparison(decision, allow_unselected=True)
        return

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
    if status == "complete":
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
                "reason",
                "remediation",
                "policy_basis_as_of",
                "locked_before_market_evaluation",
                "initial_target_pct_of_total_assets",
                "target_jpy",
                "deployment_asset",
                "trigger_index",
                "reference_high_definition",
                "decline_threshold_pct",
                "price_basis",
                "lookback_period",
                "fx_treatment",
                "tranches",
                "amount_per_tranche",
                "minimum_balance_jpy",
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
            "policy_basis_as_of",
            "locked_before_market_evaluation",
            "initial_target_pct_of_total_assets",
            "target_jpy",
            "deployment_asset",
            "trigger_index",
            "reference_high_definition",
            "decline_threshold_pct",
            "price_basis",
            "lookback_period",
            "fx_treatment",
            "tranches",
            "amount_per_tranche",
            "minimum_balance_jpy",
            "refill_rule",
            "termination_rule",
            "policy_allocation_treatment",
        )
        if any(tactical[field] is None for field in tactical_required_values):
            raise ValueError("strategic tactical_liquidity_policy must be complete")
        if tactical["locked_before_market_evaluation"] is not True:
            raise ValueError("tactical liquidity policy must be locked before market evaluation")
        active_risk = decision["active_risk_policy"]
        _require_mapping_fields(
            active_risk,
            {
                "policy_id",
                "satellites_allowed",
                "satellite_target_pct_of_investable_portfolio",
                "selected_satellite_securities",
                "all_country_only_baseline_compared",
                "selection_rationale",
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
                "satellite_target_pct_of_investable_portfolio",
            )
        ):
            raise ValueError("strategic active_risk_policy caps must be complete")
        if active_risk["satellites_allowed"] is True:
            if Decimal(
                str(active_risk["satellite_target_pct_of_investable_portfolio"])
            ) <= 0:
                raise ValueError("strategic satellite target must be positive")
            if not active_risk["selected_satellite_securities"]:
                raise ValueError("strategic satellite securities must be selected")
            if active_risk["all_country_only_baseline_compared"] is not True:
                raise ValueError("strategic satellite policy must compare the all-country-only baseline")
            selected_satellites = active_risk["selected_satellite_securities"]
            selected_symbols = [str(item["symbol"]) for item in selected_satellites]
            if len(selected_symbols) != len(set(selected_symbols)):
                raise ValueError("strategic satellite securities must be unique")
            selected_total = sum(
                (
                    Decimal(str(item["target_pct_of_investable_portfolio"]))
                    for item in selected_satellites
                ),
                start=Decimal("0"),
            )
            satellite_target = Decimal(
                str(active_risk["satellite_target_pct_of_investable_portfolio"])
            )
            if abs(selected_total - satellite_target) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    "strategic satellite security weights must reconcile to the satellite target"
                )
            total_cap = Decimal(str(active_risk["total_satellite_cap_pct"]))
            single_cap = Decimal(str(active_risk["single_security_cap_pct"]))
            if satellite_target > total_cap:
                raise ValueError("strategic satellite target exceeds the total satellite cap")
            if any(
                Decimal(str(item["target_pct_of_investable_portfolio"]))
                > single_cap
                for item in selected_satellites
            ):
                raise ValueError("strategic satellite security exceeds the single-security cap")
        if not isinstance(decision["candidate_methodology"], dict):
            raise ValueError("strategic candidate_methodology must be an object")
        _validate_candidate_comparison(decision, allow_unselected=False)


def _validate_policy_precursor_comparisons(
    decision: dict,
    *,
    allow_unselected: bool,
) -> None:
    configurations = [
        (
            "tactical_liquidity_candidate_comparison",
            "candidate_id",
            "target_pct_of_household_total_assets",
            [Decimal("0"), Decimal("2.5"), Decimal("5"), Decimal("7.5"), Decimal("10")],
            {
                "denominator",
                "household_reserve_separate",
                "long_term_investable_asset_reduction_jpy",
                "required_real_return_impact_pct_points",
                "success_probability_impact_pct_points",
                "deployable_amount_jpy",
                "expected_return_drag_pct_points",
                "implementation_complexity",
                "replenishment_feasibility",
                "candidate_feasible",
                "calculation_status",
                "reason",
                "missing_capability",
                "remediation",
                "selected",
            },
        ),
        (
            "crypto_contribution_option_comparison",
            "option_id",
            "policy",
            [
                "stop_new_contributions_and_exclude_unknown_existing_balance",
                "continue_only_within_realized_surplus_such_as_bonus",
                "continue_current_contributions_and_disclose_cash_flow_and_success_probability_impact",
            ],
            {
                "current_crypto_balance_jpy",
                "ordinary_month_cash_flow_impact_jpy",
                "success_probability_impact_pct_points",
                "funding_source_treatment",
                "calculation_status",
                "reason",
                "missing_capability",
                "remediation",
                "selected",
            },
        ),
        (
            "other_allocation_candidate_comparison",
            "candidate_id",
            "other_pct",
            [Decimal("0"), Decimal("1"), Decimal("2"), Decimal("3"), Decimal("5")],
            {
                "crypto_contribution_option_ref",
                "current_crypto_balance_jpy",
                "ordinary_month_cash_flow_consistent",
                "required_success_probability_maintained",
                "success_probability_impact_pct_points",
                "expected_return_impact_pct_points",
                "diversification_benefit",
                "incremental_risk",
                "funding_source_consistency",
                "candidate_feasible",
                "calculation_status",
                "reason",
                "missing_capability",
                "remediation",
                "selected",
            },
        ),
    ]
    for name, id_field, value_field, expected_values, required_fields in configurations:
        rows = decision[name]
        if not isinstance(rows, list) or len(rows) != len(expected_values):
            raise ValueError(f"{name} must contain the complete finite candidate grid")
        ids: set[str] = set()
        actual_values = []
        selected = []
        not_calculable_count = 0
        for index, row in enumerate(rows):
            _require_mapping_fields(
                row,
                required_fields | {id_field, value_field},
                name=f"{name}[{index}]",
            )
            row_id = str(row[id_field])
            if row_id in ids:
                raise ValueError(f"{name} contains duplicate {id_field}")
            ids.add(row_id)
            value = row[value_field]
            actual_values.append(
                Decimal(str(value)) if isinstance(expected_values[0], Decimal) else value
            )
            if row["calculation_status"] not in {"calculated", "not_calculable"}:
                raise ValueError(f"{name}[{index}].calculation_status is invalid")
            if row["calculation_status"] == "not_calculable":
                not_calculable_count += 1
                if (
                    not str(row["reason"]).strip()
                    or not row["missing_capability"]
                    or not str(row["remediation"]).strip()
                    or row["selected"] is not False
                ):
                    raise ValueError(
                        f"{name}[{index}] not_calculable requires missing capability and cannot be selected"
                    )
            elif row["missing_capability"]:
                raise ValueError(f"{name}[{index}] calculated row cannot list missing_capability")
            if row["selected"] is True:
                selected.append(row)
        if sorted(actual_values) != sorted(expected_values):
            raise ValueError(f"{name} does not match the required finite grid")
        if len(selected) > 1:
            raise ValueError(f"{name} must not select multiple rows")
        if not allow_unselected and len(selected) != 1:
            raise ValueError(f"{name} must select exactly one row")
        if allow_unselected and not selected and not_calculable_count == 0:
            raise ValueError(f"blocked {name} without selection must identify not_calculable rows")
        if selected and "candidate_feasible" in selected[0] and selected[0]["candidate_feasible"] is not True:
            raise ValueError(f"selected row in {name} must be feasible")


def _validate_financial_planning_model(
    model: dict,
    *,
    strategic: bool,
    allow_blocked: bool,
) -> None:
    required = {
        "status",
        "reason",
        "remediation",
        "return_basis",
        "current_age",
        "withdrawal_start_age",
        "planning_end_age",
        "retirement_spending_current_jpy_per_month",
        "retirement_spending_derivation",
        "public_pension_annual_current_jpy",
        "public_pension_estimation_method",
        "long_term_contribution_policy",
        "contribution_reconciliation",
        "planning_timeline",
        "liability_cash_flows",
        "inheritance_included_in_base_case",
        "inheritance_base_case_jpy",
        "inheritance_treatment",
        "terminal_asset_floor_current_jpy",
        "success_probability_pct",
        "success_probability_rationale",
        "target_return_pct",
        "target_return_formula",
        "required_return_calculation",
        "success_probability_calculation",
        "sensitivity_cases",
        "source_refs",
    }
    _require_mapping_fields(model, required, name="financial_planning_model")
    contribution = model["long_term_contribution_policy"]
    contribution_fields = {
        "annual_net_contribution_jpy",
        "contribution_end_age",
        "contribution_end_date",
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
    if allow_blocked and model["status"] in {"blocked", "partial"}:
        if not str(model["reason"]).strip() or not str(model["remediation"]).strip():
            raise ValueError(
                "blocked or partial financial_planning_model requires reason and remediation"
            )
        for field in ("required_return_calculation", "success_probability_calculation"):
            calculation = model[field]
            _require_mapping_fields(
                calculation,
                {"status", "reason", "missing_capability", "remediation"},
                name=f"financial_planning_model.{field}",
            )
            if calculation["status"] == "not_calculable" and (
                not str(calculation["reason"]).strip()
                or not calculation["missing_capability"]
                or not str(calculation["remediation"]).strip()
            ):
                raise ValueError(
                    f"strategic {field} not_calculable requires missing_capability"
                )
        return
    if model["status"] != "complete":
        raise ValueError("strategic financial_planning_model must be complete")
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
    if not model["contribution_reconciliation"]:
        raise ValueError("strategic contribution_reconciliation must be complete")
    _require_mapping_fields(
        model["planning_timeline"],
        {
            "model_start_date",
            "contribution_end_date",
            "first_withdrawal_date",
            "planned_retirement_date",
            "public_pension_start_date",
            "mortgage_repayment_end_date",
            "planning_end_date",
            "model_period",
            "overlap_check",
        },
        name="financial_planning_model.planning_timeline",
    )
    if model["planning_timeline"]["overlap_check"] != "pass":
        raise ValueError("financial planning timeline overlap check must pass")
    if not model["liability_cash_flows"]:
        raise ValueError("strategic liability_cash_flows must include the mortgage")
    for index, liability in enumerate(model["liability_cash_flows"]):
        _require_mapping_fields(
            liability,
            {
                "bank_document_values_are_authoritative",
                "generic_amortization_recalculation_performed",
                "arithmetic_mismatch_used_for_warning_or_block",
            },
            name=f"financial_planning_model.liability_cash_flows[{index}]",
        )
        if liability["bank_document_values_are_authoritative"] is not True:
            raise ValueError("bank-document mortgage values must remain authoritative")
        if liability["generic_amortization_recalculation_performed"] is not False:
            raise ValueError("generic mortgage amortization revalidation is prohibited")
        if liability["arithmetic_mismatch_used_for_warning_or_block"] is not False:
            raise ValueError("mortgage arithmetic mismatch must not trigger warning or blocking")
    for field in ("required_return_calculation", "success_probability_calculation"):
        calculation = model[field]
        _require_mapping_fields(
            calculation,
            {"status", "reason", "missing_capability", "remediation"},
            name=f"financial_planning_model.{field}",
        )
        if calculation["status"] != "calculated":
            raise ValueError(f"strategic {field} must be calculated")
        if calculation["missing_capability"]:
            raise ValueError(f"calculated strategic {field} cannot list missing_capability")
    if not model["sensitivity_cases"] or not model["source_refs"]:
        raise ValueError(
            "strategic financial_planning_model requires sensitivity cases and sources"
        )


def _validate_candidate_comparison(
    decision: dict,
    *,
    allow_unselected: bool,
) -> None:
    methodology_fields = {
        "selection_sequence",
        "tactical_liquidity_candidate_grid",
        "other_pct_candidate_grid",
        "crypto_contribution_option_grid",
        "global_equity_index",
        "bond_index",
        "bond_instrument_type",
        "bond_currency",
        "bond_fx_hedge_policy",
        "estimation_period",
        "assumptions_as_of",
        "inflation_assumption_pct",
        "return_basis",
        "tax_cost_treatment",
        "major_drawdown_definition",
        "rebalancing_frequency",
        "candidate_grid",
        "other_pct_common_base_case",
        "assumption_derivations",
        "required_return_method",
        "success_probability_method",
        "range_rationale",
    }
    methodology = decision["candidate_methodology"]
    methodology_complete = isinstance(methodology, dict) and not (
        methodology.get("status") == "blocked"
    )
    common_other_pct = None
    if methodology_complete:
        missing_methodology = sorted(methodology_fields - set(methodology))
        if missing_methodology:
            raise ValueError(
                "strategic candidate_methodology missing fields: "
                + ", ".join(missing_methodology)
            )
        if any(methodology[field] in (None, "") for field in methodology_fields):
            raise ValueError("strategic candidate_methodology must be complete")
        if methodology["candidate_grid"] != list(range(0, 101, 10)):
            raise ValueError(
                "candidate methodology must define the exhaustive 0-100 grid"
            )
        if methodology["tactical_liquidity_candidate_grid"] != [0, 2.5, 5, 7.5, 10]:
            raise ValueError("candidate methodology tactical liquidity grid is invalid")
        if methodology["other_pct_candidate_grid"] != [0, 1, 2, 3, 5]:
            raise ValueError("candidate methodology other_pct grid is invalid")
        if methodology["crypto_contribution_option_grid"] != [
            "stop_new_contributions_and_exclude_unknown_existing_balance",
            "continue_only_within_realized_surplus_such_as_bonus",
            "continue_current_contributions_and_disclose_cash_flow_and_success_probability_impact",
        ]:
            raise ValueError("candidate methodology crypto option grid is invalid")
        common_other_pct = Decimal(
            str(methodology["other_pct_common_base_case"])
        )
    elif not allow_unselected:
        raise ValueError("completed strategic candidate_methodology must be complete")
    elif methodology is not None:
        _require_mapping_fields(
            methodology,
            {"status", "reason", "remediation"},
            name="candidate_methodology",
        )
        if methodology["status"] != "blocked" or not str(
            methodology["reason"]
        ).strip() or not str(methodology["remediation"]).strip():
            raise ValueError(
                "blocked candidate_methodology requires reason and remediation"
            )
    candidate_fields = {
        "candidate_id",
        "sleeve_equity_pct",
        "total_equity_pct",
        "bond_pct",
        "other_pct",
        "expected_nominal_return_pct",
        "expected_real_return_pct",
        "expected_volatility_pct",
        "equity_bond_correlation",
        "estimated_major_drawdown_pct",
        "estimated_success_probability_pct",
        "required_success_probability_pct",
        "candidate_feasible",
        "constraint_failures",
        "primary_objective_fit_value",
        "primary_objective_fit_formula",
        "assumptions_ref",
        "calculation_status",
        "reason",
        "missing_capability",
        "remediation",
        "selected",
    }
    candidates = decision["candidate_comparison"]
    if not isinstance(candidates, list) or len(candidates) != 11:
        raise ValueError(
            "candidate_comparison must contain exactly 11 candidates for the exhaustive 0-100 grid"
        )
    candidate_ids: set[str] = set()
    selected: list[dict] = []
    not_calculable_count = 0
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or candidate_fields - set(candidate):
            raise ValueError(f"candidate_comparison[{index}] is incomplete")
        calculation_status = candidate["calculation_status"]
        if calculation_status not in {"calculated", "not_calculable"}:
            raise ValueError(
                f"candidate_comparison[{index}].calculation_status is invalid"
            )
        if calculation_status == "not_calculable":
            not_calculable_count += 1
            if not str(candidate["reason"]).strip() or not str(
                candidate["remediation"]
            ).strip() or not candidate["missing_capability"]:
                raise ValueError(
                    f"candidate_comparison[{index}] not_calculable requires reason, missing_capability, and remediation"
                )
            if candidate["selected"] is not False:
                raise ValueError(
                    f"candidate_comparison[{index}] not_calculable cannot be selected"
                )
        elif candidate["candidate_feasible"] is None:
            raise ValueError(f"candidate_comparison[{index}] feasibility is missing")
        elif candidate["missing_capability"]:
            raise ValueError(
                f"candidate_comparison[{index}] calculated row cannot list missing_capability"
            )

        weights = [
            candidate[field]
            for field in ("total_equity_pct", "bond_pct", "other_pct")
        ]
        numeric_weights = all(value is not None for value in weights)
        if any(value is None for value in weights) and numeric_weights is False:
            if not all(value is None for value in weights):
                raise ValueError(
                    f"candidate_comparison[{index}] weights must be all numeric or all null"
                )
            if methodology_complete:
                raise ValueError(
                    f"candidate_comparison[{index}] weights must use the complete "
                    "candidate_methodology.other_pct_common_base_case"
                )
            if calculation_status == "calculated":
                raise ValueError(
                    f"candidate_comparison[{index}] calculated weights cannot be null"
                )
        if numeric_weights:
            total_equity, bonds, other = (Decimal(str(value)) for value in weights)
            if common_other_pct is None:
                raise ValueError(
                    f"candidate_comparison[{index}] cannot use numeric weights when "
                    "candidate_methodology.other_pct_common_base_case is unavailable"
                )
            if abs(total_equity + bonds + other - Decimal("100")) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    f"candidate_comparison[{index}] weights must total 100 within tolerance"
                )
            if common_other_pct is not None and abs(other - common_other_pct) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    f"candidate_comparison[{index}].other_pct must equal "
                    "candidate_methodology.other_pct_common_base_case"
                )
            sleeve_equity = Decimal(str(candidate["sleeve_equity_pct"]))
            expected_total_equity = (
                (Decimal("100") - other) * sleeve_equity / Decimal("100")
            )
            expected_bonds = (
                (Decimal("100") - other)
                * (Decimal("100") - sleeve_equity)
                / Decimal("100")
            )
            if abs(total_equity - expected_total_equity) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    f"candidate_comparison[{index}].total_equity_pct violates the canonical formula"
                )
            if abs(bonds - expected_bonds) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    f"candidate_comparison[{index}].bond_pct violates the canonical formula"
                )
        candidate_id = str(candidate["candidate_id"])
        if candidate_id in candidate_ids:
            raise ValueError("candidate_comparison contains duplicate candidate_id")
        candidate_ids.add(candidate_id)
        if candidate["selected"] is True:
            selected.append(candidate)
    sleeve_grid = sorted(int(item["sleeve_equity_pct"]) for item in candidates)
    if sleeve_grid != list(range(0, 101, 10)):
        raise ValueError("candidate_comparison must include the exhaustive 0-100 grid")
    if len(selected) > 1:
        raise ValueError("candidate_comparison must not select multiple candidates")
    if not allow_unselected and len(selected) != 1:
        raise ValueError("candidate_comparison must select exactly one candidate")
    if allow_unselected and not selected:
        if not_calculable_count == 0:
            raise ValueError(
                "blocked candidate_comparison without a selection must contain a not_calculable candidate"
            )
        if not str(decision["reason"]).strip() or not str(
            decision["remediation"]
        ).strip():
            raise ValueError(
                "blocked candidate selection requires upper-level reason and remediation"
            )
    if selected and selected[0]["candidate_feasible"] is not True:
        raise ValueError("selected candidate must be feasible")


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
    _validate_required_checks(
        checks,
        required_ids=DECISION_QUALITY_CHECKS,
        name="decision_quality_checks",
    )


def _validate_required_checks(
    checks,
    *,
    required_ids: set[str],
    name: str,
    additional_required_fields: set[str] | None = None,
) -> None:
    if not isinstance(checks, list):
        raise ValueError(f"{name} must be a list")
    required_fields = {
        "check_id",
        "status",
        "evidence",
        "reason",
        "remediation",
    } | (additional_required_fields or set())
    by_id: dict[str, dict] = {}
    for index, check in enumerate(checks):
        if not isinstance(check, dict) or required_fields - set(check):
            raise ValueError(
                f"{name}[{index}] is missing required validation fields"
            )
        if check["status"] not in {
            "pass",
            "fail",
            "not_verifiable",
            "not_applicable",
        }:
            raise ValueError(f"{name}[{index}].status is invalid")
        if check["status"] == "pass" and not str(check["evidence"]).strip():
            raise ValueError(f"{name}[{index}] pass requires concrete evidence")
        if check["status"] in {"fail", "not_verifiable"} and (
            not str(check["reason"]).strip()
            or not str(check["remediation"]).strip()
        ):
            raise ValueError(
                f"{name}[{index}] {check['status']} requires reason and remediation"
            )
        if check["status"] == "not_applicable" and not str(check["reason"]).strip():
            raise ValueError(f"{name}[{index}] not_applicable requires reason")
        if check["check_id"] in by_id:
            raise ValueError(f"{name} contains duplicate check_id")
        by_id[check["check_id"]] = check
    missing = sorted(required_ids - set(by_id))
    if missing:
        raise ValueError(f"{name} missing fields: " + ", ".join(missing))


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
        "calculation_reason",
        "remediation",
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
    research_cutoff_at: str | None = None,
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
                "policy_locked_before_market_evaluation",
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
        if review["policy_locked_before_market_evaluation"] is not True:
            raise ValueError(
                f"{source_name} tactical policy must be locked before market evaluation"
            )
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
                research_cutoff_at=research_cutoff_at,
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
    if source_name == "review_response.yaml":
        use_required.update({"reason", "remediation"})
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
        "reason",
        "remediation",
        "policy_basis_as_of",
        "locked_before_market_evaluation",
        "initial_target_pct_of_total_assets",
        "target_jpy",
        "deployment_asset",
        "trigger_index",
        "reference_high_definition",
        "decline_threshold_pct",
        "price_basis",
        "lookback_period",
        "fx_treatment",
        "tranches",
        "amount_per_tranche",
        "minimum_balance_jpy",
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
    expected_current_holding_symbols: set[str],
    expected_current_holding_accounts: dict[str, str],
    new_asset_purchase_conclusion,
) -> None:
    if not isinstance(actions, list):
        raise ValueError("decisions.actions must be a list")
    required = {
        "action_id",
        "action_scope",
        "action_level",
        "symbol",
        "asset_name",
        "holding_status",
        "side",
        "account_type",
        "execution_method",
        "status",
        "reason",
        "remediation",
        "description",
        "source",
        "destination",
        "quantity",
        "amount_jpy",
        "formula",
        "inputs",
        "policy_refs",
        "assumption_independent_direction",
        "confirmed_conditions_consistent",
        "max_impact_if_assumptions_wrong_jpy",
        "timing",
        "rationale",
        "requires_user_approval",
    }
    valid_statuses = {"executable", "conditional", "blocked"}
    valid_source_types = {
        "confirmed_user_condition",
        "observed_packet_fact",
        "machine_calculation",
        "evidence_based_inference",
        "explicit_assumption",
    }
    seen_action_ids: set[str] = set()
    existing_action_symbols: list[str] = []
    new_asset_action_ids: list[str] = []
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
        action_id = str(action["action_id"])
        if action_id in seen_action_ids:
            raise ValueError(f"decisions.actions[{index}] duplicates action_id {action_id}")
        seen_action_ids.add(action_id)
        if not any(
            category in str(action["account_type"])
            for category in ("NISA", "特定口座", "一般口座")
        ):
            raise ValueError(
                f"decisions.actions[{index}].account_type must identify NISA, 特定口座, or 一般口座"
            )
        if not str(action["timing"]).strip() or not str(
            action["execution_method"]
        ).strip():
            raise ValueError(
                f"decisions.actions[{index}] must state when and how to act"
            )
        if action["action_scope"] == "existing_holding":
            if action["holding_status"] != "held" or action["side"] not in {
                "sell",
                "hold",
                "transfer",
            }:
                raise ValueError(
                    f"decisions.actions[{index}] has an invalid existing-holding action"
                )
            action_symbol = str(action["symbol"])
            expected_account_type = expected_current_holding_accounts.get(
                action_symbol
            )
            if expected_account_type is not None and classify_review_account_type(
                action["account_type"]
            ) != classify_review_account_type(expected_account_type):
                raise ValueError(
                    f"decisions.actions[{index}].account_type conflicts with the confirmed holding account"
                )
            existing_action_symbols.append(action_symbol)
        elif action["action_scope"] == "new_asset":
            if action["holding_status"] != "not_held" or action["side"] != "buy":
                raise ValueError(
                    f"decisions.actions[{index}] has an invalid new-asset action"
                )
            if str(action["symbol"]) in expected_current_holding_symbols:
                raise ValueError(
                    f"decisions.actions[{index}] marks a currently held asset as new"
                )
            new_asset_action_ids.append(action_id)
        else:
            raise ValueError(f"decisions.actions[{index}] has invalid action_scope")
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

    if expected_current_holding_symbols:
        actual = set(existing_action_symbols)
        if actual != expected_current_holding_symbols or len(existing_action_symbols) != len(
            actual
        ):
            raise ValueError(
                "decisions.actions existing holding coverage mismatch: "
                f"expected={sorted(expected_current_holding_symbols)}, actual={sorted(existing_action_symbols)}"
            )

    if not isinstance(new_asset_purchase_conclusion, dict) or set(
        new_asset_purchase_conclusion
    ) != {"status", "rationale", "action_ids"}:
        raise ValueError("decisions.new_asset_purchase_conclusion is incomplete")
    conclusion_status = new_asset_purchase_conclusion["status"]
    conclusion_ids = new_asset_purchase_conclusion["action_ids"]
    if not isinstance(conclusion_ids, list) or set(conclusion_ids) != set(
        new_asset_action_ids
    ):
        raise ValueError(
            "decisions.new_asset_purchase_conclusion action_ids do not match new-asset actions"
        )
    if conclusion_status == "buy_proposed" and not new_asset_action_ids:
        raise ValueError("buy_proposed requires at least one new-asset purchase action")
    if conclusion_status == "no_new_asset_purchase" and new_asset_action_ids:
        raise ValueError("no_new_asset_purchase cannot reference purchase actions")
    if conclusion_status not in {"buy_proposed", "no_new_asset_purchase"}:
        raise ValueError("decisions.new_asset_purchase_conclusion status is invalid")
    if not str(new_asset_purchase_conclusion["rationale"]).strip():
        raise ValueError("decisions.new_asset_purchase_conclusion requires rationale")


SOURCE_FIELDS = {
    "title",
    "publisher",
    "url",
    "publication_date",
    "data_as_of",
    "accessed_at",
    "cutoff_compliance_status",
    "source_type",
    "claim_supported",
}


def _validate_source(
    source,
    *,
    path: str,
    research_cutoff_at: str | None,
) -> None:
    if not isinstance(source, dict):
        raise ValueError(f"{path} must be an object")
    missing = sorted(SOURCE_FIELDS - set(source))
    if missing:
        raise ValueError(f"{path} missing fields: " + ", ".join(missing))
    if not str(source.get("url") or "").startswith(("https://", "http://")):
        raise ValueError(f"{path}.url must be an absolute web URL")
    if source["cutoff_compliance_status"] != "compliant":
        raise ValueError(
            f"{path} cannot support a decision unless cutoff_compliance_status is compliant"
        )
    if source["publication_date"] is None:
        raise ValueError(
            f"{path}.publication_date must identify the publication, filing, or release date"
        )
    cutoff = _parse_datetime(research_cutoff_at, path="research_cutoff_at")
    _validate_information_date_not_after_cutoff(
        source["publication_date"],
        cutoff=cutoff,
        path=f"{path}.publication_date",
    )
    if source["data_as_of"] is not None:
        _validate_information_date_not_after_cutoff(
            source["data_as_of"],
            cutoff=cutoff,
            path=f"{path}.data_as_of",
        )
    _parse_datetime(source["accessed_at"], path=f"{path}.accessed_at")


def _parse_datetime(value, *, path: str) -> datetime:
    if value is None:
        raise ValueError(f"{path} must be a timezone-aware date-time")
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path} must be a valid date-time") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{path} must include a timezone")
    return parsed.astimezone(UTC)


def _validate_information_date_not_after_cutoff(
    value,
    *,
    cutoff: datetime,
    path: str,
) -> None:
    text = str(value)
    try:
        if len(text) == 10:
            information_date = date.fromisoformat(text)
            if information_date > cutoff.date():
                raise ValueError(f"{path} is after research_cutoff_at")
            return
        information_time = _parse_datetime(text, path=path)
    except ValueError as exc:
        if "after research_cutoff_at" in str(exc):
            raise
        raise ValueError(f"{path} must be a valid date or date-time") from exc
    if information_time > cutoff:
        raise ValueError(f"{path} is after research_cutoff_at")


def _validate_empirical_evidence(items, *, research_cutoff_at: str) -> None:
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
        _validate_source(
            item["source"],
            path=f"empirical_evidence[{index}].source",
            research_cutoff_at=research_cutoff_at,
        )


def _validate_before_after_allocation(items) -> None:
    if not isinstance(items, list):
        raise ValueError("before_after_allocation must be a list")
    required = {
        "view",
        "category",
        "before_jpy",
        "after_jpy",
        "target_jpy",
        "before_pct",
        "after_pct",
        "target_pct",
        "calculation_status",
        "reason",
        "remediation",
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
            if abs(total - Decimal("100")) > ROUNDING_TOLERANCE_PCT_POINTS:
                raise ValueError(
                    f"before_after_allocation {view} after_pct must total 100 within tolerance"
                )


def _validate_account_tax_comparisons(
    items,
    *,
    research_cutoff_at: str,
) -> None:
    if not isinstance(items, list):
        raise ValueError("account_tax_comparisons must be a list")
    required = {
        "comparison_id",
        "symbol",
        "account_type",
        "status",
        "reason",
        "remediation",
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
                research_cutoff_at=research_cutoff_at,
            )


def _validate_order_proposals(items) -> None:
    if not isinstance(items, list):
        raise ValueError("decisions.order_proposals must be a list")
    required = {
        "proposal_id",
        "proposal_level",
        "symbol",
        "account_type",
        "side",
        "status",
        "reason",
        "remediation",
        "quantity",
        "amount_jpy",
        "formula",
        "inputs",
        "policy_refs",
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
    research_cutoff_at: str | None = None,
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
                    research_cutoff_at=research_cutoff_at,
                )


def _validate_thematic_fund_coverage(
    reviews,
    *,
    expected_member_symbols: set[str],
    research_cutoff_at: str,
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
                research_cutoff_at=research_cutoff_at,
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
