from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from monthly_limit_order_review.repository_records import (
    RepositoryIntegrityError,
    _audit_financial_unknowns_against_strategy,
    _audit_task_execution_contract,
    _audit_transaction_ledger,
    audit_repository,
    load_recurring_contribution_context,
)
from monthly_limit_order_review.storage import (
    default_output_paths,
    load_yaml,
    on_demand_output_paths,
    write_yaml,
)


ROOT = Path(__file__).resolve().parents[1]


def _resolved_input() -> dict:
    return {
        "key": "latest_balance",
        "label": "最新残高",
        "availability": "resolved_from_repository",
        "source_ref": "data/normalized/snapshot_2026_08.yaml",
        "value_summary": "基準残高あり",
        "as_of": "2026-08-09",
        "refresh_rule": None,
        "request_from_user_if": None,
        "blocking": False,
        "owner": "codex",
        "verification_stage": "draft",
        "trigger_evidence": "基準スナップショットに記録済み",
        "scope": "portfolio",
    }


def test_repository_audit_has_no_errors() -> None:
    issues = audit_repository(ROOT)

    assert [issue for issue in issues if issue["severity"] == "error"] == []


def test_audit_rejects_financial_unknowns_already_resolved_by_strategy() -> None:
    issues: list[dict[str, str]] = []

    _audit_financial_unknowns_against_strategy(
        {
            "unknown_information": [
                "投資待機資金の目標比率",
                "サテライトの目標比率、対象銘柄、単一テーマ・単一銘柄上限",
                "公的年金の個人別確定見込額",
            ]
        },
        {"allocation": {"status": "approved"}},
        issues,
    )

    assert [issue["code"] for issue in issues] == [
        "financial_unknowns_conflict_with_approved_strategy"
    ]
    assert "公的年金" not in issues[0]["message"]


def test_rakuten_us_sell_capability_pointer_preserves_screen_scope() -> None:
    pointer = load_yaml(ROOT / "brokers/rakuten/us_equity_sell/current.yaml")
    capability = load_yaml(ROOT / pointer["active_capability_path"])

    assert capability["capability_id"] == pointer["active_capability_id"]
    assert capability["screen_fields"]["price_type"]["observed_options"] == [
        "limit",
        "market",
        "stop",
        "trailing",
    ]
    assert capability["screen_fields"]["settlement_currency"]["observed_options"] == [
        "JPY",
        "USD",
    ]
    assert capability["scope_limits"]["evidence_screen_symbol"] == "PLTR"
    assert "available_quantity" in capability["scope_limits"]["do_not_reuse_from_evidence"]


def test_normalized_snapshot_pointer_and_raw_index_cover_latest_snapshot() -> None:
    pointer = load_yaml(ROOT / "data/normalized/current.yaml")
    raw_index = load_yaml(ROOT / "data/raw/index.yaml")

    snapshots = [
        (path, load_yaml(path))
        for path in (ROOT / "data/normalized").glob("snapshot_20??_??.yaml")
    ]
    latest_path, latest = max(snapshots, key=lambda item: item[1]["snapshot_date"])
    assert pointer["active_snapshot_path"] == latest_path.relative_to(ROOT).as_posix()
    assert pointer["active_snapshot_date"] == latest["snapshot_date"]
    latest_raw = next(
        entry
        for entry in raw_index["entries"]
        if entry["normalized_snapshot_ref"] == pointer["active_snapshot_path"]
    )
    assert latest_raw["snapshot_date"] == latest["snapshot_date"]
    for evidence_ref in latest_raw.get("partial_evidence_refs", []):
        assert (ROOT / evidence_ref).is_file()


