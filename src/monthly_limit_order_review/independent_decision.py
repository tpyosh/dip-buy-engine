from __future__ import annotations

import yaml

from .review_readiness import classify_review_account_type
from .storage import load_yaml


REQUIRED_REQUEST_FIELDS = {
    "schema_version",
    "request_type",
    "decision_id",
    "created_at",
    "decision_question",
    "decision_scope",
    "confirmed_facts",
    "user_constraints",
    "unknown_information",
    "excluded_context",
    "research_requirements",
    "required_outputs",
    "account_type_gate",
}

REQUIRED_RESPONSE_FIELDS = {
    "schema_version",
    "artifact_type",
    "decision_id",
    "completed_at",
    "decision_status",
    "recommendation",
    "action_plan",
    "evidence",
    "alternatives",
    "assumptions",
    "unresolved_information",
    "user_confirmation_required",
    "prompt_feedback",
}


def render_independent_decision_prompt(request: dict, template_text: str) -> str:
    validate_independent_decision_request(request)
    placeholder = "{{DECISION_REQUEST_YAML}}"
    if placeholder not in template_text:
        raise ValueError("Independent decision template is missing its YAML placeholder")
    request_yaml = yaml.safe_dump(
        request,
        allow_unicode=True,
        sort_keys=False,
    ).strip()
    prompt = template_text.replace(placeholder, request_yaml).rstrip() + "\n"
    if placeholder in prompt:
        raise ValueError("Independent decision prompt contains an unresolved placeholder")
    return prompt


def validate_independent_decision_request(request: dict) -> None:
    if not isinstance(request, dict):
        raise ValueError("Independent decision request must be a YAML object")
    missing = sorted(REQUIRED_REQUEST_FIELDS - set(request))
    if missing:
        raise ValueError(
            "Independent decision request missing fields: " + ", ".join(missing)
        )
    unexpected = sorted(set(request) - REQUIRED_REQUEST_FIELDS)
    if unexpected:
        raise ValueError(
            "Independent decision request has unexpected fields: "
            + ", ".join(unexpected)
        )
    if request.get("schema_version") != 1:
        raise ValueError("Independent decision request schema_version must be 1")
    if request.get("request_type") != "on_demand_independent_investment_decision":
        raise ValueError(
            "Independent decision request_type must be on_demand_independent_investment_decision"
        )
    for field in (
        "user_constraints",
        "unknown_information",
        "excluded_context",
        "research_requirements",
        "required_outputs",
    ):
        if not isinstance(request[field], list):
            raise ValueError(f"Independent decision request {field} must be a list")
    account_gate = request["account_type_gate"]
    _validate_exact_object_fields(
        account_gate,
        required={
            "status",
            "checked_holding_count",
            "required_account_categories",
            "confirmed_holdings",
        },
        context="Independent decision request account_type_gate",
    )
    if account_gate["status"] != "complete":
        raise ValueError(
            "Independent decision request account_type_gate must be complete"
        )
    if int(account_gate["checked_holding_count"]) < 1:
        raise ValueError(
            "Independent decision request account_type_gate must include holdings"
        )
    if account_gate["required_account_categories"] != [
        "NISA",
        "特定口座",
        "一般口座",
    ]:
        raise ValueError(
            "Independent decision request account categories are invalid"
        )
    confirmed_holdings = account_gate["confirmed_holdings"]
    if not isinstance(confirmed_holdings, list) or len(confirmed_holdings) != int(
        account_gate["checked_holding_count"]
    ):
        raise ValueError(
            "Independent decision request account_type_gate holding count mismatch"
        )
    for index, holding in enumerate(confirmed_holdings):
        _validate_exact_object_fields(
            holding,
            required={"symbol", "account_type"},
            context=f"Independent decision request confirmed_holdings[{index}]",
        )
        if not any(
            category in str(holding["account_type"])
            for category in ("NISA", "特定口座", "一般口座")
        ):
            raise ValueError(
                "Independent decision request contains an unclassified account type"
            )
    confirmed_facts = request["confirmed_facts"]
    if not isinstance(confirmed_facts, list):
        raise ValueError("Independent decision request confirmed_facts must be a list")
    for index, fact in enumerate(confirmed_facts):
        _validate_exact_object_fields(
            fact,
            required={"name", "value", "as_of", "source_role"},
            context=f"Independent decision request confirmed_facts[{index}]",
        )


def load_independent_decision_response(
    path,
    *,
    expected_decision_id: str,
    expected_holding_accounts: dict[str, str] | None = None,
) -> dict:
    payload = load_yaml(path)
    validate_independent_decision_response(
        payload,
        expected_decision_id=expected_decision_id,
        expected_holding_accounts=expected_holding_accounts or {},
    )
    return payload


