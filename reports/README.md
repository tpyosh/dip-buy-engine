# Generated reports

`reports/generated/` は、計算結果、レビュー依頼、レビュー構造化結果、提案差分、カレンダードラフトなどの自動生成物を置く領域です。

- 生成物は事実データ、戦略、計画、取引実績のsource of truthではない。
- 月次生成物は `reports/generated/monthly/YYYY_MM/` にまとめる。
- オンデマンド生成物は `reports/generated/on_demand/YYYY/<timestamp>/` にまとめる。
- 2026-07以前の既存生成物は移動・書換えせず、`legacy-index.yaml`から参照する。
- 生成物を手編集せず、入力または生成コードを修正して再生成する。
