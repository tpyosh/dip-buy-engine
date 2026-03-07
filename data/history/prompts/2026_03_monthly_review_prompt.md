あなたは、月次の押し目買いルールをレビューする投資アシスタントです。
以下の数値は Python スクリプトが計算したものであり、必要に応じてその妥当性も疑ってください。
ただし、数値の再計算を主目的にせず、ポートフォリオ管理・リスク管理・ルールの妥当性レビューを主眼にしてください。

目的:
- 今月の指値設定案を提案する
- SOX投信を買うべきか判定する
- ポートフォリオの偏りを指摘する
- 今月の補強優先順位を述べる
- スクリプト改善余地があれば明示する

あなたに渡す情報:
- 月次スナップショット
- Python が計算した基準値
- Python が計算した候補価格
- ポートフォリオ比率
- リスク警告

指値提案ルール:
- 各銘柄について、提案する指値段数は 0段以上の任意とする
- Python が出した候補段数に縛られず、0段、1段、2段、3段以上のいずれでもよい
- 0段にする場合は、その銘柄は今月は見送ると明記する
- Python 候補より少ない段数しか提案しない場合は、それが「ルール上そう判断した」のか「今月の裁量判断」なのかを明記する
- Python 候補より多い段数を提案する場合も、なぜ段数を増やすのか理由を明記する

必須出力形式:
【今月の指値提案】
...
【SOX投信判定】
...
【ポートフォリオ診断】
...
【ルール改善レビュー】
...
【Codex向け修正要約】
...

## 1. 前提
- snapshot_date: 2026-03-07
- currency_base: JPY
- total_assets_jpy: 32692503
- liquidity_target_jpy: null
- holdings_count: 21
- 半導体エクスポージャ: 11.83%

## 2. この月の snapshot 要約
- CASH_EQUIV | liquidity | value_jpy=14526912 | price=null | quantity=null
- 7203 | jun_core (raw=other) | value_jpy=2812000 | price=3515 | quantity=800
- 9444 | other | value_jpy=532500 | price=355 | quantity=1500
- 2353 | other | value_jpy=27400 | price=274 | quantity=100
- 7201 | other | value_jpy=38600 | price=386 | quantity=100
- SMH | satellite_core (raw=satellite) | value_jpy=62457 | price=395.35 | quantity=1
- PLTR | satellite | value_jpy=217069 | price=152.67 | quantity=9
- CIBR | satellite_core (raw=satellite) | value_jpy=914628 | price=65.79 | quantity=88
- MSFT | jun_core | value_jpy=259516 | price=410.68 | quantity=4
- URA | satellite_core (raw=satellite) | value_jpy=521959 | price=50.06 | quantity=66
- NISSEI_SOX_1 | satellite_core (raw=jun_core) | value_jpy=2566263 | price=29807 | quantity=860960
- NISSEI_SOX_2 | satellite_core (raw=jun_core) | value_jpy=1238940 | price=29807 | quantity=415654
- RAKUTEN_ALL_COUNTRY_1 | core | value_jpy=1657376 | price=17451 | quantity=949731
- RAKUTEN_ALL_COUNTRY_2 | core | value_jpy=1266398 | price=17451 | quantity=725688
- RAKUTEN_SP500 | core | value_jpy=186790 | price=17534 | quantity=106530
- EMAXIS_SP500_1 | core | value_jpy=173481 | price=39406 | quantity=44024
- EMAXIS_SP500_2 | core | value_jpy=1375061 | price=39406 | quantity=348947
- EMAXIS_SP500_3 | core | value_jpy=670663 | price=39406 | quantity=170193
- EMAXIS_ALL_COUNTRY | core | value_jpy=188260 | price=33853 | quantity=55611
- PENSION_EMAXIS_ALL_COUNTRY | pension | value_jpy=3440168 | price=null | quantity=null
- POINTS_MILES | other | value_jpy=16060 | price=null | quantity=null

