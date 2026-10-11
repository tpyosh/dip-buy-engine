"""Generate fresh independent reviews without prior advice or execution plans."""

from __future__ import annotations

import re
from hashlib import sha256
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import jsonschema
import yaml

from .context_records import apply_holding_metadata, load_financial_context, load_holding_metadata_context
from .review_readiness import require_complete_account_type_gate
from .snapshot_loader import load_snapshot
from .storage import load_yaml, write_text, write_yaml
from .strategy_policy import validate_strategy_policy


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas/independent-review-input.schema.yaml"
WORKFLOW_REF = "prompts/workflows/independent_review.md"
WORKFLOW_ID = "independent_review_decision_v2"
STAGES = ("research", "sufficiency", "decision", "integration", "documentation")
HOLDING_FIELDS = (
    "symbol", "name", "source_category", "institution", "account_type", "quantity",
    "avg_cost", "current_price", "unit_price", "profit_loss_jpy", "market_value_jpy",
    "currency", "source_ref", "acquired_on", "observed_on", "components",
)


def select(value: dict, fields: tuple[str, ...]) -> dict:
    return {key: deepcopy(value[key]) for key in fields if key in value}


def source_record(ref: str, record: dict, values: dict) -> dict:
    return {
        "source_ref": ref,
        "stable_id": record.get("record_id", record.get("strategy_id")),
        "confirmed_at": record.get("confirmed_at", record.get("effective_from")),
        "values": values,
    }


def broker_differences(holding: dict) -> dict:
    """Keep conflicting observations and execution facts, without duplicate rows."""
    observed = holding.get("broker_observation", {})
    compared = ("quantity", "avg_cost", "current_price", "market_value_jpy", "profit_loss_jpy")
    differences = {
        key: deepcopy(observed[key]) for key in compared
        if key in observed and observed[key] != holding.get(key)
    }
    differences.update(select(observed, (
        "acquisition_cost_jpy", "acquisition_cost_usd", "sellable_quantity_round_lot",
        "foreign_deposit", "jpy_deposit_jpy", "nomura_mrf_jpy",
    )))
    if observed.get("order_quantity") is not None:
        differences["order_quantity"] = observed["order_quantity"]
    if differences:
        differences = {**select(observed, ("source_ref", "observed_on", "price_as_of")), **differences}
    return differences


