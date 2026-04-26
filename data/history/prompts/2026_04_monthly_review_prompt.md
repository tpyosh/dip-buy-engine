対象月: 2026_04

あなたは、月次レビュー用の判断材料を読む投資アシスタントです。
以下の数値は Python スクリプトが整形したものであり、必要に応じて妥当性を疑ってください。
ただし、Python スクリプトは投資判断エンジンではなく、判断材料の整形エンジンです。
数値の再計算やスクリプトの結論追認ではなく、ポートフォリオ管理・リスク管理・月次レビュー・四半期ルール見直しの観点から評価してください。
月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。
指値設定は前月末または当月初に実施されるため、`snapshot_date` が前月末でも `review_target_month` の指値設定として解釈してください。
指値設定基準値は先月の終値平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均として扱ってください。

目的:
- 今月の core スポット買い実行額を必ず提案する
- 今月の指値設定案を提案する
- コア定額買い方針をレビューする
- SOX投信を買うべきか判定する
- 長期投資シナリオに大きな変化がないか点検する
- ポートフォリオの偏りを指摘する
- 今月の補強優先順位を述べる
- スクリプト改善余地があれば明示する

あなたに渡す情報:
- 月次スナップショット
- Python が計算した基準値
- Python が計算した候補材料
- ポートフォリオ比率
- リスク警告
- コア定額買いの判断材料
- 半導体エクスポージャ内訳
- 長期シナリオ点検対象

