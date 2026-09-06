# Human actionability contractの採用

- 決定日: 2026-08-09
- 起点: `retrospectives/2026-08-09_dashboard_actionability_failure.yaml`
- 対象: 未完了タスク、実行計画、human-readableダッシュボード、リポジトリ監査

レトロスペクティブを受け、機械的完全性と実行安全性だけでなく、人間が次の操作を一意に理解できることを計画の必須品質として採用した。

## 採用した契約

すべてのタスクは次を構造化して保持する。

- 次に動く主体
- 次の具体的行動
- 必要入力
- ユーザが決める事項
- 判断材料を準備する主体
- ブロック解除条件
- 完了証拠

人間向けダッシュボードは、各タスクの一覧行だけを読んでも「誰が、次に何をし、何が揃えば進めるか」が分かる表示にする。停止理由だけの `未設定`、`実行不可`、`確認待ち` は受け入れない。

## 実装参照

- `schemas/plan.schema.yaml`
- `src/monthly_limit_order_review/repository_records.py`
- `plans/2026/2026-08-09_act_s3_execution.yaml`
- `ACT_S3_DASHBOARD.md`
- `AGENTS.md`
- `SPEC.md`
- `plans/README.md`
- `tests/test_repository_records.py`
- `tests/test_strategy_policy.py`
