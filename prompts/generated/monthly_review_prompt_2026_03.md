あなたは、月次の押し目買いルールをレビューする投資アシスタントです。
以下の数値は Python スクリプトが計算したものであり、必要に応じてその妥当性も疑ってください。
ただし、数値の再計算を主目的にせず、ポートフォリオ管理・リスク管理・ルールの妥当性レビューを主眼にしてください。

## 1. 前提
- snapshot_date: 2026-03-07
- currency_base: JPY
- total_assets_jpy: 5000000
- liquidity_target_jpy: 1000000
- holdings_count: 6
- 半導体エクスポージャ: 16.00%

## 2. この月の snapshot 要約
- JPY_CASH | liquidity | value_jpy=1200000 | price=null | quantity=null
- ALL_COUNTRY_FUND | core | value_jpy=1800000 | price=null | quantity=null
- MSFT | jun_core | value_jpy=800000 | price=400 | quantity=4
- NIKKO_SOX_FUND | satellite_core | value_jpy=600000 | price=null | quantity=null
- SMH | satellite_core | value_jpy=200000 | price=230 | quantity=1
- PLTR | satellite | value_jpy=400000 | price=70 | quantity=10

## 3. 現在の資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 1800000 | 36.00% | 45.00% | -9.00% |
| jun_core | 800000 | 16.00% | 20.00% | -4.00% |
| liquidity | 1200000 | 24.00% | 10.00% | 14.00% |
| satellite | 400000 | 8.00% | 10.00% | -2.00% |
| satellite_core | 800000 | 16.00% | 15.00% | 1.00% |

## 4. 対象銘柄ごとの候補
| symbol | current_price | base_price | drawdown_pct | limit_price | shares | est_cost_jpy | suppressed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CIBR | 90 | 100 | -5% | 95 | 1 | 14250 | no |
| URA | 80 | 100 | -6% | 94 | 2 | 28200 | no |
| PLTR | 70 | 100 | -10% | 90 | 1 | 13500 | yes: PLTR already exceeds policy cap; shallow dip tranche is suppressed. |
| MSFT | 400 | 500 | -6% | 470 | 1 | 70500 | yes: Liquidity hard floor would be breached. |

## 5. SOX 判定材料
- proxy_symbol: SMH
- current_price: 230
- recent_high_63d: 250
- drawdown_pct: -8%
- buy_zone: -10% to -5%
- within_buy_zone: True
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}

## 6. 警告一覧
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 24.00% > 10.00%
- [warning] pltr_limit: PLTR exceeds total-assets cap: 8.00% > 3.00%

## 7. ChatGPT に期待する出力形式
【今月の指値提案】
- 銘柄ごとの推奨指値
- 推奨株数
- 提案理由

【SOX投信判定】
- 買う / 買わない
- 理由

【ポートフォリオ診断】
- 現在の偏り
- 注意点
- 今月の補強優先順位

【ルール改善レビュー】
- 維持してよいルール
- 改善した方がよいルール
- 追加した方がよい制約
- スクリプト修正が望ましい点

【Codex向け修正要約】
- must
- should
- nice_to_have
- 修正目的
- 変更すべき仕様
- 影響範囲
- 推奨テスト