指値提案ルール:
- この「今月」は `review_target_month` を指す
- 各銘柄について、提案する指値段数は 0段以上の任意とする
- Python が出した候補段数に縛られず、0段、1段、2段、3段以上のいずれでもよい
- 0段にする場合は、その銘柄は今月は見送ると明記する
- Python 候補より少ない段数しか提案しない場合は、それが「ルール上そう判断した」のか「今月の裁量判断」なのかを明記する
- Python 候補より多い段数を提案する場合も、なぜ段数を増やすのか理由を明記する
- 指値設定基準値は、先月平均ではなくスクリプト実行時点から直近20営業日（約1ヶ月）の終値平均として扱う
- 指値を提案する場合は、各段について「直近20営業日（約1ヶ月）の終値平均」と「その平均から何%下の指値か」を必ず併記する
- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` のパーセンテージとして扱い、マイナス値で明記する

必須出力形式:
【要約】
...
【今月のcoreスポット買い提案】
...
【今月の指値提案】
...
【コア定額買い方針レビュー】
...
【SOX投信判定】
...
【ポートフォリオ診断】
...
【長期シナリオレビュー】
...
【四半期ルール見直し】
...
【Codex向け修正要約】
...

## 1. 前提
- snapshot_date: 2026-03-29
- review_target_month: 2026_04
- currency_base: JPY
- total_assets_jpy: 33028136
- liquidity_target_jpy: null
- holdings_count: 24
- 毎月の税引前キャッシュ流入はおおむね60万〜70万円ある前提で、生活防衛資金の必要水準を評価すること
- 名古屋市中区・金山駅近くの流動性が高いマンション（約6500万円）を住居兼資産として保有している
- 上記マンションはフルローンで購入しており、ローン返済はまだほとんど進んでいない
- そのため、日本国内不動産セクターに対して実質的な積立投資エクスポージャがある前提もポートフォリオ文脈に含めること
- 半導体エクスポージャ(Direct): 11.44%
- AIインフラ感応度(Indirect): 1.21%
- 指値設定は前月末または当月初に実施しうるため、snapshot_date が月末でも翌月の指値設定として解釈してよい
- 指値設定基準値は先月平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均を使う

## 2. この月の snapshot 要約
- JPY_CASH_EQUIVALENT | liquidity | value_jpy=14942636 | price=null | quantity=null
- BTC | other | value_jpy=153210 | price=null | quantity=null
- ETH | other | value_jpy=111366 | price=null | quantity=null
- XRP | other | value_jpy=5798 | price=null | quantity=null
- 7203 | jun_core (raw=other, reason=japan_large_cap_core_position_treated_as_jun_core) | value_jpy=2686400 | price=3358 | quantity=800
- 9444 | other | value_jpy=499500 | price=333 | quantity=1500
- 2353 | other | value_jpy=27500 | price=275 | quantity=100
- 7201 | other | value_jpy=34870 | price=349 | quantity=100
- SMH | satellite_core | value_jpy=59992 | price=374.25 | quantity=1
- PLTR | satellite | value_jpy=206392 | price=143.06 | quantity=9
- CIBR | satellite_core | value_jpy=857104 | price=60.76 | quantity=88
- MSFT | jun_core | value_jpy=400331 | price=356.77 | quantity=7
- URA | satellite_core | value_jpy=508285 | price=46.63 | quantity=68
- NISSEI_SOX_1 | satellite_core | value_jpy=2507460 | price=29124 | quantity=860960
- NISSEI_SOX_2 | satellite_core | value_jpy=1210551 | price=29124 | quantity=415654
- RAKUTEN_ALL_COUNTRY_1 | core | value_jpy=1650964 | price=16871 | quantity=978581
- RAKUTEN_ALL_COUNTRY_2 | core | value_jpy=1224308 | price=16871 | quantity=725688
- RAKUTEN_SP500 | core | value_jpy=179642 | price=16863 | quantity=106530
- EMAXIS_SP500_1 | core | value_jpy=166838 | price=37897 | quantity=44024
- EMAXIS_SP500_2 | core | value_jpy=1370651 | price=37897 | quantity=361678
- EMAXIS_SP500_3 | core | value_jpy=644980 | price=37897 | quantity=170193
- EMAXIS_ALL_COUNTRY_TAXABLE | core | value_jpy=182037 | price=32734 | quantity=55611
- EMAXIS_ALL_COUNTRY_PENSION | pension | value_jpy=3381281 | price=null | quantity=null
- POINTS_MILES | other | value_jpy=16037 | price=null | quantity=null

## 3. 現在の資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 5419420 | 16.41% | 45.00% | -28.59% |
| jun_core | 3086731 | 9.35% | 20.00% | -10.65% |
| liquidity | 14942636 | 45.24% | 10.00% | 35.24% |
| other | 848281 | 2.57% | - | - |
| pension | 3381281 | 10.24% | - | - |
| satellite | 206392 | 0.62% | 10.00% | -9.38% |
| satellite_core | 5143392 | 15.57% | 15.00% | 0.57% |

## 4. 対象銘柄ごとの候補
| symbol | bucket | current_price | base_price | avg20_base_price | drawdown_rule | limit_price | avg20_gap_pct | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt | explanation |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| CIBR | satellite_core | 60.7600 | 64.3840 | 64.3840 | -5% x 1 | 61.16 | -5.01 | 1 | 9767 | yes | limit_above_current | Calculated limit price is not below the current price. | shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,limit_above_current | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 60.7600 | 64.3840 | 64.3840 | -8% x 1 | 59.23 | -8.01 | 1 | 9459 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 60.7600 | 64.3840 | 64.3840 | -12% x 1 | 56.66 | -12.00 | 1 | 9049 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 46.6300 | 51.1673 | 51.1673 | -6% x 2 | 48.10 | -5.99 | 2 | 15364 | yes | limit_above_current | Calculated limit price is not below the current price. | shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,limit_above_current | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 46.6300 | 51.1673 | 51.1673 | -10% x 2 | 46.05 | -10.00 | 2 | 14709 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 46.6300 | 51.1673 | 51.1673 | -15% x 2 | 43.49 | -15.00 | 2 | 13891 | no | - | - | deep_drawdown_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_allow_deep_drawdown_even_if_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_allow_deep_drawdown_even_if_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1557'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 143.0600 | 146.1287 | 146.1287 | -10% x 1 | 131.52 | -10.00 | 1 | 21004 | yes | high_volatility_shallow_suppressed | High-volatility names default to deeper pullbacks before adding. | high_volatility_name,rule_based_high_volatility_shallow_suppression,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization,high_volatility_shallow_suppressed | {'rule_based_reason': ['rule_based_high_volatility_shallow_suppression'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0062'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': True, 'reason_code': 'high_volatility_shallow_suppressed', 'reason_text': 'High-volatility names default to deeper pullbacks before adding.'}} |
| PLTR | satellite | 143.0600 | 146.1287 | 146.1287 | -15% x 2 | 124.21 | -15.00 | 2 | 39674 | no | - | - | deep_drawdown_candidate,high_volatility_name,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0062'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 143.0600 | 146.1287 | 146.1287 | -22% x 2 | 113.98 | -22.00 | 2 | 36406 | no | - | - | deep_drawdown_candidate,high_volatility_name,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0062'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 356.7700 | 393.9447 | 393.9447 | -6% x 1 | 370.31 | -6.00 | 1 | 59140 | yes | limit_above_current | Calculated limit price is not below the current price. | shallow_candidate,mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost,limit_above_current | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0935'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 356.7700 | 393.9447 | 393.9447 | -10% x 2 | 354.55 | -10.00 | 2 | 113246 | no | - | - | mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0935'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 356.7700 | 393.9447 | 393.9447 | -18% x 2 | 323.03 | -18.00 | 2 | 103178 | no | - | - | deep_drawdown_candidate,mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0935'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |

## 5. コア定額買い判定材料
- core_actual_pct: 16.41%
- core_target_pct: 45.00%
- core_delta_pct: -28.59%
- liquidity_actual_pct: 45.24%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 35.24%
- core_bucket_total_jpy: 5419420
- monthly_core_budget_policy: {'base_monthly_buy_amount_jpy': 100000, 'monthly_core_buy_budget_min_jpy': 100000, 'monthly_core_buy_budget_max_jpy': 300000, 'budget_tiers': {'standard': {'budget_jpy': 100000}, 'aggressive': {'budget_jpy': 300000}, 'rebalance': {'budget_jpy': 700000}}, 'override_conditions': {'core_shortfall_pct_gte': 0.15, 'cash_excess_pct_gte': 0.15, 'budget_tier': 'aggressive', 'reason_code': 'core_underweight_and_cash_overweight'}, 'rebalance_mode': {'enabled': True, 'core_shortfall_pct_gte': 0.25, 'cash_excess_pct_gte': 0.25, 'monthly_core_buy_budget_max_jpy': 700000, 'budget_tier': 'rebalance', 'reason_code': 'rebalance_mode_core_underweight_and_cash_overweight', 'description': 'core不足と現金過多が大きい局面で、月次の配分是正速度を上げる補助モード'}}
- monthly_core_buy_budget_min_jpy: 100000
- monthly_core_buy_budget_max_jpy: 300000
- monthly_core_budget_tier: rebalance
- recommended_monthly_core_buy_budget_jpy: 700000
- monthly_core_budget_override_active: True
- monthly_core_budget_override_reason: rebalance_mode_core_underweight_and_cash_overweight
- portfolio_management_mode: rebalance
- rebalance_mode_active: True
- rebalance_mode_reason: rebalance_mode_core_underweight_and_cash_overweight
- core_budget_explanation: {'rule_based_reason': 'rebalance_mode_core_underweight_and_cash_overweight', 'discretionary_reason': None, 'related_bucket_status': {'core_actual_pct': Decimal('0.1641'), 'core_target_pct': Decimal('0.45'), 'liquidity_actual_pct': Decimal('0.4524'), 'liquidity_target_pct': Decimal('0.1')}, 'mode_context': {'active_mode': 'rebalance', 'rebalance_mode_active': True, 'rebalance_mode_reason': 'rebalance_mode_core_underweight_and_cash_overweight', 'rebalance_mode_description': 'core不足と現金過多が大きい局面で、月次の配分是正速度を上げる補助モード'}}
| symbol | quantity | value_jpy | current_price | reference_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| RAKUTEN_ALL_COUNTRY_1 | 978581 | 1650964 | 16871 | VT | 134.6200 | 147.8400 | 148.9100 | -9.60 |
| RAKUTEN_ALL_COUNTRY_2 | 725688 | 1224308 | 16871 | VT | 134.6200 | 147.8400 | 148.9100 | -9.60 |
| RAKUTEN_SP500 | 106530 | 179642 | 16863 | VOO | 582.9600 | 631.2800 | 639.7000 | -8.87 |
| EMAXIS_SP500_1 | 44024 | 166838 | 37897 | VOO | 582.9600 | 631.2800 | 639.7000 | -8.87 |
| EMAXIS_SP500_2 | 361678 | 1370651 | 37897 | VOO | 582.9600 | 631.2800 | 639.7000 | -8.87 |
| EMAXIS_SP500_3 | 170193 | 644980 | 37897 | VOO | 582.9600 | 631.2800 | 639.7000 | -8.87 |
| EMAXIS_ALL_COUNTRY_TAXABLE | 55611 | 182037 | 32734 | ACWI | 134.5500 | 147.3800 | 148.6500 | -9.49 |

## 5-1. Coreスポット買い判断材料
- liquidity_actual_pct: 45.24%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 35.24%
- core_actual_pct: 16.41%
- core_target_pct: 45.00%
- core_delta_pct: -28.59%
- jun_core_actual_pct: 9.35%
- jun_core_target_pct: 20.00%
- jun_core_delta_pct: -10.65%
- current_monthly_core_auto_invest_amount_jpy: 750000
- annualized_core_auto_invest_amount_jpy: 9000000
- current_cash_jpy: 14942636
- bond_like_holdings_present: False
- bond_like_holdings: None
- emergency_fund_managed_separately: None
- near_term_large_expense: None
| reference_symbol | one_month_return_pct | three_month_return_pct | one_month_drawdown_from_high_pct | three_month_drawdown_from_high_pct |
| --- | ---: | ---: | ---: | ---: |
| VT | -9.29 | -5.44 | -8.94 | -9.60 |
| VOO | -8.04 | -8.16 | -7.65 | -8.87 |
| ACWI | -9.06 | -5.72 | -8.71 | -9.49 |
- portfolio_risk_bucket_summary:
  - core: actual_pct=16.41%, target_pct=45.00%, delta_pct=-28.59%
  - jun_core: actual_pct=9.35%, target_pct=20.00%, delta_pct=-10.65%
  - liquidity: actual_pct=45.24%, target_pct=10.00%, delta_pct=35.24%
  - other: actual_pct=2.57%, target_pct=null, delta_pct=null
  - pension: actual_pct=10.24%, target_pct=null, delta_pct=null
  - satellite: actual_pct=0.62%, target_pct=10.00%, delta_pct=-9.38%
  - satellite_core: actual_pct=15.57%, target_pct=15.00%, delta_pct=0.57%

## 5-2. Core積立設定（毎月固定）
- total_monthly_jpy: 750000
| day_of_month | fund_name | amount_jpy | settlement_type | account_type | distribution_course |
| ---: | --- | ---: | --- | --- | --- |
| 1 | eMAXIS Slim 米国株式(S&P500) | 225000 | 証券口座 | NISA成長投資枠 | 再投資型 |
| 1 | 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー) | 425000 | 証券口座 | NISA成長投資枠 | 再投資型 |
| 8 | eMAXIS Slim 米国株式(S&P500) | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
| 8 | 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー) | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
- review_guidance:
  - この固定積立は毎月すでに執行される前提で評価する
  - core不足の指摘は、固定積立の寄与を織り込んだうえで必要時のみ行う
  - 長期シナリオ悪化やリスク管理上の理由がある場合は、固定積立の減額・停止提案を明示する

## 5-3. 暗号資産積立設定（毎週固定）
| symbol | amount_jpy_per_week |
| --- | ---: |
| BTC | 2000 |
| ETH | 2000 |
| XRP | 1000 |
- crypto_review_guidance:
  - 暗号資産の週次積立は既存で実行中の前提で評価する
  - 継続・減額・停止の提案が必要な場合は、理由とトリガー条件を明示する

## 6. SOX 判定材料
- proxy_symbol: SMH
- current_price: 374.2500
- recent_high_21d: 406.3900
- recent_high_63d: 426.1600
- drawdown_pct_from_21d_high: -7.91
- drawdown_pct_from_63d_high: -12.18
- buy_zone_rule_text: drawdown from 63d high between -10% and -5%
- within_buy_zone_boolean: False
- near_boundary_boolean: False
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}
- related_bucket_actual_pct: 15.57%
- related_bucket_target_pct: 15.00%
- semiconductor_exposure_total_pct: 11.44%
- priority_lowered_boolean: True
- priority_lowered_reason: related_bucket_over_target
- explanation: {'buy_zone_assessment': {'within_buy_zone': False, 'near_boundary': False, 'drawdown_pct_from_63d_high': Decimal('-12.18'), 'rule': '-10% <= drawdown <= -5%'}, 'bucket_context': {'related_bucket': 'satellite_core', 'related_bucket_actual_pct': Decimal('0.1557'), 'related_bucket_target_pct': Decimal('0.15')}, 'exposure_context': {'semiconductor_direct_exposure_pct': Decimal('0.1144'), 'indirect_ai_infra_exposure_pct': Decimal('0.0121')}}

## 7. 半導体エクスポージャ内訳
- direct_cap_monitor_pct: 11.44%
- direct_cap_monitor_jpy: 3778003
- direct_plus_indirect_watch_metric_pct: 12.65%
- direct_plus_indirect_watch_metric_jpy: 4178334
- direct_semiconductor_exposure_pct: 11.44%
- indirect_ai_infra_exposure_pct: 1.21%
- indirect_ai_infra_exposure_jpy: 400331
- combined_semiconductor_ai_infra_watch_pct: 12.65%
| symbol | value_jpy | bucket | exposure_type | in_direct | in_indirect | inclusion_reason |
| --- | ---: | --- | --- | --- | --- | --- |
| SMH | 59992 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| MSFT | 400331 | jun_core | indirect_ai_infra | no | yes | matched_indirect_ai_infra_rule |
| NISSEI_SOX_1 | 2507460 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| NISSEI_SOX_2 | 1210551 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |

## 8. 長期シナリオ点検対象
| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| URA | satellite_core | 508285 | 1.54% | nuclear_revival | 脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。 | 炭素回収技術の量産化・低コスト化; 再エネ＋蓄電の経済性改善; 政策転換; 原子力新設の採算悪化 | high | yes |
| CIBR | satellite_core | 857104 | 2.60% | persistent_cybersecurity_spending | サイバーセキュリティ支出は構造的に維持・拡大するという仮説。 | 支出成長の鈍化; バリュエーション過熱後の長期低迷 | medium | yes |
| MSFT | jun_core | 400331 | 1.21% | hyperscaler_ai_platform_compounding | クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。 | AI投資回収の停滞; 規制強化; 競争優位の低下 | medium | yes |
| PLTR | satellite | 206392 | 0.62% | defense_ai_gov_software_scaling | 政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。 | 政府需要の鈍化; 競争激化; 収益化の鈍化 | medium | yes |

## 9. ChatGPTへの長期シナリオレビュー依頼
- この投資方針は中長期前提であり、短期トレンドやテクニカル悪化だけでは売却判断しません。
- ただし、長期の成長ストーリー・構造的需要シナリオ・政策前提・競争優位の前提が崩れた場合は再評価余地があります。
- 上の対象銘柄について、最新のWeb情報を調査した上で、長期シナリオに変化がないかレビューしてください。
- Webで確認した事実と、そこからの推論を分けて記述してください。
- 価格やチャートではなく、事業 / 技術 / 政策 / 競争環境 / 需要構造の変化を主に見てください。
- 大きな変化が見当たらない場合は、無理に懸念を捏造せず『大きな変化なし』としてください。
- 根拠が弱い場合は『判断材料不足』と言ってかまいません。
- 売却判断そのものを断定せず、`継続保有でよい` / `要監視` / `仮説弱化` の区分で返してください。
- Web調査を使い、長期視点で判断してください。

## 10. 警告一覧
- [info] core_below_range: Bucket core is below preferred range: 16.41% < 35.00%
- [info] jun_core_below_range: Bucket jun_core is below preferred range: 9.35% < 10.00%
- [warning] liquidity_above_range: Bucket liquidity is above preferred range: 45.24% > 15.00%
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 45.24% > 10.00%
- [warning] limit_above_current: CIBR: Calculated limit price is not below the current price.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] limit_above_current: URA: Calculated limit price is not below the current price.
- [warning] bucket_over_target_shallow_suppressed: URA: Shallow candidate suppressed because related bucket is over target.
- [warning] high_volatility_shallow_suppressed: PLTR: High-volatility names default to deeper pullbacks before adding.
- [warning] limit_above_current: MSFT: Calculated limit price is not below the current price.
- [info] missing_quantity: Holding JPY_CASH_EQUIVALENT is missing quantity; stored as null.
- [info] missing_avg_cost: Holding JPY_CASH_EQUIVALENT is missing avg_cost; stored as null.
- [info] missing_current_price: Holding JPY_CASH_EQUIVALENT is missing current_price; stored as null.
- [info] missing_quantity: Holding BTC is missing quantity; stored as null.
- [info] missing_avg_cost: Holding BTC is missing avg_cost; stored as null.
- [info] missing_current_price: Holding BTC is missing current_price; stored as null.
- [info] missing_quantity: Holding ETH is missing quantity; stored as null.
- [info] missing_avg_cost: Holding ETH is missing avg_cost; stored as null.
- [info] missing_current_price: Holding ETH is missing current_price; stored as null.
- [info] missing_quantity: Holding XRP is missing quantity; stored as null.
- [info] missing_avg_cost: Holding XRP is missing avg_cost; stored as null.
- [info] missing_current_price: Holding XRP is missing current_price; stored as null.
- [info] missing_quantity: Holding EMAXIS_ALL_COUNTRY_PENSION is missing quantity; stored as null.
- [info] missing_avg_cost: Holding EMAXIS_ALL_COUNTRY_PENSION is missing avg_cost; stored as null.
- [info] missing_current_price: Holding EMAXIS_ALL_COUNTRY_PENSION is missing current_price; stored as null.
- [info] missing_quantity: Holding POINTS_MILES is missing quantity; stored as null.
- [info] missing_avg_cost: Holding POINTS_MILES is missing avg_cost; stored as null.
- [info] missing_current_price: Holding POINTS_MILES is missing current_price; stored as null.

## 11. 生成ロジック上の分離データ
- monthly_execution_outputs:
  - portfolio_management_mode: rebalance
  - monthly_core_budget_tier: rebalance
  - recommended_monthly_core_buy_budget_jpy: 700000
  - monthly_total_core_deployment_jpy: 1450000
  - candidate_count: 12
  - crypto_weekly_dca_total_jpy: 5000
- quarterly_rule_review_outputs:
  - no_change: False
  - classification_override_count: 1
  - core_reference_missing_symbols: []
  - tradable_core_pct: 16.41%
  - effective_core_including_pension_pct: 26.65%
  - cash_normalization_months_estimate: 8.0
  - direct_cap_monitor_pct: 11.44%
  - direct_plus_indirect_watch_metric_pct: 12.65%
  - direct_semiconductor_exposure_pct: 11.44%
  - combined_semiconductor_ai_infra_watch_pct: 12.65%
  - indirect_ai_infra_exposure_pct: 1.21%

## 12. ChatGPT に期待する出力形式
以下の見出しを維持してください。
月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。
月次の注文判断・資金配分判断を、四半期ルール見直しセクションに混ぜないでください。
【要約】
- 3〜6行程度で短くまとめる
- 今月の最重要判断
- 今月の core スポット買い執行額
- コア / サテライトの優先順位
- SOXの判定
- ルール改善の要否
- 『今月何をする月か』が一目で分かる内容にする

【今月のcoreスポット買い提案】
- このセクションは毎回必須とする
- 今月の推奨スポット買い総額を、JPY の単一具体額で最初に明示すること
- 0円は禁止。必ず non-zero の執行額を出すこと
- `多めに` `厚めに` `数十万円` `50〜100万円` のような曖昧表現は禁止
- 配分先内訳を明示すること
- 実行方法を `一括` / `2〜4分割` / `押し目待ち併用` のいずれかで明示すること
- 判断根拠は `相場面` / `ポートフォリオ歪み` / `流動性水準` を分けて書くこと
- その判断が `ルール上の判断` か `今月の裁量判断` かを分離すること
- broad market core 商品を優先し、むやみに新規商品を増やさないこと
- 債券や低リスク商品を提案してもよいが、core equity のスポット買い額は必ず別途提示すること
- `積立しているからスポット買いは不要` とは結論しないこと

【今月の指値提案】
- この『今月』は review_target_month を指す。snapshot_date が前月末でも、対象月を取り違えないこと
- 各銘柄について 0段以上の任意段数で提案してよい
- 0段の場合は『今月は見送り』と明記する
- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する
- Python 候補より段数を増やした場合も、その理由を明記する
- 指値設定基準値はスクリプト実行時点から直近20営業日（約1ヶ月）の終値平均ベースとして扱うこと
- 指値を提案する各段で、直近20営業日（約1ヶ月）の終値平均の実数値を必ず明示すること
- 指値を提案する各段で、その指値が直近20営業日終値平均から何%下かを必ず明示すること
- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` で計算し、マイナス値で表記すること
- 推奨フォーマット例: `指値 450.00 USD（20営業日平均 500.00 USD, 平均比 -10.0%）`
- 減段理由テンプレートの例: `ルール上の判断: bucket_over_target のため浅い段を見送る`
- 減段理由テンプレートの例: `今月の裁量判断: core 補強を優先するため段数を減らす`