## 3. 現在の資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 5518029 | 16.88% | 45.00% | -28.12% |
| jun_core | 3071516 | 9.40% | 20.00% | -10.60% |
| liquidity | 14526912 | 44.43% | 10.00% | 34.43% |
| other | 614560 | 1.88% | - | - |
| pension | 3440168 | 10.52% | - | - |
| satellite | 217069 | 0.66% | 10.00% | -9.34% |
| satellite_core | 5304247 | 16.22% | 15.00% | 1.22% |

## 4. 対象銘柄ごとの候補
| symbol | current_price | base_price | drawdown_pct | limit_price | shares | est_cost_jpy | suppressed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| CIBR | 66.0000 | 65.0615 | -5% | 61.81 | 1 | 9737 | no |
| CIBR | 66.0000 | 65.0615 | -8% | 59.86 | 1 | 9430 | no |
| CIBR | 66.0000 | 65.0615 | -12% | 57.25 | 1 | 9019 | no |
| MSFT | 408.9600 | 401.1770 | -6% | 377.11 | 1 | 59408 | no |
| MSFT | 408.9600 | 401.1770 | -10% | 361.06 | 2 | 113758 | no |
| MSFT | 408.9600 | 401.1770 | -18% | 328.97 | 2 | 103648 | no |
| PLTR | 157.1600 | 138.7620 | -10% | 124.89 | 1 | 19674 | no |
| PLTR | 157.1600 | 138.7620 | -15% | 117.95 | 2 | 37162 | no |
| PLTR | 157.1600 | 138.7620 | -22% | 108.23 | 2 | 34100 | no |
| URA | 48.7800 | 53.1685 | -6% | 49.98 | 2 | 15747 | no |
| URA | 48.7800 | 53.1685 | -10% | 47.85 | 2 | 15076 | no |
| URA | 48.7800 | 53.1685 | -15% | 45.19 | 2 | 14238 | no |

## 5. SOX 判定材料
- proxy_symbol: SMH
- current_price: 380.5600
- recent_high_63d: 426.1600
- drawdown_pct: -10.70%
- buy_zone: -10% to -5%
- within_buy_zone: False
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}

## 6. 警告一覧
- [info] core_below_range: Bucket core is below preferred range: 16.88% < 35.00%
- [info] jun_core_below_range: Bucket jun_core is below preferred range: 9.40% < 10.00%
- [warning] liquidity_above_range: Bucket liquidity is above preferred range: 44.43% > 15.00%
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 44.43% > 10.00%
- [info] snapshot_warning: Holding CASH_EQUIV is missing quantity; stored as null.
- [info] snapshot_warning: Holding CASH_EQUIV is missing avg_cost; stored as null.
- [info] snapshot_warning: Holding CASH_EQUIV is missing current_price; stored as null.
- [info] snapshot_warning: Holding PENSION_EMAXIS_ALL_COUNTRY is missing quantity; stored as null.
- [info] snapshot_warning: Holding PENSION_EMAXIS_ALL_COUNTRY is missing avg_cost; stored as null.
- [info] snapshot_warning: Holding PENSION_EMAXIS_ALL_COUNTRY is missing current_price; stored as null.
- [info] snapshot_warning: Holding POINTS_MILES is missing quantity; stored as null.
- [info] snapshot_warning: Holding POINTS_MILES is missing avg_cost; stored as null.
- [info] snapshot_warning: Holding POINTS_MILES is missing current_price; stored as null.

## 7. ChatGPT に期待する出力形式
以下の見出しを維持してください。
【今月の指値提案】
- 各銘柄について 0段以上の任意段数で提案してよい
- 銘柄ごとの推奨指値
- 推奨株数
- 提案理由
- 0段の場合は「今月は見送り」と明記する
- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する
- Python 候補より段数を増やした場合も、その理由を明記する

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

## 8. 必須のルール改善レビュー
- 毎月の運用と四半期ごとのルール変更を分離してレビューしてください。
- 半導体エクスポージャの合算管理が妥当か確認してください。
- PLTR の浅い押し目候補抑制ロジックの是非も評価してください。
- 指値段数は各銘柄 0段以上の任意とし、1段しか出さない場合は『1段にした理由』を必ず書いてください。

## 9. 必須の Codex 向け修正要約
- must / should / nice_to_have を必ず埋めてください。
- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。

月次キー: 2026_03
