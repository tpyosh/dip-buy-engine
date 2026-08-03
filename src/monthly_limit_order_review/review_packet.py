from __future__ import annotations

import re
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import MonthlyComputation, ReviewPacket
from .utils import month_key, quantize


FINANCIAL_FACT_SECTIONS = {
    "Scope",
    "Living expenses and cash flow",
    "Tax and account facts",
    "Apartment mortgage",
}
UNKNOWN_MARKERS = ("未記録", "不明", "未確認", "確認できない")
VALIDATION_WARNING_PREFIXES = (
    "missing_",
    "source_",
    "category_",
    "currency_",
    "duplicate_",
    "snapshot_",
    "ocr_",
    "account_",
    "same_product_",
)
REVIEW_MODES = {
    "monthly_operational_review",
    "strategic_policy_second_opinion",
}
GENERATION_STATUSES = {"ready", "blocked_missing_strategic_inputs"}
INTERACTION_PHASES = {"objective_confirmation", "final_review"}
PRIMARY_OBJECTIVES = {
    "maximize_terminal_wealth",
    "minimize_risk_for_required_return",
    "maximize_ex_ante_sharpe_ratio",
}


def build_review_packet(
    computation: MonthlyComputation,
    *,
    financial_assumptions_text: str = "",
    financial_assumptions_source: str = "FINANCIAL_ASSUMPTIONS.md",
    financial_context: dict | None = None,
    financial_context_source: str = "financial/current.yaml",
) -> ReviewPacket:
    snapshot = computation.snapshot
    review_target_month = computation.metadata.get(
        "review_target_month",
        month_key(snapshot.snapshot_date),
    )
    if financial_context is not None:
        financial_source = financial_context_source
        financial_as_of, financial_conditions, financial_unknowns = (
            extract_structured_financial_review_context(
                financial_context,
                source=financial_source,
            )
        )
    else:
        financial_source = financial_assumptions_source
        financial_as_of, financial_conditions, financial_unknowns = (
            extract_financial_review_context(
                financial_assumptions_text,
                source=financial_source,
            )
        )
    financial_context_for_review = financial_context
    if is_after_review_date(financial_as_of, snapshot.snapshot_date):
        financial_context_for_review = None
        financial_conditions = []
        financial_unknowns = [
            {
                "item": "financial_assumptions_at_review_date",
                "reason": (
                    f"{financial_source} の基準日 {financial_as_of} は"
                    f"レビュー基準日 {snapshot.snapshot_date.isoformat()} より後のため使用しない"
                ),
                "source": financial_source,
                "as_of": financial_as_of,
            }
        ]
    recurring_source = safe_selected_source_ref(
        computation.metadata.get("core_recurring_contributions_source"),
        fallback="current_recurring_settings",
    )
    recurring = build_recurring_commitments(
        computation.metadata.get("core_recurring_contributions", {}),
        source=recurring_source,
        as_of=review_target_month,
    )
    cash_requirement_inputs = (
        build_structured_cash_requirement_inputs(
            financial_context_for_review,
            financial_unknowns,
            portfolio_snapshot_total_assets_jpy=snapshot.total_assets_jpy,
        )
        if financial_context_for_review is not None
        else build_cash_requirement_inputs(
            financial_conditions,
            financial_unknowns,
        )
    )
    review_mode = determine_review_mode(
        computation,
        cash_requirement_inputs=cash_requirement_inputs,
    )
    strategic_required_inputs = build_strategic_required_inputs(
        financial_context_for_review,
        computation=computation,
        recurring=recurring["facts"],
    )
    strategic_decision_objective = build_strategic_decision_objective(
        financial_context_for_review
    )
    missing_strategic_inputs = (
        find_missing_strategic_inputs(
            strategic_required_inputs,
            strategic_decision_objective=strategic_decision_objective,
        )
        if review_mode == "strategic_policy_second_opinion"
        else []
    )
    generation_status = (
        "blocked_missing_strategic_inputs"
        if missing_strategic_inputs
        else "ready"
    )
    interaction_phase = (
        "objective_confirmation"
        if review_mode == "strategic_policy_second_opinion"
        and strategic_decision_objective.get("primary_objective") is None
        else "final_review"
    )
    confirmed_user_conditions = (
        financial_conditions
        + build_approved_review_constraints(computation)
        + build_holding_execution_conditions(computation)
        + recurring["conditions"]
    )
    unknown_information = financial_unknowns + build_computation_unknowns(computation)

    selected_sources = [
        {
            "source_id": "normalized_snapshot",
            "source_ref": safe_selected_source_ref(
                computation.metadata.get("snapshot_path"),
                fallback="normalized_snapshot",
            ),
            "role": "observed_current_portfolio",
            "as_of": snapshot.snapshot_date.isoformat(),
        },
        {
            "source_id": "financial_assumptions",
            "source_ref": financial_source,
            "role": "explicit_user_conditions_and_confirmed_contracts",
            "as_of": financial_as_of,
        },
        {
            "source_id": "holding_metadata",
            "source_ref": safe_selected_source_ref(
                computation.metadata.get("holding_metadata_source"),
                fallback="holdings/current.yaml",
            ),
            "role": "confirmed_holding_metadata",
            "as_of": str(
                computation.metadata.get("holding_metadata_effective_from")
                or snapshot.snapshot_date.isoformat()
            ),
        },
        {
            "source_id": "current_recurring_settings",
            "source_ref": recurring_source,
            "role": "observed_recurring_commitments",
            "as_of": review_target_month,
        },
        {
            "source_id": "market_reference_collection",
            "source_ref": "embedded_market_reference_collection",
            "role": "calculated_market_reference_facts",
            "as_of": latest_market_reference_date(computation),
        },
        {
            "source_id": "investment_thesis_records",
            "source_ref": "strategy/theses/index.yaml",
            "role": "documented_investment_story_context",
            "as_of": snapshot.snapshot_date.isoformat(),
        },
    ]
    if review_mode == "monthly_operational_review":
        selected_sources.append(
            {
                "source_id": "approved_operational_policy",
                "source_ref": safe_selected_source_ref(
                    trusted_strategy_source_ref(computation),
                    fallback="approved_strategy",
                ),
                "role": "approved_operational_policy",
                "as_of": str(
                    computation.strategy_summary.get("effective_from")
                    or snapshot.snapshot_date.isoformat()
                ),
            }
        )
    return ReviewPacket(
        schema_version=2,
        packet_type="monthly_independent_review",
        generation_status=generation_status,
        interaction_phase=interaction_phase,
        review_mode=review_mode,
        review_target_month=review_target_month,
        portfolio_snapshot_as_of=snapshot.snapshot_date,
        market_reference_as_of=latest_market_reference_date(computation),
        packet_generated_at=computation.generated_at,
        research_cutoff_at=computation.generated_at,
        decision_date=None,
        strategic_required_inputs=strategic_required_inputs,
        missing_strategic_inputs=missing_strategic_inputs,
        strategic_decision_objective=strategic_decision_objective,
        candidate_methodology=build_candidate_methodology(),
        capital_layers=build_capital_layers(),
        asset_class_definitions=build_asset_class_definitions(),
        allocation_denominators=build_allocation_denominators(
            computation,
            cash_requirement_inputs=cash_requirement_inputs,
        ),
        market_decline_rule=build_market_decline_rule(financial_context_for_review),
        direct_semiconductor_limit=build_direct_semiconductor_limit(
            computation,
            review_mode=review_mode,
        ),
        user_decision_preferences=build_user_decision_preferences(
            financial_context_for_review
        ),
        active_risk_policy=build_active_risk_policy(financial_context_for_review),
        approved_policy=build_approved_policy(computation, review_mode=review_mode),
        rule_registry=build_rule_registry(review_mode),
        research_contract=build_research_contract(),
        validation_contract=build_validation_contract(interaction_phase),
        selected_sources=selected_sources,
        preflight_checklist=build_preflight_checklist(),
        allowed_quantitative_facts=build_allowed_quantitative_facts(
            computation,
            recurring=recurring["facts"],
            cash_requirement_inputs=cash_requirement_inputs,
        ),
        confirmed_user_conditions=confirmed_user_conditions,
        unknown_information=deduplicate_unknowns(unknown_information),
        output_contract=build_phase_output_contract(
            review_target_month=review_target_month,
            portfolio_snapshot_as_of=snapshot.snapshot_date.isoformat(),
            review_mode=review_mode,
            interaction_phase=interaction_phase,
        ),
        excluded_information=build_excluded_information(review_mode),
    )


def determine_review_mode(
    computation: MonthlyComputation,
    *,
    cash_requirement_inputs: dict,
) -> str:
    configured_mode = computation.metadata.get("review_mode")
    if configured_mode is not None:
        if configured_mode not in REVIEW_MODES:
            raise ValueError(f"Unsupported review_mode: {configured_mode}")
        return configured_mode
    if (
        cash_requirement_inputs.get("dip_buy_liquidity", {}).get("status")
        == "proposal_requested_from_current_review"
    ):
        return "strategic_policy_second_opinion"
    return "monthly_operational_review"