def test_historical_crypto_evidence_is_preserved() -> None:
    raw_index = load_yaml(ROOT / "data/raw/index.yaml")
    historical_raw = next(
        entry
        for entry in raw_index["entries"]
        if entry["normalized_snapshot_ref"] == "data/normalized/snapshot_2026_08.yaml"
    )
    assert historical_raw == {
        "normalized_snapshot_ref": "data/normalized/snapshot_2026_08.yaml",
        "snapshot_date": "2026-08-09",
        "raw_evidence_in_repository": False,
        "evidence_status": "partial_crypto_summary_persisted_other_sources_external",
        "partial_evidence_refs": [
            "data/raw/evidence/2026-08-09_crypto_summary.json"
        ],
        "partial_evidence_scope": {
            "confirmed": [
                "BTC・ETH・XRPの円評価額",
                "BTC・ETH・XRPの評価損益",
                "画面表示時刻17:25",
            ],
            "not_confirmed": ["利用サービス", "数量", "取得履歴", "注文画面仕様"],
        },
    }
    crypto_evidence = load_yaml(
        ROOT / "data/raw/evidence/2026-08-09_crypto_summary.json"
    )
    assert crypto_evidence["portfolio"]["current_value"] == 322_422
    assert crypto_evidence["portfolio"]["profit_loss"] == -96_091
    assert {
        item["symbol"]: item["current_value"]
        for item in crypto_evidence["assets"]
    } == {"BTC": 177_410, "ETH": 137_310, "XRP": 7_702}


