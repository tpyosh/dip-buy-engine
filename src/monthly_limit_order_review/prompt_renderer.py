from __future__ import annotations

import re

import yaml

from .models import MonthlyComputation, ReviewPacket
from .review_packet import build_review_packet
from .utils import to_serializable


SELF_CONTAINED_HANDOFF_MODE = "closed_review_packet"
FORBIDDEN_RENDERED_FIELDS = (
    "active_strategy_id",
    "active_strategy_path",
    "active_plan_id",
    "active_plan_paths",
    "candidate_orders",
    "recommended_monthly_core_buy_budget_jpy",
    "previous_snapshot_path",
    "screenshot_paths",
)
ABSOLUTE_LOCAL_PATH_RE = re.compile(r"(?:file://|/Users/|/var/folders/)")
UNRESOLVED_FILE_REFERENCE_RE = re.compile(
    r"(?i)(?:file://\S+|(?:^|[\s`\"'(])[^`\s\"']+\.csv\b)"
)
DEPRECATED_OR_UNDEFINED_REFERENCES = (
    "allowed_user_conditions",
    "review_as_of_total_assets_jpy",
    "material_trade_assumption_limit_pct",
    "dip_buy_liquidity_policy_proposal",
    "sox_decision",
)


def render_chatgpt_prompt(
    computation: MonthlyComputation,
    template_text: str,
    *,
    review_packet: ReviewPacket | None = None,
    financial_assumptions_text: str = "",
    financial_assumptions_source: str = "FINANCIAL_ASSUMPTIONS.md",
) -> str:
    packet = review_packet or build_review_packet(
        computation,
        financial_assumptions_text=financial_assumptions_text,
        financial_assumptions_source=financial_assumptions_source,
    )
    if packet.generation_status != "ready":
        raise ValueError(
            "blocked_missing_strategic_inputs: "
            + ", ".join(packet.missing_strategic_inputs)
        )
    preflight = "\n".join(f"- [ ] {item}" for item in packet.preflight_checklist)
    rendered_template = (
        template_text.replace("{{REVIEW_TARGET_MONTH}}", packet.review_target_month)
        .replace(
            "{{PORTFOLIO_SNAPSHOT_AS_OF}}",
            packet.portfolio_snapshot_as_of.isoformat(),
        )
        .replace("{{INTERACTION_PHASE}}", packet.interaction_phase)
        .replace("{{PREFLIGHT_CHECKLIST}}", preflight)
    )
    phase_gate = build_phase_gate(packet)
    input_data = {
        "date_context": {
            "review_target_month": packet.review_target_month,
            "portfolio_snapshot_as_of": packet.portfolio_snapshot_as_of,
            "market_reference_as_of": packet.market_reference_as_of,
            "packet_generated_at": packet.packet_generated_at,
            "research_cutoff_at": packet.research_cutoff_at,
            "decision_date": packet.decision_date,
        },
        "strategic_required_inputs": packet.strategic_required_inputs,
        "strategic_decision_objective": packet.strategic_decision_objective,
        "candidate_methodology": packet.candidate_methodology,
        "capital_layers": packet.capital_layers,
        "asset_class_definitions": packet.asset_class_definitions,
        "allocation_denominators": packet.allocation_denominators,
        "market_decline_rule": packet.market_decline_rule,
        "direct_semiconductor_limit": packet.direct_semiconductor_limit,
        "user_decision_preferences": packet.user_decision_preferences,
        "active_risk_policy": packet.active_risk_policy,
        "approved_policy": packet.approved_policy,
        "selected_sources": packet.selected_sources,
        "confirmed_user_conditions": packet.confirmed_user_conditions,
        "allowed_quantitative_facts": packet.allowed_quantitative_facts,
        "unknown_information": packet.unknown_information,
        "excluded_information": packet.excluded_information,
    }
    lines = [
        rendered_template.strip(),
        "",
        "---",
        "",
        "# 自己完結型レビュー・パケット",
        "",
        f"- handoff_mode: {SELF_CONTAINED_HANDOFF_MODE}",
        "- このパケット外のユーザー固有情報、過去会話、Project/GPTメモリを使用しないでください。",
        (
            "- 不明値を確認済み事実として推測で埋めず、事実と外部調査による一般情報を"
            "分離してください。明示されたreviewer_to_derive系の項目は、推定値・根拠・"
            "限界・感応度を示して導出してください。"
        ),
        "",
        "## 1. モードと対話フェーズ",
        yaml_block(phase_gate),
        "",
        "## 2. 入力データ",
        yaml_block(input_data),
        "",
        "## 3. 正規ルール台帳",
        "同じ規則を別の表現で上書きせず、判断根拠ではrule_idを参照してください。",
        yaml_block({"rule_registry": packet.rule_registry}),
        "",
        "## 4. 外部調査契約",
        yaml_block(packet.research_contract),
        "",
        "## 5. 出力スキーマと配送契約",
        yaml_block(packet.output_contract),
        "",
        "## 6. 検証契約",
        yaml_block(packet.validation_contract),
    ]
    prompt = "\n".join(lines).rstrip() + "\n"
    validate_closed_review_prompt(prompt)
    return prompt


