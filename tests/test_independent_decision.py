from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from monthly_limit_order_review.independent_decision import (
    load_independent_decision_response,
    render_independent_decision_prompt,
)


ROOT = Path(__file__).resolve().parents[1]


def request_payload() -> dict:
    return {
        "schema_version": 1,
        "request_type": "on_demand_independent_investment_decision",
        "decision_id": "test-allocation-parameter",
        "created_at": "2026-08-02T12:00:00+09:00",
        "decision_question": "独立して比率を決めてください",
        "decision_scope": "portfolio_parameter_second_opinion",
        "confirmed_facts": [
            {
                "name": "total_assets_jpy",
                "value": 10_000_000,
                "as_of": "2026-08-01",
                "source_role": "machine_total",
            }
        ],
        "user_constraints": ["総資産比率で算定する"],
        "unknown_information": ["採用比率"],
        "excluded_context": ["Codexの候補比率"],
        "research_requirements": ["一次情報を優先する"],
        "required_outputs": ["推奨比率と算式"],
        "account_type_gate": {
            "status": "complete",
            "checked_holding_count": 1,
            "required_account_categories": ["NISA", "特定口座", "一般口座"],
            "confirmed_holdings": [
                {"symbol": "MSFT", "account_type": "特定口座（源泉徴収あり）"}
            ],
        },
    }


def test_on_demand_decision_prompt_delegates_without_codex_recommendation() -> None:
    template = (
        ROOT / "prompts/templates/on_demand_independent_decision_template.md"
    ).read_text(encoding="utf-8")

    prompt = render_independent_decision_prompt(request_payload(), template)

    assert "資産運用Project外の新規Temporary Chat" in prompt
    assert "Codexは結論、候補値、推奨方向を作っていません" in prompt
    assert "decision_question: 独立して比率を決めてください" in prompt
    assert "Codexの候補比率" in prompt
    assert "{{DECISION_REQUEST_YAML}}" not in prompt


def test_on_demand_decision_prompt_rejects_incomplete_packet() -> None:
    template = "{{DECISION_REQUEST_YAML}}"
    payload = request_payload()
    payload.pop("unknown_information")

    with pytest.raises(ValueError, match="unknown_information"):
        render_independent_decision_prompt(payload, template)


def test_on_demand_decision_prompt_rejects_codex_recommendation_field() -> None:
    template = "{{DECISION_REQUEST_YAML}}"
    payload = request_payload()
    payload["codex_recommendation"] = "10%"

    with pytest.raises(ValueError, match="unexpected fields: codex_recommendation"):
        render_independent_decision_prompt(payload, template)


def test_on_demand_decision_prompt_rejects_incomplete_account_gate() -> None:
    template = "{{DECISION_REQUEST_YAML}}"
    payload = request_payload()
    payload["account_type_gate"]["status"] = "blocked"

    with pytest.raises(ValueError, match="account_type_gate must be complete"):
        render_independent_decision_prompt(payload, template)


def response_payload() -> dict:
    return {
        "schema_version": 1,
        "artifact_type": "independent_investment_decision_response",
        "decision_id": "test-allocation-parameter",
        "completed_at": "2026-08-02T13:00:00+09:00",
        "decision_status": "determined",
        "recommendation": {
            "decision": "test decision",
            "rationale": "test rationale",
            "parameter_values": [],
            "formulas": [],
            "review_triggers": [],
        },
        "action_plan": {
            "applicability": "not_applicable",
            "rationale": "parameter-only test decision",
            "existing_asset_sales": [],
            "new_asset_purchases": [],
        },
        "evidence": [],
        "alternatives": [],
        "assumptions": [],
        "unresolved_information": [],
        "user_confirmation_required": True,
        "prompt_feedback": {
            "input_gaps": [],
            "template_improvements": [],
        },
    }


def test_independent_decision_response_matches_request_id(tmp_path: Path) -> None:
    response_path = tmp_path / "independent_decision_response.yaml"
    response_path.write_text(
        yaml.safe_dump(response_payload(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    payload = load_independent_decision_response(
        response_path,
        expected_decision_id="test-allocation-parameter",
    )

    assert payload["decision_status"] == "determined"


def test_independent_decision_response_rejects_wrong_request_id(
    tmp_path: Path,
) -> None:
    response_path = tmp_path / "independent_decision_response.yaml"
    response_path.write_text(
        yaml.safe_dump(response_payload(), allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="decision_id does not match"):
        load_independent_decision_response(
            response_path,
            expected_decision_id="another-request",
        )


def test_independent_decision_sale_must_match_confirmed_account(
    tmp_path: Path,
) -> None:
    payload = response_payload()
    payload["action_plan"] = {
        "applicability": "applicable",
        "rationale": "A sale is proposed.",
        "existing_asset_sales": [
            {
                "symbol": "MSFT",
                "asset_name": "Microsoft",
                "account_type": "NISA（成長投資枠）",
                "timing": "next trading day",
                "execution_method": "market order after user approval",
                "quantity": 1,
                "amount_jpy": None,
                "formula": "sell 1 share",
                "rationale": "test",
                "requires_user_approval": True,
            }
        ],
        "new_asset_purchases": [],
    }
    response_path = tmp_path / "independent_decision_response.yaml"
    response_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="confirmed holding account"):
        load_independent_decision_response(
            response_path,
            expected_decision_id="test-allocation-parameter",
            expected_holding_accounts={
                "MSFT": "特定口座（源泉徴収あり）"
            },
        )