【コア定額買い方針レビュー】
- コアは今月最低いくら買うべきか
- 安ければ追加でどの程度厚くする考え方が妥当か
- コアとサテライトの資金配分優先順位
- 既存の毎月固定積立（Core積立設定）を前提に評価すること
- 積立設定が大きくても、それだけでスポット買い免除にしないこと
- 固定積立を維持するか、減額/停止すべきかを明示すること（必要な場合のみ）
- ルール上の判断と今月の裁量判断を分けて説明すること

【SOX投信判定】
- 買う / 買わない
- 理由

【ポートフォリオ診断】
- 現在の偏り
- 注意点
- 今月の補強優先順位
- 暗号資産の週次積立（BTC/ETH/XRP）を前提に、維持/減額/停止の要否を明示すること

【長期シナリオレビュー】
- 対象銘柄ごとに、現在の長期仮説に大きな変化があるかを書く
- Webで確認した主要事実と、そこからの推論を分けて書く
- 判定区分は `継続保有でよい` / `要監視` / `仮説弱化` を使う
- 売却を即断せず、なぜその判定にしたかを書く
- 大きな変化が見当たらない場合は『大きな変化なし』と簡潔に書く

【四半期ルール見直し】
- このセクションでは、四半期単位で見直すべき構造的なルール変更だけを書くこと
- 月次の執行判断、今月の注文可否、今月だけの資金配分判断はここに混ぜないこと
- 維持してよいルール / 改善した方がよいルール / 追加した方がよい制約 / スクリプト修正が望ましい点を整理すること
- 改善提案は、明確な問題・矛盾・欠落・ノイズ・仕様不足がある場合のみ挙げること
- 大きな問題がない場合は『大きなルール変更提案なし』と明記してよい
- ハルシネーション防止のため、推測で問題点や改善案を作らないこと
- must には月次判断に実害があるものだけを入れること