def build_phase_gate(packet: ReviewPacket) -> dict:
    gate = {
        "generation_status": packet.generation_status,
        "review_mode": packet.review_mode,
        "interaction_phase": packet.interaction_phase,
    }
    if packet.interaction_phase == "objective_confirmation":
        offered = [
            {
                "objective_id": objective_id,
                "label": model["label"],
                "definition": model["primary_objective_fit_rule"],
            }
            for objective_id, model in packet.strategic_decision_objective[
                "objective_models"
            ].items()
            if model.get("offered") is True
        ]
        gate.update(
            {
                "required_first_response": (
                    "次の候補から主目的を一つだけ選んでください: "
                    + " / ".join(
                        f"{item['objective_id']}（{item['label']}）" for item in offered
                    )
                ),
                "allowed_addition": "各候補の一行定義だけ",
                "forbidden_in_first_response": [
                    "web_research",
                    "investment_decision",
                    "six_human_sections",
                    "yaml",
                    "trade_proposals",
                    "decision_quality_checks",
                ],
                "after_user_answer": (
                    "interaction_phaseをfinal_reviewへ切り替え、回答をupdated_inputsへ入れ、"
                    "このパケット全体を最初から評価する。追加の抽象質問は禁止"
                ),
            }
        )
    else:
        gate["required_first_response"] = "【推奨方針】から始める"
    return gate


def yaml_block(value) -> str:
    payload = yaml.safe_dump(
        to_serializable(value),
        allow_unicode=True,
        sort_keys=False,
    ).rstrip()
    return f"```yaml\n{payload}\n```"


def render_review_generation_blocker(packet: ReviewPacket) -> str:
    if packet.generation_status == "ready":
        raise ValueError("A ready review packet does not need a generation blocker")
    lines = [
        "# 月次独立レビュー生成停止",
        "",
        "このファイルはChatGPTへ渡すプロンプトではありません。戦略判断に必要な入力が不足しているため、閉じたレビュー・パケットの生成を停止しました。",
        "",
        f"- generation_status: {packet.generation_status}",
        f"- review_mode: {packet.review_mode}",
        f"- intended_interaction_phase: {packet.interaction_phase}",
        "",
        "## 不足入力",
    ]
    lines.extend(f"- `{item}`" for item in packet.missing_strategic_inputs)
    lines.extend(
        [
            "",
            "未確認値を推測で埋めず、`financial/current.yaml` が指す構造化レコードへ確認済み値を追加してから再生成してください。入力形式は `schemas/financial-context.schema.yaml` を参照してください。",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def validate_closed_review_prompt(prompt: str) -> None:
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}", prompt)
    if unresolved:
        raise ValueError(
            "Rendered monthly review prompt contains unresolved placeholders: "
            + ", ".join(sorted(set(unresolved)))
        )
    if ABSOLUTE_LOCAL_PATH_RE.search(prompt):
        raise ValueError("Rendered monthly review prompt contains a local absolute path.")
    if UNRESOLVED_FILE_REFERENCE_RE.search(prompt):
        raise ValueError(
            "Rendered monthly review prompt contains unresolved local references."
        )
    leaked = [field for field in FORBIDDEN_RENDERED_FIELDS if field in prompt]
    if leaked:
        raise ValueError(
            "Closed review packet contains excluded computation fields: "
            + ", ".join(leaked)
        )
    deprecated = [
        reference
        for reference in DEPRECATED_OR_UNDEFINED_REFERENCES
        if reference in prompt
    ]
    if deprecated:
        raise ValueError(
            "Closed review packet contains deprecated or undefined references: "
            + ", ".join(deprecated)
        )
    required_structures = (
        "## 1. モードと対話フェーズ",
        "## 2. 入力データ",
        "## 3. 正規ルール台帳",
        "## 4. 外部調査契約",
        "## 5. 出力スキーマと配送契約",
        "## 6. 検証契約",
    )
    missing_structures = [item for item in required_structures if item not in prompt]
    if missing_structures:
        raise ValueError(
            "Closed review packet is missing canonical structures: "
            + ", ".join(missing_structures)
        )