def test_confirmed_fills_are_recorded_without_inventing_missing_dates_or_costs() -> None:
    ledger = load_yaml(ROOT / "transactions/ledger.yaml")
    evidence = load_yaml(ROOT / "transactions/evidence/2026-08-10_nomura_fills.yaml")
    nissan_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-10_rakuten_7201_fill.yaml"
    )
    nissan_settlement_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-12_rakuten_7201_settlement.yaml"
    )
    nomura_settlement_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-12_nomura_9444_2353_settlements.yaml"
    )
    cibr_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-12_rakuten_cibr_fill.yaml"
    )
    cibr_settlement_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-21_rakuten_cibr_settlement.yaml"
    )
    smh_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-12_rakuten_smh_fill.yaml"
    )
    smh_proceeds_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-13_rakuten_smh_proceeds_details.yaml"
    )
    smh_settlement_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-14_rakuten_smh_settlement.yaml"
    )
    transactions = {
        item["transaction_id"]: item for item in ledger["transactions"]
    }
    all_country_order = transactions[
        "rakuten-all-country-795390-buy-order-2026-08-14"
    ]
    all_country_stage1 = transactions[
        "rakuten-all-country-5861859-buy-fill-2026-08-12"
    ]
    all_country_stage2a = transactions[
        "rakuten-all-country-1946765-buy-fill-2026-08-14"
    ]
    cash_transfer = transactions[
        "nomura-existing-cash-1744557-transfer-to-rakuten-2026-08-13"
    ]
    xrp_transfer = transactions[
        "crypto-xrp-proceeds-transfer-to-rakuten-2026-08-14"
    ]
    btc_transfer = transactions[
        "crypto-btc-proceeds-transfer-to-rakuten-2026-08-14"
    ]
    eth_transfer = transactions[
        "crypto-eth-proceeds-transfer-to-rakuten-2026-08-14"
    ]
    nomura_sale_transfer = transactions[
        "nomura-9444-2353-proceeds-transfer-to-rakuten-2026-08-14"
    ]

    toshin = transactions["nomura-79153-9444-sell-fill"]
    parking = transactions["nomura-79152-2353-sell-fill"]
    nissan = transactions["rakuten-1261-7201-sell-fill"]
    crypto = transactions["crypto-btc-eth-xrp-full-liquidation-2026-08-12"]
    cibr = transactions["rakuten-1266-cibr-sell-fill"]
    smh = transactions["rakuten-1262-smh-sell-fill"]
    cibr_fx = transactions["rakuten-1275-usd-jpy-exchange-cibr-2026-08-21"]
    smh_fx = transactions["rakuten-1276-usd-jpy-exchange-smh-2026-08-21"]
    excess_cash_buy = transactions["rakuten-all-country-376158-buy-fill-2026-08-28"]
    smh_redeployment_buy = transactions["rakuten-all-country-92602-buy-fill-2026-08-26"]
    cibr_redeployment_buy = transactions["rakuten-all-country-222956-buy-fill-2026-08-25"]
    annual = load_yaml(ROOT / "transactions/tax/2026.yaml")
    annual_sales = {
        item["transaction_ref"]: item for item in annual["sales"]
    }
    assert annual["same_year_listed_stock_loss_offset"][
        "provisional_loss_available_jpy"
    ] == 485_831
    assert all_country_order["transaction_type"] == "buy"
    assert all_country_order["ordered_amount_jpy"] == 795_390
    assert all_country_order["account"]["account_type"] == "特定口座"
    assert all_country_order["order_status"] == "completed_filled"
    assert all_country_order["quantity"] == 204_329
    assert all_country_order["price_jpy_per_10000_units"] == 38_927
    assert all_country_order["plan_task_associations"] == ["ACT-S3-007", "ACT-S3-014"]
    assert all_country_order["funding_source_context"]["exact_yen_allocation"] is None
    assert "日産自動車売却代金" in all_country_order["funding_source_context"]["sources"]
    assert all_country_stage1["order"]["order_number"] == "1263"
    assert all_country_stage1["quantity"] == 1_515_633
    assert all_country_stage1["price_jpy_per_10000_units"] == 38_676
    assert all_country_stage2a["order"]["order_number"] == "1268"
    assert all_country_stage2a["quantity"] == 498_928
    assert all_country_stage2a["price_jpy_per_10000_units"] == 39_019
    assert annual["same_year_listed_stock_loss_offset"]["security_selection_authorized"] is False
    assert cash_transfer["transaction_type"] == "transfer"
    assert cash_transfer["amount_jpy"] == 1_744_557
    assert cash_transfer["from_account"]["institution"] == "野村證券"
    assert cash_transfer["account"]["institution"] == "楽天証券"
    assert cash_transfer["excluded_sale_proceeds_jpy"] == 485_024
    assert cash_transfer["fee_jpy"] is None
    assert [
        xrp_transfer["net_amount_jpy"],
        btc_transfer["net_amount_jpy"],
        eth_transfer["net_amount_jpy"],
        nomura_sale_transfer["net_amount_jpy"],
    ] == [7_346, 171_669, 131_351, 485_024]
    assert sum(
        transfer["net_amount_jpy"]
        for transfer in (xrp_transfer, btc_transfer, eth_transfer, nomura_sale_transfer)
    ) == 795_390
    latest_transfer_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-14_sale_proceeds_transfers_to_rakuten.yaml"
    )
    assert latest_transfer_evidence["aggregate"]["crypto_credited_jpy"] == 310_366
    assert latest_transfer_evidence["aggregate"]["total_credited_jpy"] == 795_390
    assert latest_transfer_evidence["reconciliation"]["difference_jpy"] == 200
    transfer_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-13_nomura_existing_cash_transfer_to_rakuten.yaml"
    )
    assert transfer_evidence["transfer"]["destination_credit_status"] == (
        "credited_and_investable"
    )
    assert transfer_evidence["rakuten_buying_power_after_transfer"]["amount_jpy"] == (
        1_946_765
    )
    assert transfer_evidence["rakuten_buying_power_after_transfer"]["composition"][
        "remaining_component_source"
    ] is None
    stage2a_evidence = load_yaml(
        ROOT / "transactions/evidence/2026-08-13_rakuten_all_country_stage2a_order.yaml"
    )
    assert stage2a_evidence["order"]["order_number"] == "1268"
    assert stage2a_evidence["order"]["status"] == "accepted_pending_allotment"
    assert stage2a_evidence["record_status"] == "superseded_by_later_fill_screen"
    assert stage2a_evidence["order"]["ordered_amount_jpy"] == 1_946_765
    assert stage2a_evidence["order"]["trade_date"] == "2026-08-14"
    assert stage2a_evidence["order"]["settlement_date"] == "2026-08-20"
    assert stage2a_evidence["order"]["fee_jpy"] == 0
    assert annual["same_year_listed_stock_loss_offset"]["reported_gain_transactions"] == [
        {
            "transaction_ref": "transactions/ledger.yaml#rakuten-1262-smh-sell-fill",
            "decision_ref": "decisions/2026-08-13_include_smh_gain_in_2026_offset.yaml",
            "direction": "gain_user_confirmed",
            "realized_gain_loss_jpy": None,
            "status": "amount_pending_tax_details_or_annual_statement",
        }
    ]

    assert toshin["quantity"] == 1500
    assert toshin["price_jpy"] == 307
    assert toshin["gross_proceeds_jpy"] == 460_500
    assert parking["quantity"] == 100
    assert parking["price_jpy"] == 252
    assert parking["gross_proceeds_jpy"] == 25_200
    assert nissan["quantity"] == 100
    assert nissan["price_jpy"] == 345
    assert nissan["gross_proceeds_jpy"] == 34_500
    assert nissan["commission_before_tax_jpy"] == 50
    assert nissan["commission_tax_jpy"] == 5
    assert nissan["fee_jpy"] == 55
    assert nissan["trade_date"] == "2026-08-10"
    assert nissan["settlement_date"] == "2026-08-13"
    assert nissan["net_proceeds_jpy"] == 34_445
    assert nissan["acquisition_cost_jpy"] == 36_800
    assert nissan["realized_gain_loss_jpy"] == -2_355
    assert nissan["tax_record"]["status"] == "settlement_recorded"
    assert crypto["previous_reported_proceeds_components_jpy"] == [7_346, 302_820]
    assert crypto["previous_reported_proceeds_total_jpy"] == 310_166
    assert crypto["reported_proceeds_by_asset_jpy"] == {
        "XRP": 7_346,
        "BTC": 171_669,
        "ETH": 131_351,
    }
    assert crypto["reported_proceeds_total_jpy"] == 310_366
    assert crypto["latest_report_difference_jpy"] == 200
    assert crypto["balance_after_sale_jpy"] == 0
    assert crypto["gross_proceeds_jpy"] is None
    assert crypto["net_proceeds_jpy"] is None
    assert crypto["tax_record"]["filing_category"] == "crypto_misc_income"
    assert annual_sales[
        "transactions/ledger.yaml#crypto-btc-eth-xrp-full-liquidation-2026-08-12"
    ]["missing_fields"] == crypto["tax_record"]["missing_fields"]
    assert cibr["trade_date"] == "2026-08-13"
    assert cibr["settlement_date"] == "2026-08-17"
    assert cibr["quantity"] == 14
    assert cibr["price_usd"] is None
    assert cibr["displayed_settlement_amount_jpy"] == 222_956
    assert cibr["user_attributed_proceeds_usd"] == 1_404.00
    assert cibr["net_proceeds_jpy"] is None
    assert cibr["fee_jpy"] == 1_111
    assert cibr["order"]["ordered_quantity"] == 14
    assert cibr["order"]["filled_quantity"] == 14
    assert cibr["order"]["unfilled_quantity"] == 0
    assert cibr_evidence["fill"]["status"] == "filled"
    assert cibr_settlement_evidence["settlement"]["settlement_amount_jpy"] == 222_956
    assert cibr_settlement_evidence["settlement"]["fee_jpy"] == 1_111
    assert cibr["tax_record"]["status"] == "settlement_recorded"
    assert cibr_fx["source_amount_usd"] == 1_404.00
    assert cibr_fx["applied_exchange_rate_jpy_per_usd"] == 158.838
    assert cibr_fx["settlement_amount_jpy"] == 222_956
    assert smh_fx["source_amount_usd"] == 582.92
    assert smh_fx["applied_exchange_rate_jpy_per_usd"] == 158.859
    assert smh_fx["settlement_amount_jpy"] == 92_602
    assert excess_cash_buy["ordered_amount_jpy"] == 376_158
    assert excess_cash_buy["quantity"] == 96_843
    assert excess_cash_buy["price_jpy_per_10000_units"] == 38_842
    assert smh_redeployment_buy["ordered_amount_jpy"] == 92_602
    assert smh_redeployment_buy["quantity"] == 23_987
    assert cibr_redeployment_buy["ordered_amount_jpy"] == 222_956
    assert cibr_redeployment_buy["quantity"] == 57_955
    assert annual_sales[
        "transactions/ledger.yaml#rakuten-1266-cibr-sell-fill"
    ]["missing_fields"] == cibr["tax_record"]["missing_fields"]
    assert smh["trade_date"] == "2026-08-12"
    assert smh["settlement_date"] == "2026-08-14"
    assert smh["quantity"] == 1
    assert smh["order_price_usd"] == 583.49
    assert smh["price_usd"] == 585.83
    assert smh["gross_proceeds_usd"] == 585.83
    assert smh["net_proceeds_usd"] == 582.92
    assert smh["fee_usd"] == 2.91
    assert smh["displayed_exchange_rate_jpy_per_usd"] == 159.140
    assert smh["gross_minus_net_proceeds_usd"] == 2.91
    assert smh["displayed_values_reconciliation_status"] == "resolved"
    assert smh["realized_gain_loss_direction"] == "gain_user_confirmed"
    assert smh["realized_gain_loss_jpy"] is None
    assert smh_evidence["fill"]["filled_quantity"] == 1
    assert smh_proceeds_evidence["displayed_transaction"][
        "displayed_settlement_amount_usd"
    ] == 582.92
    assert smh_proceeds_evidence["displayed_transaction"]["displayed_fee_usd"] == 2.91
    assert smh_proceeds_evidence["record_status"] == "superseded_by_later_settlement_screen"
    assert smh_settlement_evidence["settlement"]["execution_price_usd"] == 585.83
    assert smh_settlement_evidence["settlement"]["net_settlement_amount_usd"] == 582.92
    assert smh["tax_record"]["status"] == "settlement_recorded"
    assert annual_sales[
        "transactions/ledger.yaml#rakuten-1262-smh-sell-fill"
    ]["missing_fields"] == smh["tax_record"]["missing_fields"]
    for transaction in (toshin, parking):
        assert transaction["trade_date"] == "2026-08-10"
        assert transaction["settlement_date"] == "2026-08-13"
        assert transaction["fee_jpy"] is None
        assert transaction["tax_jpy"] is None
        assert transaction["net_proceeds_jpy"] is not None
        assert transaction["tax_record"]["status"] == "settlement_recorded"
        assert transaction["tax_record"]["annual_record_ref"] == (
            "transactions/tax/2026.yaml"
        )
        annual_ref = f"transactions/ledger.yaml#{transaction['transaction_id']}"
        assert annual_sales[annual_ref]["missing_fields"] == (
            transaction["tax_record"]["missing_fields"]
        )

    assert toshin["acquisition_cost_jpy"] == 942_000
    assert toshin["realized_gain_loss_jpy"] == -482_024
    assert parking["acquisition_cost_jpy"] == 26_500
    assert parking["realized_gain_loss_jpy"] == -1_452
    assert nomura_settlement_evidence["aggregate"]["liquid_cash_confirmed_jpy"] == 485_024
    assert nomura_settlement_evidence["provisional_realized_losses"]["total_jpy"] == -483_476

    assert evidence["interpretation_limits"] == [
        "注文日時は表示されているが、約定日は表示されていない",
        "注文期間2026-08-19を約定日または受渡日として扱わない",
        "手数料、税、受渡日は表示されていない",
    ]
    assert nissan["tax_jpy"] is None
    assert annual_sales[
        "transactions/ledger.yaml#rakuten-1261-7201-sell-fill"
    ]["missing_fields"] == nissan["tax_record"]["missing_fields"]
    assert nissan_settlement_evidence["settlement"]["net_settlement_amount_jpy"] == 34_445
    assert nissan_settlement_evidence["settlement"]["commission_before_tax_jpy"] == 50
    assert nissan_settlement_evidence["settlement"]["commission_tax_jpy"] == 5
    assert nissan_evidence["interpretation_limits"] == [
        "注文日時は表示されているが、約定日は表示されていない",
        "注文期限2026-08-20を約定日または受渡日として扱わない",
        "受渡日、取得費、源泉徴収税、実現損益、純受取額は表示されていない",
    ]


