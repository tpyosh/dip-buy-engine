from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
import re
from pathlib import Path

import pytest

from monthly_limit_order_review.storage import load_yaml
from monthly_limit_order_review.strategy_policy import (
    StrategyPolicyError,
    load_current_strategy,
    validate_strategy_policy,
)


ROOT = Path(__file__).resolve().parents[1]


def test_current_strategy_pointer_loads_the_approved_strategy() -> None:
    strategy = load_current_strategy(ROOT)

    assert strategy["strategy_id"] == "husband_personal_2026-08-09-v2"
    assert strategy["automation"]["human_approval_required_for_all_trades"] is True


def test_current_strategy_pointer_routes_to_act_s3_plan() -> None:
    pointer = load_yaml(ROOT / "strategy/current.yaml")

    assert pointer["active_plan_paths"] == [
        "plans/2026/2026-08-09_act_s3_execution.yaml"
    ]


def test_human_entrypoints_describe_approved_act_s3_policy_not_preapproval_state() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    generated_status = (
        ROOT / "reports/generated/monthly/2026_08/README.md"
    ).read_text(encoding="utf-8")

    assert "コア82.5%中心、サテライト17.5%中心" in readme
    assert "戦術的待機資金なし" in readme
    assert "ACT-S3-001`～`ACT-S3-016" in readme
    assert "現在のレビュー依頼、現在方針、現在の次の操作ではありません" in generated_status
    assert "decisions/2026-08-09_act_s3_policy_approval.md" in generated_status
    assert "このディレクトリのレビュー依頼をChatGPTへ再送しません" in generated_status


def test_strategy_targets_and_rebalance_thresholds_are_consistent() -> None:
    strategy = load_current_strategy(ROOT)
    groups = strategy["allocation"]["target_groups"]

    target_sum = sum((Decimal(str(group["target_pct"])) for group in groups.values()), start=Decimal("0"))

    assert target_sum == Decimal("1.0")
    assert Decimal(str(groups["broad_core"]["rebalance_proposal_below_pct"])) == Decimal("0.80")
    assert Decimal(str(groups["active_hobby"]["rebalance_proposal_above_pct"])) == Decimal("0.20")


