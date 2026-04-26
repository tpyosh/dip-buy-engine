対象月: 2026_05

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

coreスポット買い出力ルール:
- `【今月のcoreスポット買い提案】` では、提案総額、配分先内訳、実行スケジュールを必ず記載する
- core を積み増したほうがよい月は、`eMAXIS Slim 米国株式(S&P500)` と `eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)` の今月の積み増しスケジュールを明示する
- `配分先内訳` では銘柄ごとの金額を記載し、合計は提案総額と一致させる
- `実行スケジュール` では `review_target_month` 内の日付を使い、各行を `4月1日: eMAXIS Slim 米国株式(S&P500) 150,000円` の形式で記載する
- 実行スケジュールの金額合計は、配分先内訳および提案総額と一致させる
- coreスポット買いを見送る場合は、見送り理由を明記し、`実行スケジュールなし` と記載する
- フォーマット例:
```text
【今月のcoreスポット買い提案】
700,000円
配分先内訳
eMAXIS Slim 全世界株式(オール・カントリー)(オルカン): 400,000円
eMAXIS Slim 米国株式(S&P500): 300,000円
実行スケジュール
4月1日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 200,000円
4月4日: eMAXIS Slim 米国株式(S&P500) 150,000円
4月11日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 100,000円
4月18日: eMAXIS Slim 米国株式(S&P500) 100,000円
4月25日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 100,000円
4月25日: eMAXIS Slim 米国株式(S&P500) 50,000円
```

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
- snapshot_date: 2026-04-25
- review_target_month: 2026_05
- currency_base: JPY
- total_assets_jpy: 35558948
- liquidity_target_jpy: null
- holdings_count: 21
- 毎月の税引前キャッシュ流入はおおむね60万〜70万円ある前提で、生活防衛資金の必要水準を評価すること
- 名古屋市中区・金山駅近くの流動性が高いマンション（約6500万円）を住居兼資産として保有している
- 上記マンションはフルローンで購入しており、ローン返済はまだほとんど進んでいない
- そのため、日本国内不動産セクターに対して実質的な積立投資エクスポージャがある前提もポートフォリオ文脈に含めること
- 半導体エクスポージャ(Direct): 13.83%
- AIインフラ感応度(Indirect): 1.31%
- 指値設定は前月末または当月初に実施しうるため、snapshot_date が月末でも翌月の指値設定として解釈してよい
- 指値設定基準値は先月平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均を使う

## 2. この月の snapshot 要約
- LIQUIDITY | liquidity | value_jpy=14644262 | price=null | quantity=null
- 7203 | jun_core | value_jpy=2498400 | price=3123 | quantity=800
- 9444 | satellite | value_jpy=556500 | price=371 | quantity=1500
- 2353 | satellite | value_jpy=25100 | price=251 | quantity=100
- 7201 | satellite | value_jpy=35820 | price=358 | quantity=100
- SMH | satellite_core | value_jpy=76989 | price=481.85 | quantity=1
- PLTR | satellite | value_jpy=203580 | price=141.57 | quantity=9
- CIBR | satellite_core | value_jpy=936298 | price=66.59 | quantity=88
- MSFT | jun_core | value_jpy=464999 | price=415.75 | quantity=7
- URA | satellite_core (raw=satellite, reason=symbol_to_bucket) | value_jpy=613548 | price=56.47 | quantity=68
- NISSEI_SOX_1 | satellite_core | value_jpy=3265621 | price=37930 | quantity=860960
- NISSEI_SOX_2 | satellite_core | value_jpy=1576576 | price=37930 | quantity=415654
- RAKUTEN_PLUS_ALL_COUNTRY_1 | core | value_jpy=1858647 | price=18460 | quantity=1006851
- RAKUTEN_PLUS_ALL_COUNTRY_2 | core | value_jpy=1339620 | price=18460 | quantity=725688
- RAKUTEN_PLUS_SP500 | core | value_jpy=197784 | price=18566 | quantity=106530
- EMAXIS_SLIM_SP500_1 | core | value_jpy=452649 | price=41725 | quantity=108484
- EMAXIS_SLIM_SP500_2 | core | value_jpy=1561884 | price=41725 | quantity=374328
- EMAXIS_SLIM_SP500_3 | core | value_jpy=955482 | price=41725 | quantity=228995
- EMAXIS_SLIM_ALL_COUNTRY | core | value_jpy=524645 | price=35810 | quantity=146508
- PENSION_EMAXIS_SLIM_ALL_COUNTRY | pension | value_jpy=3754327 | price=3754327 | quantity=null
- POINTS_MILES | other | value_jpy=16214 | price=null | quantity=null