def test_transaction_audit_rejects_sale_without_annual_tax_tracking(
    tmp_path: Path,
) -> None:
    transaction_dir = tmp_path / "transactions"
    transaction_dir.mkdir()
    write_yaml(
        transaction_dir / "ledger.yaml",
        {
            "transactions": [
                {
                    "transaction_id": "sale-without-tax-record",
                    "status": "confirmed",
                    "transaction_type": "sell",
                    "trade_date": "2026-08-10",
                    "account": {"account_type": "general_taxable"},
                    "currency": "JPY",
                    "source_evidence": "evidence.yaml",
                }
            ]
        },
    )
    issues: list[dict[str, str]] = []

    _audit_transaction_ledger(tmp_path, issues)

    assert {issue["code"] for issue in issues} == {"sale_tax_record_missing"}


def test_recurring_contributions_load_from_versioned_plan_not_legacy_config() -> None:
    context = load_recurring_contribution_context(ROOT)

    assert context["legacy_fallback"] is False
    assert context["source_path"] == "plans/recurring/versions/2026-08-09.yaml"
    assert context["record"]["record_type"] == "observed_recurring_contribution_state"
    assert context["contributions"]["total_monthly_jpy"] == 100000


def test_recurring_pointer_cannot_escape_repository(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "core_recurring_contributions.yaml").write_text(
        'source_of_truth_ref: "../outside.yaml"\n',
        encoding="utf-8",
    )

    with pytest.raises(RepositoryIntegrityError, match="within the repository"):
        load_recurring_contribution_context(tmp_path)