def test_act_s3_resume_plan_preserves_policy_and_all_task_ids() -> None:
    strategy = load_current_strategy(ROOT)
    plan = load_yaml(ROOT / "plans/2026/2026-08-09_act_s3_execution.yaml")
    task_ids = [task["id"] for task in plan["tasks"]]

    assert plan["strategy_ref"] == "strategy/versions/2026-08-09-v2.yaml"
    expected_active_ids = [
        f"ACT-S3-{index:03d}" for index in (*range(1, 13), *range(14, 17))
    ]
    assert task_ids == expected_active_ids
    assert plan["resume_contract"]["canonical_task_ids"]["active"] == expected_active_ids
    assert plan["resume_contract"]["canonical_task_ids"]["retired"] == ["ACT-S3-013"]
    assert plan["retired_task_records"] == [
        {
            "id": "ACT-S3-013",
            "retired_at": "2026-08-13",
            "reason": "独立した成果物を持たない禁止・不作為をタスクとして登録しており、終了条件と完了報告を持てなかったため",
            "migrated_to": "execution_guardrails.first_stage_satellite_buy_freeze",
            "disposition": "not_applicable_not_a_task",
            "id_reuse_allowed": False,
        }
    ]
    guardrail = plan["execution_guardrails"]["first_stage_satellite_buy_freeze"]
    assert guardrail["task_tracking"] is False
    assert guardrail["user_todo"] is False
    assert guardrail["source_retired_task_id"] == "ACT-S3-013"
    assert len(task_ids) == len(set(task_ids))
    assert plan["tasks"][0]["status"] == "completed"
    assert plan["tasks"][0]["actual_execution"]["gross_proceeds_jpy"] == 460_500
    assert plan["tasks"][0]["actual_execution"]["trade_date"] == "2026-08-10"
    assert plan["tasks"][0]["actual_execution"]["settlement_date"] == "2026-08-13"
    assert plan["tasks"][0]["actual_execution"]["net_proceeds_jpy"] == 459_976
    assert plan["tasks"][0]["actual_execution"]["provisional_realized_gain_loss_jpy"] == -482_024
    assert plan["tasks"][1]["status"] == "completed"
    assert plan["tasks"][1]["actual_execution"]["gross_proceeds_jpy"] == 25_200
    assert plan["tasks"][1]["actual_execution"]["trade_date"] == "2026-08-10"
    assert plan["tasks"][1]["actual_execution"]["settlement_date"] == "2026-08-13"
    assert plan["tasks"][1]["actual_execution"]["net_proceeds_jpy"] == 25_048
    assert plan["tasks"][1]["actual_execution"]["provisional_realized_gain_loss_jpy"] == -1_452
    act_s3_004 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-004")
    assert act_s3_004["status"] == "completed"
    assert act_s3_004["actual_result"] == {
        "approved_at": "2026-08-10",
        "approval_ref": "decisions/2026-08-10_act_s3_004_emergency_fund_location_approval.md",
        "emergency_fund_account": "三菱UFJ銀行 普通預金",
        "emergency_fund_jpy": 2_000_000,
        "basis_investable_cash_jpy": 11_147_713,
        "basis_as_of": "2026-08-09",
        "execution_amount_status": "reference_ceiling_not_an_order_amount",
        "execution_refresh_rule": "ACT-S3-005の各注文入力時に、当該資金源の実買付可能額、拘束資金、未反映入出金、直近確定支払を反映する",
    }
    assert strategy["allocation"]["asset_mix"] == {
        "equity_pct": 1.0,
        "bond_pct": 0.0,
        "crypto_target_pct": 0.0,
    }
    assert strategy["allocation"]["tactical_cash"]["enabled"] is False
    assert strategy["allocation"]["emergency_fund"]["target_jpy"] == 2_000_000

    known_ids = set(task_ids)
    dependencies = {
        task["id"]: set(task.get("depends_on", []))
        for task in plan["tasks"]
    }
    assert all(required <= known_ids for required in dependencies.values())

    remaining = dict(dependencies)
    completed: set[str] = set()
    while remaining:
        ready = {
            task_id
            for task_id, required in remaining.items()
            if required <= completed
        }
        assert ready, "ACT-S3 dependencies must be acyclic"
        completed.update(ready)
        for task_id in ready:
            remaining.pop(task_id)

    parallel_now = {
        task["id"]
        for task in plan["tasks"]
        if str(task.get("scheduling", "")).startswith("parallel_now")
    }
    assert {"ACT-S3-001", "ACT-S3-002", "ACT-S3-004", "ACT-S3-006", "ACT-S3-008", "ACT-S3-010"} <= parallel_now

    act_s3_008 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-008")
    assert act_s3_008["status"] == "completed"
    assert act_s3_008["actual_execution"]["order_number"] == "1262"
    assert act_s3_008["actual_execution"]["filled_quantity"] == 1
    assert act_s3_008["actual_execution"]["order_price_usd"] == 583.49
    assert act_s3_008["actual_execution"]["execution_price_usd"] == 585.83
    assert act_s3_008["actual_execution"]["displayed_settlement_amount_usd"] == 582.92
    assert act_s3_008["actual_execution"]["displayed_fee_usd"] == 2.91
    assert act_s3_008["actual_execution"]["displayed_exchange_rate_jpy_per_usd"] == 159.140
    assert act_s3_008["actual_execution"]["displayed_values_reconciliation_status"] == "resolved"
    assert act_s3_008["actual_execution"]["settlement_date_japan"] == "2026-08-14"
    assert act_s3_008["actual_execution"]["remaining_quantity"] == 0

    act_s3_009 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-009")
    assert act_s3_009["status"] == "in_progress"

    act_s3_010 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-010")
    assert act_s3_010["allocation_basis"]["denominator"] == "long_term_investable_assets_jpy"
    assert act_s3_010["allocation_basis"]["targets"] == [
        {
            "numerator": "CIBR_market_value_jpy",
            "relation": "approximately_equal",
            "value": 0.03,
        }
    ]
    order = act_s3_010["order_specification"]
    assert act_s3_010["status"] == "completed"
    assert order["status"] == "filled"
    assert order["order_type"] == "market"
    assert order["intraday_quote_required"] is False
    assert order["realtime_bid_ask_monitoring_required"] is False
    recheck = act_s3_010["current_state_recheck"]
    assert recheck["provisional_long_term_investable_assets_jpy"] == 38_011_311
    assert recheck["reference_remaining_shares"] == 74
    assert recheck["reference_ratio_after_sale"] == 0.0300598
    assert recheck["price_refresh_completed"] is False
    assert recheck["executable"] is False
    assert order["quantity"] == 14
    assert order["expected_remaining_quantity"] == 74
    assert order["expiration"].startswith("本日中")
    assert order["extended_hours_enabled"] is False
    assert order["settlement_currency"] == "JPY"
    assert order["skip_confirmation_screen"] is False
    assert order["execution_allowed"] is False
    assert order["user_approval_status"] == "approved"
    assert order["quantity_intent_status"] == "approved_14_shares"
    assert order["settings_approval_status"] == "approved_and_executed"
    execution = act_s3_010["actual_execution"]
    assert execution["order_number"] == "1266"
    assert execution["filled_quantity"] == 14
    assert execution["remaining_quantity"] == 74
    assert execution["settlement_date_japan"] == "2026-08-17"
    assert execution["execution_price_usd"] is None
    assert "追加注文不要" in act_s3_010["human_actionability"]["next_action"]
    assert act_s3_010["human_actionability"]["unblock_condition"] == "completed"

    act_s3_005 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-005")
    staged = act_s3_005["staged_execution_design"]
    assert staged["tactical_market_timing"] is False
    assert staged["execution_design_approval_status"] == (
        "approved_by_user_direction_to_deploy_available_cash_without_waiting_for_all_sources"
    )
    assert staged["aggregate_reference_ceiling_jpy"] == 11_147_713
    assert staged["current_adjustment"] == {
        "effective_at": "2026-08-29",
        "decision_ref": "decisions/2026-08-29_mufg_large_purchase_reserve.yaml",
        "excluded_near_term_large_purchase_reserve_jpy": 467_987,
        "adjusted_aggregate_reference_ceiling_jpy": 10_679_726,
        "committed_core_purchases_jpy": 8_184_782,
        "adjusted_reference_ceiling_remaining_jpy": 2_494_944,
        "formula": "10,679,726円 - 5,861,859円 - 1,946,765円 - 376,158円 = 2,494,944円",
    }
    assert [stage["reference_balance_jpy"] for stage in staged["stages"][:1]] == [
        8_471_062
    ]
    assert staged["stages"][1]["reference_subtotal_jpy"] == 2_212_544
    assert staged["stages"][2]["reference_net_jpy"] == 464_107
    assert all(stage["wait_for_other_sources"] is False for stage in staged["stages"])
    stage_1 = act_s3_005["current_stage_proposal"]
    assert stage_1["status"] == "completed_filled"
    assert stage_1["current_buying_power_jpy"] == 5_861_859
    assert stage_1["proposed_purchase_amount_jpy"] == 5_861_859
    assert stage_1["aggregate_reference_ceiling_remaining_after_stage_jpy"] == 5_285_854
    assert stage_1["order_ticket"] == {
        "broker": "楽天証券",
        "product_name": "eMAXIS Slim 全世界株式（オール・カントリー）",
        "account_type": "特定口座",
        "order_method": "投資信託の金額指定買付",
        "amount_jpy": 5_861_859,
        "point_use": "使わない",
        "distribution_course": "再投資型",
        "nisa_growth_quota_used_jpy": 0,
        "prospectus_action": "交付目論見書を確認し、同意チェックを入れる",
        "confirmation_screen": "省略せず、商品・口座・金額・ポイント不使用・再投資型・注文受付日を確認してから発注する",
    }
    assert stage_1["committed_amount_jpy"] == 5_861_859
    assert stage_1["uncommitted_reference_ceiling_jpy"] == 5_285_854
    assert stage_1["actual_order"]["status"] == "completed_filled"
    assert stage_1["actual_order"]["ordered_amount_jpy"] == 5_861_859
    assert stage_1["actual_order"]["allotted_units"] == 1_515_633
    assert stage_1["actual_order"]["execution_nav_jpy_per_10000_units"] == 38_676
    assert stage_1["execution_allowed"] is False
    assert stage_1["user_approval_status"] == "approved"
    stage_2a = act_s3_005["ready_followup_stage_proposals"][0]
    assert stage_2a["stage_id"] == "ACT-S3-005-STAGE-2A"
    assert stage_2a["status"] == "completed_filled"
    assert stage_2a["transferred_amount_jpy"] == 1_744_557
    assert stage_2a["observed_rakuten_buying_power_jpy"] == 1_946_765
    assert stage_2a["buying_power_excess_over_confirmed_transfer_jpy"] == 202_208
    assert stage_2a["excess_component_source"] is None
    assert stage_2a["proposed_purchase_amount_jpy"] == 1_946_765
    assert stage_2a["aggregate_reference_ceiling_remaining_after_stage_jpy"] == 3_339_089
    assert stage_2a["user_approval_status"] == "approved"
    assert stage_2a["actual_order"] == {
        "status": "completed_filled",
        "order_number": "1268",
        "order_placed_at": "2026-08-13T09:05:00+09:00",
        "ordered_amount_jpy": 1_946_765,
        "trade_date": "2026-08-14",
        "settlement_date": "2026-08-20",
        "fee_jpy": 0,
        "point_use_jpy": 0,
        "allotted_units": 498_928,
        "execution_nav_jpy_per_10000_units": 39_019,
        "settlement_amount_jpy": 1_946_765,
        "execution_confirmed_at": "2026-08-21",
        "transaction_ref": "transactions/ledger.yaml#rakuten-all-country-1946765-buy-fill-2026-08-14",
        "evidence_ref": "transactions/evidence/2026-08-21_rakuten_all_country_fills.yaml#fills.order_1268",
    }
    act_s3_005_order = act_s3_005["order_specification"]
    assert act_s3_005_order["status"] == "stage_1_stage_2a_stage_2b_completed_followup_cash_pending"
    stage_2b = act_s3_005["ready_followup_stage_proposals"][1]
    assert stage_2b["stage_id"] == "ACT-S3-005-STAGE-2B"
    assert stage_2b["actual_purchase_amount_jpy"] == 376_158
    assert stage_2b["aggregate_reference_ceiling_remaining_after_stage_jpy"] == 2_962_931
    assert stage_2b["actual_order"]["order_number"] == "1282"
    assert act_s3_005_order["order_type"] == "investment_fund_amount_order"
    assert act_s3_005_order["execution_allowed"] is False
    assert act_s3_005_order["user_approval_status"] == "approved"
    assert act_s3_010["reference_draft"]["reference_shares_to_sell"] == 14
    assert act_s3_010["reference_draft"]["executable"] is False

    act_s3_004 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-004")
    assert act_s3_004["reference_draft"] == {
        "as_of": "2026-08-09",
        "total_cash_and_deposits_jpy": 13_147_713,
        "proposed_emergency_fund_account": "三菱UFJ銀行 普通預金",
        "proposed_emergency_fund_jpy": 2_000_000,
        "proposed_mufg_excess_above_emergency_fund_jpy": 467_987,
        "reference_investable_cash_before_execution_adjustments_jpy": 11_147_713,
        "formula": "13,147,713円 - 生活防衛資金2,000,000円 = 11,147,713円",
        "executable": False,
        "execution_adjustments": [
            "現在残高",
            "未約定注文の拘束資金",
            "未受渡・未反映資金",
            "直近の確定支払額",
        ],
    }

    act_s3_005 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-005")
    assert act_s3_005["reference_draft"]["account_institution"] == "楽天証券"
    assert act_s3_005["reference_draft"]["account_type"] == (
        "特定口座（源泉徴収あり）"
    )
    assert act_s3_005["reference_draft"]["product_symbol"] == (
        "EMAXIS_SLIM_ALL_COUNTRY"
    )
    assert act_s3_005["reference_draft"]["purchase_method"] == (
        "投資信託の金額指定買付"
    )
    assert act_s3_005["reference_draft"]["nisa_growth_quota_status"] == (
        "exhausted"
    )
    assert act_s3_005["reference_draft"]["executable"] is False

    act_s3_006 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-006")
    assert act_s3_006["status"] == "completed"
    assert act_s3_006["completed_at"] == "2026-08-12"
    assert act_s3_006["actual_execution"]["portfolio_balance_after_sale_jpy"] == 0
    assert act_s3_006["actual_execution"]["previous_reported_proceeds_components_jpy"] == [
        7_346,
        302_820,
    ]
    assert act_s3_006["actual_execution"]["reported_proceeds_by_asset_jpy"] == {
        "XRP": 7_346,
        "BTC": 171_669,
        "ETH": 131_351,
    }
    assert act_s3_006["actual_execution"]["reported_proceeds_total_jpy"] == 310_366
    assert act_s3_006["actual_execution"]["per_asset_breakdown_status"] == (
        "user_reported_cash_amounts_not_tax_reconciled"
    )
    assert act_s3_006["reference_draft"]["total_market_value_jpy"] == 322_422
    assert act_s3_006["reference_draft"]["total_profit_loss_jpy"] == -96_091
    assert act_s3_006["reference_draft"]["total_implied_acquisition_cost_jpy"] == 418_513
    assert act_s3_006["reference_draft"]["tax_use_allowed"] is False
    crypto_inputs = {
        item["key"]: item for item in act_s3_006["human_actionability"]["required_inputs"]
    }
    assert crypto_inputs["crypto_snapshot_balance"]["availability"] == (
        "resolved_from_repository"
    )
    assert crypto_inputs["crypto_acquisition_history_evidence"]["availability"] == (
        "known_event_pending"
    )
    assert crypto_inputs["crypto_acquisition_history_evidence"]["blocking"] is False
    assert crypto_inputs["crypto_current_balance_and_sell_screen"]["availability"] == (
        "resolved_from_repository"
    )
    act_s3_007 = next(task for task in plan["tasks"] if task["id"] == "ACT-S3-007")
    assert act_s3_007["status"] == "completed"
    assert act_s3_007["actual_order"]["order_number"] == "1274"
    assert act_s3_007["actual_order"]["allotted_units"] == 204_329
    assert act_s3_007["actual_order"]["execution_nav_jpy_per_10000_units"] == 38_927
    assert act_s3_007["known_state"]["reported_yen_proceeds_jpy"] == 310_366
    assert act_s3_007["known_state"]["crypto_portfolio_balance_jpy"] == 0
    assert act_s3_007["known_state"]["transfer_to_broker_status"] == (
        "completed_credited_and_investable"
    )
    inputs = {
        item["key"]: item
        for item in act_s3_010["human_actionability"]["required_inputs"]
    }
    assert inputs["cibr_basis_position"]["availability"] == "resolved_from_repository"
    assert inputs["cibr_basis_position"]["request_from_user_if"] is None
    assert "cibr_position_and_order_delta" not in inputs
    assert inputs["cibr_settlement_details"]["availability"] == "resolved_from_repository"
    assert inputs["cibr_settlement_details"]["owner"] == "codex"
    assert inputs["cibr_settlement_details"]["blocking"] is False
    assert inputs["cibr_broker_order_capabilities"] == {
        "key": "cibr_broker_order_capabilities",
        "label": "楽天証券の米国株売却画面の入力項目と選択肢",
        "availability": "resolved_from_repository",
        "source_ref": "brokers/rakuten/us_equity_sell/versions/2026-08-10.yaml",
        "value_summary": "数量、指値／成行／逆指値／トレイリング、本日中、時間外、特定口座、円／ドル受取、米ドルMMF、暗証番号、確認画面省略を確認済み",
        "as_of": "2026-08-10",
        "refresh_rule": None,
        "request_from_user_if": None,
        "blocking": False,
        "owner": "codex",
        "verification_stage": "draft",
        "trigger_evidence": "ユーザ提供の楽天証券米国株売却画面を証拠転記済み",
        "scope": "security:CIBR",
    }


