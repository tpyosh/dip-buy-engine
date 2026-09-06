# Plans

`plans/` は、現在の資産状況から導かれる期間限定の購入・売却・資金移動計画を置く場所です。

- 各計画は使用したスナップショット、基準日、戦略版、税区分、状態を持つ。
- `approved_pending_execution` は承認済みだが未実行であり、取引実績として扱わない。
- 実行前に残高・価格・税区分など変化し得る事実を再確認する。
- 約定後は計画を書き換えて実績化せず、将来の `transactions/` に別記録する。
- 比率・上限・レンジを使うタスクは、`allocation_basis` に分子、分母、分母定義の参照、測定時点、目標値を明記する。「3%」のように分母を省略した表現は禁止する。
- 買付・売却タスクは、`order_specification` に口座、数量ルール、成行／指値等の注文種別、指値ルール、時期、有効期限、部分約定、失効時の再注文、資金移動先、税確認、ユーザ承認を明記する。
- 注文設定が未決定ならフィールドを省略せず、`status: pending_execution_time_configuration`、`execution_allowed: false` として実行を止める。
- `repository-audit` は、タスク型計画の分母または注文仕様が欠けていればエラーにする。
- 進行中・未完了の全タスクは `human_actionability` に、次に動く主体、次の一手、必要入力、ユーザが決める事項、比較材料を準備する主体、実行可能になる条件、完了証拠を持つ。
- `required_inputs` は自由記述にせず、入力ごとに `key`、`availability`、`source_ref`、`value_summary`、`as_of`、`refresh_rule`、`request_from_user_if`、`blocking`、`owner`、`verification_stage`、`trigger_evidence`、`scope` を持たせる。
- `availability` は `resolved_from_repository`、`known_event_pending`、`refresh_by_codex`、`verify_at_execution`、`user_input_blocking` のいずれかとする。変更証拠のない抽象的可能性は入力として登録しない。
- ユーザへ入力を求める前に、計画が参照するスナップショット、`financial/current.yaml`、`holdings/current.yaml`、`strategy/current.yaml`、生成済み計算、取引記録を探索する。最新正本後の変更イベントがなければ、基準状態を下書きへ継続利用する。
- 既存注文・受渡等は `known_event_pending`、価格・為替・政策分母は `refresh_by_codex`、数量・重複注文・拘束数量等の通常確認は `verify_at_execution`、真に欠ける必須情報だけを `user_input_blocking` とする。
- `verify_at_execution` は下書き作成をブロックせず、全売買共通の注文入力時プリフライトへ置く。個別銘柄に前倒しする場合は `trigger_evidence` を必須とする。
- `未設定`、`実行不可`、`確認する` だけで終わる表示は禁止する。停止理由と同じ場所に、誰が何をすれば解除できるかを記載する。
- 人間向けダッシュボードは、各タスクの一覧行だけを読んでも次の行動が分かるよう、正本の `human_actionability.next_action` と `unblock_condition` を局所表示する。現在ブロッカー、Codex更新、ユーザ必須入力、注文入力時プリフライトを分離する。

## 現在の引き継ぎ計画

- `plans/2026/2026-08-09_act_s3_execution.yaml`: 承認済みの `ACT-S3-001`〜`ACT-S3-016`、現在状態、再開手順、実行時再計算ルールの正本。