def test_task_plan_audit_rejects_implicit_denominator_and_missing_order_settings() -> None:
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "ETFを3%へ縮小",
                    "action_kind": "sell",
                    "allocation_effect": "target_ratio",
                    "human_actionability": {
                        "actor": "codex_and_user",
                        "next_action": "最新情報を渡して注文案を作る",
                        "required_inputs": [_resolved_input()],
                        "decision_needed": "注文方式",
                        "decision_support_owner": "Codex",
                        "unblock_condition": "注文案をユーザが承認",
                        "completion_evidence": ["約定明細"],
                    },
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_allocation_basis_missing",
        "task_order_specification_missing",
    }


def test_task_plan_audit_rejects_prohibition_only_hold_task() -> None:
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "waiting",
                    "action": "ETFを買わない",
                    "action_kind": "hold",
                    "allocation_effect": "none",
                    "human_actionability": {
                        "actor": "user",
                        "next_action": "買い注文を出さない",
                        "required_inputs": [],
                        "decision_needed": None,
                        "decision_support_owner": None,
                        "unblock_condition": "後続判定の完了",
                        "completion_evidence": ["買い注文なし"],
                    },
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_prohibition_only_control_invalid"
    }


def test_task_plan_audit_allows_explicit_pending_order_only_when_not_executable() -> None:
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "ETFを長期運用資産の3%へ縮小",
                    "action_kind": "sell",
                    "allocation_effect": "target_ratio",
                    "allocation_basis": {
                        "denominator": "long_term_investable_assets_jpy",
                        "denominator_definition_ref": "strategy/current.yaml",
                        "measurement_time": "execution_time",
                        "targets": [
                            {
                                "numerator": "ETF_market_value_jpy",
                                "relation": "approximately_equal",
                                "value": 0.03,
                            }
                        ],
                    },
                    "order_specification": {
                        "status": "pending_execution_time_configuration",
                        "execution_allowed": False,
                        "account_type": "特定口座",
                        "side": "sell",
                        "quantity_rule": "実行時に再計算",
                        "order_type": "pending_user_approval",
                        "limit_price_rule": None,
                        "timing": "実行時に指定",
                        "expiration": "実行時に指定",
                        "partial_fill_handling": "実行時に指定",
                        "unfilled_or_expired_reorder_rule": "再承認",
                        "proceeds_destination": "全世界株式コア",
                        "pretrade_tax_check": "取得価額を確認",
                        "user_approval_required": True,
                        "user_approval_status": "pending",
                    },
                    "human_actionability": {
                        "actor": "codex_and_user",
                        "next_action": "最新情報を渡して注文案を作る",
                        "required_inputs": [_resolved_input()],
                        "decision_needed": "注文方式",
                        "decision_support_owner": "Codex",
                        "unblock_condition": "注文案をユーザが承認",
                        "completion_evidence": ["約定明細"],
                    },
                }
            ]
        },
        issues,
    )

    assert issues == []


