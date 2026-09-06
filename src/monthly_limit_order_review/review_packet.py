from __future__ import annotations

import re
from collections import defaultdict
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from .models import MonthlyComputation, ReviewPacket
from .review_readiness import build_account_type_gate
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
    "on_demand_operational_review",
    "strategic_policy_second_opinion",
}
GENERATION_STATUSES = {
    "ready",
    "blocked_missing_strategic_inputs",
    "blocked_missing_account_types",
}
INTERACTION_PHASES = {"objective_confirmation", "final_review"}
PRIMARY_OBJECTIVES = {
    "maximize_terminal_wealth",
    "minimize_risk_for_required_return",
    "maximize_ex_ante_sharpe_ratio",
}


def is_crypto_holding(holding) -> bool:
    source_category = str(getattr(holding, "source_category", "") or "")
    symbol = str(getattr(holding, "symbol", "") or "").upper()
    return source_category == "暗号資産" or symbol in {"BTC", "ETH", "XRP"}


def snapshot_has_crypto_holdings(snapshot) -> bool:
    return any(is_crypto_holding(holding) for holding in snapshot.holdings)


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
        financial_context_for_review,
        portfolio_snapshot_as_of=snapshot.snapshot_date,
    )
    missing_strategic_inputs = (
        find_missing_strategic_inputs(
            strategic_required_inputs,
            strategic_decision_objective=strategic_decision_objective,
        )
        if review_mode == "strategic_policy_second_opinion"
        else []
    )
    account_type_gate = build_account_type_gate(snapshot)
    if account_type_gate["status"] != "complete":
        generation_status = "blocked_missing_account_types"
    elif missing_strategic_inputs:
        generation_status = "blocked_missing_strategic_inputs"
    else:
        generation_status = "ready"
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
    unknown_information = financial_unknowns + build_computation_unknowns(
        computation,
        review_mode=review_mode,
    )

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
    if review_mode == "on_demand_operational_review":
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
        packet_type="on_demand_independent_review",
        generation_status=generation_status,
        review_cadence="on_demand",
        interaction_phase=interaction_phase,
        review_mode=review_mode,
        review_target_month=review_target_month,
        portfolio_snapshot_as_of=snapshot.snapshot_date,
        market_reference_as_of=latest_market_reference_date(computation),
        packet_generated_at=computation.generated_at,
        research_cutoff_at=computation.generated_at,
        decision_date=None,
        strategic_required_inputs=normalize_review_cadence_terms(
            strategic_required_inputs
        ),
        missing_strategic_inputs=missing_strategic_inputs,
        account_type_gate=account_type_gate,
        strategic_decision_objective=normalize_review_cadence_terms(
            strategic_decision_objective
        ),
        candidate_methodology=normalize_review_cadence_terms(
            build_candidate_methodology(
                has_crypto_holdings=snapshot_has_crypto_holdings(snapshot)
            )
        ),
        decision_stage_contract=build_decision_stage_contract(),
        execution_capability_contract=build_execution_capability_contract(),
        capital_layers=build_capital_layers(),
        asset_class_definitions=build_asset_class_definitions(
            has_crypto_holdings=snapshot_has_crypto_holdings(snapshot)
        ),
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
        active_risk_policy=build_active_risk_policy(
            financial_context_for_review,
            computation=computation,
        ),
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
    satellite_review = computation.metadata.get("satellite_review_policy", {})
    if any(
        isinstance(satellite_review.get(field), dict)
        and satellite_review[field].get("status") == "reviewer_to_propose"
        for field in ("target_pct", "securities")
    ):
        return "strategic_policy_second_opinion"
    if (
        cash_requirement_inputs.get("dip_buy_liquidity", {}).get("status")
        == "proposal_requested_from_current_review"
    ):
        return "strategic_policy_second_opinion"
    return "on_demand_operational_review"


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
    household_balance, household_balance_as_of = extract_scheduled_mortgage_balance(
        household_mortgage
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

    planned_contributions = deepcopy(profile.get("planned_contributions"))
    if isinstance(planned_contributions, dict):
        planned_contributions["observed_commitments_ref"] = recurring.get("source")
        constraints = planned_contributions.get("constraints")
        if isinstance(constraints, list):
            planned_contributions["constraints"] = [
                item
                for item in constraints
                if item
                != "do_not_treat_the_observed_750000_jpy_monthly_setting_as_salary_funded_without_evidence"
            ]

    planning_timeline = build_planning_timeline(
        profile,
        snapshot_date=computation.snapshot.snapshot_date,
        mortgage_maturity_date=maturity_date,
    )
    liability_cash_flows = build_liability_cash_flows(
        computation=computation,
        household_mortgage=household_mortgage,
        user_mortgage=user_mortgage,
        user_balance=user_balance,
        balance_as_of=household_balance_as_of,
        planning_timeline=planning_timeline,
    )
    contribution_reconciliation = build_contribution_reconciliation(
        source,
        recurring=recurring,
    )

    return {
        "date_of_birth": date_of_birth,
        "user_age": user_age,
        "user_age_as_of": user_age_as_of,
        "tax_residency": profile.get("tax_residency"),
        "investment_horizon_years_display_only": profile.get(
            "investment_horizon_years"
        ),
        "planning_end_age": profile.get("planning_end_age"),
        "expected_withdrawal_start": profile.get("expected_withdrawal_start"),
        "earliest_possible_asset_use_date": profile.get(
            "earliest_possible_asset_use_date"
        ),
        "planning_timeline": planning_timeline,
        "planned_contributions": planned_contributions,
        "current_recurring_commitments": recurring,
        "contribution_reconciliation": contribution_reconciliation,
        "expected_future_cash_flows": profile.get("expected_future_cash_flows"),
        "bonus_information": build_bonus_information(source),
        "human_capital_assumptions": profile.get("human_capital_assumptions"),
        "liabilities": {
            "mortgage_outstanding_jpy": household_balance,
            "user_share_jpy": user_balance,
            "interest_rate": household_mortgage.get("annual_interest_rate"),
            "fixed_or_variable": household_mortgage.get("fixed_or_variable"),
            "remaining_term_years": remaining_term_years,
            "annual_repayment_jpy": user_mortgage.get("annual_payment_jpy"),
            "balance_as_of": household_balance_as_of,
        },
        "liability_cash_flows": liability_cash_flows,
        "pension_and_other_future_assets": profile.get(
            "pension_and_other_future_assets"
        ),
    }


def add_years(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(month=2, day=28, year=value.year + years)


def extract_scheduled_mortgage_balance(mortgage: dict) -> tuple[object, str | None]:
    for key, value in mortgage.items():
        match = re.fullmatch(
            r"scheduled_balance_after_(\d{4})_(\d{2})_(\d{2})_jpy",
            str(key),
        )
        if match and value is not None:
            return value, "-".join(match.groups())
    return None, None


def complete_months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day:
        months -= 1
    return max(months, 0)


def build_planning_timeline(
    profile: dict,
    *,
    snapshot_date: date,
    mortgage_maturity_date,
) -> dict:
    birth_raw = profile.get("date_of_birth")
    withdrawal_raw = profile.get("expected_withdrawal_start")
    planning_end_age = profile.get("planning_end_age")
    human_capital = profile.get("human_capital_assumptions", {})
    retirement_age = human_capital.get("planned_retirement_age")

    birth_date = date.fromisoformat(str(birth_raw)) if birth_raw else None
    withdrawal_date = (
        date.fromisoformat(str(withdrawal_raw)) if withdrawal_raw else None
    )
    planning_end_date = (
        add_years(birth_date, int(planning_end_age))
        if birth_date is not None and planning_end_age is not None
        else None
    )
    retirement_date = (
        add_years(birth_date, int(retirement_age))
        if birth_date is not None and retirement_age is not None
        else None
    )
    contribution_end_date = (
        withdrawal_date - timedelta(days=1) if withdrawal_date is not None else None
    )
    maturity = (
        date.fromisoformat(str(mortgage_maturity_date))
        if mortgage_maturity_date
        else None
    )
    pension_start_contract = {
        "value": None,
        "status": "reviewer_to_derive",
        "decision_owner": "independent_on_demand_reviewer",
        "selection_criteria": (
            "現行の公的年金制度、確認済み就業期間、退職予定日を使い、"
            "一つのベースケース日付と感応度を選ぶ"
        ),
        "allowed_primary_sources": [
            "Japan_Pension_Service",
            "Ministry_of_Health_Labour_and_Welfare",
        ],
        "base_case_required": True,
        "sensitivity_required": True,
    }
    return {
        "date_source_of_truth_rule": (
            "日付を計算の正本とし、年齢・整数年は表示用に限る。"
            "同一キャッシュフローを拠出期と取崩期の両方へ計上しない"
        ),
        "model_period": "monthly",
        "model_start_date": snapshot_date.isoformat(),
        "contribution_end_date": (
            contribution_end_date.isoformat() if contribution_end_date else None
        ),
        "first_withdrawal_date": (
            withdrawal_date.isoformat() if withdrawal_date else None
        ),
        "planned_retirement_date": (
            retirement_date.isoformat() if retirement_date else None
        ),
        "public_pension_start_date": pension_start_contract,
        "mortgage_repayment_end_date": maturity.isoformat() if maturity else None,
        "planning_end_date": (
            planning_end_date.isoformat() if planning_end_date else None
        ),
        "accumulation_complete_months": (
            complete_months_between(snapshot_date, withdrawal_date)
            if withdrawal_date
            else None
        ),
        "withdrawal_complete_months": (
            complete_months_between(withdrawal_date, planning_end_date)
            if withdrawal_date and planning_end_date
            else None
        ),
        "total_complete_months": (
            complete_months_between(snapshot_date, planning_end_date)
            if planning_end_date
            else None
        ),
        "cash_flow_boundary_rule": (
            "拠出はcontribution_end_dateまで、最初の取崩しはfirst_withdrawal_dateから。"
            "年金は導出した開始日から、住宅ローンは返済終了日まで別建てで計上する"
        ),
        "annual_model_fallback_rule": (
            "月次モデルを使えない場合だけ、各暦年末にフローを置き、"
            "境界年は実在月数で按分し、同じ月を重複させない"
        ),
    }


def build_liability_cash_flows(
    *,
    computation: MonthlyComputation,
    household_mortgage: dict,
    user_mortgage: dict,
    user_balance,
    balance_as_of: str | None,
    planning_timeline: dict,
) -> list[dict]:
    monthly_payment = user_mortgage.get("monthly_payment_jpy")
    maturity_date = household_mortgage.get("maturity_date")
    first_model_payment_date = None
    if balance_as_of and maturity_date:
        balance_date = date.fromisoformat(balance_as_of)
        month = balance_date.month + 1
        year = balance_date.year + (1 if month == 13 else 0)
        month = 1 if month == 13 else month
        first_model_payment_date = date(year, month, balance_date.day).isoformat()
    return [
        {
            "liability_id": "husband_share_home_mortgage",
            "status": "confirmed_schedule_with_variable_rate_sensitivity_required",
            "treatment": "future_repayment_cash_flows",
            "bank_document_values_are_authoritative": True,
            "generic_amortization_recalculation_prohibited": True,
            "arithmetic_mismatch_warning_or_block_prohibited": True,
            "current_asset_offset_prohibited": True,
            "outstanding_principal_jpy": user_balance,
            "balance_as_of": balance_as_of,
            "base_case_annual_interest_rate": household_mortgage.get(
                "annual_interest_rate"
            ),
            "rate_type": household_mortgage.get("fixed_or_variable"),
            "base_case_monthly_payment_jpy": monthly_payment,
            "first_model_payment_date": first_model_payment_date,
            "last_scheduled_payment_date": maturity_date,
            "retirement_period": {
                "starts_on": planning_timeline.get("planned_retirement_date"),
                "ends_on": maturity_date,
                "monthly_payment_jpy": monthly_payment,
                "spending_inclusion_status": "not_confirmed_separate_cash_flow_required",
            },
            "active_period_double_count_prevention": (
                "確認済み月次収入は住宅ローン控除後。"
                "この控除後収入を現役期フローへ使う月は返済額を再控除しない。"
                "控除前収入を使う場合だけ住宅ローンを別途控除する"
            ),
            "retirement_period_rule": (
                "退職後支出へ住宅ローンが含まれる確認はないため、"
                "planned_retirement_dateからlast_scheduled_payment_dateまで別建てで控除する"
            ),
            "variable_rate_base_case_rule": (
                "current schedule payment and current annual rateを基準にし、"
                "新しい返済予定表を確認済み事実として捏造しない"
            ),
            "rate_sensitivity": {
                "required": True,
                "parallel_rate_shocks_percentage_points": [1, 2],
                "method": (
                    "各shockで残高、残存月数、shock後月利から満期一定の元利均等返済額を"
                    "再計算し、退職後支払総額と成功確率への影響を示す"
                ),
            },
        }
    ]


def build_contribution_reconciliation(context: dict, *, recurring: dict) -> dict:
    regular = context.get("cash_flow", {}).get("regular_month", {})
    income = _structured_value(
        regular.get("income_after_tax_social_insurance_mortgage_ideco_jpy")
    )
    essential = _structured_value(regular.get("essential_expenses_jpy"))
    core_monthly = recurring.get("core_monthly_total_jpy") or 0
    pension_monthly = recurring.get("pension_monthly_total_jpy") or 0
    crypto_weekly = recurring.get("crypto_weekly_total_jpy") or 0
    crypto_annual = crypto_weekly * 52
    crypto_monthly_equivalent = round(crypto_annual / 12, 2)
    rows = [
        {
            "contribution_type": "nisa_broad_equity_core",
            "periodic_amount_jpy": core_monthly,
            "period": "monthly",
            "annualized_amount_jpy": core_monthly * 12,
            "funding_source": "salary_credit_card_recurring",
            "already_deducted_from_reported_current_income": False,
            "include_in_financial_planning_model": True,
            "capital_source_classification": "new_savings",
            "continuation_period": {
                "value": None,
                "status": "reviewer_to_derive",
                "latest_observed_setting_as_of": recurring.get("as_of"),
            },
            "uncertainty_status": "observed_setting_with_continuation_to_be_derived",
            "source_ref": recurring.get("source"),
        },
        {
            "contribution_type": "ideco_broad_equity_core",
            "periodic_amount_jpy": pension_monthly,
            "period": "monthly",
            "annualized_amount_jpy": pension_monthly * 12,
            "funding_source": "salary_before_reported_after_ideco_income",
            "already_deducted_from_reported_current_income": True,
            "include_in_financial_planning_model": True,
            "capital_source_classification": "new_savings",
            "continuation_period": {
                "value": None,
                "status": "reviewer_to_derive",
                "latest_observed_setting_as_of": recurring.get("as_of"),
            },
            "uncertainty_status": "observed_setting_with_continuation_to_be_derived",
            "source_ref": recurring.get("source"),
        },
        {
            "contribution_type": "crypto_btc_eth",
            "periodic_amount_jpy": crypto_weekly,
            "period": "weekly",
            "annualized_amount_jpy": crypto_annual,
            "monthly_equivalent_jpy": crypto_monthly_equivalent,
            "funding_source": None,
            "already_deducted_from_reported_current_income": False,
            "include_in_financial_planning_model": None,
            "capital_source_classification": "unknown_new_savings_or_other_cash",
            "continuation_period": {
                "value": None,
                "status": "reviewer_to_derive",
                "latest_observed_setting_as_of": recurring.get("as_of"),
            },
            "uncertainty_status": "funding_source_unknown_reviewer_selects_conservative_base_case",
            "source_ref": recurring.get("source"),
        },
    ]
    return {
        "status": "reviewer_to_reconcile_before_long_term_contribution_policy",
        "rows": rows,
        "reported_current_income_jpy": income,
        "reported_income_definition": "after_tax_social_insurance_mortgage_ideco",
        "monthly_essential_expenses_jpy": essential,
        "ordinary_month_balance_user_description": regular.get("balance", {}).get(
            "value"
        ),
        "mechanical_cross_check_jpy": (
            income - core_monthly - essential - crypto_monthly_equivalent
            if None not in (income, essential)
            else None
        ),
        "cross_check_interpretation": (
            "機械差額は追加投資余力の確認済み値ではない。通常月収支がおおむねゼロという"
            "ユーザー説明を優先し、暗号資産の資金源を推測で確定しない"
        ),
        "base_case_selection_contract": (
            "crypto funding source and continuationについて、確認済み収支を破らない"
            "一つの保守的ベースケースをreviewerが選び、感応度を示す。ユーザーへ再質問しない"
        ),
        "double_count_prevention": (
            "iDeCoはreported_current_incomeから既に控除済み。NISAとcryptoは未控除。"
            "temporary cash redeploymentはnew savingsへ含めない"
        ),
    }


def build_bonus_information(context: dict) -> dict:
    current = context.get("cash_flow", {}).get("bonus", {})
    expected = context.get("strategic_profile", {}).get(
        "expected_future_cash_flows", {}
    )
    if isinstance(expected, dict):
        items = expected.get("items", {})
        future = items.get("bonus", {}) if isinstance(items, dict) else {}
    elif isinstance(expected, list):
        future = next(
            (
                item
                for item in expected
                if isinstance(item, dict) and item.get("type") == "bonus"
            ),
            {},
        )
    else:
        future = {}
    return {
        "current_confirmed_rough_reference": {
            "take_home_reference_jpy": current.get("take_home_reference_jpy"),
            "amount_qualifier": current.get("amount_qualifier"),
            "certainty": current.get("certainty"),
            "annual_frequency": current.get("annual_frequency"),
            "payment_months": current.get("payment_months", []),
        },
        "future_continuation_model_assumption": {
            "value_jpy": future.get("future_amount_jpy"),
            "status": future.get("status", "unknown"),
            "decision_owner": "independent_on_demand_reviewer",
            "base_case_required": True,
            "rule": (
                "粗い現在参考額を将来継続額の確認済み事実に変換せず、"
                "一つの保守的モデル仮定と感応度を示す"
            ),
        },
    }


def find_missing_strategic_inputs(
    inputs: dict,
    *,
    strategic_decision_objective: dict,
) -> list[str]:
    required_paths = [
        "user_age",
        "tax_residency",
        "planning_timeline",
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
        "liability_cash_flows",
        "contribution_reconciliation",
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
        and derivation.get("decision_owner")
        in {"independent_monthly_reviewer", "independent_on_demand_reviewer"}
        and bool(derivation.get("method"))
        and bool(derivation.get("evidence_requirements"))
        and derivation.get("base_case_required") is True
    )


def build_strategic_decision_objective(
    context: dict | None,
    *,
    portfolio_snapshot_as_of: date | None = None,
) -> dict:
    profile = (context or {}).get("strategic_profile", {})
    configured = profile.get("objective_configuration", {})
    primary_objective = configured.get("primary_objective")
    if primary_objective not in PRIMARY_OBJECTIVES:
        primary_objective = None
    models = configured.get("objective_models", {})
    terminal = models.get("maximize_terminal_wealth", {})
    minimum_risk = models.get("minimize_risk_for_required_return", {})
    risk_adjusted = models.get("maximize_ex_ante_sharpe_ratio", {})
    terminal_target_date = terminal.get("target_date")
    terminal_horizon_years = terminal.get("horizon_years")
    if terminal_target_date and portfolio_snapshot_as_of is not None:
        target_date = date.fromisoformat(str(terminal_target_date))
        terminal_horizon_years = round(
            max((target_date - portfolio_snapshot_as_of).days, 0) / 365.2425,
            4,
        )
    objective_models = {
        "maximize_terminal_wealth": {
            "label": "65歳時点の投資利益最大化",
            "target_age": terminal.get("target_age"),
            "target_date": terminal_target_date,
            "optimization_target": terminal.get("optimization_target"),
            "profit_definition": terminal.get("profit_definition"),
            "lifestyle_constraints": terminal.get("lifestyle_constraints", []),
            "horizon_years": terminal_horizon_years,
            "planned_contributions": terminal.get("planned_contributions"),
            "return_basis": terminal.get("return_basis"),
            "statistic": terminal.get("statistic"),
            "downside_quantile_pct": terminal.get("downside_quantile_pct"),
            "leverage_allowed": terminal.get("leverage_allowed"),
            "required_parameters": [
                "target_age",
                "target_date",
                "optimization_target",
                "profit_definition",
                "lifestyle_constraints",
                "horizon_years",
                "planned_contributions",
                "return_basis",
                "statistic",
                "leverage_allowed",
            ],
            "primary_objective_fit_rule": (
                "今の生活を楽しめる持続可能な拠出額を全候補で共通に固定し、"
                "指定された利益定義・期間・名目/実質・レバレッジ条件で65歳時点の"
                "投資利益が最大の実行可能候補を最良とする"
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


def build_asset_class_definitions(*, has_crypto_holdings: bool = False) -> dict:
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
        "allocation_composition_rules": {
            "candidate_comparison_denominator": "long_term_investable_portfolio_jpy",
            "candidate_top_level_weights": [
                "total_equity_pct",
                "bond_pct",
                "other_pct",
            ],
            "top_level_sum_rule": "total_equity_pct + bond_pct + other_pct = 100",
            "equity_internal_split_rule": (
                "総株式比率を決定した後、その内数としてcore_equity_pctと"
                "satellite_equity_pctへ分解する。satelliteは総株式の外数にしない"
            ),
            "active_risk_cap_denominator": "long_term_investable_portfolio_jpy",
            "approved_semiconductor_exception_denominator": (
                "household_total_assets_jpy"
            ),
            "crypto_rule": (
                "継続する暗号資産はother_pctの内数。"
                + (
                    "スナップショットに暗号資産残高の独立明細があるため、"
                    "その current_value_jpy は使用してよいが、数量や取得単価は捏造しない"
                    if has_crypto_holdings
                    else "スナップショットに暗号資産残高の独立明細がないため現在残高や現在配分を捏造しない"
                )
            ),
            "calculation_order": [
                "exclude_household_reserve",
                "set_and_exclude_tactical_liquidity_before_candidate_comparison",
                "exclude_noninvestable_other",
                "compare_total_equity_bond_investable_other_weights",
                "split_total_equity_into_core_and_satellite",
                "apply_active_risk_caps",
                "translate_policy_to_products_and_lots",
            ],
        },
    }


def build_decision_stage_contract() -> dict:
    return {
        "required_order": [
            "strategic_policy_stage",
            "implementation_stage",
        ],
        "strategic_policy_stage": {
            "output_path": "strategic_policy_decision",
            "required_decisions": [
                "required_real_return",
                "required_success_probability",
                "long_term_investable_assets",
                "equity_bond_other_policy_allocation",
                "satellite_target_pct_and_securities",
                "satellite_limits",
                "permanent_tactical_liquidity_policy",
                "recurring_contribution_policy",
            ],
            "market_and_holdings_reverse_inference_prohibited": True,
        },
        "implementation_stage": {
            "output_path": "implementation_decision",
            "must_reference_completed_strategy": True,
            "required_decisions": [
                "product_hold_reduce_exit_buy_proposals",
                "all_existing_holding_actions_and_new_asset_purchase_conclusion",
                "current_month_tactical_liquidity_deployment",
                "before_after_allocation",
                "account_tax_lot_readiness",
            ],
            "account_lot_output_path": "account_lot_execution",
            "order_rule": "the review request exists only after every holding account category is confirmed; emit executable account-lot orders only when remaining tax, cost-basis, and lot facts are also confirmed",
        },
        "status_paths": [
            "strategic_policy_decision.status",
            "implementation_decision.status",
            "account_lot_execution.status",
        ],
        "blocking_isolation_rule": (
            "口座区分不足は生成前ゲートでレビュー全体を停止する。口座区分確認後に税額、"
            "取得価額またはロット詳細だけが不足する場合はaccount_lot_executionを"
            "blockedまたはnot_calculableにし、独立して完成できる戦略方針を巻き込まない"
        ),
    }


def build_execution_capability_contract() -> dict:
    return {
        "gate_output_path": "execution_capability_gate",
        "required_before_calculation": True,
        "required_capabilities": [
            "monthly_cash_flow_calculation",
            "bisection_required_return_calculation",
            "multivariate_monthly_monte_carlo",
            "fixed_random_seed",
            "complete_11_candidate_comparison",
            "interest_rate_sensitivity_calculation",
            "candidate_allocation_order_arithmetic_reconciliation",
            "yaml_or_json_schema_validation",
        ],
        "capability_status_enum": ["available", "partial", "unavailable"],
        "unavailable_result_contract": {
            "calculation_status": "not_calculable",
            "required_fields": [
                "reason",
                "missing_capability",
                "remediation",
            ],
        },
        "partial_completion_rule": (
            "利用不能な能力に依存する計算だけをnot_calculableにし、利用可能な計算、"
            "市場調査および定性的判断は続行する"
        ),
        "fabrication_prohibited": True,
    }


def build_allocation_denominators(
    computation: MonthlyComputation,
    *,
    cash_requirement_inputs: dict,
) -> dict:
    total = computation.snapshot.total_assets_jpy
    crypto_balance_jpy = sum(
        (
            holding.market_value_jpy
            for holding in computation.snapshot.holdings
            if is_crypto_holding(holding)
        ),
        start=Decimal("0"),
    )
    has_crypto_holdings = crypto_balance_jpy > 0
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
            "current_balance_status": (
                "present_in_portfolio_snapshot"
                if has_crypto_holdings
                else "not_present_in_portfolio_snapshot"
            ),
            "current_balance_jpy": (
                crypto_balance_jpy if has_crypto_holdings else None
            ),
            "snapshot_scope": (
                "use_observed_current_balance_without_inventing_quantity_or_cost_basis"
                if has_crypto_holdings
                else "do_not_invent_current_allocation"
            ),
            "policy_scope": (
                "if_continued_classify_as_investable_other_within_other_pct"
            ),
            "recurring_contribution_is_not_current_balance": True,
        },
        "calculation_order_rule": (
            "household reserveとtactical liquidityを候補比較前に総資産から除外し、"
            "残るlong-term investable portfolioだけを政策配分の分母にする"
        ),
        "calculation_status": (
            "complete" if investable is not None else "blocked_pending_tactical_liquidity_policy"
        ),
    }


def build_candidate_methodology(*, has_crypto_holdings: bool = False) -> dict:
    def delegated(
        selection_criteria: str,
        allowed_primary_sources: list[str],
        *,
        sensitivity_required: bool,
    ) -> dict:
        return {
            "value": None,
            "status": "reviewer_to_derive",
            "decision_owner": "independent_on_demand_reviewer",
            "selection_criteria": selection_criteria,
            "allowed_primary_sources": allowed_primary_sources,
            "base_case_required": True,
            "sensitivity_required": sensitivity_required,
            "same_value_for_all_candidates": True,
        }

    return {
        "staged_selection_sequence": [
            "compare_and_select_tactical_liquidity",
            "compare_crypto_contribution_options_and_select_other_pct",
            "compare_all_11_equity_bond_sleeve_candidates",
            "compare_all_country_only_baseline_and_positive_satellite_parameter_candidates",
            "run_sensitivity_around_selected_results",
            "lock_strategic_policy_before_implementation_stage",
        ],
        "tactical_liquidity_candidates_pct": [0, 2.5, 5, 7.5, 10],
        "tactical_liquidity_denominator": "household_total_assets_jpy",
        "tactical_liquidity_is_separate_from_household_reserve": True,
        "tactical_liquidity_required_comparison_fields": [
            "long_term_investable_asset_reduction_jpy",
            "required_real_return_impact_pct_points",
            "success_probability_impact_pct_points",
            "deployable_amount_jpy",
            "expected_return_drag_pct_points",
            "implementation_complexity",
            "replenishment_feasibility",
        ],
        "tactical_liquidity_selection_priority": [
            "maintain_lifetime_plan_success_probability_at_or_above_required_level",
            "do_not_unnecessarily_increase_required_return",
            "require_decline_deployment_benefit_to_reasonably_exceed_permanent_cash_carry_cost",
            "if_differences_are_small_select_the_lower_tactical_liquidity_pct",
        ],
        "tactical_policy_configuration_after_selection": [
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
        ],
        "anti_hindsight_rule": (
            "tactical liquidity比率と発動ルールを当月市場データの評価前に固定し、"
            "当月値動きを見て候補、閾値、参照高値またはlookbackを変更しない"
        ),
        "other_pct_candidates": [0, 1, 2, 3, 5],
        "crypto_contribution_options": [
            "stop_new_contributions_and_exclude_unknown_existing_balance",
            "continue_only_within_realized_surplus_such_as_bonus",
            "continue_current_contributions_and_disclose_cash_flow_and_success_probability_impact",
        ],
        "crypto_current_balance_rule": (
            "スナップショットに暗号資産残高があるため observed current_value_jpy は使ってよいが、"
            "数量・取得単価・通貨建て配分は未確認なら捏造しない"
            if has_crypto_holdings
            else "スナップショットに暗号資産残高がないため現在残高を推測せず、"
            "未知の既存残高を現在配分へ含めない"
        ),
        "other_pct_selection_priority": [
            "do_not_worsen_confirmed_ordinary_month_cash_flow",
            "maintain_required_success_probability",
            "require_estimated_diversification_benefit_to_exceed_incremental_risk",
            "do_not_treat_unfunded_recurring_crypto_as_confirmed_new_savings",
            "if_differences_are_small_select_the_lower_other_pct",
        ],
        "satellite_parameter_contract": {
            "all_country_only_baseline_required": True,
            "positive_satellite_allocation_required": True,
            "reviewer_must_propose": [
                "satellite_target_pct_of_investable_portfolio",
                "selected_satellite_securities",
                "total_satellite_cap_pct",
                "single_theme_cap_pct",
                "single_security_cap_pct",
            ],
            "candidate_value_rule": (
                "Codexの既存比率や保有銘柄を候補値の根拠にせず、65歳時点の利益、"
                "分散、費用、税、売買回転、趣味としての正の配分制約から独立に候補を作る"
            ),
            "selection_output_path": "strategic_policy_decision.active_risk_policy",
        },
        "candidate_grid": {
            "equity_share_of_equity_bond_sleeve_pct": list(range(0, 101, 10)),
            "other_pct_rule": (
                "other_pct_candidatesとcrypto_contribution_optionsを選択規則で比較して一つの"
                "共通比率を先に決め、"
                "全候補へ同じother_pctを使う。残るequity-bond sleeveを0～100%の"
                "10ポイント刻みで完全比較する"
            ),
            "candidate_weight_formula": (
                "total_equity_pct=(100-other_pct)*sleeve_equity_pct/100; "
                "bond_pct=(100-other_pct)*(100-sleeve_equity_pct)/100"
            ),
            "boundary_rule": (
                "0%株式と100%株式を含む全11点を評価するため境界拡張は不要。"
                "評価した候補集合外を含む最小リスクとは表現しない"
            ),
        },
        "assumption_delegations": {
            "global_equity_index": delegated(
                "日本居住者が低コストで実装できる広範な世界株式の代表性",
                ["index_provider", "fund_manager"],
                sensitivity_required=False,
            ),
            "bond_index": delegated(
                "通貨、デュレーション、信用力、実装商品の整合性",
                ["index_provider", "fund_manager", "government_or_central_bank"],
                sensitivity_required=True,
            ),
            "bond_instrument_type": delegated(
                "流動性、信用リスク、デュレーション、費用、税務",
                ["fund_manager", "regulator"],
                sensitivity_required=True,
            ),
            "bond_currency": delegated(
                "日本円負債・支出との通貨整合性",
                ["index_provider", "fund_manager", "government_or_central_bank"],
                sensitivity_required=True,
            ),
            "bond_fx_hedge_policy": delegated(
                "JPYベースのボラティリティ、ヘッジコスト、負債通貨との整合性",
                ["index_provider", "fund_manager", "academic_primary_research"],
                sensitivity_required=True,
            ),
            "estimation_period": delegated(
                "十分な市場局面を含み、各資産で共通に取得可能な期間",
                ["index_provider", "academic_primary_research"],
                sensitivity_required=True,
            ),
            "assumptions_as_of": delegated(
                "research_cutoff_at以前で最も新しい利用可能な前提日",
                ["government_or_central_bank", "index_provider", "fund_manager"],
                sensitivity_required=False,
            ),
            "inflation_assumption_pct": delegated(
                "日本の長期物価目標、実績、市場予想を区別したcurrent-JPY基準",
                ["Bank_of_Japan", "Statistics_Bureau_of_Japan"],
                sensitivity_required=True,
            ),
            "tax_cost_treatment": delegated(
                "NISA、iDeCo、課税口座を区別し、手数料控除後の同一基準にそろえる",
                ["National_Tax_Agency_Japan", "regulator", "fund_manager"],
                sensitivity_required=True,
            ),
            "major_drawdown_definition": delegated(
                "全候補に共通のJPY total-return peak-to-trough定義",
                ["index_provider", "academic_primary_research"],
                sensitivity_required=False,
            ),
            "rebalancing_frequency": delegated(
                "費用、税、ドリフト管理を踏まえた一つの共通頻度",
                ["academic_primary_research", "regulator"],
                sensitivity_required=True,
            ),
        },
        "common_assumptions_rule": (
            "全委譲項目を市場データ評価より先に一つのベースケースへ固定し、"
            "同じ前提を全候補へ適用する"
        ),
        "required_return_calculation_contract": {
            "currency_and_price_basis": "snapshot-date current JPY",
            "return_basis": "real_after_product_cost_before_personal_tax",
            "period": "monthly",
            "cash_flow_timing": (
                "B_t = B_(t-1)*(1+r_annual)^(1/12) + C_t + P_t - S_t - L_t - T_t; "
                "all end-of-month, with exact boundary dates prorated only for partial months"
            ),
            "initial_balance_rule": (
                "long_term_investable_portfolio_jpy after household reserve, tactical liquidity, "
                "and noninvestable exclusions; mortgage principal is not deducted"
            ),
            "cash_flow_columns": [
                "date",
                "opening_balance_current_jpy",
                "net_contribution_after_tax_current_jpy",
                "public_pension_after_tax_current_jpy",
                "retirement_spending_current_jpy",
                "liability_payment_current_jpy",
                "personal_tax_and_transaction_cost_current_jpy",
                "closing_balance_current_jpy",
            ],
            "cost_double_count_prevention": (
                "fund expense ratios and recurring product costs are embedded once in r; personal taxes "
                "and transaction-specific costs are included once in T_t"
            ),
            "account_rules": (
                "NISA tax-free treatment, iDeCo contribution/withdrawal tax treatment, and taxable "
                "account realization taxes are modeled separately then aggregated on the same after-tax basis"
            ),
            "liability_rule": (
                "use liability_cash_flows; do not both subtract mortgage principal from current assets "
                "and include future repayments"
            ),
            "root_finding": (
                "solve closing_balance(planning_end_date)-terminal_asset_floor_current_jpy=0 "
                "by bisection on annual real return [-99%, 100%], tolerance 0.0001 percentage points; "
                "if no sign change return status=not_calculable with reason and remediation"
            ),
        },
        "success_probability_calculation_contract": {
            "method": "parametric_multivariate_monthly_log_return_monte_carlo",
            "period": "monthly",
            "trials": 50000,
            "random_seed_rule": "integer YYYYMMDD from decision_date in Asia/Tokyo",
            "required_parameters": [
                "equity_expected_return",
                "bond_expected_return",
                "other_expected_return",
                "volatilities",
                "correlation_matrix",
                "inflation_base_case",
            ],
            "cash_flow_and_account_rule": (
                "use the same contribution, withdrawal, pension, mortgage, tax, cost, and timing "
                "assumptions as the required-return calculation"
            ),
            "rebalancing_rule": (
                "use the one common reviewer-derived frequency and apply taxes/costs consistently"
            ),
            "sequence_risk_rule": (
                "draw a new correlated monthly return vector each period and apply returns before "
                "the common end-of-month cash flows"
            ),
            "log_return_parameterization": (
                "for annual arithmetic mean mu and annual covariance Sigma, use monthly log covariance "
                "Sigma/12 and monthly log mean (ln(1+mu)-0.5*diag(Sigma))/12"
            ),
            "success_definition": (
                "balance never falls below zero before planning_end_date and closing balance is at "
                "least terminal_asset_floor_current_jpy"
            ),
            "candidate_feasibility_rule": (
                "estimated_success_probability_pct >= required_success_probability_pct and all "
                "hard allocation, concentration, leverage, and implementation constraints pass"
            ),
            "sensitivity_required": True,
        },
        "primary_objective_fit_definition": {
            "minimize_risk_for_required_return": (
                "among candidate_feasible=true candidates, minimize expected_volatility_pct; "
                "tie-break by estimated_major_drawdown_pct closest to zero, then lower cost"
            ),
            "maximize_terminal_wealth": (
                "maximize configured after-tax real investment profit at age 65 under the same lifestyle-sustainable contribution and feasibility constraints"
            ),
            "maximize_ex_ante_sharpe_ratio": (
                "maximize common-basis ex-ante Sharpe ratio under the same feasibility constraints"
            ),
        },
        "required_candidate_fields": [
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
        "policy_design_sequence": [
            "derive_policy_from_long_term_general_evidence_before_current_market_observation",
            "set_deployment_asset_and_same_broad_trigger_index",
            "lock_reference_high_lookback_price_basis_and_fx_treatment",
            "exclude_tactical_liquidity_from_policy_denominator",
            "then_apply_locked_rule_to_market_data_at_research_cutoff",
        ],
        "anti_hindsight_rule": (
            "当月の市場状態を見た後でthreshold、lookback、price basis、FX treatmentを変更しない"
        ),
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
        "current_approved_constraint": {
            "policy_id": "approved_direct_semiconductor_max_pct",
            "status": "hard_constraint",
            "limit_pct": current_limit,
            "denominator": "household_total_assets_jpy",
            "approved": True,
            "execution_rule": (
                "新しい上限がユーザー承認されるまで全売買案へ適用する"
            ),
        },
        "proposed_future_policy": {
            "policy_id": None,
            "status": (
                "reviewer_to_propose"
                if review_mode == "strategic_policy_second_opinion"
                else "not_applicable"
            ),
            "limit_pct": None,
            "denominator": "household_total_assets_jpy",
            "approved": False,
        },
        "priority": (
            "家計用現金と法的・口座制約を満たした後、サテライト総枠・単一テーマ枠の"
            "うち最も厳しい上限を優先する"
        ),
        "approval_gate": [
            "未承認の緩和案を現行上限超過の理由に使わない",
            "未承認の新上限をユーザー承認済みと表現しない",
            "各売買案へ参照したpolicy_idを記録する",
        ],
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


def build_active_risk_policy(
    context: dict | None,
    *,
    computation: MonthlyComputation | None = None,
) -> dict:
    configured = (context or {}).get("active_risk_policy", {})
    satellite_review = (
        (computation.metadata.get("satellite_review_policy", {}))
        if computation is not None
        else {}
    )
    return {
        "satellites_allowed": satellite_review.get(
            "satellites_allowed",
            configured.get("satellites_allowed"),
        ),
        "satellite_target_pct": satellite_review.get("target_pct"),
        "satellite_securities": satellite_review.get("securities"),
        "review_dimensions": satellite_review.get("review_dimensions", []),
        "all_country_only_baseline_required": satellite_review.get(
            "all_country_only_baseline_required",
            True,
        ),
        "positive_satellite_allocation_required": satellite_review.get(
            "positive_satellite_allocation_required",
            False,
        ),
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
    if review_mode != "on_demand_operational_review":
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
    ]


def build_static_reference_checks() -> list[str]:
    return [
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
    ]


def build_semantic_validation_checks() -> list[str]:
    return [
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
            "rule": (
                "一つのreview_mode内でstrategic_policy_stageを先に完了し、その結果だけを"
                "implementation_stageへ渡す。戦略根拠と実装根拠を別フィールドに記録し、"
                "市場状況や現保有から戦略配分を逆算しない"
            ),
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
            "rule_id": "R-PLANNING-002",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "planning_timelineの日付を期間計算の正本とし、月次キャッシュフローで"
                "必要実質収益率と成功確率を再現する。整数年は表示用に限る"
            ),
        },
        {
            "rule_id": "R-LIABILITY-001",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "住宅ローンはliability_cash_flowsで退職後も満期まで計上する。"
                "現在資産から元本控除する方式と将来返済方式を混在させず、現役期の控除後収入と二重計上しない"
            ),
        },
        {
            "rule_id": "R-LIABILITY-002",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "銀行書類由来の住宅ローン元本、金利、返済額、返済日、満期を正本として"
                "そのまま使う。一般的な元利均等返済式で入力間の算術的一致を再検証せず、"
                "推定不一致を理由に修正、警告またはblocked判定を行わない"
            ),
        },
        {
            "rule_id": "R-CONTRIBUTION-001",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "contribution_reconciliationを先に完成させ、iDeCo、NISA、crypto、"
                "temporary cash redeploymentとnew savingsを二重計上しない"
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
            "rule_id": "R-MARKET-002",
            "applies_to": "final_review",
            "rule": (
                "長期的根拠から投資待機資金政策を先に固定し、その後で当月市場へ適用する。"
                "当月値動きを理由にthresholdやlookbackを変更しない"
            ),
        },
        {
            "rule_id": "R-CANDIDATE-001",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "investable other比率を共通固定後、equity-bond sleeveの株式0～100%を"
                "10ポイント刻みで全件比較し、境界候補を選んだまま探索を省略しない"
            ),
        },
        {
            "rule_id": "R-CANDIDATE-002",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "tactical liquidityはhousehold_total_assets_jpyを分母とする0、2.5、5、7.5、10%を"
                "所定の成功確率、必要収益率、投入効果、現金保有コスト、複雑性、補充可能性で比較し、"
                "選択規則に従って一つを選んでから発動ルールを固定する"
            ),
        },
        {
            "rule_id": "R-CANDIDATE-003",
            "applies_to": "strategic_policy_second_opinion",
            "rule": (
                "other_pctは0、1、2、3、5%と暗号資産積立の3選択肢を比較し、"
                "通常月収支、必要成功確率、分散効果、資金源、低比率優先の順で一つを選んだ後に"
                "equity-bond sleeve 11候補を比較する。現在の暗号資産残高は推測しない"
            ),
        },
        {
            "rule_id": "R-SEMICON-001",
            "applies_to": "final_review",
            "rule": (
                "current_approved_constraintとproposed_future_policyを分離し、"
                "新上限が承認されるまでは現行policy_idを執行制約として各売買案へ記録する"
            ),
        },
        {
            "rule_id": "R-RESEARCH-001",
            "applies_to": "final_review",
            "rule": (
                "accessed_atはresearch_cutoff_at後でもよい。判断に使う情報はpublication_date、"
                "filing/release date、data_as_ofをaccessed_atと分離し、公表日時がcutoff以前である"
                "ことを確認する。公表日時不明の動的ページとcutoff後公表情報は判断に使わず、"
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
            "rule_id": "R-TRADE-002",
            "applies_to": "final_review",
            "rule": (
                "戦略目標、商品単位方針、口座・ロット注文を別レイヤーで判定する。"
                "口座区分は生成前に全件確認し、税額・取得価額・ロット詳細の不足だけを"
                "該当ロット執行のblocked理由として扱う"
            ),
        },
        {
            "rule_id": "R-TAX-001",
            "applies_to": "final_review",
            "rule": (
                "保有銘柄の売却を一件でも提案する場合は、日本の最新税制の一次情報に基づき、"
                "課税口座の含み益ロットと含み損ロットを同一暦年に実現して譲渡益を相殺する"
                "損益通算（tax-loss harvesting）を必ず比較する。当年の確定損益、利用可能な"
                "繰越損失、配当等との通算可否、口座区分、NISA内損失は損益通算・繰越控除できない"
                "点、概算税効果、手数料、再取得までの価格変動リスク、申告実務を確認し、"
                "税効果だけで投資判断を歪めない。採用しない場合も理由をaccount_tax_comparisonsへ記録する"
            ),
        },
        {
            "rule_id": "R-WINDOW-001",
            "applies_to": "final_review",
            "rule": (
                "recommendation_windowはpacket_generated_atを始点とし、データ鮮度、イベント日程、"
                "予測可能性、実行可能性からreviewerがdays、weeks、monthsの尺度と長さを選ぶ。"
                "全推奨行動のtimingをその範囲内へ具体化する"
            ),
        },
        {
            "rule_id": "R-REVIEW-001",
            "applies_to": "final_review",
            "rule": (
                "next_review_recommendationはrecommendation_window終了以前に設定せず、"
                "早期再レビュー条件と最新スナップショットによる次回依頼文を回答末尾に置く"
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
                "quality checkはpass、fail、not_verifiable、not_applicableから検証結果どおりに選ぶ。"
                "passにも具体的なYAML path、式、件数または値のevidenceを記録し、確認不能事項を"
                "passにしない。JSON Schema検証とsemantic_validation_checksを分離する"
            ),
        },
        {
            "rule_id": "R-CAPABILITY-001",
            "applies_to": "final_review",
            "rule": (
                "execution_capability_gateを計算前に完了する。利用不能な能力に依存する数値は"
                "not_calculableとしてreason、missing_capability、remediationを記録し、"
                "計算可能な項目と定性的判断は続行する"
            ),
        },
        {
            "rule_id": "R-ROUNDING-001",
            "applies_to": "final_review",
            "rule": (
                "金額±10円、比率±0.02ポイント、モンテカルロ確率±0.01ポイント、"
                "収益率・ボラティリティ±0.01ポイントを照合許容差とし、範囲内の差は"
                "rounding residualとして記録してfailまたはblockedにしない"
            ),
        },
    ]
    if review_mode == "on_demand_operational_review":
        rules.append(
            {
                "rule_id": "R-ONDEMAND-001",
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
            "data_as_of",
            "accessed_at",
            "cutoff_compliance_status",
            "source_type",
            "claim_supported",
        ],
        "cutoff_compliance_rules": [
            "accessed_at may be later than research_cutoff_at and is not cutoff evidence",
            "publication_date means publication, filing, or release date/time and must be at or before research_cutoff_at",
            "data_as_of, when present, must be at or before research_cutoff_at but cannot cure a later publication_date",
            "a dynamic page without a verifiable publication, filing, or release date is not_verifiable and must not support a decision",
            "information published after research_cutoff_at is non_compliant even when it covers an earlier period",
        ],
        "portfolio_valuation_rule": (
            "外部情報は判断根拠にだけ使い、portfolio_snapshot_as_ofの価格・為替・"
            "評価額・比率を更新しない"
        ),
    }


