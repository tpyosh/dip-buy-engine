あなたは、月次レビュー用の判断材料を読む投資アシスタントです。
以下の数値は Python スクリプトが整形したものであり、必要に応じて妥当性を疑ってください。
ただし、Python スクリプトは投資判断エンジンではなく、判断材料の整形エンジンです。
数値の再計算やスクリプトの結論追認ではなく、ポートフォリオ管理・リスク管理・月次レビュー・四半期ルール見直しの観点から評価してください。
月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。

目的:
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
- 各銘柄について、提案する指値段数は 0段以上の任意とする
- Python が出した候補段数に縛られず、0段、1段、2段、3段以上のいずれでもよい
- 0段にする場合は、その銘柄は今月は見送ると明記する
- Python 候補より少ない段数しか提案しない場合は、それが「ルール上そう判断した」のか「今月の裁量判断」なのかを明記する
- Python 候補より多い段数を提案する場合も、なぜ段数を増やすのか理由を明記する

必須出力形式:
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
| symbol | bucket | current_price | base_price | drawdown_rule | limit_price | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| CIBR | satellite_core | 66.0000 | 65.0615 | -5% x 1 | 61.81 | 1 | 9737 | no | - | - | shallow_candidate,bucket_over_target,default_deep_only_due_to_bucket_over_target |
| CIBR | satellite_core | 66.0000 | 65.0615 | -8% x 1 | 59.86 | 1 | 9430 | no | - | - | bucket_over_target,default_deep_only_due_to_bucket_over_target |
| CIBR | satellite_core | 66.0000 | 65.0615 | -12% x 1 | 57.25 | 1 | 9019 | no | - | - | bucket_over_target,default_deep_only_due_to_bucket_over_target |
| URA | satellite_core | 48.7800 | 53.1685 | -6% x 2 | 49.98 | 2 | 15747 | yes | limit_above_current | Calculated limit price is not below the current price. | shallow_candidate,bucket_over_target,default_deep_only_due_to_bucket_over_target,limit_above_current |
| URA | satellite_core | 48.7800 | 53.1685 | -10% x 2 | 47.85 | 2 | 15076 | no | - | - | bucket_over_target,default_deep_only_due_to_bucket_over_target |
| URA | satellite_core | 48.7800 | 53.1685 | -15% x 2 | 45.19 | 2 | 14238 | no | - | - | deep_drawdown_candidate,bucket_over_target,default_allow_deep_drawdown_even_if_bucket_over_target |
| PLTR | satellite | 157.1600 | 138.7620 | -10% x 1 | 124.89 | 1 | 19674 | yes | high_volatility_shallow_suppressed | High-volatility names default to deeper pullbacks before adding. | high_volatility_name,rule_based_high_volatility_shallow_suppression,high_volatility_shallow_suppressed |
| PLTR | satellite | 157.1600 | 138.7620 | -15% x 2 | 117.95 | 2 | 37162 | no | - | - | deep_drawdown_candidate,high_volatility_name |
| PLTR | satellite | 157.1600 | 138.7620 | -22% x 2 | 108.23 | 2 | 34100 | no | - | - | deep_drawdown_candidate,high_volatility_name |
| MSFT | jun_core | 408.9600 | 401.1770 | -6% x 1 | 377.11 | 1 | 59408 | no | - | - | shallow_candidate |
| MSFT | jun_core | 408.9600 | 401.1770 | -10% x 2 | 361.06 | 2 | 113758 | no | - | - | - |
| MSFT | jun_core | 408.9600 | 401.1770 | -18% x 2 | 328.97 | 2 | 103648 | no | - | - | deep_drawdown_candidate |