def test_act_s3_dashboard_makes_every_task_locally_actionable() -> None:
    dashboard = (ROOT / "ACT_S3_DASHBOARD.md").read_text(encoding="utf-8")
    section = dashboard.split("## 全タスク：次に誰が何をするか", 1)[1].split(
        "## 比率の分母", 1
    )[0]
    rows = [
        line
        for line in section.splitlines()
        if line.startswith("| ACT-S3-")
    ]

    assert len(rows) == 15
    assert {row.split()[1] for row in rows} == {
        f"ACT-S3-{index:03d}" for index in (*range(1, 13), *range(14, 17))
    }
    assert all(len([cell for cell in row.split("|") if cell.strip()]) == 4 for row in rows)

    act_s3_010_row = next(row for row in rows if row.startswith("| ACT-S3-010"))
    assert "Codex" in act_s3_010_row
    assert "CIBR 14株" in act_s3_010_row
    assert "全量約定・受渡完了" in act_s3_010_row
    assert "受渡代金222,956円" in act_s3_010_row
    assert "手数料1,111円" in act_s3_010_row
    assert "残り74株" in act_s3_010_row

    assert "### CIBR 14株の実行済み注文票" in dashboard
    assert "米ドルMMF自動買付" in dashboard
    assert "取引暗証番号" in dashboard

    assert "リポジトリで確認済みの情報をユーザへ再提出させません" in dashboard
    assert "全残高の再提出や「変化がないこと」の確認は不要" in dashboard
    assert "ユーザは次を提示してください" not in dashboard
    assert "2026-08-09後にCIBRの売買・入出庫があったか" not in dashboard
    assert "現在、CIBRの未反映注文または拘束数量があるか" not in dashboard
    assert "全売買共通の注文入力時プリフライト" in dashboard
    assert "### ACT-S3-005 第1段階注文（約定済み）" in dashboard
    assert "5,861,859円" in dashboard
    assert "5,285,854円" in dashboard
    assert "ポイント不使用" in dashboard
    assert "三菱UFJ銀行の467,987円は移管しません" in dashboard
    assert "調整後の未投入参考上限2,494,944円" in dashboard
    assert "1,515,633口、1万口当たり基準価額38,676円" in dashboard
    assert "### 暗号資産の全売却結果" in dashboard
    assert "暗号資産ポートフォリオ残高は**0円**" in dashboard
    assert "XRP 7,346円＋BTC 171,669円＋ETH 131,351円＝310,366円" in dashboard
    assert "今回報告されたコア買付注文額は**795,390円**" in dashboard
    assert "### 2026年の損益通算利用方針" in dashboard
    assert "暫定譲渡損失合計 **485,831円**" in dashboard
    assert "日産の受渡金額は**34,445円**" in dashboard
    assert "野村2銘柄の売却代金485,024円も楽天証券へ入金済み" in dashboard
    assert "795,390円で楽天証券・特定口座" in dashboard
    assert "204,329口、1万口当たり基準価額38,927円" in dashboard
    assert "楽天証券内で確認された余剰現金はすべてオルカンへ投入済み" in dashboard
    assert "### ACT-S3-005 第2A段階（約定済み）" in dashboard
    assert "野村證券に以前からあった流動現金 **1,744,557円**" in dashboard
    assert "現在の楽天証券買付可能額は **1,946,765円**" in dashboard
    assert "注文番号1268" in dashboard
    assert "## 実行ガードレール（ユーザの「やること」ではない）" in dashboard
    assert "旧ACT-S3-013" in dashboard
    assert not any(row.startswith("| ACT-S3-013") for row in rows)