def build_validation_contract(interaction_phase: str) -> dict:
    return {
        "quality_check_schema": {
            "required_fields": [
                "check_id",
                "status",
                "evidence",
                "reason",
                "remediation",
            ],
            "status_enum": [
                "pass",
                "fail",
                "not_verifiable",
                "not_applicable",
            ],
            "pass_evidence_rule": (
                "passにも検証した具体的なYAML path、式、件数または値を記録する"
            ),
            "unknown_rule": "確認できない事項をpassにしない",
        },
        "required_check_ids": build_decision_quality_checks(),
        "phase_rule": (
            "objective_confirmationではquality checksを出力しない。final_reviewでは"
            "各checkを実測結果に従って判定し、自己申告でpassへ揃えない"
        ),
        "static_reference_checks": build_static_reference_checks(),
        "static_reference_check_rule": (
            "final_reviewのroot static_reference_checksへ全IDを一度ずつ出力する。"
            "各checkはpass、fail、not_verifiable、not_applicableを使い分け、"
            "evidence、reason、remediationを記録する"
        ),
        "standard_json_schema_scope": [
            "required_fields",
            "data_types",
            "enums",
            "array_shapes",
            "explicit_nullability",
            "numeric_ranges",
        ],
        "semantic_validation_check_ids": build_semantic_validation_checks(),
        "semantic_validation_rule": (
            "ID一意性、候補集合、選択数、feasibility、クロスフィールド算術、全対象coverage、"
            "資金源照合、売却明細照合、二段階順序はJSON Schemaだけで検証済みとみなさず"
            "semantic_validation_checksへ具体値と許容差を記録する"
        ),
        "numeric_tolerances": {
            "amount_jpy": 10,
            "percentage_points": 0.02,
            "monte_carlo_probability_pct_points": 0.01,
            "return_and_volatility_pct_points": 0.01,
        },
        "rounding_rule": (
            "許容差以内の差はrounding_residualとして記録しfailまたはblockedにしない。"
            "超過時だけfailまたはnot_verifiableにする"
        ),
        "review_completion_status_enum": [
            "complete",
            "complete_with_execution_blocks",
            "blocked",
            "invalid",
        ],
        "completion_rule": (
            "口座区分は全件確認済みであることを前提とする。税額、取得価額またはロット詳細だけが"
            "blockedまたはnot_calculableならcomplete_with_execution_blocksを使用する。"
            "戦略判断に不可欠な計算が成立しない場合だけstrategic policyをblockedにする"
        ),
        "interaction_phase_at_generation": interaction_phase,
    }