def build_strategic_required_inputs(
    context: dict | None,
    *,
    computation: MonthlyComputation,
    recurring: dict,
) -> dict:
    """Build only confirmed strategic inputs; missing values stay explicit nulls."""
    source = context or {}
    profile = source.get("strategic_profile", {})
    mortgage = source.get("mortgage", {})
    household_mortgage = mortgage.get("household_total", {})
    user_mortgage = mortgage.get("husband_share", {})
    household_balance = household_mortgage.get(
        "scheduled_balance_after_2026_07_27_jpy"
    )
    user_share_pct = user_mortgage.get("allocation_pct")
    user_balance = None
    if household_balance is not None and user_share_pct is not None:
        user_balance = int(
            (Decimal(str(household_balance)) * Decimal(str(user_share_pct))).quantize(
                Decimal("1")
            )
        )
    maturity_date = household_mortgage.get("maturity_date")
    remaining_term_years = None
    if maturity_date:
        remaining_days = (
            date.fromisoformat(str(maturity_date)) - computation.snapshot.snapshot_date
        ).days
        remaining_term_years = round(max(remaining_days, 0) / 365.2425, 2)

    date_of_birth = profile.get("date_of_birth")
    user_age = profile.get("user_age")
    user_age_as_of = profile.get("user_age_as_of")
    if date_of_birth:
        birth_date = date.fromisoformat(str(date_of_birth))
        age_date = computation.snapshot.snapshot_date
        user_age = age_date.year - birth_date.year - (
            (age_date.month, age_date.day) < (birth_date.month, birth_date.day)
        )
        user_age_as_of = age_date.isoformat()

    return {
        "date_of_birth": date_of_birth,
        "user_age": user_age,
        "user_age_as_of": user_age_as_of,
        "tax_residency": profile.get("tax_residency"),
        "investment_horizon_years": profile.get("investment_horizon_years"),
        "planning_end_age": profile.get("planning_end_age"),
        "expected_withdrawal_start": profile.get("expected_withdrawal_start"),
        "earliest_possible_asset_use_date": profile.get(
            "earliest_possible_asset_use_date"
        ),
        "planned_contributions": profile.get("planned_contributions"),
        "current_recurring_commitments": recurring,
        "expected_future_cash_flows": profile.get("expected_future_cash_flows"),
        "human_capital_assumptions": profile.get("human_capital_assumptions"),
        "liabilities": {
            "mortgage_outstanding_jpy": household_balance,
            "user_share_jpy": user_balance,
            "interest_rate": household_mortgage.get("annual_interest_rate"),
            "fixed_or_variable": household_mortgage.get("fixed_or_variable"),
            "remaining_term_years": remaining_term_years,
            "annual_repayment_jpy": user_mortgage.get("annual_payment_jpy"),
            "balance_as_of": "2026-07-27" if household_balance is not None else None,
        },
        "pension_and_other_future_assets": profile.get(
            "pension_and_other_future_assets"
        ),
    }


def find_missing_strategic_inputs(
    inputs: dict,
    *,
    strategic_decision_objective: dict,
) -> list[str]:
    required_paths = [
        "user_age",
        "tax_residency",
        "investment_horizon_years",
        "planning_end_age",
        "expected_withdrawal_start",
        "earliest_possible_asset_use_date",
        "planned_contributions",
        "expected_future_cash_flows",
        "human_capital_assumptions",
        "liabilities.mortgage_outstanding_jpy",
        "liabilities.user_share_jpy",
        "liabilities.interest_rate",
        "liabilities.fixed_or_variable",
        "liabilities.remaining_term_years",
        "liabilities.annual_repayment_jpy",
        "pension_and_other_future_assets",
    ]
    missing = [path for path in required_paths if _path_is_missing(inputs, path)]
    objective = strategic_decision_objective.get("primary_objective")
    if objective is None:
        if not any(
            model.get("offered") is True
            for model in strategic_decision_objective["objective_models"].values()
        ):
            missing.append("strategic_decision_objective.no_calculable_option")
    else:
        objective_model = strategic_decision_objective["objective_models"].get(
            objective, {}
        )
        for field in objective_model.get("required_parameters", []):
            if _objective_parameter_is_missing(objective_model, field):
                missing.append(f"strategic_decision_objective.{objective}.{field}")
    return sorted(set(missing))


def _path_is_missing(value: dict, dotted_path: str) -> bool:
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return True
        current = current[part]
    # Empty arrays can be an explicit confirmation of "none" (for example, no
    # planned contributions or no other future assets). Null and empty objects
    # still mean that the required fact has not been supplied.
    if current is None or current == "" or current == {}:
        return True
    if isinstance(current, dict) and current.get("status") in {
        "continuation_horizon_undecided",
        "requires_clarification",
        "unknown",
        "undecided",
    }:
        return True
    return False


def _objective_parameter_is_missing(model: dict, field: str) -> bool:
    if not _path_is_missing(model, field):
        return False
    derivation_field = {
        "target_return_pct": "target_return_derivation",
        "success_probability_pct": "success_probability_derivation",
    }.get(field)
    if derivation_field is None:
        return True
    derivation = model.get(derivation_field)
    return not (
        isinstance(derivation, dict)
        and derivation.get("status") == "reviewer_to_derive"
        and derivation.get("decision_owner") == "independent_monthly_reviewer"
        and bool(derivation.get("method"))
        and bool(derivation.get("evidence_requirements"))
        and derivation.get("base_case_required") is True
    )


def build_strategic_decision_objective(context: dict | None) -> dict:
    profile = (context or {}).get("strategic_profile", {})
    configured = profile.get("objective_configuration", {})
    primary_objective = configured.get("primary_objective")
    if primary_objective not in PRIMARY_OBJECTIVES:
        primary_objective = None
    models = configured.get("objective_models", {})
    terminal = models.get("maximize_terminal_wealth", {})
    minimum_risk = models.get("minimize_risk_for_required_return", {})
    risk_adjusted = models.get("maximize_ex_ante_sharpe_ratio", {})
    objective_models = {
        "maximize_terminal_wealth": {
            "label": "最終資産額の最大化",
            "horizon_years": terminal.get("horizon_years"),
            "planned_contributions": terminal.get("planned_contributions"),
            "return_basis": terminal.get("return_basis"),
            "statistic": terminal.get("statistic"),
            "downside_quantile_pct": terminal.get("downside_quantile_pct"),
            "leverage_allowed": terminal.get("leverage_allowed"),
            "required_parameters": [
                "horizon_years",
                "planned_contributions",
                "return_basis",
                "statistic",
                "leverage_allowed",
            ],
            "primary_objective_fit_rule": (
                "同一の拠出・期間・名目/実質・レバレッジ条件で、指定された期待値、"
                "中央値または下方分位の終価が最大の候補を最良とする"
            ),
        },
        "minimize_risk_for_required_return": {
            "label": "必要収益を満たす最小リスク",
            "target_return_pct": minimum_risk.get("target_return_pct"),
            "target_return_derivation": minimum_risk.get(
                "target_return_derivation"
            ),
            "return_basis": minimum_risk.get("return_basis"),
            "horizon_years": minimum_risk.get("horizon_years"),
            "accumulation_horizon_years": minimum_risk.get(
                "accumulation_horizon_years"
            ),
            "withdrawal_horizon_years": minimum_risk.get(
                "withdrawal_horizon_years"
            ),
            "success_probability_pct": minimum_risk.get(
                "success_probability_pct"
            ),
            "success_probability_derivation": minimum_risk.get(
                "success_probability_derivation"
            ),
            "retirement_spending_derivation": minimum_risk.get(
                "retirement_spending_derivation"
            ),
            "public_pension_derivation": minimum_risk.get(
                "public_pension_derivation"
            ),
            "terminal_asset_floor_derivation": minimum_risk.get(
                "terminal_asset_floor_derivation"
            ),
            "required_parameters": [
                "target_return_pct",
                "return_basis",
                "horizon_years",
                "success_probability_pct",
            ],
            "offer_rule": (
                "必須パラメータは確認済み数値または明示的なreviewer_to_derive契約を持つこと。"
                "導出契約がある項目はfinal_review内で根拠、式、感応度と一つのベースケースを"
                "提示し、ユーザーへ再質問しない"
            ),
            "primary_objective_fit_rule": (
                "目標収益と成功確率を満たす候補のうち、推定ボラティリティまたは"
                "指定下方リスクが最小の候補を最良とする"
            ),
        },
        "maximize_ex_ante_sharpe_ratio": {
            "label": "リスク当たり収益の最大化",
            "metric": "ex_ante_sharpe_ratio",
            "risk_free_rate_definition": risk_adjusted.get(
                "risk_free_rate_definition"
            ),
            "return_basis": risk_adjusted.get("return_basis"),
            "horizon_years": risk_adjusted.get("horizon_years"),
            "required_parameters": [
                "risk_free_rate_definition",
                "return_basis",
                "horizon_years",
            ],
            "primary_objective_fit_rule": (
                "同一の無リスク金利定義、名目/実質区分、期間で計算した"
                "ex_ante_sharpe_ratioが最大の候補を最良とする"
            ),
        },
    }
    for model in objective_models.values():
        model["offered"] = not any(
            _objective_parameter_is_missing(model, field)
            for field in model["required_parameters"]
        )
    return {
        "primary_objective": primary_objective,
        "objective_question": (
            "長期政策の主目的を一つ選んでください。選択肢に不足パラメータが示される場合は、"
            "同じ回答でその値も指定してください。"
        ),
        "objective_models": objective_models,
        "selection_rule": (
            "同一の資本市場前提で全候補を比較し、選択されたobjective_modelsの"
            "primary_objective_fit_ruleに従って一案を選ぶ"
        ),
        "tie_breaker": (
            "適合度が実質同等なら、推定総コスト、売買回転率、実装複雑性が低い順に選ぶ"
        ),
    }


def build_capital_layers() -> dict:
    return {
        "household_reserve": {
            "purpose": "emergency_and_confirmed_spending",
            "strategic_allocation_treatment": "exclude_from_long_term_investable_portfolio",
        },
        "tactical_liquidity": {
            "purpose": "temporary_dip_buying_overlay",
            "strategic_allocation_treatment": (
                "not_a_permanent_asset_class; state explicitly how undeployed cash relates to policy numerator and denominator"
            ),
        },
        "long_term_investable_portfolio": {
            "purpose": "strategic_asset_allocation",
            "strategic_allocation_treatment": (
                "determine equity, bond, and other policy weights independently within this layer"
            ),
        },
        "prohibited_residual_rule": (
            "必要現金または総現金比率を総資産から控除した残額を、そのまま目標株式額・株式比率として採用しない"
        ),
        "required_views": [
            "policy_allocation_within_investable_portfolio",
            "household_total_asset_allocation",
        ],
    }


def build_asset_class_definitions() -> dict:
    return {
        "core": {
            "core_satellite_group": "core",
            "included_in_long_term_investable_portfolio": True,
            "tradable": True,
            "household_allocation_category": "equity",
            "cap_treatment": "core_policy",
        },
        "jun_core": {
            "core_satellite_group": "satellite",
            "included_in_long_term_investable_portfolio": True,
            "tradable": True,
            "household_allocation_category": "equity",
            "cap_treatment": "counts_toward_total_satellite_and_relevant_theme_caps",
        },
        "satellite_core": {
            "core_satellite_group": "satellite",
            "included_in_long_term_investable_portfolio": True,
            "tradable": True,
            "household_allocation_category": "equity",
            "cap_treatment": "counts_toward_total_satellite_and_relevant_theme_caps",
        },
        "satellite": {
            "core_satellite_group": "satellite",
            "included_in_long_term_investable_portfolio": True,
            "tradable": True,
            "household_allocation_category": "equity",
            "cap_treatment": "counts_toward_total_satellite_and_security_or_theme_caps",
        },
        "pension": {
            "core_satellite_group": "core",
            "included_in_long_term_investable_portfolio": True,
            "tradable": False,
            "household_allocation_category": "equity",
            "cap_treatment": "core_policy; iDeCoは長期配分へ含めるが直接売買不可",
        },
        "other": {
            "core_satellite_group": "excluded",
            "included_in_long_term_investable_portfolio": False,
            "tradable": False,
            "household_allocation_category": "excluded_other",
            "cap_treatment": "excluded_from_policy_allocation_denominator",
        },
        "liquidity": {
            "core_satellite_group": "excluded",
            "included_in_long_term_investable_portfolio": False,
            "tradable": True,
            "household_allocation_category": "cash_pending_layer_assignment",
            "cap_treatment": "split_between_household_reserve_and_tactical_liquidity",
        },
    }


