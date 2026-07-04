対象月: 2026_07

あなたは、月次レビュー用の判断材料を読む投資アシスタントです。
以下の数値は、Codex が Money Forward スクリーンショットを一次情報として OCR・正規化し、Python スクリプトが整形したものです。必要に応じて妥当性を疑ってください。
ChatGPT は Money Forward スクリーンショットの読取や OCR を担当しません。画像読取は Codex 側で完了済みとして扱い、このプロンプト内の構造化データだけをレビュー対象にしてください。
Money Forward から貼り付けられたテキストが使われている場合でも、それは補助情報です。HTML由来のコピーはレイアウト、列、階層、並び順、カテゴリ対応が崩れている可能性があります。
OCR・正規化・前月差分の検証警告が含まれる場合は、投資判断の前提条件として明示的に扱ってください。
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
- OCR / 正規化 / 前月差分の検証警告
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
- 2026年5月〜12月は coreスポット買いの優先度を上げ、指値候補が出ても coreスポット買い予算を削ってまでテーマ銘柄を買わない
- satellite_core が over target の場合、SOX / CIBR / URA の追加は深い押し目限定とする
- PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定する
- MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先する
- 指値設定基準値は、先月平均ではなくスクリプト実行時点から直近20営業日（約1ヶ月）の終値平均として扱う
- 指値を提案する場合は、各段について「直近20営業日（約1ヶ月）の終値平均」と「その平均から何%下の指値か」を必ず併記する
- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` のパーセンテージとして扱い、マイナス値で明記する

coreスポット買い出力ルール:
- `【今月のcoreスポット買い提案】` では、提案総額、配分先内訳、実行スケジュールを必ず記載する
- 2026年5月〜12月で `nisa_growth_quota_status: exhausted` の場合は、固定core積立額を 100,000円として扱い、NISA成長投資枠750,000円/月を前提にしない
- 2026年5月〜12月で `taxable_core_spot_buy_required: True` の場合は、coreスポット買い提案に `account_type: 特定口座`、理由、税効率メモを必ず明記する
- NISA枠がない月でも core 購入を弱めるのではなく、core不足と現金過多が続く限り、特定口座スポット買いで補う前提で判断する
- 税効率低下よりも core不足と現金過多の是正を優先する。ただし生活防衛資金・住宅ローン・大口支出不明リスクを考慮し、現金を一気に削りすぎない
- 2026年5月〜12月は、固定core積立額、特定口座coreスポット買い提案額、固定積立+スポット買いの合計core投入額を必ず明記する
- 2026年5月〜12月の core スポット買いは、normal 300,000〜600,000円、aggressive 700,000〜1,000,000円、rebalance 1,000,000〜1,500,000円を基本レンジとして扱う
- 2026年5月〜12月の rebalance mode では、固定core積立 100,000円、baseline_total_core_deployment_target_jpy 1,380,000円、baseline_core_spot_buy_jpy 1,280,000円を目安にする。iDeCo55,000円/月とBTC/ETH週次積立もキャッシュアウトとして別枠で考慮し、総投資額は月145万円程度を目安にする。ただし毎月必ず1,280,000円に固定せず、core_delta_pct、cash_excess_pct、current_cash_jpy、生活防衛資金、大口支出不明、相場下落/高値圏、毎月のキャッシュ流入、住宅ローン文脈で調整する
- 単月の core スポット買いは原則1,500,000円を上限とする。例外的に大きな下落局面で上限超過を提案する場合は明確な理由を出す
- coreスポット買いの配分は既存core商品に限定し、新規商品を増やさない。基本は eMAXIS Slim 全世界株式（オール・カントリー）60% / eMAXIS Slim 米国株式（S&P500）40%。米国株・半導体・AIインフラ感応度が高い月はオルカン65% / S&P500 35% などオルカンを厚めにする
- 2026年5月〜12月は、今月の提案が rule-based なのか discretionary なのかを必ず分けて書く
- core を積み増したほうがよい月は、`eMAXIS Slim 米国株式(S&P500)` と `eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)` の今月の積み増しスケジュールを明示する
- `配分先内訳` では銘柄ごとの金額を記載し、合計は提案総額と一致させる
- `実行スケジュール` は Google Calendar の手動発注リマインダー作成に使うため、各行に具体日付、ファンド名、金額を必ず含める
- `実行スケジュール` では `review_target_month` 内の日付を使い、各行を `7月1日: eMAXIS Slim 米国株式(S&P500) 150,000円` の形式で記載する
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
7月1日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 200,000円
7月4日: eMAXIS Slim 米国株式(S&P500) 150,000円
7月11日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 100,000円
7月18日: eMAXIS Slim 米国株式(S&P500) 100,000円
7月25日: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) 100,000円
7月25日: eMAXIS Slim 米国株式(S&P500) 50,000円
```

Codex向け修正要約ルール:
- `【Codex向け修正要約】` は、修正指摘の有無にかかわらず毎回必ず出力する
- コードやルールへの修正指摘が実質的にない月でも、`README.md` の最新月セクションに月次サマリーと今月の指値買い設定を反映する依頼は必ず含める
- 修正指摘がない場合でも、少なくとも `should` には `README.md` へ最新月サマリー・購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する依頼を入れる
- `README.md` 更新依頼だけの月でも、must / should / nice_to_have / 修正目的 / 変更すべき仕様 / 影響範囲 / 推奨テスト を省略しない
- `README.md` 更新依頼を入れる場合は、既存構成を壊さず、最新月セクションの見やすい位置に「今月の指値買い設定」を追加または更新する前提を明記する
- `README.md` 更新依頼には、ルート README へ月次レビュー履歴を蓄積せず、既存の `## Monthly Review: YYYY_MM` を最新月の内容で置換し、過去月の `Monthly Review` セクションを残さない前提を必ず含める

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

## 0. 6月末レトロスペクティブ依頼

このプロンプトは、6月末時点のMoney Forwardスナップショットを使って、6月運用のレトロスペクティブと7月の運用計画を同時に依頼するものです。

6月開始時の前回レビューでは、主な運用案として以下が提示されていました。

- 固定core積立: 100,000円
- coreスポット買い: 900,000円
- 6月のcore投入合計: 1,000,000円
- coreスポット買い配分: eMAXIS Slim 全世界株式（オール・カントリー）585,000円 / eMAXIS Slim 米国株式（S&P500）315,000円
- SOX投信: 追加購入見送り
- 6月の補強優先順位: オルカン > S&P500 > MSFT深めの押し目 > URA深い押し目 > PLTRさらに深い押し目 > CIBR/SOX見送り

6月末スナップショットでは、総資産は 39,370,393円、株式（現物）カテゴリは 5,193,713円、投資信託カテゴリは 16,476,610円、預金・現金・暗号資産カテゴリは 13,620,505円です。前回スナップショットでは総資産 37,592,966円、株式（現物） 5,342,359円、投資信託 14,480,913円、預金・現金・暗号資産 13,749,225円でした。

