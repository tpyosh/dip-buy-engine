from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path

import pytest

from monthly_limit_order_review.context_records import load_financial_context
from monthly_limit_order_review.prompt_builder import build_monthly_review_prompt
from monthly_limit_order_review.review_packet import build_review_packet

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "prompts/templates/monthly_review_template.md"


def render_prompt(sample_computation) -> str:
    return build_monthly_review_prompt(
        sample_computation,
        TEMPLATE_PATH.read_text(encoding="utf-8"),
        financial_assumptions_text=(
            ROOT / "FINANCIAL_ASSUMPTIONS.md"
        ).read_text(encoding="utf-8"),
    )


def test_monthly_review_prompt_is_a_closed_decision_packet(sample_computation) -> None:
    prompt = render_prompt(sample_computation)

    assert prompt.startswith("# ChatGPT向け月次独立レビュー\n")
    assert "- 対象月: 2026_03" in prompt
    assert "## 実行前チェック（利用者向け）" in prompt
    assert "ChatGPTの資産運用プロジェクト内では実行しない" in prompt
    assert "プロジェクト外の新規Temporary Chat" in prompt
    assert "前月のレビュースレッドを再利用しない" in prompt
    assert "このレビュー・パケット以外のファイルを添付しない" in prompt
    assert "カスタム指示を無効化するか" in prompt

    assert "review_mode: monthly_operational_review" in prompt
    assert "## 1. モードと対話フェーズ" in prompt
    assert "## 2. 入力データ" in prompt
    assert "## 3. 正規ルール台帳" in prompt
    assert "## 4. 外部調査契約" in prompt
    assert "## 5. 出力スキーマと配送契約" in prompt
    assert "## 6. 検証契約" in prompt
    assert "strategic_decision_objective:" in prompt
    assert "capital_layers:" in prompt
    assert "prohibited_residual_rule" in prompt
    assert "user_decision_preferences:" in prompt
    assert "approved_policy:" in prompt
    assert "target_groups:" in prompt
    assert "confirmed_user_conditions:" in prompt
    assert "allowed_quantitative_facts:" in prompt
    assert "unknown_information:" in prompt
    assert "portfolio_snapshot_as_of:" in prompt
    assert "market_reference_as_of:" in prompt
    assert "research_cutoff_at:" in prompt
    assert "decision_date:" in prompt
    assert "R-CASH-001" in prompt
    assert "R-DELIVERY-001" in prompt
    assert "range_rationale_required: true" in prompt
    assert "GE60_B40" in prompt
    assert "source_required_fields:" in prompt
    assert "publication_date" in prompt
    assert "claim_supported" in prompt
    assert "【具体的な売買・資金移動】" in prompt
    assert "review_response.yaml" in prompt
    assert "prompt_feedback" in prompt
    assert "strategic_policy_decision:" in prompt
    assert "updated_inputs:" in prompt
    assert "decision_axes:" in prompt
    assert "schema_ref: schemas/monthly-review-response.schema.yaml" in prompt
    assert "tactical_liquidity_policy_ref" in prompt
    assert "portfolio_snapshot_as_ofの価格・為替・評価額・比率を更新しない" in prompt
    assert "decision_quality_checks: []" in prompt
    assert "status_enum:" in prompt
    assert "- pass" in prompt
    assert "- fail" in prompt
    assert "- not_applicable" in prompt

    assert "active_strategy_id" not in prompt
    assert "active_plan_id" not in prompt
    assert "candidate_orders" not in prompt
    assert "recommended_monthly_core_buy_budget_jpy" not in prompt
    assert "allowed_user_conditions" not in prompt
    assert "review_as_of_total_assets_jpy" not in prompt
    assert "material_trade_assumption_limit_pct" not in prompt
    assert "総資産の5%" not in prompt
    assert "dip_buy_liquidity_policy_proposal" not in prompt
    assert "sox_decision" not in prompt


def test_review_packet_excludes_unselected_history_and_recommendations(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)
    computation.metadata["active_strategy_path"] = "old-private-review-do-not-leak.md"
    computation.metadata["active_plan_paths"] = ["old-approved-plan-do-not-leak.yaml"]
    computation.strategy_summary["legacy_review_name"] = "stale-chatgpt-review-do-not-leak"
    computation.core_buy_materials["recommended_monthly_core_buy_budget_jpy"] = 987654321

    prompt = render_prompt(computation)

    assert "old-private-review-do-not-leak" not in prompt
    assert "old-approved-plan-do-not-leak" not in prompt
    assert "stale-chatgpt-review-do-not-leak" not in prompt
    assert "987654321" not in prompt


def test_unknown_information_is_separated_without_a_point_estimate(
    sample_computation,
) -> None:
    sample_computation.snapshot.liquidity_target_jpy = None
    prompt = render_prompt(sample_computation)

    assert "liquidity_target_jpy" in prompt
    assert "不明値を確認済み事実として推測で埋めず" in prompt
    assert "reviewer_to_derive" in prompt
    assert "unknown_information:" in prompt


def test_review_packet_selects_financial_facts_without_copying_values_into_template(
    sample_computation,
) -> None:
    computation = deepcopy(sample_computation)
    computation.snapshot.snapshot_date = date(2026, 7, 26)
    computation.metadata["review_target_month"] = "2026_08"
    financial = load_financial_context(ROOT)
    packet = build_review_packet(
        computation,
        financial_context=financial["record"],
        financial_context_source=financial["source_path"],
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    assert packet.review_mode == "strategic_policy_second_opinion"

    statements = [
        item["statement"] for item in packet.confirmed_user_conditions
    ]
    unknown_reasons = [
        item["reason"] for item in packet.unknown_information
    ]
    assert any("月次収入: 374,171円" in item for item in statements)
    assert any("通常月の実質可処分収入: 274,171円" in item for item in statements)
    assert "月間必須支出額: 250,000円" in statements
    assert "生活防衛資金の目標額: 2,000,000円" in statements
    assert "生活防衛資金とは別の予備費は確保しない" in statements
    assert "投資待機資金の目標比率は今回の月次独立レビューから提案を受ける" in statements
    assert any(
        "相場下落中でもオール・カントリー型の投資信託を売却"
        in item
        for item in statements
    )
    assert any("NISA月次積立額: 100,000円" in item for item in statements)
    assert not any("月額100,000円の具体的な差引先" in item for item in unknown_reasons)
    assert any("ボーナスの正確な手取り額" in item for item in unknown_reasons)
    assert any("投資待機資金の目標比率" in item for item in unknown_reasons)
    assert "account_tax_comparison" in packet.output_contract["array_schemas"]
    assert "374,171円" not in template
    assert "274,171円" not in template
    assert "2026-07-25_cash_redeployment" not in template
    assert "楽天・プラス・オールカントリー" not in template
    assert "必要現金" not in template
    assert "心理的リスク許容度" not in template


def test_monthly_review_prompt_rejects_unresolved_local_file_reference(
    sample_computation,
) -> None:
    template = (
        TEMPLATE_PATH.read_text(encoding="utf-8")
        + "\nローカル参照: stale_reference.csv\n"
    )

    with pytest.raises(ValueError, match="unresolved local references"):
        build_monthly_review_prompt(sample_computation, template)
