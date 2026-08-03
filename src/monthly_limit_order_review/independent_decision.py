from __future__ import annotations

import yaml

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
}

REQUIRED_RESPONSE_FIELDS = {
    "schema_version",
    "artifact_type",
    "decision_id",
    "completed_at",
    "decision_status",
    "recommendation",
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
) -> dict:
    payload = load_yaml(path)
    validate_independent_decision_response(
        payload,
        expected_decision_id=expected_decision_id,
    )
    return payload


def validate_independent_decision_response(
    payload: dict,
    *,
    expected_decision_id: str,
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