def test_task_plan_audit_rejects_unstructured_required_input() -> None:
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "残高を確認する",
                    "action_kind": "calculate",
                    "allocation_effect": "cash_amount",
                    "human_actionability": {
                        "actor": "codex_and_user",
                        "next_action": "既知値を確認して差分だけ更新する",
                        "required_inputs": ["最新残高"],
                        "decision_needed": None,
                        "decision_support_owner": None,
                        "unblock_condition": "差分確認完了",
                        "completion_evidence": ["計算結果"],
                    },
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_input_resolution_unstructured"
    }


def test_task_plan_audit_rejects_user_resubmission_of_repository_input() -> None:
    repository_input = _resolved_input()
    repository_input["request_from_user_if"] = "ユーザへ再提出を求める"
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "残高を確認する",
                    "action_kind": "calculate",
                    "allocation_effect": "cash_amount",
                    "human_actionability": {
                        "actor": "codex_and_user",
                        "next_action": "既知値を再利用する",
                        "required_inputs": [repository_input],
                        "decision_needed": None,
                        "decision_support_owner": None,
                        "unblock_condition": "確認完了",
                        "completion_evidence": ["計算結果"],
                    },
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_repository_input_contract_invalid"
    }


def test_task_plan_audit_allows_nonblocking_order_entry_preflight() -> None:
    preflight = {
        "key": "current_quantity_and_duplicate_orders",
        "label": "現在数量と重複注文",
        "availability": "verify_at_execution",
        "source_ref": "data/normalized/snapshot_2026_08.yaml",
        "value_summary": "基準数量あり",
        "as_of": "2026-08-09",
        "refresh_rule": "具体的注文を入力するときに注文画面で確認",
        "request_from_user_if": None,
        "blocking": False,
        "owner": "user_and_external_broker",
        "verification_stage": "order_entry",
        "trigger_evidence": "具体的注文案が承認された",
        "scope": "all_buy_and_sell_tasks",
    }
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "注文案を作る",
                    "action_kind": "calculate",
                    "allocation_effect": "cash_amount",
                    "human_actionability": {
                        "actor": "codex",
                        "next_action": "Codexが注文案を作る",
                        "required_inputs": [preflight],
                        "decision_needed": None,
                        "decision_support_owner": None,
                        "unblock_condition": "注文案完成",
                        "completion_evidence": ["注文案"],
                    },
                }
            ]
        },
        issues,
    )

    assert issues == []


