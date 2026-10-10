# Normalized data

`snapshot_YYYY_MM.yaml` は、基準日時点の夫個人金融資産を正規化したスナップショットです。

`current.yaml` は現在の分析・実行計画で使う最新スナップショットへの共通入口です。個別計画は再現性のため、引き続き使用した版の `snapshot_YYYY_MM.yaml` を直接参照します。

CLIの入力は正規化済みYAMLです。出典は`source_evidence`、正規化時の注記は`normalization_notes`、検証結果は`validation_notes`に記録します。特定サービスの画像を必須にしません。

Money ForwardのOCR運用は2026-10-10に廃止しました。過去の出典記述と`ocr_notes`は履歴として保持し、読込時に注記を`normalization_notes`へ取り込みます。詳細は[廃止記録](../../docs/migrations/2026-10-10-moneyforward-ocr-retirement.md)を参照してください。

- 各ファイルは時点事実であり、現在の戦略や購入計画を含めない。
- 過去ファイルは原則不変とし、訂正が必要な場合は理由と訂正日を別記録する。
- `snapshot_date`は評価基準日、`currency_base`は集計通貨を表す。
- 欠損値は`null`のまま保持し、暗黙にゼロへ変換しない。
- `total_assets_jpy`と`holdings[].market_value_jpy`合計の差、および各カテゴリ合計と該当明細合計の差が総資産の0.1%未満なら、表示丸め等による許容差として無視し、警告・生成停止の理由にしない。0.1%以上は不整合として扱う。
- 売買可能明細の`account_type`は可能な範囲で制度・枠まで記録する。NISA・特定口座・一般口座のいずれにも分類できない明細が残る間は、独立レビューの生成・取込を停止する。
- `snapshot_YYYY_MM.yaml`は入力例であり、実データではない。