## 3. 現在の資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 6890711 | 19.38% | 45.00% | -25.62% |
| jun_core | 2963399 | 8.33% | 20.00% | -11.67% |
| liquidity | 14644262 | 41.18% | 10.00% | 31.18% |
| other | 16214 | 0.05% | - | - |
| pension | 3754327 | 10.56% | - | - |
| satellite | 821000 | 2.31% | 10.00% | -7.69% |
| satellite_core | 6469032 | 18.19% | 15.00% | 3.19% |

## 4. 対象銘柄ごとの候補
| symbol | bucket | current_price | base_price | avg20_base_price | drawdown_rule | limit_price | avg20_gap_pct | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt | explanation |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| CIBR | satellite_core | 67.2400 | 64.4873 | 64.4873 | -5% x 1 | 61.26 | -5.00 | 1 | 9761 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 67.2400 | 64.4873 | 64.4873 | -8% x 1 | 59.33 | -8.00 | 1 | 9453 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 67.2400 | 64.4873 | 64.4873 | -12% x 1 | 56.75 | -12.00 | 1 | 9042 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 55.3100 | 50.8060 | 50.8060 | -6% x 2 | 47.76 | -6.00 | 2 | 15219 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 55.3100 | 50.8060 | 50.8060 | -10% x 2 | 45.73 | -9.99 | 2 | 14573 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_deep_only_due_to_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 55.3100 | 50.8060 | 50.8060 | -15% x 2 | 43.19 | -14.99 | 2 | 13763 | no | - | - | deep_drawdown_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:low,default_allow_deep_drawdown_even_if_bucket_over_target,mode_context:rebalance,mode_priority_weight:-1,mode_rebalance_relative_deprioritization | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:low', 'default_allow_deep_drawdown_even_if_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.1819'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 143.0900 | 146.1227 | 146.1227 | -10% x 1 | 131.51 | -10.00 | 1 | 20954 | yes | high_volatility_shallow_suppressed | High-volatility names default to deeper pullbacks before adding. | high_volatility_name,rule_based_high_volatility_shallow_suppression,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization,high_volatility_shallow_suppressed | {'rule_based_reason': ['rule_based_high_volatility_shallow_suppression'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0231'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': True, 'reason_code': 'high_volatility_shallow_suppressed', 'reason_text': 'High-volatility names default to deeper pullbacks before adding.'}} |
| PLTR | satellite | 143.0900 | 146.1227 | 146.1227 | -15% x 2 | 124.20 | -15.00 | 2 | 39578 | no | - | - | deep_drawdown_candidate,high_volatility_name,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0231'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 143.0900 | 146.1227 | 146.1227 | -22% x 2 | 113.98 | -22.00 | 2 | 36322 | no | - | - | deep_drawdown_candidate,high_volatility_name,mode_context:rebalance,mode_priority_weight:-2,mode_rebalance_relative_deprioritization | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0231'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': -2}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 424.6200 | 389.6593 | 389.6593 | -6% x 1 | 366.28 | -6.00 | 1 | 58360 | no | - | - | shallow_candidate,mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0833'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 424.6200 | 389.6593 | 389.6593 | -10% x 2 | 350.69 | -10.00 | 2 | 111753 | no | - | - | mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0833'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 424.6200 | 389.6593 | 389.6593 | -18% x 2 | 319.52 | -18.00 | 2 | 101820 | no | - | - | deep_drawdown_candidate,mode_context:rebalance,mode_priority_weight:3,mode_rebalance_priority_boost | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0833'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'rebalance', 'priority_weight': 3}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |

## 5. コア定額買い判定材料
- core_actual_pct: 19.38%
- core_target_pct: 45.00%
- core_delta_pct: -25.62%
- liquidity_actual_pct: 41.18%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 31.18%
- core_bucket_total_jpy: 6890711
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
- core_budget_explanation: {'rule_based_reason': 'rebalance_mode_core_underweight_and_cash_overweight', 'discretionary_reason': None, 'related_bucket_status': {'core_actual_pct': Decimal('0.1938'), 'core_target_pct': Decimal('0.45'), 'liquidity_actual_pct': Decimal('0.4118'), 'liquidity_target_pct': Decimal('0.1')}, 'mode_context': {'active_mode': 'rebalance', 'rebalance_mode_active': True, 'rebalance_mode_reason': 'rebalance_mode_core_underweight_and_cash_overweight', 'rebalance_mode_description': 'core不足と現金過多が大きい局面で、月次の配分是正速度を上げる補助モード'}}
| symbol | quantity | value_jpy | current_price | reference_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| RAKUTEN_PLUS_ALL_COUNTRY_1 | 1006851 | 1858647 | 18460 | - | null | null | null | null |
| RAKUTEN_PLUS_ALL_COUNTRY_2 | 725688 | 1339620 | 18460 | - | null | null | null | null |
| RAKUTEN_PLUS_SP500 | 106530 | 197784 | 18566 | - | null | null | null | null |
| EMAXIS_SLIM_SP500_1 | 108484 | 452649 | 41725 | - | null | null | null | null |
| EMAXIS_SLIM_SP500_2 | 374328 | 1561884 | 41725 | - | null | null | null | null |
| EMAXIS_SLIM_SP500_3 | 228995 | 955482 | 41725 | - | null | null | null | null |
| EMAXIS_SLIM_ALL_COUNTRY | 146508 | 524645 | 35810 | - | null | null | null | null |

## 5-1. Coreスポット買い判断材料
- liquidity_actual_pct: 41.18%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 31.18%
- core_actual_pct: 19.38%
- core_target_pct: 45.00%
- core_delta_pct: -25.62%
- jun_core_actual_pct: 8.33%
- jun_core_target_pct: 20.00%
- jun_core_delta_pct: -11.67%
- current_monthly_core_auto_invest_amount_jpy: 750000
- annualized_core_auto_invest_amount_jpy: 9000000
- current_cash_jpy: 14644262
- bond_like_holdings_present: False
- bond_like_holdings: None
- emergency_fund_managed_separately: None
- near_term_large_expense: None
| reference_symbol | one_month_return_pct | three_month_return_pct | one_month_drawdown_from_high_pct | three_month_drawdown_from_high_pct |
| --- | ---: | ---: | ---: | ---: |
| - | null | null | null | null |
- portfolio_risk_bucket_summary:
  - core: actual_pct=19.38%, target_pct=45.00%, delta_pct=-25.62%
  - jun_core: actual_pct=8.33%, target_pct=20.00%, delta_pct=-11.67%
  - liquidity: actual_pct=41.18%, target_pct=10.00%, delta_pct=31.18%
  - other: actual_pct=0.05%, target_pct=null, delta_pct=null
  - pension: actual_pct=10.56%, target_pct=null, delta_pct=null
  - satellite: actual_pct=2.31%, target_pct=10.00%, delta_pct=-7.69%
  - satellite_core: actual_pct=18.19%, target_pct=15.00%, delta_pct=3.19%

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
- current_price: 506.4400
- recent_high_21d: 506.4400
- recent_high_63d: 506.4400
- drawdown_pct_from_21d_high: 0.00
- drawdown_pct_from_63d_high: 0.00
- buy_zone_rule_text: drawdown from 63d high between -10% and -5%
- within_buy_zone_boolean: False
- near_boundary_boolean: False
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}
- related_bucket_actual_pct: 18.19%
- related_bucket_target_pct: 15.00%
- semiconductor_exposure_total_pct: 13.83%
- priority_lowered_boolean: True
- priority_lowered_reason: related_bucket_over_target
- explanation: {'buy_zone_assessment': {'within_buy_zone': False, 'near_boundary': False, 'drawdown_pct_from_63d_high': Decimal('0.00'), 'rule': '-10% <= drawdown <= -5%'}, 'bucket_context': {'related_bucket': 'satellite_core', 'related_bucket_actual_pct': Decimal('0.1819'), 'related_bucket_target_pct': Decimal('0.15')}, 'exposure_context': {'semiconductor_direct_exposure_pct': Decimal('0.1383'), 'indirect_ai_infra_exposure_pct': Decimal('0.0131')}}