お願いしたいこと:

- まず、6月の運用が前回方針に対してどう進んだように見えるかを、事実・推定・不明点に分けてレトロスペクティブしてください。
- 6月の実際の取引明細はこのプロンプトに含まれていないため、投資信託カテゴリ増加をそのまま実行済み購入と断定しないでください。
- 株式（現物）は追加スクリーンショットで個別明細を確認済みです。ただし明細表示値合計 5,193,712円 とカテゴリ合計 5,193,713円 に1円差があるため、Money Forwardの表示丸めとして扱ってください。
- PLTRは9株から11株、MSFTは7株から9株、URAは68株から70株に増えています。6月の指値や裁量買いの可能性がありますが、取引明細は未確認なので断定しないでください。
- そのうえで、7月のcoreスポット買い、指値設定、SOX投信判定、長期シナリオ点検、ルール見直しを提案してください。


## 1. 前提
- snapshot_date: 2026-06-28
- review_target_month: 2026_07
- currency_base: JPY
- total_assets_jpy: 39370393
- liquidity_target_jpy: null
- holdings_count: 21
- スナップショットは Money Forward スクリーンショットを一次情報として Codex が OCR・正規化したものとして扱うこと
- ChatGPT は Money Forward スクリーンショットの読取や OCR を担当しないこと。画像読取は Codex 側で完了済みとして扱い、このプロンプト内の構造化データだけをレビューすること
- Money Forward から貼り付けられたテキストがある場合でも、それは補助情報であり、HTML由来でレイアウト・列・階層・並び順が崩れている可能性がある
- OCR・正規化・前月差分の検証警告は後続の警告一覧に含めているため、投資レビューでは警告を前提条件として扱うこと
- 毎月の税引前キャッシュ流入はおおむね60万〜70万円ある前提で、生活防衛資金の必要水準を評価すること
- 名古屋市中区・金山駅近くの流動性が高いマンション（約6500万円）を住居兼資産として保有している
- 上記マンションはフルローンで購入しており、ローン返済はまだほとんど進んでいない
- そのため、日本国内不動産セクターに対して実質的な積立投資エクスポージャがある前提もポートフォリオ文脈に含めること
- 半導体エクスポージャ(Direct): 17.80%
- AIインフラ感応度(Indirect): 1.38%
- 指値設定は前月末または当月初に実施しうるため、snapshot_date が月末でも翌月の指値設定として解釈してよい
- 指値設定基準値は先月平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均を使う

## 2. この月の snapshot 要約
- LIQUIDITY | liquidity | value_jpy=13620505 | price=null | quantity=null | source_category=預金・現金・暗号資産 | notes=内訳: PayPay -130,485円; モバイルSuica 1,915円; 三菱UFJ銀行 普通 2,928,471円; 楽天銀行 円預金(普通預金) 8,471,062円; 楽天証券 米ドル 606,738円; 野村証券 MRF 1,742,804円。
- 7203 | jun_core | value_jpy=2214400 | price=2768 | quantity=800 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=1788800 | notes=前日比 0円、評価損益率 420.30%。
- 9444 | satellite | value_jpy=373500 | price=249 | quantity=1500 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=-568500 | notes=前日比 0円、評価損益率 -60.35%。
- 2353 | satellite | value_jpy=24600 | price=246 | quantity=100 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=-1900 | notes=前日比 0円、評価損益率 -7.17%。
- 7201 | satellite | value_jpy=30000 | price=300 | quantity=100 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-6755 | notes=前日比 0円、評価損益率 -18.38%。
- SMH | satellite_core | value_jpy=98921 | price=611.61 | quantity=1 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=39138 | notes=前日比 0円、評価損益率 65.47%。
- PLTR | satellite | value_jpy=200918 | price=112.93 | quantity=11 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-68130 | notes=前日比 0円、評価損益率 -25.32%。
- CIBR | satellite_core | value_jpy=1214939 | price=85.36 | quantity=88 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=123869 | notes=前日比 0円、評価損益率 11.35%。
- MSFT | jun_core | value_jpy=542917 | price=372.97 | quantity=9 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-37507 | notes=前日比 0円、評価損益率 -6.46%。
- URA | satellite_core (raw=satellite, reason=symbol_to_bucket) | value_jpy=493517 | price=43.59 | quantity=70 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-30107 | notes=前日比 0円、評価損益率 -5.75%。config/portfolio_policy.yaml では satellite_core に解決される。
- NISSEI_SOX_1 | satellite_core | value_jpy=4660463 | price=54131 | quantity=860960 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=3300005 | notes=前日比 0円、評価損益率 242.57%。
- NISSEI_SOX_2 | satellite_core | value_jpy=2249977 | price=54131 | quantity=415654 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=1649977 | notes=前日比 0円、評価損益率 275.00%。
- RAKUTEN_PLUS_ALL_COUNTRY_1 | core | value_jpy=2060012 | price=19442 | quantity=1059568 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=560012 | notes=前日比 0円、評価損益率 37.33%。
- RAKUTEN_PLUS_ALL_COUNTRY_2 | core | value_jpy=1646728 | price=19442 | quantity=846995 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=146727 | notes=前日比 0円、評価損益率 9.78%。
- RAKUTEN_PLUS_SP500 | core | value_jpy=207488 | price=19477 | quantity=106530 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=82688 | notes=前日比 0円、評価損益率 66.26%。
- EMAXIS_SLIM_SP500_1 | core | value_jpy=1168489 | price=43772 | quantity=266949 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=55489 | notes=前日比 0円、評価損益率 4.99%。
- EMAXIS_SLIM_SP500_2 | core | value_jpy=1740046 | price=43772 | quantity=397525 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=425046 | notes=前日比 0円、評価損益率 32.32%。
- EMAXIS_SLIM_SP500_3 | core | value_jpy=1002357 | price=43772 | quantity=228995 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=102357 | notes=前日比 0円、評価損益率 11.37%。
- EMAXIS_SLIM_ALL_COUNTRY | core | value_jpy=1741050 | price=37729 | quantity=461462 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=84050 | notes=前日比 0円、評価損益率 5.07%。
- PENSION_EMAXIS_SLIM_ALL_COUNTRY | pension | value_jpy=4063372 | price=null | quantity=null | source_category=年金 | account_type=iDeCo | profit_loss_jpy=722677 | notes=Money Forward画面では年金カテゴリの詳細1行を確認。取得価額 3,340,695円、現在価値 4,063,372円、評価損益率 21.63%。
- POINTS_MILES | other | value_jpy=16193 | price=null | quantity=null | source_category=ポイント | notes=内訳詳細は今回の画像に含まれていないため、カテゴリ合計のみ記録。