【Codex向け修正要約】
- このセクションの本文全体を、必ず単一の ```md コードブロックで出力すること
- コードブロック外に Codex向け修正要約を書かないこと
- 問題がない場合でもコードブロックは省略せず、`must: なし` のように明記すること
- must / should / nice_to_have は空欄不可だが、該当なしの場合は `なし` と書いてよい
- 出力例:
```md
must:
- なし

should:
- なし

nice_to_have:
- なし

修正目的:
- 大きな修正提案なし

変更すべき仕様:
- なし

影響範囲:
- なし

推奨テスト:
- なし
```

## 13. 必須の月次・四半期レビュー観点
- 毎月の運用レビューと四半期ごとのルール変更レビューを分離して評価してください。
- 指値設定は前月末または当月初に実施されるため、snapshot_date が月末なら翌月の指値設定として扱ってください。
- 四半期ルール見直しセクションには、月次の執行判断を混ぜないでください。
- 半導体エクスポージャの合算管理が妥当か確認してください。
- PLTR の浅い押し目候補抑制ロジックの是非を評価してください。
- 指値段数は各銘柄 0段以上の任意とし、1段しか出さない場合はその理由を明記してください。
- 指値を出す場合は、各段で直近20営業日（約1ヶ月）の終値平均と平均比の乖離率を併記してください。
- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` に基づくマイナス値で記述してください。
- コアについては『毎月一定額買う / 安ければ追加で厚く買う』という運用思想の妥当性も評価してください。
- 月次レビューでは、毎回必ず core スポット買い額を提案してください。
- core スポット買い額は 0円不可で、最初に単一の具体額を出してください。
- 金額はその月の portfolio 歪み、相場状況、流動性水準で変動してよいです。
- cash_excess_pct が大きいほど、core スポット買い額を増やしてください。
- core_delta_pct が大きいほど、core スポット買い額を増やしてください。
- broad market ベースで明確に下落している月は、core スポット買い額を増やしてください。
- 高値圏でも cash_excess と core不足が大きい場合は、一定額は必ず実行してください。
- satellite_core が過大でも、core不足是正を優先してください。
- 既存の broad market core 商品を優先し、新規商品追加は最小限にしてください。
- 債券や低リスク商品を提案する場合でも、core equity スポット買い額そのものは別で必ず提示してください。
- `全部債券` `全部現金維持` は不可です。
- 生活防衛資金や大口支出情報が不明なら、不明として保守的に扱ってください。
- 毎月の税引前キャッシュ流入が60万〜70万円ある前提を、生活防衛資金の残し方判断に反映してください。
- 名古屋市中区・金山駅近くの約6500万円のマンションを住居兼資産として保有し、しかもフルローンで返済初期である点を考慮してください。
- 上記不動産保有により、日本国内不動産セクターへの実質的なエクスポージャが既にある前提で配分やリスクを評価してください。
- Core積立設定（毎月固定）は既に実行される前提として扱い、同じ強化提案の反復は避けてください。
- ただし長期シナリオ悪化やリスク管理上の妥当性がある場合は、固定積立の減額・停止提案を明示してください。
- 暗号資産の週次積立（BTC/ETH/XRP）も既に実行される前提で扱い、必要時のみ変更提案してください。
- コア不足と現金過多が同時発生している場合、押し目買いルール設計に問題がないかもレビューしてください。
- 中長期投資前提のため、短期トレンドやテクニカル悪化を売却理由にしない前提でレビューしてください。
- ただし、長期シナリオ・政策前提・技術前提・競争優位の前提が崩れた可能性がある場合は、その有無をWebベースで点検してください。
- 大きな変化が見当たらない場合は、無理に懸念を作らず『大きな変化なし』としてください。
- 事実と推論を分けて記述してください。
- 大きな問題がない場合は、無理に改善提案を作らないでください。
- ハルシネーション防止のため、明確な根拠がある改善提案のみを挙げてください。
- must / should / nice_to_have は空欄不可ですが、該当なしの場合は `なし` と明記してください。
- Codex向け修正要約は必ず md コードブロックで出力してください。
- ルール改善が不要な場合は、その旨を明記してください。

## 14. 必須の Codex 向け修正要約観点
- must / should / nice_to_have は必ず埋めてください。
- 空欄は不可ですが、該当なしの場合は `なし` と明記してください。
- 【Codex向け修正要約】 全体を単一の ```md コードブロックで出力してください。
- monthly review と quarterly rule review を分けて整理してください。
- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。

指値設定対象月キー: 2026_04
