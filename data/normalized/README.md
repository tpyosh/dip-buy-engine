# Normalized data

`snapshot_YYYY_MM.yaml` は、基準日時点の夫個人金融資産を正規化したスナップショットです。

- 各ファイルは時点事実であり、現在の戦略や購入計画を含めない。
- 過去ファイルは原則不変とし、訂正が必要な場合は理由と訂正日を別記録する。
- `snapshot_date`は評価基準日、`currency_base`は集計通貨を表す。
- 欠損値は`null`のまま保持し、暗黙にゼロへ変換しない。
- `snapshot_YYYY_MM.yaml`は入力例であり、実データではない。