## 3. 現在の資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 9566170 | 24.30% | 45.00% | -20.70% |
| jun_core | 2757317 | 7.00% | 20.00% | -13.00% |
| liquidity | 13620505 | 34.60% | 10.00% | 24.60% |
| other | 16193 | 0.04% | - | - |
| pension | 4063372 | 10.32% | - | - |
| satellite | 629018 | 1.60% | 10.00% | -8.40% |
| satellite_core | 8717817 | 22.14% | 15.00% | 7.14% |

## 4. 対象銘柄ごとの候補
| symbol | bucket | current_price | snapshot_price_source_date | market_candidate_price_source_date | base_price | avg20_base_price | drawdown_rule | limit_price | avg20_gap_pct | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt | explanation |
| --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| CIBR | satellite_core | 85.3600 | 2026-06-28 | 2026-06-26 | 84.9617 | 84.9617 | -5% x 1 | 80.71 | -5.00 | 1 | 13050 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | drawdown_profile:shallow,shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_deep_only_due_to_bucket_over_target,mode_context:normal,mode_priority_weight:0,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 85.3600 | 2026-06-28 | 2026-06-26 | 84.9617 | 84.9617 | -8% x 1 | 78.16 | -8.01 | 1 | 12637 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | drawdown_profile:shallow,shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_deep_only_due_to_bucket_over_target,mode_context:normal,mode_priority_weight:0,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| CIBR | satellite_core | 85.3600 | 2026-06-28 | 2026-06-26 | 84.9617 | 84.9617 | -12% x 1 | 74.77 | -12.00 | 1 | 12089 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | drawdown_profile:shallow,shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_deep_only_due_to_bucket_over_target,mode_context:normal,mode_priority_weight:0,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 43.5900 | 2026-06-28 | 2026-06-26 | 47.8267 | 47.8267 | -6% x 2 | 44.96 | -5.99 | 2 | 14539 | yes | limit_above_current | Calculated limit price is not below the current price. | drawdown_profile:shallow,shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_deep_only_due_to_bucket_over_target,mode_context:normal,mode_priority_weight:0,limit_above_current | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 43.5900 | 2026-06-28 | 2026-06-26 | 47.8267 | 47.8267 | -10% x 2 | 43.04 | -10.01 | 2 | 13918 | yes | bucket_over_target_shallow_suppressed | Shallow candidate suppressed because related bucket is over target. | drawdown_profile:shallow,shallow_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_deep_only_due_to_bucket_over_target,mode_context:normal,mode_priority_weight:0,bucket_over_target_shallow_suppressed | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_deep_only_due_to_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': True, 'reason_code': 'bucket_over_target_shallow_suppressed', 'reason_text': 'Shallow candidate suppressed because related bucket is over target.'}} |
| URA | satellite_core | 43.5900 | 2026-06-28 | 2026-06-26 | 47.8267 | 47.8267 | -15% x 2 | 40.65 | -15.01 | 2 | 13145 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,bucket_over_target,auto_tranche_adjustment_bucket_over_target:medium,bucket_over_target_deep_threshold_pct:-15,default_allow_deep_drawdown_even_if_bucket_over_target,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': ['auto_tranche_adjustment_bucket_over_target:medium', 'bucket_over_target_deep_threshold_pct:-15', 'default_allow_deep_drawdown_even_if_bucket_over_target'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2214'), 'target_pct': Decimal('0.15'), 'is_over_target': True}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 112.9300 | 2026-06-28 | 2026-06-26 | 133.5195 | 133.5195 | -10% x 1 | 120.17 | -10.00 | 1 | 19430 | yes | limit_above_current | Calculated limit price is not below the current price. | drawdown_profile:shallow,shallow_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,rule_based_high_volatility_shallow_suppression,mode_context:normal,mode_priority_weight:-1,limit_above_current | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12', 'rule_based_high_volatility_shallow_suppression'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0160'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'high_volatility_shallow_suppressed', 'reason_text': 'High-volatility names default to deeper pullbacks before adding.'}} |
| PLTR | satellite | 112.9300 | 2026-06-28 | 2026-06-26 | 133.5195 | 133.5195 | -15% x 2 | 113.49 | -15.00 | 2 | 36699 | yes | limit_above_current | Calculated limit price is not below the current price. | drawdown_profile:deep,deep_drawdown_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,mode_context:normal,mode_priority_weight:-1,limit_above_current | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0160'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 112.9300 | 2026-06-28 | 2026-06-26 | 133.5195 | 133.5195 | -22% x 2 | 104.15 | -22.00 | 2 | 33679 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,mode_context:normal,mode_priority_weight:-1 | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0160'), 'target_pct': Decimal('0.1'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 372.9700 | 2026-06-28 | 2026-06-26 | 406.2960 | 406.2960 | -6% x 1 | 381.92 | -6.00 | 1 | 61751 | yes | limit_above_current | Calculated limit price is not below the current price. | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:1,limit_above_current | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0700'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 372.9700 | 2026-06-28 | 2026-06-26 | 406.2960 | 406.2960 | -10% x 2 | 365.67 | -10.00 | 2 | 118247 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:1 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0700'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 372.9700 | 2026-06-28 | 2026-06-26 | 406.2960 | 406.2960 | -18% x 2 | 333.16 | -18.00 | 2 | 107734 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,mode_context:normal,mode_priority_weight:1 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0700'), 'target_pct': Decimal('0.2'), 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |

Candidate availability notes:
- CIBR: 今月は eligible deep candidate なし。bucket over target のため浅い候補は suppressed され、設定済み候補に deep threshold 以下の段がありません。

## 5. コア定額買い判定材料
- core_actual_pct: 24.30%
- core_target_pct: 45.00%
- core_delta_pct: -20.70%
- liquidity_actual_pct: 34.60%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 24.60%
- core_bucket_total_jpy: 9566170
- monthly_core_budget_policy: {'base_monthly_buy_amount_jpy': 100000, 'monthly_core_buy_budget_min_jpy': 300000, 'monthly_core_buy_budget_max_jpy': 1500000, 'budget_tiers': {'standard': {'budget_jpy': 300000, 'min_jpy': 300000, 'max_jpy': 600000, 'description': 'Normal mode: core不足はあるが現金過多が軽度、または相場が高値圏'}, 'aggressive': {'budget_jpy': 900000, 'min_jpy': 700000, 'max_jpy': 1000000, 'description': 'Aggressive mode: core不足が大きく、liquidityがtargetを大きく上回る'}, 'rebalance': {'budget_jpy': 1280000, 'min_jpy': 1000000, 'max_jpy': 1500000, 'description': 'Rebalance mode: 現在の固定積立等を踏まえて特定口座スポットで補う'}}, 'override_conditions': {'core_shortfall_pct_gte': 0.15, 'cash_excess_pct_gte': 0.15, 'budget_tier': 'aggressive', 'reason_code': 'nisa_exhaustion_core_underweight_and_cash_overweight'}, 'rebalance_mode': {'enabled': True, 'core_shortfall_pct_gte': 0.25, 'cash_excess_pct_gte': 0.25, 'monthly_core_buy_budget_max_jpy': 1500000, 'budget_tier': 'rebalance', 'reason_code': 'nisa_exhaustion_rebalance_core_underweight_and_cash_overweight', 'description': '2026年5月〜12月は固定core積立が100,000円/月のため、core不足と現金過多が大きい月は特定口座スポット買いで是正速度を維持する'}, 'active_from': '2026-05', 'active_to': '2026-12', 'reason_code': 'nisa_growth_quota_exhausted_2026', 'reason': '2026年NISA成長投資枠を使い切ったため', 'nisa_growth_quota_status': 'exhausted', 'taxable_core_spot_buy_required': True, 'core_spot_buy_account_type': '特定口座', 'fixed_core_auto_invest_jpy': 100000, 'baseline_total_core_deployment_target_jpy': 1380000, 'baseline_core_spot_buy_jpy': 1280000, 'hard_cap_core_spot_buy_jpy': 1500000, 'spot_buy_bands': {'normal': {'min_jpy': 300000, 'max_jpy': 600000, 'conditions': ['core不足はあるが、現金過多が軽度', '相場が高値圏で、急いで投入する必要が低い']}, 'aggressive': {'min_jpy': 700000, 'max_jpy': 1000000, 'conditions': ['core不足が大きい', 'liquidity が target を大きく上回る', 'ただし rebalance mode ほどではない']}, 'rebalance': {'min_jpy': 1000000, 'max_jpy': 1500000, 'conditions': ['core_delta_pct <= -25pt 程度', 'cash_excess_pct >= +25pt 程度', '生活防衛資金を残しても現金過多が明確', '現在の固定積立等を踏まえて特定口座スポットで補う必要がある']}}, 'hard_cap_note': '単月のcoreスポット買いは原則1,500,000円を上限とし、例外的に大きな下落局面で上限超過を提案する場合は明確な理由を出す', 'satellite_interaction_policy': ['satellite_core が over target の場合、SOX / CIBR / URA の追加は深い押し目限定', 'PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定', 'MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先', '指値候補が出ても、coreスポット買い予算を削ってまでテーマ銘柄を買わない'], 'date_based_override_active': True, 'active_date_based_override': {'active_from': '2026-05', 'active_to': '2026-12', 'reason_code': 'nisa_growth_quota_exhausted_2026', 'reason': '2026年NISA成長投資枠を使い切ったため', 'nisa_growth_quota_status': 'exhausted', 'taxable_core_spot_buy_required': True, 'core_spot_buy_account_type': '特定口座', 'fixed_core_auto_invest_jpy': 100000, 'baseline_total_core_deployment_target_jpy': 1380000, 'baseline_core_spot_buy_jpy': 1280000, 'hard_cap_core_spot_buy_jpy': 1500000, 'monthly_core_buy_budget_min_jpy': 300000, 'monthly_core_buy_budget_max_jpy': 1500000, 'budget_tiers': {'standard': {'budget_jpy': 300000, 'min_jpy': 300000, 'max_jpy': 600000, 'description': 'Normal mode: core不足はあるが現金過多が軽度、または相場が高値圏'}, 'aggressive': {'budget_jpy': 900000, 'min_jpy': 700000, 'max_jpy': 1000000, 'description': 'Aggressive mode: core不足が大きく、liquidityがtargetを大きく上回る'}, 'rebalance': {'budget_jpy': 1280000, 'min_jpy': 1000000, 'max_jpy': 1500000, 'description': 'Rebalance mode: 現在の固定積立等を踏まえて特定口座スポットで補う'}}, 'override_conditions': {'core_shortfall_pct_gte': 0.15, 'cash_excess_pct_gte': 0.15, 'budget_tier': 'aggressive', 'reason_code': 'nisa_exhaustion_core_underweight_and_cash_overweight'}, 'rebalance_mode': {'enabled': True, 'core_shortfall_pct_gte': 0.25, 'cash_excess_pct_gte': 0.25, 'monthly_core_buy_budget_max_jpy': 1500000, 'budget_tier': 'rebalance', 'reason_code': 'nisa_exhaustion_rebalance_core_underweight_and_cash_overweight', 'description': '2026年5月〜12月は固定core積立が100,000円/月のため、core不足と現金過多が大きい月は特定口座スポット買いで是正速度を維持する'}, 'spot_buy_bands': {'normal': {'min_jpy': 300000, 'max_jpy': 600000, 'conditions': ['core不足はあるが、現金過多が軽度', '相場が高値圏で、急いで投入する必要が低い']}, 'aggressive': {'min_jpy': 700000, 'max_jpy': 1000000, 'conditions': ['core不足が大きい', 'liquidity が target を大きく上回る', 'ただし rebalance mode ほどではない']}, 'rebalance': {'min_jpy': 1000000, 'max_jpy': 1500000, 'conditions': ['core_delta_pct <= -25pt 程度', 'cash_excess_pct >= +25pt 程度', '生活防衛資金を残しても現金過多が明確', '現在の固定積立等を踏まえて特定口座スポットで補う必要がある']}}, 'hard_cap_note': '単月のcoreスポット買いは原則1,500,000円を上限とし、例外的に大きな下落局面で上限超過を提案する場合は明確な理由を出す', 'satellite_interaction_policy': ['satellite_core が over target の場合、SOX / CIBR / URA の追加は深い押し目限定', 'PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定', 'MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先', '指値候補が出ても、coreスポット買い予算を削ってまでテーマ銘柄を買わない']}}
- monthly_core_buy_budget_min_jpy: 300000
- monthly_core_buy_budget_max_jpy: 1500000
- monthly_core_budget_tier: aggressive
- monthly_core_budget_band: {'min_jpy': 700000, 'max_jpy': 1000000, 'description': 'Aggressive mode: core不足が大きく、liquidityがtargetを大きく上回る'}
- recommended_monthly_core_buy_budget_jpy: 900000
- monthly_core_budget_override_active: True
- monthly_core_budget_override_reason: nisa_exhaustion_core_underweight_and_cash_overweight
- portfolio_management_mode: normal_with_override
- rebalance_mode_active: False
- rebalance_mode_reason: -
- date_based_core_budget_override_active: True
- nisa_growth_quota_status: exhausted
- taxable_core_spot_buy_required: True
- core_spot_buy_account_type: 特定口座
- fixed_core_auto_invest_jpy: 100000
- baseline_total_core_deployment_target_jpy: 1380000
- baseline_core_spot_buy_jpy: 1280000
- hard_cap_core_spot_buy_jpy: 1500000
- spot_buy_bands: {'normal': {'min_jpy': 300000, 'max_jpy': 600000, 'conditions': ['core不足はあるが、現金過多が軽度', '相場が高値圏で、急いで投入する必要が低い']}, 'aggressive': {'min_jpy': 700000, 'max_jpy': 1000000, 'conditions': ['core不足が大きい', 'liquidity が target を大きく上回る', 'ただし rebalance mode ほどではない']}, 'rebalance': {'min_jpy': 1000000, 'max_jpy': 1500000, 'conditions': ['core_delta_pct <= -25pt 程度', 'cash_excess_pct >= +25pt 程度', '生活防衛資金を残しても現金過多が明確', '現在の固定積立等を踏まえて特定口座スポットで補う必要がある']}}
- satellite_interaction_policy: ['satellite_core が over target の場合、SOX / CIBR / URA の追加は深い押し目限定', 'PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定', 'MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先', '指値候補が出ても、coreスポット買い予算を削ってまでテーマ銘柄を買わない']
- core_budget_explanation: {'rule_based_reason': 'nisa_exhaustion_core_underweight_and_cash_overweight', 'discretionary_reason': None, 'related_bucket_status': {'core_actual_pct': Decimal('0.2430'), 'core_target_pct': Decimal('0.45'), 'liquidity_actual_pct': Decimal('0.3460'), 'liquidity_target_pct': Decimal('0.1')}, 'mode_context': {'active_mode': 'normal_with_override', 'rebalance_mode_active': False, 'rebalance_mode_reason': None, 'selected_budget_band': {'min_jpy': 700000, 'max_jpy': 1000000, 'description': 'Aggressive mode: core不足が大きく、liquidityがtargetを大きく上回る'}, 'rebalance_mode_description': None}}
| symbol | quantity | value_jpy | current_price | reference_symbol | suggested_proxy_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| RAKUTEN_PLUS_ALL_COUNTRY_1 | 1059568 | 2060012 | 19442 | VT | ACWI | 153.9500 | 159.3500 | 159.3500 | -3.39 |
| RAKUTEN_PLUS_ALL_COUNTRY_2 | 846995 | 1646728 | 19442 | VT | ACWI | 153.9500 | 159.3500 | 159.3500 | -3.39 |
| RAKUTEN_PLUS_SP500 | 106530 | 207488 | 19477 | VOO | VOO | 670.2600 | 698.2600 | 698.2600 | -4.01 |
| EMAXIS_SLIM_SP500_1 | 266949 | 1168489 | 43772 | VOO | VOO | 670.2600 | 698.2600 | 698.2600 | -4.01 |
| EMAXIS_SLIM_SP500_2 | 397525 | 1740046 | 43772 | VOO | VOO | 670.2600 | 698.2600 | 698.2600 | -4.01 |
| EMAXIS_SLIM_SP500_3 | 228995 | 1002357 | 43772 | VOO | VOO | 670.2600 | 698.2600 | 698.2600 | -4.01 |
| EMAXIS_SLIM_ALL_COUNTRY | 461462 | 1741050 | 37729 | ACWI | ACWI | 154.2800 | 159.9700 | 159.9700 | -3.56 |

## 5-1. Coreスポット買い判断材料
- liquidity_actual_pct: 34.60%
- liquidity_target_pct: 10.00%
- cash_excess_pct: 24.60%
- core_actual_pct: 24.30%
- core_target_pct: 45.00%
- core_delta_pct: -20.70%
- jun_core_actual_pct: 7.00%
- jun_core_target_pct: 20.00%
- jun_core_delta_pct: -13.00%
- nisa_growth_quota_status: exhausted
- nisa_exhaustion_adjustment_reason: NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う
- taxable_core_spot_buy_required: True
- account_type: 特定口座
- taxable_account_note: NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う
- tax_note: NISAより税効率は落ちるが、現在の主問題はcore不足と現金過多であるため、特定口座でのcore積増しを許容する
- fixed_core_auto_invest_amount_jpy: 100000
- current_monthly_core_auto_invest_amount_jpy: 100000
- annualized_core_auto_invest_amount_jpy: 1200000
- recommended_taxable_core_spot_buy_jpy: 900000
- recommended_monthly_core_buy_budget_jpy: 900000
- total_monthly_core_deployment_jpy: 1000000
- baseline_total_core_deployment_target_jpy: 1380000
- baseline_core_spot_buy_jpy: 1280000
- hard_cap_core_spot_buy_jpy: 1500000
- monthly_core_budget_band: {'min_jpy': 700000, 'max_jpy': 1000000, 'description': 'Aggressive mode: core不足が大きく、liquidityがtargetを大きく上回る'}
- spot_buy_bands: {'normal': {'min_jpy': 300000, 'max_jpy': 600000, 'conditions': ['core不足はあるが、現金過多が軽度', '相場が高値圏で、急いで投入する必要が低い']}, 'aggressive': {'min_jpy': 700000, 'max_jpy': 1000000, 'conditions': ['core不足が大きい', 'liquidity が target を大きく上回る', 'ただし rebalance mode ほどではない']}, 'rebalance': {'min_jpy': 1000000, 'max_jpy': 1500000, 'conditions': ['core_delta_pct <= -25pt 程度', 'cash_excess_pct >= +25pt 程度', '生活防衛資金を残しても現金過多が明確', '現在の固定積立等を踏まえて特定口座スポットで補う必要がある']}}
- core_spot_buy_allocation_rule: {'allowed_products_only': True, 'default_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.6, 'eMAXIS Slim 米国株式（S&P500）': 0.4}, 'high_us_ai_infra_sensitivity_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.65, 'eMAXIS Slim 米国株式（S&P500）': 0.35}, 'note': '既存core商品に限定し、米国株・半導体・AIインフラ感応度が高い月はオルカン比率を厚めにする'}
- date_based_override_active: True
- active_date_based_override: {'active_from': '2026-05', 'active_to': '2026-12', 'reason_code': 'nisa_growth_quota_exhausted_2026', 'reason': '2026年NISA成長投資枠を使い切ったため', 'nisa_growth_quota_status': 'exhausted', 'total_monthly_jpy': 100000, 'monthly_core_auto_invest_amount_jpy': 100000, 'taxable_core_spot_buy_required': True, 'core_spot_buy_account_type': '特定口座', 'baseline_total_core_deployment_target_jpy': 1380000, 'rebalance_mode_core_spot_buy_reference_jpy': 1280000, 'taxable_account_note': 'NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う', 'tax_note': 'NISAより税効率は落ちるが、現在の主問題はcore不足と現金過多であるため、特定口座でのcore積増しを許容する', 'nisa_exhaustion_adjustment_reason': 'NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う', 'core_spot_buy_allocation_rule': {'allowed_products_only': True, 'default_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.6, 'eMAXIS Slim 米国株式（S&P500）': 0.4}, 'high_us_ai_infra_sensitivity_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.65, 'eMAXIS Slim 米国株式（S&P500）': 0.35}, 'note': '既存core商品に限定し、米国株・半導体・AIインフラ感応度が高い月はオルカン比率を厚めにする'}, 'requires_explicit_followup_rule': True, 'followup_warning_code': 'post_2026_nisa_growth_quota_rule_missing'}
- configuration_warnings: []
- current_cash_jpy: 13620505
- bond_like_holdings_present: False
- bond_like_holdings: None
- emergency_fund_managed_separately: None
- near_term_large_expense: None
- real_estate_exposure_present: True
- real_estate_use: residence_and_asset
- mortgage_status: full_loan_early_stage
- liquidity_comment: residential real estate should not be treated as emergency liquidity
| reference_symbol | one_month_return_pct | three_month_return_pct | one_month_drawdown_from_high_pct | three_month_drawdown_from_high_pct |
| --- | ---: | ---: | ---: | ---: |
| VT | -2.04 | 12.83 | -3.39 | -3.39 |
| VOO | -2.86 | 12.66 | -4.01 | -4.01 |
| ACWI | -2.13 | 13.13 | -3.56 | -3.56 |
- portfolio_risk_bucket_summary:
  - core: actual_pct=24.30%, target_pct=45.00%, delta_pct=-20.70%
  - jun_core: actual_pct=7.00%, target_pct=20.00%, delta_pct=-13.00%
  - liquidity: actual_pct=34.60%, target_pct=10.00%, delta_pct=24.60%
  - other: actual_pct=0.04%, target_pct=null, delta_pct=null
  - pension: actual_pct=10.32%, target_pct=null, delta_pct=null
  - satellite: actual_pct=1.60%, target_pct=10.00%, delta_pct=-8.40%
  - satellite_core: actual_pct=22.14%, target_pct=15.00%, delta_pct=7.14%