def test_act_s3_dashboard_status_summary_matches_plan_machine_state() -> None:
    plan = load_yaml(ROOT / "plans/2026/2026-08-09_act_s3_execution.yaml")
    dashboard = (ROOT / "ACT_S3_DASHBOARD.md").read_text(encoding="utf-8")
    section = dashboard.split("## いまの状況", 1)[1].split(
        "## いま並行して進めるレーン", 1
    )[0]
    summary: dict[str, set[str]] = {}
    for line in section.splitlines():
        if not line.startswith("|") or "ACT-S3-" not in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        category, stated_count, targets = cells
        task_ids = set(re.findall(r"ACT-S3-\d{3}", targets))
        assert int(stated_count) == len(task_ids)
        summary[category] = task_ids

    expected: dict[str, set[str]] = {
        "完了": set(),
        "進行中・継続中": set(),
        "前提・イベント待ち": set(),
    }
    for task in plan["tasks"]:
        task_id = task["id"]
        status = task["status"]
        if status == "completed":
            category = "完了"
        elif status in {"ongoing", "in_progress", "collecting"}:
            category = "進行中・継続中"
        else:
            category = "前提・イベント待ち"
        expected[category].add(task_id)

    assert summary == expected
    all_listed = set().union(*summary.values())
    assert all_listed == {task["id"] for task in plan["tasks"]}
    assert sum(len(task_ids) for task_ids in summary.values()) == 15