## 5. コア定額買い判定材料
- core_actual_pct: 16.88%
- core_target_pct: 45.00%
- core_delta_pct: -28.12%
- liquidity_actual_pct: 44.43%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 34.43%
- core_bucket_total_jpy: 5518029
- monthly_core_budget_policy: {'base_monthly_buy_amount_jpy': 100000, 'monthly_core_buy_budget_min_jpy': 100000, 'monthly_core_buy_budget_max_jpy': 300000, 'budget_tiers': {'standard': {'budget_jpy': 100000}, 'aggressive': {'budget_jpy': 300000}}, 'override_conditions': {'core_shortfall_pct_gte': 0.15, 'cash_excess_pct_gte': 0.15, 'budget_tier': 'aggressive', 'reason_code': 'core_underweight_and_cash_overweight'}}
- monthly_core_buy_budget_min_jpy: 100000
- monthly_core_buy_budget_max_jpy: 300000
- monthly_core_budget_tier: aggressive
- recommended_monthly_core_buy_budget_jpy: 300000
- monthly_core_budget_override_active: True
- monthly_core_budget_override_reason: core_underweight_and_cash_overweight
| symbol | quantity | value_jpy | current_price | reference_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| RAKUTEN_ALL_COUNTRY_1 | 949731 | 1657376 | 17451 | VT | 141.9300 | 148.9100 | 148.9100 | -4.69 |
| RAKUTEN_ALL_COUNTRY_2 | 725688 | 1266398 | 17451 | VT | 141.9300 | 148.9100 | 148.9100 | -4.69 |
| RAKUTEN_SP500 | 106530 | 186790 | 17534 | VOO | 618.4300 | 638.2300 | 639.7000 | -3.32 |
| EMAXIS_SP500_1 | 44024 | 173481 | 39406 | VOO | 618.4300 | 638.2300 | 639.7000 | -3.32 |
| EMAXIS_SP500_2 | 348947 | 1375061 | 39406 | VOO | 618.4300 | 638.2300 | 639.7000 | -3.32 |
| EMAXIS_SP500_3 | 170193 | 670663 | 39406 | VOO | 618.4300 | 638.2300 | 639.7000 | -3.32 |
| EMAXIS_ALL_COUNTRY | 55611 | 188260 | 33853 | VT | 141.9300 | 148.9100 | 148.9100 | -4.69 |

## 6. SOX 判定材料
- proxy_symbol: SMH
- current_price: 380.5600
- recent_high_21d: 426.1600
- recent_high_63d: 426.1600
- drawdown_pct_from_21d_high: -10.70
- drawdown_pct_from_63d_high: -10.70
- buy_zone_rule_text: drawdown from 63d high between -10% and -5%
- within_buy_zone_boolean: False
- near_boundary_boolean: True
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}
- related_bucket_actual_pct: 16.22%
- related_bucket_target_pct: 15.00%
- semiconductor_exposure_total_pct: 11.83%
- priority_lowered_boolean: True
- priority_lowered_reason: related_bucket_over_target

## 7. 半導体エクスポージャ内訳
- semiconductor_exposure_total_pct: 11.83%
- semiconductor_exposure_total_jpy: 3867660
| symbol | value_jpy | bucket | exposure_type | included_in_semiconductor_exposure | inclusion_reason |
| --- | ---: | --- | --- | --- | --- |
| SMH | 62457 | satellite_core | direct_semiconductor | yes | matched_exposure_group_rule |
| MSFT | 259516 | jun_core | config_optional_symbol | no | config_optional_excluded |
| NISSEI_SOX_1 | 2566263 | satellite_core | direct_semiconductor | yes | matched_exposure_group_rule |
| NISSEI_SOX_2 | 1238940 | satellite_core | direct_semiconductor | yes | matched_exposure_group_rule |