## 5-2. Core積立設定（毎月固定）
- total_monthly_jpy: 100000
- monthly_core_auto_invest_amount_jpy: 100000
- nisa_growth_quota_status: exhausted
- taxable_core_spot_buy_required: True
- core_spot_buy_account_type: 特定口座
- date_based_override_active: True
- active_date_based_override: {'active_from': '2026-05', 'active_to': '2026-12', 'reason_code': 'nisa_growth_quota_exhausted_2026', 'reason': '2026年NISA成長投資枠を使い切ったため', 'nisa_growth_quota_status': 'exhausted', 'total_monthly_jpy': 100000, 'monthly_core_auto_invest_amount_jpy': 100000, 'taxable_core_spot_buy_required': True, 'core_spot_buy_account_type': '特定口座', 'baseline_total_core_deployment_target_jpy': 1380000, 'rebalance_mode_core_spot_buy_reference_jpy': 1280000, 'taxable_account_note': 'NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う', 'tax_note': 'NISAより税効率は落ちるが、現在の主問題はcore不足と現金過多であるため、特定口座でのcore積増しを許容する', 'nisa_exhaustion_adjustment_reason': 'NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う', 'core_spot_buy_allocation_rule': {'allowed_products_only': True, 'default_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.6, 'eMAXIS Slim 米国株式（S&P500）': 0.4}, 'high_us_ai_infra_sensitivity_allocation': {'eMAXIS Slim 全世界株式（オール・カントリー）': 0.65, 'eMAXIS Slim 米国株式（S&P500）': 0.35}, 'note': '既存core商品に限定し、米国株・半導体・AIインフラ感応度が高い月はオルカン比率を厚めにする'}, 'requires_explicit_followup_rule': True, 'followup_warning_code': 'post_2026_nisa_growth_quota_rule_missing'}
- taxable_account_note: NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う
- tax_note: NISAより税効率は落ちるが、現在の主問題はcore不足と現金過多であるため、特定口座でのcore積増しを許容する
- nisa_exhaustion_adjustment_reason: NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う
- baseline_total_core_deployment_target_jpy: 1380000
- rebalance_mode_core_spot_buy_reference_jpy: 1280000
- configuration_warnings: []
| day_of_month | fund_name | amount_jpy | settlement_type | account_type | distribution_course |
| ---: | --- | ---: | --- | --- | --- |
| 8 | eMAXIS Slim 全世界株式（オール・カントリー） | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
| 8 | eMAXIS Slim 米国株式（S&P500） | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
- review_guidance:
  - この固定積立は毎月すでに執行される前提で評価する
  - core不足の指摘は、固定積立の寄与を織り込んだうえで必要時のみ行う
  - 長期シナリオ悪化やリスク管理上の理由がある場合は、固定積立の減額・停止提案を明示する
  - 2026年5月〜12月は、NISA成長投資枠の固定積立750,000円/月を前提にしない
  - 固定core積立は100,000円/月として扱う
  - core不足と現金過多が続く限り、特定口座でのcoreスポット買いを厚めに提案する
  - 税効率よりも、core不足と現金過多の是正を優先する
  - 生活防衛資金・住宅ローン・大口支出不明リスクを考慮し、現金を一気に削りすぎない

## 5-3. iDeCo積立設定（毎月固定）
- pension_monthly_dca_total_jpy: 55000
- annualized_pension_dca_jpy: 660000
- annualized_pension_dca_pct_of_total_assets: 1.68%
| symbol | fund_name | amount_jpy_per_month | account_type | asset_class |
| --- | --- | ---: | --- | --- |
| IDECO_ALL_COUNTRY | eMAXIS Slim 全世界株式（オール・カントリー） | 55000 | iDeCo | pension |
- pension_review_guidance:
  - iDeCoのオルカン月次積立はpensionとして既存で実行中の前提で評価する
  - tradable coreとは分け、effective_core_including_pension_pctの文脈で補助的に扱う

## 5-4. 暗号資産積立設定（毎週固定）
- crypto_weekly_dca_total_jpy: 4000
- annualized_crypto_dca_jpy: 208000
- annualized_crypto_dca_pct_of_total_assets: 0.53%
| symbol | amount_jpy_per_week |
| --- | ---: |
| BTC | 2000 |
| ETH | 2000 |
- crypto_review_guidance:
  - 暗号資産の週次積立は既存で実行中の前提で評価する
  - 継続・減額・停止の提案が必要な場合は、理由とトリガー条件を明示する

## 6. SOX 判定材料
- proxy_symbol: SMH
- current_price: 611.6100
- recent_high_21d: 668.9100
- recent_high_63d: 668.9100
- drawdown_pct_from_21d_high: -8.57
- drawdown_pct_from_63d_high: -8.57
- buy_zone_rule_text: drawdown from 63d high between -10% and -5%
- within_buy_zone_boolean: True
- near_boundary_boolean: False
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}
- related_bucket_actual_pct: 22.14%
- related_bucket_target_pct: 15.00%
- semiconductor_exposure_total_pct: 17.80%
- priority_lowered_boolean: True
- priority_lowered_reason: related_bucket_over_target
- explanation: {'buy_zone_assessment': {'within_buy_zone': True, 'near_boundary': False, 'drawdown_pct_from_63d_high': Decimal('-8.57'), 'rule': '-10% <= drawdown <= -5%'}, 'bucket_context': {'related_bucket': 'satellite_core', 'related_bucket_actual_pct': Decimal('0.2214'), 'related_bucket_target_pct': Decimal('0.15')}, 'exposure_context': {'semiconductor_direct_exposure_pct': Decimal('0.1780'), 'indirect_ai_infra_exposure_pct': Decimal('0.0138')}}

## 7. 半導体エクスポージャ内訳
- direct_cap_monitor_pct: 17.80%
- direct_cap_monitor_jpy: 7009361
- direct_plus_indirect_watch_metric_pct: 19.18%
- direct_plus_indirect_watch_metric_jpy: 7552278
- direct_semiconductor_exposure_pct: 17.80%
- indirect_ai_infra_exposure_pct: 1.38%
- indirect_ai_infra_exposure_jpy: 542917
- combined_semiconductor_ai_infra_watch_pct: 19.18%
| symbol | value_jpy | bucket | exposure_type | in_direct | in_indirect | inclusion_reason |
| --- | ---: | --- | --- | --- | --- | --- |
| SMH | 98921 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| MSFT | 542917 | jun_core | indirect_ai_infra | no | yes | matched_indirect_ai_infra_rule |
| NISSEI_SOX_1 | 4660463 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| NISSEI_SOX_2 | 2249977 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |

## 8. 長期シナリオ点検対象
| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- |
| URA | satellite_core | 493517 | 1.25% | nuclear_revival | 脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。 | 炭素回収技術の量産化・低コスト化; 再エネ＋蓄電の経済性改善; 政策転換; 原子力新設の採算悪化 | high | yes |
| CIBR | satellite_core | 1214939 | 3.09% | persistent_cybersecurity_spending | サイバーセキュリティ支出は構造的に維持・拡大するという仮説。 | 支出成長の鈍化; バリュエーション過熱後の長期低迷 | medium | yes |
| MSFT | jun_core | 542917 | 1.38% | hyperscaler_ai_platform_compounding | クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。 | AI投資回収の停滞; 規制強化; 競争優位の低下 | medium | yes |
| PLTR | satellite | 200918 | 0.51% | defense_ai_gov_software_scaling | 政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。 | 政府需要の鈍化; 競争激化; 収益化の鈍化 | medium | yes |

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
- [info] core_below_range: Bucket core is below preferred range: 24.30% < 35.00%
- [info] jun_core_below_range: Bucket jun_core is below preferred range: 7.00% < 10.00%
- [warning] liquidity_above_range: Bucket liquidity is above preferred range: 34.60% > 15.00%
- [info] cash_above_preferred: Liquidity is above preferred total-assets band: 34.60% > 10.00%
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] bucket_over_target_shallow_suppressed: CIBR: Shallow candidate suppressed because related bucket is over target.
- [warning] limit_above_current: URA: Calculated limit price is not below the current price.
- [warning] bucket_over_target_shallow_suppressed: URA: Shallow candidate suppressed because related bucket is over target.
- [warning] limit_above_current: PLTR: Calculated limit price is not below the current price.
- [warning] limit_above_current: PLTR: Calculated limit price is not below the current price.
- [warning] limit_above_current: MSFT: Calculated limit price is not below the current price.
- [info] asset_class_resolved_by_rules: URA: raw asset_class=satellite was resolved to satellite_core by symbol_to_bucket.
- [warning] large_month_over_month_change: EMAXIS_SLIM_SP500_1: market_value_jpy changed from 735693 to 1168489 (gap=432796, pct=0.5882834280059753185092151210). Verify OCR digits, purchases/sales, and account grouping.
- [warning] large_month_over_month_change: EMAXIS_SLIM_ALL_COUNTRY: market_value_jpy changed from 964412 to 1741050 (gap=776638, pct=0.8052969063014562241033914966). Verify OCR digits, purchases/sales, and account grouping.
- [info] missing_quantity: Holding LIQUIDITY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding LIQUIDITY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding LIQUIDITY is missing current_price; stored as null.
- [info] missing_quantity: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing current_price; stored as null.
- [info] missing_quantity: Holding POINTS_MILES is missing quantity; stored as null.
- [info] missing_avg_cost: Holding POINTS_MILES is missing avg_cost; stored as null.
- [info] missing_current_price: Holding POINTS_MILES is missing current_price; stored as null.