def build_independent_review_input(
    project_root: Path,
    snapshot_path: Path,
    *,
    requested_at: datetime | None = None,
) -> dict:
    root = project_root.resolve()
    path = snapshot_path.resolve()
    snapshot = load_snapshot(path)
    raw = load_yaml(path)
    financial = load_financial_context(root)
    metadata = load_holding_metadata_context(root)
    apply_holding_metadata(snapshot, metadata["record"])
    gate = require_complete_account_type_gate(snapshot)
    symbols = [holding.symbol for holding in snapshot.holdings]
    if len(set(symbols)) != len(symbols):
        raise ValueError("Duplicate holding symbols")
    snapshot_ref = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    current = requested_at or datetime.now(ZoneInfo("Asia/Tokyo"))
    stamp = current.astimezone(ZoneInfo("Asia/Tokyo")).isoformat(timespec="seconds")
    record = financial["record"]
    profile = record.get("strategic_profile", {})
    objective = profile.get("objective_configuration", {})
    investment_goal = objective.get("objective_models", {}).get("maximize_terminal_wealth", {})
    direction_values = {
        "primary_goal": objective.get("user_stated_goal"),
        "target_date": investment_goal.get("target_date"),
    }
    direction_source = financial["source_path"]
    direction_record = record
    pointer_path = root / "strategy/current.yaml"
    if pointer_path.exists():
        pointer = load_yaml(pointer_path)
        direction_source = pointer["active_strategy_path"]
        strategy_path = (root / direction_source).resolve()
        if not strategy_path.is_relative_to(root):
            raise ValueError("Strategy source must stay within repository")
        strategy = load_yaml(strategy_path)
        if pointer["active_strategy_id"] != strategy["strategy_id"]:
            raise ValueError("Strategy pointer ID mismatch")
        validate_strategy_policy(strategy)
        direction_record = strategy
        purpose = strategy["purpose"]
        direction_values = select(purpose, ("statement", "target_age", "target_date", "lifestyle_constraint"))
        direction_values["positive_satellite_allocation_required"] = strategy["review_policy"]["satellite_parameters"]["positive_satellite_allocation_required"]
    holdings = []
    for original, holding in zip(raw["holdings"], snapshot.holdings):
        item = select(original, HOLDING_FIELDS)
        item["account_type"] = holding.account_type
        differences = broker_differences(original)
        if differences:
            item["broker_observation"] = differences
        holdings.append(item)
    active_intents = {
        symbol: select(metadata["record"].get("holdings", {}).get(symbol, {}), ("user_intent",))
        for symbol in symbols
        if metadata["record"].get("holdings", {}).get(symbol, {}).get("user_intent")
    }
    human_capital = select(profile.get("human_capital_assumptions", {}), (
        "education", "employment_status", "occupation", "income_stability", "income_stability_reason",
        "expected_salary_continuation_years", "planned_retirement_age", "retirement_age_certainty",
        "known_long_leave_or_unemployment_risk",
    ))
    future = profile.get("expected_future_cash_flows", {}).get("items", {})
    future_facts = {key: select(value, (
        "expected_continuation_years", "planned_retirement_age", "certainty", "future_amount_jpy", "status",
        "source_owner", "source_estimated_total_assets_jpy", "estimate_qualifier", "reported_beneficiaries",
        "user_is_beneficiary", "user_share_jpy", "possible_timing_within_years", "timing_certainty",
    )) for key, value in future.items() if isinstance(value, dict)}
    recurring_pointer = load_yaml(root / "plans/recurring/current.yaml")
    recurring_ref = recurring_pointer["active_record_path"]
    recurring = load_yaml(root / recurring_ref)
    recurring_values = select(recurring["core_recurring_contributions"], (
        "total_monthly_jpy", "nisa_growth_quota_status", "plans", "pension_monthly_dca", "crypto_weekly_dca",
    ))
    payload = {
        "schema_version": 1,
        "packet_type": "fresh_snapshot_independent_review",
        "requested_at": stamp,
        "research_cutoff_at": stamp,
        "portfolio_snapshot": {
            "source_ref": snapshot_ref,
            "stable_id": f"snapshot_{snapshot.snapshot_date.isoformat()}",
            "as_of": snapshot.snapshot_date.isoformat(),
            "currency_base": raw["currency_base"],
            "total_assets_jpy": raw["total_assets_jpy"],
            "category_totals_jpy": raw.get("category_totals_jpy", {}),
            "observation_basis": select(raw.get("source_evidence", {}), (
                "snapshot_date_basis", "valuation_basis", "broker_export_time_basis", "usd_jpy_reference",
            )),
            "holdings": holdings,
        },
        "financial_facts": source_record(financial["source_path"], record, {
            **select(record, ("scope", "cash_flow", "cash_requirements", "mortgage", "unknown_information")),
            "personal_profile": select(profile, ("date_of_birth", "tax_residency", "planning_end_age", "expected_withdrawal_start", "earliest_possible_asset_use_date")),
            "human_capital": human_capital,
            "expected_future_cash_flows": future_facts,
            "leverage_allowed": investment_goal.get("leverage_allowed"),
            "confirmed_investment_objective": select(investment_goal, (
                "target_age", "target_date", "optimization_target", "profit_definition", "return_basis", "statistic",
                "lifestyle_constraints",
            )),
        }),
        "user_directions": source_record(direction_source, direction_record, direction_values),
        "holding_user_intents": source_record(metadata["source_path"], metadata["record"], active_intents),
        "observed_recurring_settings": source_record(recurring_ref, recurring, recurring_values),
        "account_type_gate": {"status": gate["status"], "checked_holding_count": gate["checked_holding_count"]},
        "data_quality_notes": raw.get("validation_notes", []),
    }
    jsonschema.Draft202012Validator(load_yaml(SCHEMA_PATH)).validate(payload)
    return payload


def render_independent_review(payload: dict, template: str, workflow: str | None = None) -> str:
    jsonschema.Draft202012Validator(load_yaml(SCHEMA_PATH)).validate(payload)
    if payload["account_type_gate"]["status"] != "complete":
        raise ValueError("blocked_missing_account_types")
    workflow = (ROOT / WORKFLOW_REF).read_text() if workflow is None else workflow
    if (f"<!-- workflow_id: {WORKFLOW_ID} -->" not in workflow
            or tuple(re.findall(r"<!-- stage:([a-z]+) -->", workflow)) != STAGES):
        raise ValueError("Review workflow missing or reordered stages")
    rendered = template
    for key, value in {
        "REQUESTED_AT": payload["requested_at"],
        "SNAPSHOT_DATE": payload["portfolio_snapshot"]["as_of"],
        "REVIEW_WORKFLOW": workflow.strip(),
        "REVIEW_INPUT_YAML": yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).strip(),
    }.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in rendered:
            raise ValueError(f"Review template missing {placeholder}")
        rendered = rendered.replace(placeholder, value)
    if re.search(r"\{\{[A-Z_]+\}\}", rendered):
        raise ValueError("Unresolved review template placeholder")
    return rendered.rstrip() + "\n"


