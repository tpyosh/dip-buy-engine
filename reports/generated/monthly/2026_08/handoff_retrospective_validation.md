# ChatGPT月次レビューハンドオフ改善の検証

- validation_date: 2026-07-26
- sandbox_root: /tmp/stock-sandbox.4OhoyN
- canonical_repository: /Users/tappeiyoshida/projects/stock
- canonical_write_performed_during_sandbox_run: false
- promotion_to_canonical_after_user_authorization: true
- external_service_write_performed: false

## 原因

1. 自己完結を否定指示だけで表現し、周辺会話にある古い外部ファイル情報より本文を優先する契約と、最終出力の禁止事項が不足していた。
2. active planの承認時履歴値と現在スナップショット再計算値について、基準日、役割、比較規則、不変条件が近接表示されていなかった。
3. `must`へ入れてよい根拠を限定せず、現行source of truthにない新規ガバナンス提案が承認済み計画の欠陥へ格上げされた。
4. 住宅ローンの当初借入額と現在残高のラベルが不十分だった。
5. 生成依頼の自己完結性だけを検査し、ChatGPT応答のinstruction-followingを検査していなかった。

## 実装した改善

- テンプレートに、周辺会話からの隔離、金額セマンティクス、severity、住宅ローン、正確な商品名、一次情報リンク、回答終端の契約を追加した。
- 計算結果と生成プロンプトに次のactive plan項目を追加した。
  - 承認時のbasis snapshot date、現金、計画額
  - current snapshot date、再計算額
  - 差額
  - 差が期待されるか
  - historical basisを上書きしてはならないこと
- ChatGPT応答に外部ファイル名・再アップロード案内、またはactive plan履歴値と現在値の誤統合があればparser warningを出すlintを追加した。
- 実際のChatGPT応答を回帰入力として確認し、次の3警告を検出した。
  - `Self-contained review mentions an external data file or asks for re-upload.`
  - `Review may misclassify the historical active-plan basis amount and current recalculation as fields that must be equal.`
  - `Review contains content after the final Codex summary code block.`

## 実データ再生成結果

- active_plan_basis_snapshot_date: 2026-06-28
- active_plan_basis_planned_amount_jpy: 12620505
- active_plan_current_snapshot_date: 2026-07-26
- active_plan_current_recalculated_amount_jpy: 12622664
- active_plan_amount_delta_jpy: 2159
- active_plan_amount_difference_expected: true
- active_plan_historical_basis_must_not_be_overwritten: true

## 検証結果

- 全テスト: 90 passed
- repository-audit: passed with 0 warnings
- `data/history/`: 正本とサンドボックスで差分なし
- `prompts/generated/`: 正本とサンドボックスで差分なし
- `transactions/ledger.yaml`: 正本とサンドボックスで一致
- `strategy/current.yaml`: 正本とサンドボックスで一致
- `plans/2026/2026-07-25_cash_redeployment.yaml`: 正本とサンドボックスで一致

## 正本のgit status --short

以下は検証終了時の読取結果であり、既存の未コミット変更はユーザー作業として保護した。

```text
 M .gitignore
 M README.md
 M SPEC.md
 M config/allocation_rules.yaml
 M config/buy_rules.yaml
 M config/core_recurring_contributions.yaml
 M config/portfolio_policy.yaml
 M config/tickers.yaml
 M prompts/moneyforward_normalization_prompt.md
 M prompts/templates/moneyforward_monthly_session_start_prompt.md
 M src/monthly_limit_order_review/cli.py
 M src/monthly_limit_order_review/market_data.py
 M src/monthly_limit_order_review/models.py
 M src/monthly_limit_order_review/portfolio_metrics.py
 M src/monthly_limit_order_review/prompt_renderer.py
 M src/monthly_limit_order_review/rules.py
 M src/monthly_limit_order_review/storage.py
 M src/monthly_limit_order_review/thesis_metrics.py
 M tests/test_cli.py
 M tests/test_market_data.py
 M tests/test_prompt_builder.py
 M tests/test_regression_2026_03.py
?? .github/
?? AGENTS.md
?? FINANCIAL_ASSUMPTIONS.md
?? data/history/README.md
?? data/history/on_demand/
?? data/normalized/README.md
?? data/raw/
?? decisions/
?? docs/architecture.md
?? docs/migrations/
?? plans/
?? prompts/generated/2026_07_14T223457Z_on_demand_assessment_prompt.md
?? prompts/generated/README.md
?? prompts/templates/on_demand_assessment_template.md
?? prompts/templates/on_demand_market_assessment_session_start_prompt.md
?? reports/
?? retrospectives/
?? schemas/
?? src/monthly_limit_order_review/on_demand.py
?? src/monthly_limit_order_review/repository_records.py
?? src/monthly_limit_order_review/strategy_metrics.py
?? src/monthly_limit_order_review/strategy_policy.py
?? strategy/
?? tests/test_active_strategy_runtime.py
?? tests/test_on_demand.py
?? tests/test_repository_records.py
?? tests/test_strategy_policy.py
?? transactions/
```