def test_invalid_semiconductor_threshold_order_is_rejected() -> None:
    strategy = deepcopy(load_current_strategy(ROOT))
    strategy["risk_limits"]["direct_themes"]["semiconductor"]["rebalance_proposal_above_pct"] = 0.10

    with pytest.raises(StrategyPolicyError, match="semiconductor rebalance trigger"):
        validate_strategy_policy(strategy)


def test_cash_redeployment_plan_preserves_the_approved_reserve() -> None:
    plan = load_yaml(ROOT / "plans/2026/2026-07-25_cash_redeployment.yaml")
    liquidity = plan["basis"]["liquidity_jpy"]
    reserve = plan["allocations"]["hobby_dip_buy_reserve"]["amount_jpy"]
    core_purchase = plan["allocations"]["broad_core_lump_sum"]["planned_amount_jpy"]
    projection = plan["projection_if_executed_at_basis_amounts"]

    assert liquidity - reserve == core_purchase
    assert projection["broad_core_after_jpy"] == projection["broad_core_before_jpy"] + core_purchase
    assert projection["active_hobby_after_reserve_jpy"] == (
        projection["active_hobby_before_reserve_jpy"] + reserve
    )
    assert plan["basis"]["total_assets_jpy"] == (
        projection["broad_core_before_jpy"]
        + projection["active_hobby_before_reserve_jpy"]
        + liquidity
        + projection["residual_other_jpy"]
        + projection["unreconciled_snapshot_rounding_jpy"]
    )