## 11. 生成ロジック上の分離データ
- monthly_execution_outputs:
  - review_target_month: 2026_07
  - nisa_growth_quota_status: exhausted
  - fixed_core_auto_invest_amount_jpy: 100000
  - taxable_core_spot_buy_required: True
  - recommended_taxable_core_spot_buy_jpy: 900000
  - core_spot_buy_account_type: 特定口座
  - portfolio_management_mode: normal_with_override
  - monthly_core_budget_tier: aggressive
  - recommended_monthly_core_buy_budget_jpy: 900000
  - monthly_total_core_deployment_jpy: 1000000
  - candidate_count: 12
  - pension_monthly_dca_total_jpy: 55000
  - annualized_pension_dca_jpy: 660000
  - annualized_pension_dca_pct_of_total_assets: 1.68%
  - crypto_weekly_dca_total_jpy: 4000
  - annualized_crypto_dca_jpy: 208000
  - annualized_crypto_dca_pct_of_total_assets: 0.53%
  - taxable_account_note: NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う
  - nisa_exhaustion_adjustment_reason: NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う
- quarterly_rule_review_outputs:
  - no_change: False
  - classification_override_count: 1
  - core_reference_missing_symbols: []
  - core_reference_proxy_suggestions: {}
  - tradable_core_pct: 24.30%
  - effective_core_including_pension_pct: 34.62%
  - cash_normalization_months_estimate:
    - gross_deployment_months: 9.7
    - net_cash_reduction_months: 27.7
    - assumed_monthly_cash_inflow_jpy: 650000
    - net_cash_reduction_jpy: 350000
  - direct_cap_monitor_pct: 17.80%
  - direct_plus_indirect_watch_metric_pct: 19.18%
  - direct_semiconductor_exposure_pct: 17.80%
  - combined_semiconductor_ai_infra_watch_pct: 19.18%
  - indirect_ai_infra_exposure_pct: 1.38%

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
- 2026年5月〜12月で `nisa_growth_quota_status: exhausted` の場合は、固定core積立額を100,000円として明示すること
- 2026年5月〜12月で `taxable_core_spot_buy_required: True` の場合は、`account_type: 特定口座`、NISA成長投資枠枯渇の理由、税効率メモを明示すること
- 2026年5月〜12月は、固定core積立額 + coreスポット買い提案額 = total_monthly_core_deployment_jpy を明示すること
- NISA枠がないからcore購入を弱めるのではなく、core不足と現金過多の是正を優先して特定口座スポットで補うこと
- 税効率低下よりもcore不足と現金過多の是正を優先するが、住宅ローン・生活防衛資金・大口支出不明を理由に現金を一気に削りすぎないこと
- 2026年5月〜12月の提案額は、normal / aggressive / rebalance のどの rule-based band に基づくか、また今月の discretionary adjustment があるかを分けて書くこと
- 配分先内訳を明示すること
- 実行方法を `一括` / `2〜4分割` / `押し目待ち併用` のいずれかで明示すること
- 判断根拠は `相場面` / `ポートフォリオ歪み` / `流動性水準` を分けて書くこと
- その判断が `ルール上の判断` か `今月の裁量判断` かを分離すること
- broad market core 商品を優先し、むやみに新規商品を増やさないこと
- coreスポット買いは原則として eMAXIS Slim 全世界株式（オール・カントリー）と eMAXIS Slim 米国株式（S&P500）に限定すること
- 基本配分はオルカン60% / S&P500 40%、米国株・半導体・AIインフラ感応度が高い場合はオルカン65% / S&P500 35% などオルカン厚めにすること
- 実行スケジュールは Google Calendar の手動発注リマインダー作成に使うため、各行に具体日付、ファンド名、金額を必ず含めること
- 債券や低リスク商品を提案してもよいが、core equity のスポット買い額は必ず別途提示すること
- `積立しているからスポット買いは不要` とは結論しないこと