def validate_independent_decision_response(
    payload: dict,
    *,
    expected_decision_id: str,
    expected_holding_accounts: dict[str, str] | None = None,
) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Independent decision response must be a YAML object")
    missing = sorted(REQUIRED_RESPONSE_FIELDS - set(payload))
    if missing:
        raise ValueError(
            "Independent decision response missing fields: " + ", ".join(missing)
        )
    unexpected = sorted(set(payload) - REQUIRED_RESPONSE_FIELDS)
    if unexpected:
        raise ValueError(
            "Independent decision response has unexpected fields: "
            + ", ".join(unexpected)
        )
    if payload.get("schema_version") != 1:
        raise ValueError("independent_decision_response.yaml schema_version must be 1")
    if payload.get("artifact_type") != "independent_investment_decision_response":
        raise ValueError(
            "independent_decision_response.yaml artifact_type must be "
            "independent_investment_decision_response"
        )
    if payload.get("decision_id") != expected_decision_id:
        raise ValueError(
            "independent_decision_response.yaml decision_id does not match the request"
        )
    if payload.get("decision_status") not in {
        "determined",
        "conditional",
        "not_calculable",
    }:
        raise ValueError("independent_decision_response.yaml decision_status is invalid")
    if payload.get("user_confirmation_required") is not True:
        raise ValueError(
            "independent_decision_response.yaml must require user confirmation"
        )

    recommendation = payload.get("recommendation")
    recommendation_fields = {
        "decision",
        "rationale",
        "parameter_values",
        "formulas",
        "review_triggers",
    }
    _validate_exact_object_fields(
        recommendation,
        required=recommendation_fields,
        context="independent_decision_response.yaml recommendation",
    )
    action_plan = payload.get("action_plan")
    _validate_exact_object_fields(
        action_plan,
        required={
            "applicability",
            "rationale",
            "existing_asset_sales",
            "new_asset_purchases",
        },
        context="independent_decision_response.yaml action_plan",
    )
    if action_plan["applicability"] not in {"applicable", "not_applicable"}:
        raise ValueError(
            "independent_decision_response.yaml action_plan applicability is invalid"
        )
    if not str(action_plan["rationale"]).strip():
        raise ValueError(
            "independent_decision_response.yaml action_plan requires rationale"
        )
    concrete_action_fields = {
        "symbol",
        "asset_name",
        "account_type",
        "timing",
        "execution_method",
        "quantity",
        "amount_jpy",
        "formula",
        "rationale",
        "requires_user_approval",
    }
    holding_accounts = expected_holding_accounts or {}
    for action_group in ("existing_asset_sales", "new_asset_purchases"):
        actions = action_plan[action_group]
        if not isinstance(actions, list):
            raise ValueError(
                f"independent_decision_response.yaml action_plan.{action_group} must be a list"
            )
        for index, action in enumerate(actions):
            _validate_exact_object_fields(
                action,
                required=concrete_action_fields,
                context=(
                    "independent_decision_response.yaml "
                    f"action_plan.{action_group}[{index}]"
                ),
            )
            if action["requires_user_approval"] is not True:
                raise ValueError("every independent decision action requires user approval")
            action_account_category = classify_review_account_type(
                action["account_type"]
            )
            if action_account_category is None:
                raise ValueError("every independent decision action requires an account category")
            if not str(action["timing"]).strip() or not str(
                action["execution_method"]
            ).strip():
                raise ValueError("every independent decision action requires when and how")
            if not str(action["formula"]).strip():
                raise ValueError("every independent decision action requires a quantity or amount formula")
            symbol = str(action["symbol"])
            if action_group == "existing_asset_sales":
                expected_account = holding_accounts.get(symbol)
                if expected_account is not None and action_account_category != (
                    classify_review_account_type(expected_account)
                ):
                    raise ValueError(
                        "independent decision sale account conflicts with the confirmed holding account"
                    )
            elif symbol in holding_accounts:
                raise ValueError(
                    "independent decision marks a currently held asset as a new purchase"
                )
    for field in (
        "parameter_values",
        "formulas",
        "review_triggers",
        "evidence",
        "alternatives",
        "assumptions",
        "unresolved_information",
    ):
        value = recommendation.get(field) if field in recommendation else payload.get(field)
        if not isinstance(value, list):
            raise ValueError(f"independent_decision_response.yaml {field} must be a list")

    for index, parameter in enumerate(recommendation["parameter_values"]):
        _validate_exact_object_fields(
            parameter,
            required={"name", "value", "unit"},
            context=(
                "independent_decision_response.yaml "
                f"recommendation.parameter_values[{index}]"
            ),
        )
    for index, evidence in enumerate(payload["evidence"]):
        _validate_exact_object_fields(
            evidence,
            required={"title", "url", "as_of", "finding", "inference_use"},
            context=f"independent_decision_response.yaml evidence[{index}]",
        )
    for index, alternative in enumerate(payload["alternatives"]):
        _validate_exact_object_fields(
            alternative,
            required={"description", "switch_condition"},
            context=f"independent_decision_response.yaml alternatives[{index}]",
        )

    prompt_feedback = payload.get("prompt_feedback")
    _validate_exact_object_fields(
        prompt_feedback,
        required={"input_gaps", "template_improvements"},
        context="independent_decision_response.yaml prompt_feedback",
    )
    for field in ("input_gaps", "template_improvements"):
        if not isinstance(prompt_feedback[field], list):
            raise ValueError(
                f"independent_decision_response.yaml prompt_feedback.{field} "
                "must be a list"
            )


def _validate_exact_object_fields(
    value,
    *,
    required: set[str],
    context: str,
) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{context} must be an object")
    missing = sorted(required - set(value))
    if missing:
        raise ValueError(f"{context} missing fields: " + ", ".join(missing))
    unexpected = sorted(set(value) - required)
    if unexpected:
        raise ValueError(f"{context} has unexpected fields: " + ", ".join(unexpected))