def test_task_plan_audit_rejects_generic_staleness_as_input_state() -> None:
    generic_question = _resolved_input()
    generic_question.update(
        {
            "availability": "stale_refresh_required",
            "refresh_rule": "変化がないか聞く",
            "request_from_user_if": "論理的に変更可能だから聞く",
            "blocking": True,
            "owner": "user",
            "verification_stage": "draft",
            "trigger_evidence": "具体的証拠なし",
            "scope": "security:CIBR",
        }
    )
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "注文案を作る",
                    "action_kind": "calculate",
                    "allocation_effect": "cash_amount",
                    "human_actionability": {
                        "actor": "codex_and_user",
                        "next_action": "ユーザへ変更がないか聞く",
                        "required_inputs": [generic_question],
                        "decision_needed": None,
                        "decision_support_owner": None,
                        "unblock_condition": "否定確認完了",
                        "completion_evidence": ["回答"],
                    },
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_input_resolution_availability_invalid"
    }


def test_task_plan_audit_rejects_state_without_human_next_action() -> None:
    issues: list[dict[str, str]] = []
    _audit_task_execution_contract(
        "plans/2026/test.yaml",
        {
            "tasks": [
                {
                    "id": "ACT-TEST-001",
                    "status": "not_started",
                    "action": "残高を確認する",
                    "action_kind": "calculate",
                    "allocation_effect": "cash_amount",
                }
            ]
        },
        issues,
    )

    assert {issue["code"] for issue in issues} == {
        "task_plan_core_fields_missing"
    }


def test_generated_outputs_are_routed_under_reports() -> None:
    monthly = default_output_paths(ROOT, "2026_08")
    on_demand = on_demand_output_paths(
        ROOT,
        datetime(2026, 7, 26, 12, 0, tzinfo=UTC),
    )

    assert monthly["computation"] == (
        ROOT / "reports/generated/monthly/2026_08/computation.yaml"
    )
    assert monthly["review_prompt"] == (
        ROOT / "reports/generated/monthly/2026_08/review_request.md"
    )
    assert on_demand["market_data"] == (
        ROOT
        / "reports/generated/on_demand/2026/2026_07_26T120000Z/market_data.yaml"
    )
    assert on_demand["prompt"] == (
        ROOT
        / "reports/generated/on_demand/2026/2026_07_26T120000Z/health_check_request.md"
    )
    assert on_demand["response"] == (
        ROOT
        / "reports/generated/on_demand/2026/2026_07_26T120000Z/health_check_response.yaml"
    )