def build_allocation_denominators(
    computation: MonthlyComputation,
    *,
    cash_requirement_inputs: dict,
) -> dict:
    total = computation.snapshot.total_assets_jpy
    asset_class_values: dict[str, Decimal] = defaultdict(Decimal)
    for holding in computation.snapshot.holdings:
        asset_class_values[holding.asset_class] += holding.market_value_jpy
    excluded_other = asset_class_values.get("other", Decimal("0"))
    reserve = cash_requirement_inputs.get("emergency_fund", {}).get("target_jpy")
    tactical = cash_requirement_inputs.get("dip_buy_liquidity", {}).get("target_jpy")
    investable = None
    if reserve is not None and tactical is not None:
        investable = total - Decimal(str(reserve)) - Decimal(str(tactical)) - excluded_other
    return {
        "household_total_assets_jpy": total,
        "long_term_investable_portfolio_jpy": investable,
        "policy_allocation_denominator_jpy": investable,
        "household_reserve_jpy": reserve,
        "tactical_liquidity_jpy": tactical,
        "excluded_other_assets_jpy": excluded_other,
        "ideco_treatment": (
            "pension asset_classとして長期運用資産と政策配分分母に含めるが、"
            "直接の売買・資金移動対象にはしない"
        ),
        "crypto_treatment": {
            "current_balance_status": "not_present_in_portfolio_snapshot",
            "snapshot_scope": "excluded",
            "policy_scope": "excluded_until_balance_and_classification_are_confirmed",
            "recurring_contribution_is_not_current_balance": True,
        },
        "calculation_status": (
            "complete" if investable is not None else "blocked_pending_tactical_liquidity_policy"
        ),
    }


def build_candidate_methodology() -> dict:
    return {
        "candidate_range": [
            {"candidate_id": "GE100_B0", "global_equity_pct": 100, "bonds_pct": 0},
            {"candidate_id": "GE90_B10", "global_equity_pct": 90, "bonds_pct": 10},
            {"candidate_id": "GE80_B20", "global_equity_pct": 80, "bonds_pct": 20},
            {"candidate_id": "GE70_B30", "global_equity_pct": 70, "bonds_pct": 30},
        ],
        "range_rationale_required": True,
        "boundary_extension_rule": (
            "minimize_risk_for_required_returnで最適候補がGE70_B30境界に達した場合だけ、"
            "GE60_B40を一度追加して同じ前提で再比較する"
        ),
        "global_equity_index": None,
        "bond_index": None,
        "bond_instrument_type": None,
        "estimation_period": None,
        "assumptions_as_of": None,
        "inflation_assumption_pct": None,
        "return_basis": None,
        "tax_cost_treatment": None,
        "major_drawdown_definition": None,
        "rebalancing_frequency": None,
        "required_candidate_fields": [
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
        ],
    }


def build_market_decline_rule(context: dict | None) -> dict:
    configured = (context or {}).get("market_decline_rule", {})
    return {
        "status": configured.get("status", "not_configured"),
        "deployment_target": configured.get("deployment_target"),
        "trigger_index": configured.get("trigger_index"),
        "same_broad_index_required": True,
        "reference_high_definition": configured.get("reference_high_definition"),
        "price_basis": configured.get("price_basis"),
        "lookback_period": configured.get("lookback_period"),
        "fx_treatment": configured.get("fx_treatment"),
        "theme_or_sector_decline_is_trigger": False,
        "unavailable_data_result": "unclear",
    }


def build_direct_semiconductor_limit(
    computation: MonthlyComputation,
    *,
    review_mode: str,
) -> dict:
    current_limit = next(
        (
            item.get("upper_bound_pct")
            for item in computation.metadata.get("approved_review_constraints", [])
            if item.get("condition_id") == "approved_direct_semiconductor_max_pct"
        ),
        None,
    )
    if current_limit is None:
        current_limit = 12
    return {
        "status": (
            "policy_to_reconsider"
            if review_mode == "strategic_policy_second_opinion"
            else "hard_constraint"
        ),
        "limit_pct": current_limit,
        "denominator": "household_total_assets_jpy",
        "priority": (
            "家計用現金と法的・口座制約を満たした後、サテライト総枠・単一テーマ枠の"
            "うち最も厳しい上限を優先する"
        ),
        "strategic_review_note": (
            "戦略モードでは12%を不変条件とせず、根拠と他のアクティブリスク上限との"
            "整合性を再評価する。新上限はユーザー承認まで提案扱い"
        ),
    }


def build_user_decision_preferences(context: dict | None) -> dict:
    configured = (context or {}).get("user_decision_preferences", {})
    defaults = {
        "wants_concrete_policy_recommendation": True,
        "wants_decision_based_on_investment_theory": True,
        "does_not_want_unrequested_evaluation_axes": True,
        "does_not_want_generic_theory_without_decision": True,
        "expects_independent_reviewer_to_select_one_base_case": True,
    }
    defaults.update(configured)
    return defaults


def build_active_risk_policy(context: dict | None) -> dict:
    configured = (context or {}).get("active_risk_policy", {})
    return {
        "satellites_allowed": configured.get("satellites_allowed"),
        "total_satellite_cap_pct": configured.get("total_satellite_cap_pct"),
        "single_theme_cap_pct": configured.get("single_theme_cap_pct"),
        "single_security_cap_pct": configured.get("single_security_cap_pct"),
        "exceptions": configured.get("exceptions", []),
        "missing_policy_rule": (
            "未設定ならテーマごとに場当たり的な上限を作らず、戦略判断モードで全項目を同時に提案する"
        ),
    }


def build_approved_policy(
    computation: MonthlyComputation,
    *,
    review_mode: str,
) -> dict | None:
    if review_mode != "monthly_operational_review":
        return None
    return {
        "strategy_id": computation.strategy_summary.get("strategy_id"),
        "effective_from": computation.strategy_summary.get("effective_from"),
        "target_groups": [
            {
                "group": allocation.bucket,
                "target_pct": allocation.target_pct,
                "rebalance_proposal_below_pct": allocation.preferred_min_pct,
                "rebalance_proposal_above_pct": allocation.preferred_max_pct,
            }
            for allocation in (
                computation.strategy_allocations or computation.bucket_allocations
            )
        ],
        "approved_constraints": [
            item.get("statement")
            for item in computation.metadata.get("approved_review_constraints", [])
            if item.get("status") == "confirmed"
        ],
        "use_rule": (
            "この承認済み政策からの乖離点検にだけ使い、未設定の比率や閾値を推測で補完しない"
        ),
    }


def trusted_strategy_source_ref(computation: MonthlyComputation) -> str | None:
    value = computation.metadata.get("active_strategy_path")
    if value and "strategy/versions/" in str(value).replace("\\", "/"):
        return str(value)
    return None


def build_decision_quality_checks() -> list[str]:
    return [
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
    ]


def build_rule_registry(review_mode: str) -> list[dict]:
    rules = [
        {
            "rule_id": "R-PHASE-001",
            "applies_to": "all",
            "rule": (
                "objective_confirmationでは目的確認の一問だけを出力し、Web調査、投資判断、"
                "6セクション、YAML、売買案、quality checksを出力しない。回答後はfinal_reviewへ移る"
            ),
        },
        {
            "rule_id": "R-MODE-001",
            "applies_to": "all",
            "rule": "一つのreview_modeだけを適用し、月次運用判断と戦略判断を混在させない",
        },
        {
            "rule_id": "R-OBJECTIVE-001",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "primary_objectiveと対応するprimary_objective_fit_formulaで全候補を比較し、"
                "一つのベースケースを選ぶ"
            ),
        },
        {
            "rule_id": "R-PLANNING-001",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "reviewer_to_derive、reviewer_to_estimate_with_uncertainty、"
                "reviewer_to_model_with_uncertaintyは明示的な判断委譲として扱う。final_review内で"
                "根拠、式、限界、感応度と一つのベースケースを導出し、ユーザーへ再質問しない。"
                "導出値はfinancial_planning_modelだけを正本とする"
            ),
        },
        {
            "rule_id": "R-CASH-001",
            "applies_to": "all",
            "rule": (
                "家計用現金、戦術的待機資金、長期運用資産を分離し、必要現金の残余から"
                "長期株式比率を逆算しない"
            ),
        },
        {
            "rule_id": "R-CASH-002",
            "applies_to": "all",
            "rule": (
                "tactical_liquidity_policyの正本はstrategic_policy_decision."
                "tactical_liquidity_policyだけとし、cash_assessmentとdecisionsはID参照だけにする"
            ),
        },
        {
            "rule_id": "R-MARKET-001",
            "applies_to": "all",
            "rule": (
                "市場下落判定は投入対象と同じ広範指数を使う。テーマ・セクター下落は"
                "発動条件にせず、必要データを確認できなければunclearとする"
            ),
        },
        {
            "rule_id": "R-RESEARCH-001",
            "applies_to": "final_review",
            "rule": (
                "外部調査はresearch_cutoff_atまでの判断材料に使うが、"
                "portfolio_snapshot_as_ofの評価額を再評価しない"
            ),
        },
        {
            "rule_id": "R-STORY-001",
            "applies_to": "final_review",
            "rule": (
                "security_story_review_targetsとthematic_fund_review_targetsを全件評価し、"
                "価格変動だけを売却理由にしない"
            ),
        },
        {
            "rule_id": "R-THEME-001",
            "applies_to": "final_review",
            "rule": (
                "同一テーマ投信は商品・指数ストーリーを一度だけ評価し、口座・ロット別の"
                "税務と執行判断を別配列へ記録する"
            ),
        },
        {
            "rule_id": "R-TRADE-001",
            "applies_to": "final_review",
            "rule": (
                "売買・資金移動は算式、型付き入力、仮定への依存、税・口座、最大影響、"
                "実行時期を示し、承認済み根拠のない金額閾値は追加しない"
            ),
        },
        {
            "rule_id": "R-ID-001",
            "applies_to": "final_review",
            "rule": (
                "人間向け回答では正式名称を使い、machine_id・symbol・銘柄コードは"
                "Codex向けYAMLの識別子フィールドに限定する"
            ),
        },
        {
            "rule_id": "R-DELIVERY-001",
            "applies_to": "final_review",
            "rule": (
                "ファイル生成可能ならreview_response.yamlを添付する。不可なら6セクション後の"
                "区切り線直後にYAMLコードブロックを一つだけ置く。YAMLファイル本体には"
                "コードフェンスや説明文を入れない"
            ),
        },
        {
            "rule_id": "R-QUALITY-001",
            "applies_to": "final_review",
            "rule": (
                "quality checkがfailなら回答を修正し、修正不能ならfinal_reviewを提出せず"
                "blockedとして不足とremediationを返す"
            ),
        },
    ]
    if review_mode == "monthly_operational_review":
        rules.append(
            {
                "rule_id": "R-MONTHLY-001",
                "applies_to": review_mode,
                "rule": "未承認の資産配分、比率、閾値、銘柄選択を新たに決定しない",
            }
        )
    return rules