## 8. 長期シナリオ点検対象
| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| URA | satellite_core | 521959 | 1.60% | nuclear_revival | 脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。 | 炭素回収技術の量産化・低コスト化; 再エネ＋蓄電の経済性改善; 政策転換; 原子力新設の採算悪化 | high | yes |
| CIBR | satellite_core | 914628 | 2.80% | persistent_cybersecurity_spending | サイバーセキュリティ支出は構造的に維持・拡大するという仮説。 | 支出成長の鈍化; バリュエーション過熱後の長期低迷 | medium | yes |
| MSFT | jun_core | 259516 | 0.79% | hyperscaler_ai_platform_compounding | クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。 | AI投資回収の停滞; 規制強化; 競争優位の低下 | medium | yes |
| PLTR | satellite | 217069 | 0.66% | defense_ai_gov_software_scaling | 政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。 | 政府需要の鈍化; 競争激化; 収益化の鈍化 | medium | yes |

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
- [info] core_below_range: Bucket core is below preferred range: 16.88% < 35.00%
- [info] jun_core_below_range: Bucket jun_core is below preferred range: 9.40% < 10.00%
- [warning] liquidity_above_range: Bucket liquidity is above preferred range: 44.43% > 15.00%
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 44.43% > 10.00%
- [warning] limit_above_current: URA: Calculated limit price is not below the current price.
- [warning] high_volatility_shallow_suppressed: PLTR: High-volatility names default to deeper pullbacks before adding.
- [info] missing_quantity: Holding CASH_EQUIV is missing quantity; stored as null.
- [info] missing_avg_cost: Holding CASH_EQUIV is missing avg_cost; stored as null.
- [info] missing_current_price: Holding CASH_EQUIV is missing current_price; stored as null.
- [info] missing_quantity: Holding PENSION_EMAXIS_ALL_COUNTRY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding PENSION_EMAXIS_ALL_COUNTRY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding PENSION_EMAXIS_ALL_COUNTRY is missing current_price; stored as null.
- [info] missing_quantity: Holding POINTS_MILES is missing quantity; stored as null.
- [info] missing_avg_cost: Holding POINTS_MILES is missing avg_cost; stored as null.
- [info] missing_current_price: Holding POINTS_MILES is missing current_price; stored as null.

## 11. ChatGPT に期待する出力形式
以下の見出しを維持してください。
月次の執行判断と、四半期単位のルール見直し提案は明確に分離してください。
月次の注文判断・資金配分判断を、四半期ルール見直しセクションに混ぜないでください。
【要約】
- 3〜6行程度で短くまとめる
- 今月の最重要判断
- コア / サテライトの優先順位
- SOXの判定
- ルール改善の要否
- 『今月何をする月か』が一目で分かる内容にする

【今月の指値提案】
- 各銘柄について 0段以上の任意段数で提案してよい
- 0段の場合は『今月は見送り』と明記する
- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する
- Python 候補より段数を増やした場合も、その理由を明記する
- 減段理由テンプレートの例: `ルール上の判断: bucket_over_target のため浅い段を見送る`
- 減段理由テンプレートの例: `今月の裁量判断: core 補強を優先するため段数を減らす`

【コア定額買い方針レビュー】
- コアは今月最低いくら買うべきか
- 安ければ追加でどの程度厚くする考え方が妥当か
- コアとサテライトの資金配分優先順位
- ルール上の判断と今月の裁量判断を分けて説明すること

【SOX投信判定】
- 買う / 買わない
- 理由

【ポートフォリオ診断】
- 現在の偏り
- 注意点
- 今月の補強優先順位

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

## 12. 必須の月次・四半期レビュー観点
- 毎月の運用レビューと四半期ごとのルール変更レビューを分離して評価してください。
- 四半期ルール見直しセクションには、月次の執行判断を混ぜないでください。
- 半導体エクスポージャの合算管理が妥当か確認してください。
- PLTR の浅い押し目候補抑制ロジックの是非を評価してください。
- 指値段数は各銘柄 0段以上の任意とし、1段しか出さない場合はその理由を明記してください。
- コアについては『毎月一定額買う / 安ければ追加で厚く買う』という運用思想の妥当性も評価してください。
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

## 13. 必須の Codex 向け修正要約観点
- must / should / nice_to_have は必ず埋めてください。
- 空欄は不可ですが、該当なしの場合は `なし` と明記してください。
- 【Codex向け修正要約】 全体を単一の ```md コードブロックで出力してください。
- monthly review と quarterly rule review を分けて整理してください。
- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。

月次キー: 2026_03