def write_independent_review(
    project_root: Path, snapshot_path: Path, *, output: Path | None = None,
) -> Path:
    payload = build_independent_review_input(project_root, snapshot_path)
    template_ref = "prompts/templates/independent_review_template.md"
    prompt = render_independent_review(payload, (project_root / template_ref).read_text(),
                                       (project_root / WORKFLOW_REF).read_text())
    current = datetime.now(ZoneInfo("Asia/Tokyo"))
    output_path = output or (project_root / "reports/generated/on_demand" / str(current.year)
                             / (current.strftime("%Y_%m_%dT%H%M%S_%f") + "_independent_review") / "review_request.md")
    input_path = output_path.parent / "review_input.yaml"
    readme_path = output_path.parent / "README.md"
    manifest_path = output_path.parent / "generation_manifest.yaml"
    if any(path.exists() for path in (output_path, input_path, readme_path, manifest_path)):
        raise FileExistsError("Use a new output directory to preserve review history")
    source_refs = ["src/monthly_limit_order_review/independent_review.py", template_ref, WORKFLOW_REF]
    source_refs.extend(payload[key]["source_ref"] for key in (
        "portfolio_snapshot", "financial_facts", "user_directions", "holding_user_intents", "observed_recurring_settings"))
    manifest = {
        "schema_version": 1,
        "generated_at": payload["requested_at"],
        "workflow_id": WORKFLOW_ID,
        "sources": [{"source_ref": ref, "sha256": sha256((project_root / ref).read_bytes()).hexdigest()}
                    for ref in dict.fromkeys(source_refs)],
        "prompt_sha256": sha256(prompt.encode()).hexdigest(),
    }
    write_text(output_path, prompt)
    write_yaml(input_path, payload)
    write_yaml(manifest_path, manifest)
    write_text(readme_path, f"""# 独立レビュー依頼の状態

<!-- Generated by src/monthly_limit_order_review/independent_review.py; do not edit directly. -->

- 生成日時：{payload['requested_at']}
- 状態：入力検証・依頼準備済み。独立ChatGPTでのレビューは未実施。
- 引き渡し：A・本文完結型。`{output_path.name}`全体をProject外の新規Temporary Chatへコピー＆ペースト。添付は不要。
- 基準スナップショット：`{payload['portfolio_snapshot']['source_ref']}`（{payload['portfolio_snapshot']['as_of']}）
- 共通ルール：`docs/independent-review.md`
- 生成テンプレート：`prompts/templates/independent_review_template.md`
- 工程定義：`{WORKFLOW_REF}`（`{WORKFLOW_ID}`）
- 生成元と出力のSHA-256：`generation_manifest.yaml`。生成時点の対応を確認するための記録です。
- 現行の運用上の正本：`strategy/current.yaml`。この依頼や入力ファイルは正本ではありません。
- この依頼から作成された承認記録：なし。承認後は対応する`decisions/`参照と履歴・再利用禁止を状態説明に追記します。

初回はレビュワーが選ぶ一論点のみ。その後は調査 → 証拠の充足判定 → 投資判断・行動設計 → 統合 → Codex文書化を、同じ会話で一工程ずつ明示的に依頼します。
判断工程と統合工程では意思決定価値の品質ゲートを確認します。数量や税額の未知だけで全判断を止めません。
ローカルファイルはChatGPTへ自動共有されません。この処理はChatGPTへ送信していません。

再生成は新しいディレクトリを使います。

```sh
.venv/bin/python -m monthly_limit_order_review.cli generate-review-prompt --snapshot {payload['portfolio_snapshot']['source_ref']}
```
""")
    return output_path


def mark_review_superseded(directory: Path, replacement: Path) -> None:
    """Update only the status explanation; preserve historical prompt contents."""
    readme = directory / "README.md"
    previous = readme.read_text()
    marker = "## Superseded"
    if marker in previous:
        raise ValueError("Review is already superseded")
    write_text(readme, previous.rstrip() + f"\n\n{marker}\n\n"
               "<!-- Status generated by src/monthly_limit_order_review/independent_review.py -->\n\n"
               f"この依頼は共通レビュー設計の変更により履歴となりました。再送しないでください。新しい依頼：`{replacement}`。"
               "承認済み投資判断への接続はなく、戦略の正本は`strategy/current.yaml`のままです。\n")
