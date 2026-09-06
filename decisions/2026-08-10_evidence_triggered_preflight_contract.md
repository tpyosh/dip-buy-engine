# Evidence-triggered freshness and preflight contractの採用

- 決定日: 2026-08-10
- 承認者: ユーザ
- 起点: `retrospectives/2026-08-10_cibr_generic_staleness_blocker_failure.yaml`
- 対象: エージェント行動規則、実行計画、ダッシュボード、スキーマ、監査、テスト

変更を示す具体的証拠がない銘柄について、基準日後の売買なし・注文なしという否定確認をユーザへ求めない。最新正本後に取引・移管・注文の報告、既知イベント、または矛盾する証拠がなければ、正本の保有状態を注文案の下書き基準として継続利用する。

## 採用した確認段階

- `resolved_from_repository`: 正本から解決済み。再提出不要
- `known_event_pending`: 既存注文、受渡、依存タスク等の具体的イベント待ち
- `refresh_by_codex`: 最新価格、為替、政策分母等をCodexが更新
- `verify_at_execution`: 現在数量、重複注文、拘束数量、買付可能額等を注文入力時に共通確認。下書きは止めない
- `user_input_blocking`: 正本・接続済み情報源に存在せず、下書きまたは承認に本当に不可欠な情報

ユーザ確認を発火させる項目は、具体的な `trigger_evidence`、確認主体、確認段階、ブロッキング性、適用範囲を持たせる。現在注目している銘柄だけに、全銘柄共通の抽象的不確実性を展開しない。

## 実装参照

- `AGENTS.md`
- `SPEC.md`
- `plans/README.md`
- `schemas/plan.schema.yaml`
- `src/monthly_limit_order_review/repository_records.py`
- `plans/2026/2026-08-09_act_s3_execution.yaml`
- `ACT_S3_DASHBOARD.md`
- `tests/test_repository_records.py`
- `tests/test_strategy_policy.py`