def build_research_contract() -> dict:
    return {
        "phase": "final_review_only",
        "required_for": [
            "capital_market_assumptions",
            "financial_planning_assumptions",
            "public_pension_estimation",
            "retirement_spending_and_success_probability",
            "tax_and_account_rules",
            "product_specifications",
            "security_story_reviews",
            "thematic_fund_reviews",
        ],
        "preferred_source_types": [
            "academic_primary_research",
            "government_or_regulator",
            "index_provider",
            "fund_manager",
            "issuer_ir_or_filing",
        ],
        "source_required_fields": [
            "title",
            "publisher",
            "url",
            "publication_date",
            "accessed_at",
            "source_type",
            "claim_supported",
        ],
        "portfolio_valuation_rule": (
            "外部情報は判断根拠にだけ使い、portfolio_snapshot_as_ofの価格・為替・"
            "評価額・比率を更新しない"
        ),
    }


def build_validation_contract(interaction_phase: str) -> dict:
    return {
        "quality_check_schema": {
            "required_fields": ["check_id", "status", "evidence", "remediation"],
            "status_enum": ["pass", "fail", "not_applicable"],
        },
        "required_check_ids": build_decision_quality_checks(),
        "phase_rule": (
            "objective_confirmationでは全件not_applicable。final_reviewでは適用対象をpassとし、"
            "failを残したまま提出しない"
        ),
        "static_reference_checks": [
            "no_undefined_packet_reference",
            "no_deprecated_date_alias",
            "no_unapproved_material_trade_threshold",
            "one_canonical_tactical_liquidity_policy",
            "allocation_percentages_total_100",
            "no_machine_ids_in_human_sections",
        ],
        "interaction_phase_at_generation": interaction_phase,
    }


def build_phase_output_contract(
    *,
    review_target_month: str,
    portfolio_snapshot_as_of: str,
    review_mode: str,
    interaction_phase: str,
) -> dict:
    return {
        "interaction_phase": interaction_phase,
        "objective_confirmation": {
            "response_type": "one_objective_question_only",
            "optional_content": "各選択肢の一行定義",
            "forbidden": [
                "web_research",
                "investment_decision",
                "six_human_sections",
                "yaml",
                "trade_proposals",
                "decision_quality_checks",
            ],
            "transition": (
                "ユーザーの一回答をupdated_inputsへ反映し、同じ初期入力全体でfinal_reviewを再実行する"
            ),
        },
        "final_review": {
            "required_sections": [
                "【推奨方針】",
                "【採用した決定規則】",
                "【具体的な売買・資金移動】",
                "【実行後配分】",
                "【実行前確認事項】",
                "【Codex向け改善フィードバック】",
            ],
            "updated_inputs_location": "【推奨方針】の冒頭。独立見出しは禁止",
            "general_explanation_max_pct": 20,
            "delivery": {
                "schema_ref": "schemas/monthly-review-response.schema.yaml",
                "preferred": "attach_review_response_yaml",
                "fallback": "six_sections_then_delimiter_then_one_yaml_code_block",
                "yaml_file_transport": "コードフェンスなしの純粋なYAMLファイル",
                "chat_transport": "区切り線後の一つのyamlコードブロック",
            },
        },
        "response_identity": {
            "schema_version": 2,
            "artifact_type": "monthly_review_response",
            "review_mode": review_mode,
            "interaction_phase": "final_review",
            "review_target_month": review_target_month,
            "portfolio_snapshot_as_of": portfolio_snapshot_as_of,
        },
        "canonical_paths": {
            "tactical_liquidity_policy": (
                "strategic_policy_decision.tactical_liquidity_policy"
            ),
            "current_deployment_evaluation": (
                "dip_buy_liquidity_deployment_review"
            ),
            "cash_policy_reference": (
                "cash_assessment.tactical_liquidity_policy_ref"
            ),
            "decision_references": "decisions.policy_refs",
        },
        "array_schemas": {
            "candidate_comparison": build_candidate_methodology()[
                "required_candidate_fields"
            ],
            "source": build_research_contract()["source_required_fields"],
            "empirical_evidence": [
                "evidence_id",
                "claim",
                "source",
                "observed_market_or_population",
                "observation_period",
                "result",
                "limitations",
                "decision_supported",
            ],
            "security_story_source": build_research_contract()[
                "source_required_fields"
            ],
            "thematic_fund_review": [
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
            ],
            "order_proposal": [
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
            ],
            "execution_check": [
                "check_id",
                "status",
                "evidence",
                "blocking_action_ids",
            ],
            "prompt_feedback": [
                "feedback_id",
                "category",
                "severity",
                "problem",
                "recommended_change",
                "affected_path",
            ],
            "before_after_allocation": [
                "view",
                "category",
                "before_pct",
                "after_pct",
                "target_pct",
                "calculation_status",
            ],
            "account_tax_comparison": [
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
            ],
        },
        "root_fields": [
            "schema_version",
            "artifact_type",
            "review_mode",
            "interaction_phase",
            "review_target_month",
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
        ],
        "response_skeleton": build_response_skeleton(
            review_target_month=review_target_month,
            portfolio_snapshot_as_of=portfolio_snapshot_as_of,
            review_mode=review_mode,
        ),
    }