def build_phase_output_contract(
    *,
    review_target_month: str,
    portfolio_snapshot_as_of: str,
    review_mode: str,
    interaction_phase: str,
) -> dict:
    inline_schema = load_inline_monthly_response_schema()
    return {
        "interaction_phase": interaction_phase,
        "objective_confirmation": {
            "response_type": "one_objective_question_only",
            "optional_content": "各選択肢の一行定義",
            "forbidden": [
                "web_research",
                "investment_decision",
                "seven_human_sections",
                "yaml",
                "trade_proposals",
                "decision_quality_checks",
            ],
            "transition": (
                "ユーザーの一回答をupdated_inputsへ反映し、同じ初期入力全体でfinal_reviewを再実行する"
            ),
        },
        "final_review": {
            "required_stage_order": [
                "strategic_policy_stage",
                "implementation_stage",
            ],
            "strategic_policy_stage_output": "strategic_policy_decision",
            "implementation_stage_output": "implementation_decision",
            "account_lot_execution_output": "account_lot_execution",
            "stage_transition_rule": (
                "implementation_stageはstrategic_policy_decision.status=completeで確定した政策を"
                "参照して開始し、保有商品または当月市場から戦略配分を逆算しない"
            ),
            "required_sections": [
                "【推奨方針】",
                "【採用した決定規則】",
                "【具体的な売買・資金移動】",
                "【実行後配分】",
                "【実行前確認事項】",
                "【Codex向け改善フィードバック】",
                "【次回レビュー時期】",
            ],
            "updated_inputs_location": "【推奨方針】の冒頭。独立見出しは禁止",
            "human_section_rules": (
                "一般論は判断根拠に必要な段落だけに限定する。測定不能な割合制限は使わない"
            ),
            "delivery": {
                "schema_authority": "output_contract.inline_response_schema_only",
                "external_schema_reference_allowed": False,
                "preferred": "attach_review_response_yaml",
                "fallback": "six_sections_then_delimiter_then_one_yaml_code_block",
                "yaml_file_transport": "コードフェンスなしの純粋なYAMLファイル",
                "chat_transport": "区切り線後の一つのyamlコードブロック",
            },
            "decision_date_rule": (
                "ユーザー入力ではなく、final_reviewを生成したAsia/Tokyoの暦日をYYYY-MM-DDで記録する"
            ),
            "recommendation_window_rule": (
                "packet_generated_atを始点とし、reviewerが根拠を示してdays、weeks、monthsの"
                "単位と長さを選ぶ。全推奨行動はend_atまでの具体的な時期へ落とす"
            ),
            "next_review_rule": (
                "次回レビュー日はrecommendation_window.end_at以前にせず、早期再レビュー条件と"
                "最新スナップショットを求める締めの一文を最終セクションに置く"
            ),
        },
        "response_identity": {
            "schema_version": 2,
            "artifact_type": "investment_review_response",
            "review_cadence": "on_demand",
            "review_mode": review_mode,
            "interaction_phase": "final_review",
            "review_target_month": review_target_month,
            "portfolio_snapshot_as_of": portfolio_snapshot_as_of,
        },
        "canonical_paths": {
            "strategic_policy_stage": "strategic_policy_decision",
            "implementation_stage": "implementation_decision",
            "account_lot_execution": "account_lot_execution",
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
        "inline_response_schema": inline_schema,
    }


def load_inline_monthly_response_schema() -> dict:
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "schemas"
        / "monthly-review-response.schema.yaml"
    )
    schema = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ValueError("investment review response schema must be an object")
    return schema


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
    target_ratio = dip.get("target_ratio", {})
    if target_ratio.get("value") == 0:
        add("戦術的な投資待機資金は設けない")
    else:
        add("投資待機資金は市場下落時に使う手段であり、残高維持自体を目的にしない")
    if target_ratio.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の目標比率は今回のオンデマンド独立レビューから提案を受ける")
    purchase_target = dip.get("purchase_target", {})
    if purchase_target.get("status") == "undecided":
        add("投資待機資金の買付対象は未定")
    activation = dip.get("activation_condition", {})
    if activation.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の発動条件は今回のオンデマンド独立レビューから提案を受ける")
    tranches = dip.get("tranche_count", {})
    if tranches.get("status") == "proposal_requested_from_current_monthly_independent_review":
        add("投資待機資金の投入回数は今回のオンデマンド独立レビューから提案を受ける")
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
    if ratio_value == 0:
        dip_status = "configured"
    elif ratio_value is not None:
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
            "decision_owner": (
                "user_confirmed_policy"
                if ratio_value == 0
                else "current_on_demand_independent_review_then_user_approval"
            ),
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
        ] + (
            ["承認済みの戦術的待機資金0円を、独立レビューなしに正の残高へ変更しない"]
            if ratio_value == 0
            else [
                "投資待機資金の確保・満額維持自体をレビュー目的にしない",
                "市場下落時に投資待機資金を使う選択肢を省略しない",
            ]
        ),
    }