## 7. 半導体エクスポージャ内訳
- direct_cap_monitor_pct: 13.83%
- direct_cap_monitor_jpy: 4919186
- direct_plus_indirect_watch_metric_pct: 15.14%
- direct_plus_indirect_watch_metric_jpy: 5384185
- direct_semiconductor_exposure_pct: 13.83%
- indirect_ai_infra_exposure_pct: 1.31%
- indirect_ai_infra_exposure_jpy: 464999
- combined_semiconductor_ai_infra_watch_pct: 15.14%
| symbol | value_jpy | bucket | exposure_type | in_direct | in_indirect | inclusion_reason |
| --- | ---: | --- | --- | --- | --- | --- |
| SMH | 76989 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| MSFT | 464999 | jun_core | indirect_ai_infra | no | yes | matched_indirect_ai_infra_rule |
| NISSEI_SOX_1 | 3265621 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| NISSEI_SOX_2 | 1576576 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |

## 8. 長期シナリオ点検対象
| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| URA | satellite_core | 613548 | 1.73% | nuclear_revival | 脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。 | 炭素回収技術の量産化・低コスト化; 再エネ＋蓄電の経済性改善; 政策転換; 原子力新設の採算悪化 | high | yes |
| CIBR | satellite_core | 936298 | 2.63% | persistent_cybersecurity_spending | サイバーセキュリティ支出は構造的に維持・拡大するという仮説。 | 支出成長の鈍化; バリュエーション過熱後の長期低迷 | medium | yes |
| MSFT | jun_core | 464999 | 1.31% | hyperscaler_ai_platform_compounding | クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。 | AI投資回収の停滞; 規制強化; 競争優位の低下 | medium | yes |
| PLTR | satellite | 203580 | 0.57% | defense_ai_gov_software_scaling | 政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。 | 政府需要の鈍化; 競争激化; 収益化の鈍化 | medium | yes |

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
- [info] core_below_range: Bucket core is below preferred range: 19.38% < 35.00%
- [info] jun_core_below_range: Bucket jun_core is below preferred range: 8.33% < 10.00%
- [warning] liquidity_above_range: Bucket liquidity is above preferred range: 41.18% > 15.00%
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 41.18% > 10.00%
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: URA: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: URA: Shallow candidate suppressed because related bucket is over target.
- [warning] high_volatility_shallow_suppressed: PLTR: High-volatility names default to deeper pullbacks before adding.
- [warning] missing_core_market_reference: Core constituent RAKUTEN_PLUS_ALL_COUNTRY_1 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent RAKUTEN_PLUS_ALL_COUNTRY_2 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent RAKUTEN_PLUS_SP500 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent EMAXIS_SLIM_SP500_1 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent EMAXIS_SLIM_SP500_2 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent EMAXIS_SLIM_SP500_3 is missing market reference data.
- [warning] missing_core_market_reference: Core constituent EMAXIS_SLIM_ALL_COUNTRY is missing market reference data.
- [info] missing_quantity: Holding LIQUIDITY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding LIQUIDITY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding LIQUIDITY is missing current_price; stored as null.
- [info] missing_quantity: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing quantity; stored as null.
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
  - core_reference_missing_symbols: ['EMAXIS_SLIM_ALL_COUNTRY', 'EMAXIS_SLIM_SP500_1', 'EMAXIS_SLIM_SP500_2', 'EMAXIS_SLIM_SP500_3', 'RAKUTEN_PLUS_ALL_COUNTRY_1', 'RAKUTEN_PLUS_ALL_COUNTRY_2', 'RAKUTEN_PLUS_SP500']
  - tradable_core_pct: 19.38%
  - effective_core_including_pension_pct: 29.94%
  - cash_normalization_months_estimate: 7.6
  - direct_cap_monitor_pct: 13.83%
  - direct_plus_indirect_watch_metric_pct: 15.14%
  - direct_semiconductor_exposure_pct: 13.83%
  - combined_semiconductor_ai_infra_watch_pct: 15.14%
  - indirect_ai_infra_exposure_pct: 1.31%

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

指値設定対象月キー: 2026_05