def build_response_skeleton(
    *,
    review_target_month: str,
    portfolio_snapshot_as_of: str,
    review_mode: str,
) -> dict:
    return {
        "schema_version": 2,
        "artifact_type": "monthly_review_response",
        "review_mode": review_mode,
        "interaction_phase": "final_review",
        "review_target_month": review_target_month,
        "portfolio_snapshot_as_of": portfolio_snapshot_as_of,
        "market_reference_as_of": "<packet value>",
        "packet_generated_at": "<packet value>",
        "research_cutoff_at": "<packet value>",
        "decision_date": "<YYYY-MM-DD>",
        "strategic_policy_decision": {
            "status": "<proposed|not_applicable|blocked>",
            "objective": "<objective_id|null>",
            "updated_inputs": {
                "newly_confirmed": [],
                "superseded_assumptions": [],
                "decisions_now_unblocked": [],
                "decisions_still_blocked": [],
            },
            "financial_planning_model": {
                "status": "<derived|not_applicable|blocked>",
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
                "policy_id": "<id>",
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
            "tactical_liquidity_policy": {
                "policy_id": "<id>",
                "status": "<proposed|approved_unchanged|not_applicable|blocked>",
                "initial_target_pct_of_total_assets": None,
                "target_jpy": None,
                "deployment_asset": None,
                "trigger_index": None,
                "reference_high_definition": None,
                "price_basis": None,
                "lookback_period": None,
                "fx_treatment": None,
                "tranches": None,
                "amount_per_tranche": None,
                "refill_rule": None,
                "termination_rule": None,
                "policy_allocation_treatment": None,
                "rationale": "<string>",
                "source_refs": [],
                "requires_user_approval": True,
            },
            "active_risk_policy": {
                "policy_id": "<id>",
                "satellites_allowed": None,
                "total_satellite_cap_pct": None,
                "single_theme_cap_pct": None,
                "single_security_cap_pct": None,
                "exceptions": [],
            },
            "direct_semiconductor_limit": {
                "policy_id": "<id>",
                "status": "<hard_constraint|policy_to_reconsider|explicit_exception>",
                "limit_pct": None,
                "denominator": "household_total_assets_jpy",
                "priority": "<string>",
                "rationale": "<string>",
            },
            "candidate_methodology": "<object matching array_schemas and packet assumptions>",
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
        "human_summary": {"overall_assessment": "<string>", "priority_actions": []},
        "cash_assessment": {
            "emergency_fund_target_jpy": None,
            "emergency_fund_status": "<enum>",
            "monthly_essential_expenses_jpy": None,
            "spending_months": None,
            "near_term_confirmed_expenses_jpy": None,
            "contingency_reserve_jpy": None,
            "tactical_liquidity_policy_ref": (
                "strategic_policy_decision.tactical_liquidity_policy"
            ),
            "dip_buy_liquidity_status": "<enum>",
            "minimum_confirmed_cash_jpy": None,
            "maximum_calculable_cash_jpy": None,
            "total_cash_target_status": "<enum>",
            "total_cash_target_jpy": None,
            "derivation_notes": [],
        },
        "dip_buy_liquidity_deployment_review": {
            "policy_ref": "strategic_policy_decision.tactical_liquidity_policy",
            "reserve_status": "<available|unavailable|unknown>",
            "market_decline_status": "<declining|not_declining|unclear>",
            "trigger_index_matches_deployment_target": None,
            "theme_or_sector_decline_used_as_trigger": False,
            "market_evidence": [],
            "use_option": {
                "considered": False,
                "status": "<enum>",
                "target": None,
                "amount_jpy": None,
                "formula": "<string>",
                "timing": None,
                "rationale": "<string>",
            },
            "selected_action": "<enum>",
            "selection_rationale": "<string>",
            "reserve_maintenance_is_objective": False,
        },
        "security_story_reviews": [],
        "thematic_fund_reviews": [],
        "before_after_allocation": [],
        "account_tax_comparisons": [],
        "decisions": {
            "policy_refs": [],
            "portfolio_diagnosis": [],
            "rule_refs": [],
            "order_proposals": [],
            "actions": [],
        },
        "codex_handoff": {
            "execution_checks": [],
            "prompt_feedback": [],
            "repository_changes": {"must": [], "should": [], "nice_to_have": []},
        },
        "decision_quality_checks": [],
    }


def extract_financial_review_context(
    text: str,
    *,
    source: str,
) -> tuple[str, list[dict], list[dict]]:
    if not text.strip():
        return (
            "unknown",
            [],
            [
                {
                    "item": "financial_assumptions",
                    "reason": "今回のレビュー・パケットに明示的な家計前提が入力されていない",
                    "source": source,
                    "as_of": "unknown",
                }
            ],
        )

    basis_match = re.search(r"^- 基準日:\s*(\d{4}-\d{2}-\d{2})\s*$", text, re.MULTILINE)
    basis_date = basis_match.group(1) if basis_match else "unknown"
    current_section: str | None = None
    conditions: list[dict] = []
    unknowns: list[dict] = []
    condition_index = 0

    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            current_section = heading.group(1)
            continue
        if current_section not in FINANCIAL_FACT_SECTIONS:
            continue
        if not (line.startswith("- ") or line.startswith("根拠資料:")):
            continue

        statement = line[2:].strip() if line.startswith("- ") else line
        if any(marker in statement for marker in UNKNOWN_MARKERS):
            unknowns.append(
                {
                    "item": f"financial_unknown_{len(unknowns) + 1:02d}",
                    "reason": statement,
                    "source": source,
                    "as_of": basis_date,
                }
            )
            continue

        condition_index += 1
        conditions.append(
            {
                "condition_id": f"financial_condition_{condition_index:02d}",
                "statement": statement,
                "source": source,
                "as_of": basis_date,
                "status": "confirmed",
            }
        )
    return basis_date, conditions, unknowns


def build_approved_review_constraints(computation: MonthlyComputation) -> list[dict]:
    constraints = computation.metadata.get("approved_review_constraints", [])
    if not isinstance(constraints, list):
        return []
    required = {"condition_id", "statement", "source", "as_of", "status"}
    return [
        dict(item)
        for item in constraints
        if isinstance(item, dict) and required.issubset(item)
    ]


def build_holding_execution_conditions(computation: MonthlyComputation) -> list[dict]:
    context = computation.metadata.get("holding_execution_context", {})
    if not isinstance(context, dict) or context.get("scope") != "portfolio":
        return []
    if any(
        context.get(field) is not False
        for field in ("unreflected_orders", "planned_withdrawals", "restricted_funds")
    ):
        return []
    return [
        {
            "condition_id": "confirmed_portfolio_execution_clearance",
            "statement": "未反映注文、出金予定、拘束資金はいずれもない",
            "source": safe_selected_source_ref(
                computation.metadata.get("holding_metadata_source"),
                fallback="holdings/current.yaml",
            ),
            "as_of": str(context.get("confirmed_at") or "unknown"),
            "status": "confirmed",
        }
    ]


def extract_structured_financial_review_context(
    context: dict,
    *,
    source: str,
) -> tuple[str, list[dict], list[dict]]:
    effective_from = str(context.get("effective_from") or "unknown")
    conditions: list[dict] = []

    def add(statement: str) -> None:
        conditions.append(
            {
                "condition_id": f"financial_condition_{len(conditions) + 1:02d}",
                "statement": statement,
                "source": source,
                "as_of": effective_from,
                "status": "confirmed",
            }
        )

    regular = context.get("cash_flow", {}).get("regular_month", {})
    income = _structured_value(
        regular.get("income_after_tax_social_insurance_mortgage_ideco_jpy")
    )
    nisa = _structured_value(regular.get("nisa_contribution_jpy"))
    disposable = _structured_value(regular.get("disposable_after_nisa_jpy"))
    essential = _structured_value(regular.get("essential_expenses_jpy"))
    if income is not None:
        add(
            "税金、社会保険料、住宅ローン、iDeCo拠出後の月次収入: "
            f"{income:,}円。この値は支出額ではない"
        )
    if nisa is not None:
        add(f"NISA月次積立額: {nisa:,}円。この値は支出額ではない")
    if disposable is not None:
        add(f"通常月の実質可処分収入: {disposable:,}円。この値は支出額ではない")
    if essential is not None:
        add(f"月間必須支出額: {essential:,}円")
    if regular.get("balance", {}).get("value") == "approximately_zero":
        add("通常月の収支はおおむねプラスマイナスゼロ")

    bonus = context.get("cash_flow", {}).get("bonus", {})
    if bonus:
        add(
            "ボーナスは年"
            f"{bonus.get('annual_frequency')}回、支給月は"
            f"{bonus.get('payment_months')}、手取りは"
            f"{bonus.get('take_home_reference_jpy'):,}円をやや下回る程度の粗い見積もり"
        )
        add("ボーナスの使途は固定せず、旅行や裁量支出を実現した黒字の範囲で行う")

    cash_requirements = context.get("cash_requirements", {})
    emergency = cash_requirements.get("emergency_fund", {})
    if emergency.get("target_jpy") is not None:
        add(f"生活防衛資金の目標額: {emergency['target_jpy']:,}円")
    if (
        emergency.get("permitted_fallback")
        == "sell_all_country_fund_even_during_market_decline_if_needed"
    ):
        add(
            "緊急時は、相場下落中でもオール・カントリー型の投資信託を売却して資金化することを許容する"
        )
    contingency = cash_requirements.get("contingency_reserve", {})
    if contingency.get("enabled") is False:
        add("生活防衛資金とは別の予備費は確保しない")
    near_term = cash_requirements.get("near_term_large_expenses", {})
    if near_term.get("confirmed_items") == []:
        add("今後1～3年以内の金額・時期が確定した大型支出はない")
    travel = near_term.get("unplanned_travel", {})
    if travel.get("expected"):
        add("旅行は予定するが金額・時期は未確定で、ボーナス等の実現黒字から支出する")

    dip = context.get("dip_buy_liquidity", {})
    add("投資待機資金は市場下落時に使う手段であり、残高維持自体を目的にしない")
    target_ratio = dip.get("target_ratio", {})
    if target_ratio.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の目標比率は今回の月次独立レビューから提案を受ける")
    purchase_target = dip.get("purchase_target", {})
    if purchase_target.get("status") == "undecided":
        add("投資待機資金の買付対象は未定")
    activation = dip.get("activation_condition", {})
    if activation.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の発動条件は今回の月次独立レビューから提案を受ける")
    tranches = dip.get("tranche_count", {})
    if tranches.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の投入回数は今回の月次独立レビューから提案を受ける")
    if dip.get("review_rule", {}).get("declining_market_requires_use_option"):
        add("市場下落時は投資待機資金を使う選択肢を必ず比較する")

    unknowns = [
        {
            "item": f"financial_unknown_{index:02d}",
            "reason": str(reason),
            "source": source,
            "as_of": effective_from,
        }
        for index, reason in enumerate(
            context.get("unknown_information", []),
            start=1,
        )
    ]
    return effective_from, conditions, unknowns


def build_structured_cash_requirement_inputs(
    context: dict,
    unknown_information: list[dict],
    *,
    portfolio_snapshot_total_assets_jpy: Decimal,
) -> dict:
    regular = context.get("cash_flow", {}).get("regular_month", {})
    cash_requirements = context.get("cash_requirements", {})
    dip = context.get("dip_buy_liquidity", {})

    income = _structured_value(
        regular.get("income_after_tax_social_insurance_mortgage_ideco_jpy")
    )
    nisa = _structured_value(regular.get("nisa_contribution_jpy"))
    disposable = _structured_value(regular.get("disposable_after_nisa_jpy"))
    essential = _structured_value(regular.get("essential_expenses_jpy"))
    emergency = cash_requirements.get("emergency_fund", {})
    emergency_target = emergency.get("target_jpy")
    contingency = cash_requirements.get("contingency_reserve", {})
    contingency_target = contingency.get("target_jpy")
    near_term = cash_requirements.get("near_term_large_expenses", {})
    confirmed_expenses = near_term.get("confirmed_items", [])
    near_term_total = sum(
        int(item.get("amount_jpy", 0))
        for item in confirmed_expenses
        if isinstance(item, dict) and item.get("amount_jpy") is not None
    )
    near_term_status = (
        "confirmed_no_scheduled_large_expense"
        if confirmed_expenses == []
        else "confirmed_amount"
    )

    target_ratio = dip.get("target_ratio", {})
    ratio_value = target_ratio.get("value")
    dip_target = (
        int(
            (
                Decimal(str(portfolio_snapshot_total_assets_jpy))
                * Decimal(str(ratio_value))
            ).quantize(Decimal("1"))
        )
        if ratio_value is not None
        else None
    )
    dip_status = "unconfigured"
    if ratio_value is not None:
        dip_status = "target_calculated_deployment_unconfigured"
    elif target_ratio.get("status") == "proposal_requested_from_current_monthly_independent_review":
        dip_status = "proposal_requested_from_current_review"

    spending_months = None
    if emergency_target is not None and essential not in (None, 0):
        calculated_months = round(emergency_target / essential, 2)
        spending_months = (
            int(calculated_months)
            if float(calculated_months).is_integer()
            else calculated_months
        )
    minimum_confirmed_cash = sum(
        amount
        for amount in (emergency_target, near_term_total, contingency_target)
        if amount is not None
    )
    total_cash_target = (
        minimum_confirmed_cash + dip_target
        if dip_target is not None
        else None
    )

    bonus = context.get("cash_flow", {}).get("bonus", {})
    return {
        "information_priority": [
            "confirmed_user_condition",
            "observed_packet_fact",
            "machine_calculation",
            "evidence_based_inference",
            "explicit_assumption",
        ],
        "monthly_cash_flow": {
            "after_tax_social_insurance_mortgage_ideco_income_jpy": income,
            "nisa_monthly_contribution_jpy": nisa,
            "effective_monthly_disposable_income_jpy": disposable,
            "monthly_essential_expenses_jpy": essential,
            "ordinary_month_balance": regular.get("balance", {}).get("value", "unknown"),
            "bonus_income": {
                "take_home_reference_jpy": bonus.get("take_home_reference_jpy"),
                "amount_qualifier": bonus.get("amount_qualifier"),
                "annual_frequency": bonus.get("annual_frequency"),
                "payment_months": bonus.get("payment_months", []),
                "certainty": bonus.get("certainty"),
            },
            "income_values_are_not_expense_values": True,
        },
        "emergency_fund": {
            "target_jpy": emergency_target,
            "status": emergency.get("status", "not_calculable"),
            "monthly_essential_expenses_jpy": essential,
            "required_months": spending_months,
            "spending_months": spending_months,
            "derivation": "confirmed_user_target",
        },
        "near_term_confirmed_expenses": {
            "amount_jpy": near_term_total,
            "status": near_term_status,
        },
        "contingency_reserve": {
            "amount_jpy": contingency_target,
            "status": contingency.get("status", "not_defined"),
        },
        "dip_buy_liquidity": {
            "status": dip_status,
            "target_jpy": dip_target,
            "target_ratio": ratio_value,
            "amount_calculation_policy": dip.get("amount_basis"),
            "decision_owner": "current_monthly_independent_review_then_user_approval",
            "purchase_target": _structured_value(dip.get("purchase_target")),
            "activation_condition": _structured_value(dip.get("activation_condition")),
            "tranche_amount_jpy": _structured_value(dip.get("tranche_amount_jpy")),
            "tranche_count": _structured_value(dip.get("tranche_count")),
            "minimum_balance_jpy": _structured_value(dip.get("minimum_balance_jpy")),
            "replenishment_method": _structured_value(dip.get("replenishment_method")),
            "unknown_reason": "; ".join(
                str(item.get("reason"))
                for item in unknown_information
                if "投資待機資金" in str(item.get("reason"))
            ),
        },
        "result": {
            "cash_target_status": (
                "fully_calculable"
                if total_cash_target is not None
                else "confirmed_minimum_only"
            ),
            "minimum_confirmed_cash_jpy": minimum_confirmed_cash,
            "total_cash_target_jpy": total_cash_target,
            "spending_months": spending_months,
            "maximum_cash_target_jpy": total_cash_target,
            "derivation_rule": (
                "emergency_fund + near_term_confirmed_expenses + "
                "explicit_contingency_reserve + approved_ratio_based_dip_buy_liquidity"
            ),
        },
        "prohibited_substitutions": [
            "収入、手取り、可処分所得、NISA積立額、通常月の残額を月間必須支出へ代用しない",
            "資産総額から月間支出または月間必須支出を推定しない",
            "生活防衛資金、確定支出、予備費を総資産比率または目標株式比率から逆算しない",
            "投資待機資金の確保・満額維持自体をレビュー目的にしない",
            "市場下落時に投資待機資金を使う選択肢を省略しない",
        ],
    }


def _structured_value(value):
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def build_cash_requirement_inputs(
    confirmed_conditions: list[dict],
    unknown_information: list[dict],
) -> dict:
    confirmed = [str(item.get("statement", "")) for item in confirmed_conditions]
    unknown = [str(item.get("reason", "")) for item in unknown_information]

    after_deductions_income = find_jpy_amount(
        confirmed,
        "税金、社会保険料、住宅ローン、iDeCo拠出金を給与から差し引いた後の月次手取り相当額",
    )
    nisa_monthly_contribution = find_jpy_amount(
        confirmed,
        "NISA積立として月額",
    )
    disposable_income = find_jpy_amount(
        confirmed,
        "通常月の実質可処分収入",
    )
    monthly_essential_expenses = first_jpy_amount(
        confirmed,
        ("月間必須支出:", "月間必須支出額:"),
    )
    required_emergency_months = find_count(
        confirmed,
        "必要生活防衛月数",
        "か月",
    )
    confirmed_emergency_target = find_jpy_amount(
        confirmed,
        "生活防衛資金の目標額",
    )
    if confirmed_emergency_target is not None:
        emergency_target = confirmed_emergency_target
        emergency_derivation = "confirmed_user_target"
    elif monthly_essential_expenses is not None and required_emergency_months is not None:
        emergency_target = monthly_essential_expenses * required_emergency_months
        emergency_derivation = "monthly_essential_expenses_jpy * required_emergency_months"
    else:
        emergency_target = None
        emergency_derivation = "not_calculable"

    near_term_expenses = first_jpy_amount(
        confirmed,
        (
            "2年以内の確定支出",
            "近い将来の確定支出",
        ),
    )
    near_term_status = (
        "confirmed_amount"
        if near_term_expenses is not None
        else (
            "no_large_outflow_expected_but_amount_not_quantified"
            if any("直近で大きな資金流出は想定していない" in item for item in confirmed)
            else "unknown"
        )
    )
    contingency_reserve = first_jpy_amount(
        confirmed,
        ("明示的に算定した予備費", "予備費の算定額"),
    )

    dip_buy_target = first_jpy_amount(
        confirmed,
        (
            "相場下落時の買い増し用流動資金の目標額",
            "投資待機資金の目標額",
        ),
    )
    dip_buy_fields = {
        "purchase_target": find_text_value(confirmed, ("買付対象",)),
        "activation_condition": find_text_value(
            confirmed,
            ("発動条件", "発動する下落率"),
        ),
        "tranche_amount_jpy": first_jpy_amount(
            confirmed,
            ("各回の投入額", "1回あたりの投入額"),
        ),
        "tranche_count": find_count(confirmed, "投入回数", "回"),
        "minimum_balance_jpy": first_jpy_amount(
            confirmed,
            ("最低残高",),
        ),
        "replenishment_method": find_text_value(confirmed, ("補充方法",)),
    }
    dip_buy_configured = dip_buy_target is not None and all(
        value not in (None, "") for value in dip_buy_fields.values()
    )
    dip_buy_ratio_delegated = any(
        "具体的な目標比率はオンデマンド独立判断へ委譲中" in item
        for item in confirmed
    )
    if dip_buy_configured:
        dip_buy_status = "configured"
    elif dip_buy_target is not None:
        dip_buy_status = "target_calculated_deployment_unconfigured"
    elif dip_buy_ratio_delegated:
        dip_buy_status = "pending_independent_second_opinion"
    else:
        dip_buy_status = "unconfigured"
    dip_buy_unknown_reason = next(
        (
            item
            for item in unknown
            if "相場下落時の買い増し用流動資金" in item
            or "投資待機資金" in item
        ),
        None,
    )

    spending_months = (
        round(emergency_target / monthly_essential_expenses, 2)
        if emergency_target is not None and monthly_essential_expenses not in (None, 0)
        else None
    )
    minimum_confirmed_cash = sum(
        amount
        for amount in (emergency_target, near_term_expenses, contingency_reserve)
        if amount is not None
    )
    minimum_confirmed_cash = minimum_confirmed_cash or None
    fully_calculable = (
        emergency_target is not None
        and near_term_expenses is not None
        and dip_buy_target is not None
    )
    total_cash_target = (
        emergency_target
        + near_term_expenses
        + (contingency_reserve or 0)
        + dip_buy_target
        if fully_calculable
        else None
    )
    if fully_calculable:
        cash_target_status = "fully_calculable"
    elif emergency_target is not None:
        cash_target_status = "confirmed_minimum_only"
    else:
        cash_target_status = "not_calculable"

    return {
        "information_priority": [
            "confirmed_user_condition",
            "observed_packet_fact",
            "machine_calculation",
            "evidence_based_inference",
            "explicit_assumption",
        ],
        "monthly_cash_flow": {
            "after_tax_social_insurance_mortgage_ideco_income_jpy": after_deductions_income,
            "nisa_monthly_contribution_jpy": nisa_monthly_contribution,
            "effective_monthly_disposable_income_jpy": disposable_income,
            "monthly_essential_expenses_jpy": monthly_essential_expenses,
            "ordinary_month_balance": (
                "approximately_zero"
                if any("通常月の収支はおおむねプラスマイナスゼロ" in item for item in confirmed)
                else "unknown"
            ),
            "bonus_income": (
                "exists_amount_and_timing_unknown"
                if any("ボーナス収入がある" in item for item in confirmed)
                else "unknown"
            ),
            "income_values_are_not_expense_values": True,
        },
        "emergency_fund": {
            "target_jpy": emergency_target,
            "status": (
                "confirmed_user_target"
                if confirmed_emergency_target is not None
                else "calculated" if emergency_target is not None else "not_calculable"
            ),
            "monthly_essential_expenses_jpy": monthly_essential_expenses,
            "required_months": required_emergency_months,
            "spending_months": spending_months,
            "derivation": emergency_derivation,
        },
        "near_term_confirmed_expenses": {
            "amount_jpy": near_term_expenses,
            "status": near_term_status,
        },
        "contingency_reserve": {
            "amount_jpy": contingency_reserve,
            "status": "calculated" if contingency_reserve is not None else "not_defined",
        },
        "dip_buy_liquidity": {
            "status": dip_buy_status,
            "target_jpy": dip_buy_target,
            "amount_calculation_policy": (
                "portfolio_snapshot_total_assets_jpy * independently_recommended_pct"
                if dip_buy_ratio_delegated
                else None
            ),
            "decision_owner": (
                "independent_chatgpt_second_opinion_then_user_approval"
                if dip_buy_ratio_delegated
                else None
            ),
            **dip_buy_fields,
            "unknown_reason": dip_buy_unknown_reason,
        },
        "result": {
            "cash_target_status": cash_target_status,
            "minimum_confirmed_cash_jpy": minimum_confirmed_cash,
            "total_cash_target_jpy": total_cash_target,
            "spending_months": spending_months,
            "maximum_cash_target_jpy": total_cash_target,
            "derivation_rule": (
                "emergency_fund + near_term_confirmed_expenses + "
                "explicit_contingency_reserve + confirmed_dip_buy_liquidity_target"
            ),
        },
        "prohibited_substitutions": [
            "収入、手取り、可処分所得、NISA積立額、通常月の残額を月間必須支出へ代用しない",
            "収入と通常月収支から通常支出の条件付き概算を行う場合も、月間必須支出の確定値や支出月数の分母にはしない",
            "資産総額から月間支出または月間必須支出を推定しない",
            "生活防衛資金、確定支出、予備費を総資産比率または目標株式比率から逆算しない。投資待機資金だけは独立ChatGPTが提案しユーザが承認した総資産比率から算定する",
            "未設定の投資待機資金を生活防衛資金へ上乗せしない",
            "オンデマンド独立判断へ委譲中の比率を月次レビューまたはCodexで先回りして決定しない",
            "confirmed条件を一般的な資産配分、保守的な印象、丸い比率で上書きしない",
        ],
    }


def find_jpy_amount(statements: list[str], label: str) -> int | None:
    return first_jpy_amount(statements, (label,))


def first_jpy_amount(statements: list[str], labels: tuple[str, ...]) -> int | None:
    for statement in statements:
        if not any(label in statement for label in labels):
            continue
        match = re.search(r"(?:約)?\s*([0-9][0-9,]*)円", statement)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def find_count(statements: list[str], label: str, unit: str) -> int | None:
    for statement in statements:
        if label not in statement:
            continue
        match = re.search(rf"([0-9]+)\s*{re.escape(unit)}", statement)
        if match:
            return int(match.group(1))
    return None


def find_text_value(statements: list[str], labels: tuple[str, ...]) -> str | None:
    for statement in statements:
        for label in labels:
            match = re.search(rf"{re.escape(label)}\s*:\s*(.+)$", statement)
            if match:
                return match.group(1).strip()
    return None


def build_allowed_quantitative_facts(
    computation: MonthlyComputation,
    *,
    recurring: dict,
    cash_requirement_inputs: dict,
) -> dict:
    snapshot = computation.snapshot
    total = snapshot.total_assets_jpy
    asset_class_values: dict[str, Decimal] = defaultdict(Decimal)
    for holding in snapshot.holdings:
        asset_class_values[holding.asset_class] += holding.market_value_jpy

    liquidity_jpy = asset_class_values.get("liquidity", Decimal("0"))
    other_jpy = asset_class_values.get("other", Decimal("0"))
    equity_like_jpy = total - liquidity_jpy - other_jpy
    core_like_jpy = sum(
        value
        for asset_class, value in asset_class_values.items()
        if asset_class in {"core", "pension"}
    )
    satellite_like_jpy = sum(
        value
        for asset_class, value in asset_class_values.items()
        if asset_class in {"jun_core", "satellite_core", "satellite"}
    )

    category_totals = [
        {
            "category": category,
            "market_value_jpy": value,
            "portfolio_pct": percentage_of(value, total),
        }
        for category, value in sorted(snapshot.category_totals_jpy.items())
    ]
    asset_class_allocations = [
        {
            "asset_class": asset_class,
            "market_value_jpy": value,
            "portfolio_pct": percentage_of(value, total),
        }
        for asset_class, value in sorted(asset_class_values.items())
    ]
    holdings = [
        {
            "symbol": holding.symbol,
            "name": holding.name,
            "human_label": holding.name,
            "asset_class": holding.asset_class,
            "source_category": holding.source_category,
            "institution": holding.institution,
            "account_type": holding.account_type,
            "quantity": holding.quantity,
            "avg_cost": holding.avg_cost,
            "current_price": holding.current_price,
            "market_value_jpy": holding.market_value_jpy,
            "profit_loss_jpy": holding.profit_loss_jpy,
            "currency": holding.currency,
            "portfolio_pct": percentage_of(holding.market_value_jpy, total),
        }
        for holding in snapshot.holdings
    ]

    investable_holdings = [
        holding
        for holding in snapshot.holdings
        if holding.asset_class not in {"liquidity", "other"}
    ]
    largest_positions = [
        {
            "symbol": holding.symbol,
            "name": holding.name,
            "market_value_jpy": holding.market_value_jpy,
            "portfolio_pct": percentage_of(holding.market_value_jpy, total),
        }
        for holding in sorted(
            investable_holdings,
            key=lambda item: item.market_value_jpy,
            reverse=True,
        )[:10]
    ]

    return {
        "cash_requirement_inputs": cash_requirement_inputs,
        "portfolio_totals": {
            "currency_base": snapshot.currency_base,
            "total_assets_jpy": total,
            "liquidity_jpy": liquidity_jpy,
            "liquidity_pct": percentage_of(liquidity_jpy, total),
            "equity_like_jpy": equity_like_jpy,
            "equity_like_pct": percentage_of(equity_like_jpy, total),
            "core_like_jpy": core_like_jpy,
            "core_like_pct": percentage_of(core_like_jpy, total),
            "satellite_like_jpy": satellite_like_jpy,
            "satellite_like_pct": percentage_of(satellite_like_jpy, total),
            "classification_note": (
                "equity_likeはliquidity/other以外、core_likeはcore+pension、"
                "satellite_likeはjun_core+satellite_core+satelliteを機械集計"
            ),
        },
        "category_totals": category_totals,
        "asset_class_allocations": asset_class_allocations,
        "holdings": holdings,
        "security_story_review_targets": list(computation.security_story_targets),
        "thematic_fund_review_targets": build_thematic_fund_review_targets(
            snapshot.holdings
        ),
        "same_product_account_groups": build_same_product_account_groups(
            snapshot.holdings
        ),
        "market_references": build_market_reference_facts(computation),
        "concentration_metrics": {
            "largest_positions": largest_positions,
            "direct_semiconductor_exposure_jpy": computation.exposure_breakdown.get(
                "direct_semiconductor_exposure_jpy"
            ),
            "direct_semiconductor_exposure_pct": ratio_to_percentage(
                computation.exposure_breakdown.get(
                    "direct_semiconductor_exposure_pct"
                )
            ),
            "indirect_ai_infra_exposure_jpy": computation.exposure_breakdown.get(
                "indirect_ai_infra_exposure_jpy"
            ),
            "indirect_ai_infra_exposure_pct": ratio_to_percentage(
                computation.exposure_breakdown.get(
                    "indirect_ai_infra_exposure_pct"
                )
            ),
            "exposure_components": build_exposure_components(
                computation.exposure_breakdown
            ),
            "calculation_note": (
                "現在評価額を総資産で割った機械計算。目標値、上限、売買提案は含まない"
            ),
        },
        "recurring_commitments": recurring,
        "data_quality_notes": {
            "ocr_notes": list(snapshot.ocr_notes),
            "validation_notes": list(snapshot.validation_notes),
            "validation_findings": build_validation_findings(computation),
        },
    }


def build_thematic_fund_review_targets(holdings) -> list[dict]:
    groups = build_same_product_account_groups(holdings)
    targets: list[dict] = []
    for group in groups:
        symbols = list(group.get("symbols", []))
        product_name = str(group.get("product_name") or "")
        if not (
            any(symbol.startswith("NISSEI_SOX_") for symbol in symbols)
            or "SOX" in product_name.upper()
            or "半導体" in product_name
        ):
            continue
        targets.append(
            {
                "theme_review_id": "nissei_sox_index_fund",
                "product_name": product_name,
                "member_symbols": symbols,
                "story_review_scope": "product_and_underlying_index_once",
                "underlying_index": None,
                "underlying_index_status": "requires_primary_source_research",
                "account_lot_review_scope": "each_member_separately",
                "account_lots": [
                    {
                        "symbol": member.get("symbol"),
                        "human_label": member.get("human_label"),
                        "account_type": member.get("account_type"),
                        "market_value_jpy": member.get("market_value_jpy"),
                        "profit_loss_jpy": member.get("profit_loss_jpy"),
                    }
                    for member in group.get("members", [])
                ],
                "required_assessment": (
                    "商品・指数ストーリーを一度評価し、口座・ロットごとの税務・執行判断を分離する"
                ),
            }
        )
    return targets


def build_market_reference_facts(computation: MonthlyComputation) -> list[dict]:
    facts: list[dict] = []
    for reference in computation.market_references:
        facts.append(
            {
                "symbol": reference.symbol,
                "reference_symbol": reference.yfinance_symbol,
                "as_of": reference.as_of.isoformat(),
                "currency": reference.currency,
                "current_price": reference.current_price,
                "mean_close_20d": reference.mean_close_20d,
                "recent_high_21d": reference.recent_high_21d,
                "recent_high_63d": reference.recent_high_63d,
                "return_21d_pct": percent_change(
                    reference.current_price,
                    reference.prior_close_21d,
                ),
                "return_63d_pct": percent_change(
                    reference.current_price,
                    reference.prior_close_63d,
                ),
                "drawdown_from_21d_high_pct": percent_change(
                    reference.current_price,
                    reference.recent_high_21d,
                ),
                "drawdown_from_63d_high_pct": percent_change(
                    reference.current_price,
                    reference.recent_high_63d,
                ),
            }
        )
    return facts


def build_exposure_components(exposure_breakdown: dict) -> list[dict]:
    components: list[dict] = []
    for item in exposure_breakdown.get("breakdown", []):
        direct = is_yes(item.get("included_in_direct_semiconductor_exposure"))
        indirect = is_yes(item.get("included_in_indirect_ai_infra_exposure"))
        if not (direct or indirect):
            continue
        components.append(
            {
                "symbol": item.get("symbol"),
                "market_value_jpy": item.get("value_jpy"),
                "portfolio_pct": ratio_to_percentage(item.get("portfolio_pct")),
                "included_in_direct_semiconductor_exposure": direct,
                "included_in_indirect_ai_infra_exposure": indirect,
            }
        )
    return components


def build_recurring_commitments(
    config: dict,
    *,
    source: str,
    as_of: str,
) -> dict:
    plans = [
        select_keys(
            item,
            (
                "day_of_month",
                "fund_name",
                "amount_jpy",
                "settlement_type",
                "account_type",
                "distribution_course",
            ),
        )
        for item in config.get("plans", [])
    ]
    pension = [
        select_keys(
            item,
            (
                "symbol",
                "fund_name",
                "amount_jpy_per_month",
                "account_type",
                "asset_class",
            ),
        )
        for item in config.get("pension_monthly_dca", [])
    ]
    crypto = [
        select_keys(item, ("symbol", "amount_jpy_per_week"))
        for item in config.get("crypto_weekly_dca", [])
    ]
    facts = {
        "core_monthly_total_jpy": sum(
            int(item.get("amount_jpy", 0)) for item in plans
        ),
        "core_monthly_plans": plans,
        "pension_monthly_total_jpy": sum(
            int(item.get("amount_jpy_per_month", 0)) for item in pension
        ),
        "pension_monthly_plans": pension,
        "crypto_weekly_total_jpy": sum(
            int(item.get("amount_jpy_per_week", 0)) for item in crypto
        ),
        "crypto_weekly_plans": crypto,
        "nisa_growth_quota_status": config.get("nisa_growth_quota_status"),
        "source": source,
        "as_of": as_of,
    }
    conditions: list[dict] = []
    if plans:
        conditions.append(
            {
                "condition_id": "observed_core_recurring_settings",
                "statement": (
                    "現在記録されているcore定期積立設定を、実行済み取引ではなく"
                    "継続中の設定として扱う"
                ),
                "source": source,
                "as_of": as_of,
                "status": "observed_setting",
            }
        )
    if pension:
        conditions.append(
            {
                "condition_id": "observed_pension_recurring_settings",
                "statement": "現在記録されているiDeCo月次積立設定",
                "source": source,
                "as_of": as_of,
                "status": "observed_setting",
            }
        )
    if crypto:
        conditions.append(
            {
                "condition_id": "observed_crypto_recurring_settings",
                "statement": "現在記録されている暗号資産週次積立設定",
                "source": source,
                "as_of": as_of,
                "status": "observed_setting",
            }
        )
    return {"facts": facts, "conditions": conditions}


def build_computation_unknowns(computation: MonthlyComputation) -> list[dict]:
    snapshot = computation.snapshot
    unknowns: list[dict] = []
    if snapshot.liquidity_target_jpy is None:
        unknowns.append(
            {
                "item": "liquidity_target_jpy",
                "reason": "正規化スナップショットに現金目標額が記録されていない",
                "source": "normalized_snapshot",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    if any(
        holding.asset_class == "liquidity"
        and holding.institution is None
        for holding in snapshot.holdings
    ):
        unknowns.append(
            {
                "item": "liquidity_account_breakdown",
                "reason": "現金は集約値で、口座別の利用可能額がパケットにない",
                "source": "normalized_snapshot",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    missing_account_symbols = sorted(
        holding.symbol
        for holding in snapshot.holdings
        if holding.asset_class not in {"liquidity", "pension", "other"}
        and holding.account_type is None
    )
    if missing_account_symbols:
        unknowns.append(
            {
                "item": "tradable_holding_account_types",
                "reason": (
                    "売買可能資産の口座区分が未確認: "
                    + ", ".join(missing_account_symbols)
                    + "。口座区分を確認するまで、売却ロット、一本化、口座間移管を確定しない"
                ),
                "source": "normalized_snapshot",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    unverified_groups = [
        group
        for group in build_same_product_account_groups(snapshot.holdings)
        if group["account_separation_status"] == "unverified"
    ]
    if unverified_groups:
        group_members = "; ".join(
            f"{group['product_name']} ({', '.join(group['symbols'])})"
            for group in unverified_groups
        )
        unknowns.append(
            {
                "item": "same_product_account_separation",
                "reason": (
                    "同一商品の複数明細について口座区分が未確認: "
                    + group_members
                    + "。商品名の一致だけを重複・一本化の根拠にしない"
                ),
                "source": "normalized_snapshot",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    missing_thesis_symbols = sorted(
        target["symbol"]
        for target in computation.security_story_targets
        if not target.get("thesis_recorded")
    )
    if missing_thesis_symbols:
        unknowns.append(
            {
                "item": "individual_stock_etf_investment_theses",
                "reason": (
                    "投資仮説・棄却条件が正本に未記録の個別株・ETF: "
                    + ", ".join(missing_thesis_symbols)
                    + "。レビュー対象から除外せず、一次情報から暫定ストーリーを再構成し、"
                    "買い増しはユーザが保有理由を確認するまで確定しない"
                ),
                "source": "strategy/theses/index.yaml",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    unknowns.extend(
        [
            {
                "item": "sale_tax_and_transaction_costs",
                "reason": "売却税、取得ロット、手数料の確定値はパケットにない",
                "source": "review_packet_boundary",
                "as_of": snapshot.snapshot_date.isoformat(),
            },
            {
                "item": "risk_target_parameters",
                "reason": (
                    "未承認の投資待機資金比率など必要入力がない指標は算定不能として扱う。"
                    "目標株式比率と目標コア・サテライト比率は、"
                    "導出可能な現金要件を先に確保した後で評価する。"
                    "確認済みの集中上限はconfirmed_user_conditionsを優先する"
                ),
                "source": "review_scope",
                "as_of": snapshot.snapshot_date.isoformat(),
            },
        ]
    )
    execution = computation.metadata.get("holding_execution_context", {})
    execution_clear = isinstance(execution, dict) and all(
        execution.get(field) is False
        for field in ("unreflected_orders", "planned_withdrawals", "restricted_funds")
    )
    if not execution_clear:
        unknowns.append(
            {
                "item": "unsettled_orders_and_transfers",
                "reason": "未反映注文、入出金、拘束資金はパケットにない",
                "source": "review_packet_boundary",
                "as_of": snapshot.snapshot_date.isoformat(),
            }
        )
    for reference in computation.market_references:
        if reference.current_price is None:
            unknowns.append(
                {
                    "item": f"market_price_{reference.symbol}",
                    "reason": "市場参照価格を取得できていない",
                    "source": "market_reference_collection",
                    "as_of": reference.as_of.isoformat(),
                }
            )
    return unknowns


def build_validation_findings(computation: MonthlyComputation) -> list[dict]:
    return [
        {
            "code": warning.code,
            "severity": warning.severity,
            "message": warning.message,
            "related_symbols": list(warning.related_symbols),
        }
        for warning in computation.warnings
        if warning.code.startswith(VALIDATION_WARNING_PREFIXES)
    ]


def build_preflight_checklist() -> list[str]:
    return [
        "ChatGPTの資産運用プロジェクト内では実行しない",
        "プロジェクト外の新規Temporary Chatなど、過去会話を参照しない環境で実行する",
        "前月のレビュースレッドを再利用しない",
        "このレビュー・パケット以外のファイルを添付しない",
        "独立レビューへ影響するカスタム指示を無効化するか、影響しないことを確認する",
    ]


def build_same_product_account_groups(holdings) -> list[dict]:
    grouped: dict[str, list] = defaultdict(list)
    display_names: dict[str, str] = {}
    for holding in holdings:
        normalized_name = normalize_product_name(holding.name)
        if not normalized_name:
            continue
        grouped[normalized_name].append(holding)
        display_names.setdefault(normalized_name, holding.name)

    groups: list[dict] = []
    for normalized_name, members in grouped.items():
        if len(members) < 2:
            continue
        account_types = [member.account_type for member in members]
        accounts_known = all(account_types)
        if accounts_known and len(set(account_types)) > 1:
            status = "separate_accounts_confirmed"
        elif accounts_known:
            status = "same_account_multiple_lots"
        else:
            status = "unverified"
        groups.append(
            {
                "product_name": display_names[normalized_name],
                "human_label": (
                    f"{display_names[normalized_name]}（口座区分未確認の{len(members)}明細）"
                    if not accounts_known
                    else display_names[normalized_name]
                ),
                "symbols": [member.symbol for member in members],
                "account_separation_status": status,
                "members": [
                    {
                        "symbol": member.symbol,
                        "human_label": (
                            f"{member.name}（{member.account_type}）"
                            if member.account_type
                            else f"{member.name}（評価額{int(member.market_value_jpy):,}円の明細・口座区分未確認）"
                        ),
                        "institution": member.institution,
                        "account_type": member.account_type,
                        "market_value_jpy": member.market_value_jpy,
                        "avg_cost": member.avg_cost,
                        "profit_loss_jpy": member.profit_loss_jpy,
                    }
                    for member in members
                ],
                "decision_note": (
                    "経済的エクスポージャーは合算して評価するが、売却・移管・一本化は"
                    "口座区分と税引後結果を確認してロット単位で判断する"
                ),
            }
        )
    return sorted(groups, key=lambda item: item["product_name"])


def normalize_product_name(value: str | None) -> str:
    if value is None:
        return ""
    return "".join(str(value).lower().split())


def build_excluded_information(review_mode: str) -> list[str]:
    items = [
        "過去の会話、前月以前のレビュー回答、プロジェクト内メモリ",
        "Codexの過去評価、過去推奨、承認済みまたは保留中の売買計画",
        "Pythonがルールから生成した候補注文、推奨予算、抑制判断",
        "今回selected_sourcesに選ばれていない履歴、取引記録、意思決定記録",
        "レビューに無関係なファイル名、添付メタデータ、取得失敗、再アップロード履歴",
        "パケット外のProject/GPT参照ファイル、カスタムメモリ、周辺会話",
    ]
    if review_mode == "strategic_policy_second_opinion":
        items.insert(
            1,
            "現行戦略の目標比率・閾値（政策配分を現在保有に合わせて後付けしないため）",
        )
    return items


def safe_selected_source_ref(value, *, fallback: str) -> str:
    if not value:
        return fallback
    raw = str(value).replace("\\", "/")
    for marker in (
        "data/normalized/",
        "plans/recurring/",
        "financial/versions/",
        "holdings/versions/",
        "strategy/versions/",
        "FINANCIAL_ASSUMPTIONS.md",
    ):
        if marker in raw:
            return raw[raw.index(marker) :]
    return Path(raw).name or fallback


def latest_market_reference_date(computation: MonthlyComputation) -> str:
    dates = [reference.as_of for reference in computation.market_references]
    return max(dates).isoformat() if dates else "unknown"


def is_after_review_date(as_of: str, review_date: date) -> bool:
    try:
        return date.fromisoformat(as_of) > review_date
    except ValueError:
        return False


def percentage_of(value: Decimal, total: Decimal) -> Decimal | None:
    if total == 0:
        return None
    return quantize((value / total) * Decimal("100"), 2)


def ratio_to_percentage(value) -> Decimal | None:
    if value is None:
        return None
    return quantize(Decimal(str(value)) * Decimal("100"), 2)


def percent_change(current, reference) -> Decimal | None:
    if current is None or reference in (None, 0):
        return None
    return quantize(
        ((Decimal(str(current)) / Decimal(str(reference))) - Decimal("1"))
        * Decimal("100"),
        2,
    )


def select_keys(payload: dict, keys: tuple[str, ...]) -> dict:
    return {key: payload.get(key) for key in keys}


def is_yes(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"yes", "true", "1"}


def deduplicate_unknowns(items: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    result: list[dict] = []
    for item in items:
        key = (str(item.get("item")), str(item.get("reason")))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result