【今月の指値提案】
- この『今月』は review_target_month を指す。snapshot_date が前月末でも、対象月を取り違えないこと
- 各銘柄について 0段以上の任意段数で提案してよい
- 0段の場合は『今月は見送り』と明記する
- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する
- Python 候補より段数を増やした場合も、その理由を明記する
- 2026年5月〜12月は coreスポット買いの優先度を上げ、coreスポット買い予算を削ってまでテーマ銘柄を買わないこと
- satellite_core が over target の場合、SOX / CIBR / URA の追加は深い押し目限定とすること
- PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定すること
- MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先すること
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
- 2026年5月〜12月で NISA成長投資枠が枯渇している場合は、固定core積立100,000円/月を前提にし、特定口座スポット買いで補う方針を明示すること
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
- iDeCoのオルカン月次積立55,000円はpensionとして前提にし、tradable coreとは分けて評価すること
- 暗号資産の週次積立（BTC/ETH）を前提に、維持/減額/停止の要否を明示すること

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
- コードやルールへの修正指摘が実質的にない月でも、`README.md` の最新月セクションに月次サマリーと今月の指値買い設定を反映する依頼は必ず含めること
- 修正指摘がない月は、少なくとも `should` に `README.md` へ最新月サマリー・購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する` と書くこと
- README.md では、今月の指値買い設定を最新月セクション内の見やすい位置に置き、銘柄、指値、株数、見送り対象、主な理由を一覧化すること
- README.md 更新依頼には、ルートREADMEに月次レビュー履歴を蓄積せず、既存の `## Monthly Review: YYYY_MM` を最新月の内容で置換し、過去月の `Monthly Review` セクションを残さない前提を必ず含めること
- 出力例:
```md
must:
- なし

should:
- README.md に最新月の月次サマリー・購入計画・今月の指値買い設定・ポートフォリオサマリーを反映し、過去月の Monthly Review セクションは残さない

nice_to_have:
- なし

修正目的:
- コード修正提案がない月でも README.md に最新月の運用要約と指値買い設定を反映できるようにする

変更すべき仕様:
- 修正提案がない月でも README.md 更新依頼は必ず含める
- README.md の最新月セクションには、今月の指値買い設定を見やすい表で含める
- ルートREADMEには月次レビュー履歴を蓄積せず、過去月の Monthly Review セクションは data/history 側の履歴に任せる

影響範囲:
- README.md

推奨テスト:
- README.md の見出し、表、Mermaid が壊れず、Monthly Review セクションが最新月だけであることを確認
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
- 2026年5月〜12月は、NISA成長投資枠の固定積立750,000円/月を前提にせず、固定core積立100,000円/月として扱ってください。
- 2026年5月〜12月は、NISA枠枯渇により特定口座でcoreスポット買いを行う旨を明示してください。
- 2026年5月〜12月は、税効率よりもcore不足と現金過多の是正を優先する理由を明示してください。
- 2026年5月〜12月は、固定core積立100,000円とスポット買い提案額の合計core投入額を明示してください。
- 2026年5月〜12月は、iDeCo55,000円/月とBTC/ETH週次積立もキャッシュアウトとして別枠で考慮し、総投資額は月145万円程度を目安にしてください。
- 2026年5月〜12月は、coreスポット買いの提案が rule-based なのか discretionary なのかを明示してください。
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
- iDeCoのオルカン月次積立55,000円はpensionとして既に実行される前提で扱い、tradable coreとは分けて評価してください。
- 暗号資産の週次積立（BTC/ETH）も既に実行される前提で扱い、必要時のみ変更提案してください。
- コア不足と現金過多が同時発生している場合、押し目買いルール設計に問題がないかもレビューしてください。
- 中長期投資前提のため、短期トレンドやテクニカル悪化を売却理由にしない前提でレビューしてください。
- ただし、長期シナリオ・政策前提・技術前提・競争優位の前提が崩れた可能性がある場合は、その有無をWebベースで点検してください。
- 大きな変化が見当たらない場合は、無理に懸念を作らず『大きな変化なし』としてください。
- 事実と推論を分けて記述してください。
- 大きな問題がない場合は、無理に改善提案を作らないでください。
- ハルシネーション防止のため、明確な根拠がある改善提案のみを挙げてください。
- must / should / nice_to_have は空欄不可ですが、該当なしの場合は `なし` と明記してください。
- Codex向け修正要約は必ず md コードブロックで出力してください。
- コード修正提案がない月でも、README.md の最新月セクションにサマリーと今月の指値買い設定を反映し、過去月の Monthly Review セクションを残さない依頼は必ず Codex向け修正要約に含めてください。
- ルール改善が不要な場合は、その旨を明記してください。

## 14. 必須の Codex 向け修正要約観点
- must / should / nice_to_have は必ず埋めてください。
- 空欄は不可ですが、該当なしの場合は `なし` と明記してください。
- 【Codex向け修正要約】 全体を単一の ```md コードブロックで出力してください。
- コード修正提案がない月でも、README.md に最新月の月次サマリー・購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する依頼を必ず 1件以上含めてください。
- 今月の指値買い設定は、銘柄、指値、株数、見送り対象、主な理由が一目で分かる表としてREADME.mdの最新月セクションに置いてください。
- ルートREADMEには月次レビュー履歴を蓄積せず、過去月の Monthly Review セクションは残さないでください。
- monthly review と quarterly rule review を分けて整理してください。
- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。

指値設定対象月キー: 2026_07