def _structured_value(value):
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def normalize_review_cadence_terms(value):
    """Translate legacy reviewer-owner labels before exposing a new review packet."""

    replacements = {
        "independent_monthly_reviewer": "independent_on_demand_reviewer",
        "current_monthly_independent_review_then_user_approval": (
            "current_on_demand_independent_review_then_user_approval"
        ),
        "proposal_requested_from_current_monthly_independent_review": (
            "proposal_requested_from_current_on_demand_independent_review"
        ),
    }
    if isinstance(value, dict):
        return {
            key: normalize_review_cadence_terms(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_review_cadence_terms(item) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_review_cadence_terms(item) for item in value)
    if isinstance(value, str):
        return replacements.get(value, value)
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
            "オンデマンド包括レビューへ委譲中の比率をCodexで先回りして決定しない",
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


def build_computation_unknowns(
    computation: MonthlyComputation,
    *,
    review_mode: str | None = None,
) -> list[dict]:
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
    unknowns.append(
        {
            "item": "sale_tax_and_transaction_costs",
            "reason": "売却税、取得ロット、手数料の確定値はパケットにない",
            "source": "review_packet_boundary",
            "as_of": snapshot.snapshot_date.isoformat(),
        }
    )
    if review_mode != "on_demand_operational_review":
        unknowns.append(
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
            }
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
        "全売買可能明細がNISA・特定口座・一般口座のいずれかに分類済みで、account_type_gateがcompleteである",
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
