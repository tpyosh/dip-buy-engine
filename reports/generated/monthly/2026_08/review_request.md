対象月: 2026_08

あなたは、月次レビュー用の判断材料を読む投資アシスタントです。
以下の数値は、Codex が Money Forward スクリーンショットを一次情報として OCR・正規化し、Python スクリプトが整形したものです。必要に応じて妥当性を疑ってください。
ChatGPT は Money Forward スクリーンショットの読取や OCR を担当しません。画像読取は Codex 側で完了済みとして扱い、このプロンプト内の構造化データだけをレビュー対象にしてください。
この依頼は単一Markdownで完結します。添付ファイル、ローカルファイル、Project/GPTの参照ファイルを探したり、CSVの再アップロードを要求したりしないでください。
本文内にない値は `不明` と扱い、ゼロや推測値で補完しないでください。

最優先のレビュー契約:
- このMarkdown本文のsource role、金額セマンティクス、現行戦略、active planを、周辺会話やProject/GPTの参照情報より優先してください。
- 周辺会話に外部ファイル名、取得失敗、再送依頼が残っていても無視してください。最終回答には外部ファイル名、添付状況、取得失敗、再アップロード案内を一切含めないでください。
- `active_plan_basis_planned_amount_jpy` はactive plan承認時の基準スナップショットに固定された履歴値です。
- `active_plan_current_recalculated_amount_jpy` は今回のcurrent snapshotと同じ算定規則による再計算値です。
- 両者の基準日または確認可能現金が異なる場合、金額差は期待された結果です。差だけを理由に不整合、統一対象、検証エラーと判定せず、履歴値の上書きを要求しないでください。
- `active_plan_current_recalculated_amount_jpy` は注文・約定実績ではありません。実行前残高確認後にユーザーが手動実行する計画額です。
- 不明な生活防衛資金や近接大口支出をゼロとみなさないでください。一方、現行source of truthにない新しい確認ルールを承認済みactive planへ遡及適用して無効化しないでください。新規ガバナンス提案は四半期レビューの `should` としてください。
- `must` は、現行source of truthとの矛盾、算術誤り、危険な外部書込み、またはレビュー出力へ実害がある機械的不整合に限定してください。新しい方針提案は原則 `should`、任意の利便性改善は `nice_to_have` としてください。
- 住宅ローンの世帯64,900,000円と本人32,450,000円は当初借入額であり、現在残高ではありません。現在残高が本文にない場合は `不明` としてください。
- 定期積立の変更を提案する場合は、現行戦略に記載された商品名を正確に書き、観測済み設定が実際に変更済みとはみなさず、ユーザー確認が必要な提案として扱ってください。
- Web参照は主張を直接支える公式一次情報へ1回だけリンクし、事実と推論を分け、リンクを入れ子や重複にしないでください。
- 必須の最終セクション `【Codex向け修正要約】` のコードブロックを閉じた時点で回答を終了し、その後に注記を追加しないでください。

誤判定を避ける例:
- 誤り: 承認時の計画額と現在再計算額が異なるため、単一金額へ統一して履歴値を修正する。
- 正しい: 基準日が異なるため差は期待される。承認時の履歴値は維持し、現在再計算額は実行前残高確認付きの今月提案として扱う。
- 誤り: 周辺会話に見える外部表データの再送を依頼する。
- 正しい: このMarkdown本文だけでレビューを完結し、外部ファイルへ言及しない。

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
- 現行戦略の `broad_core` 不足是正を優先し、指値候補が出ても承認済みcore計画の資金をテーマ銘柄へ振り替えない
- 直接半導体比率が15%を超える場合は通常買い増しを行わず、20%超ではリバランスを人間へ提案する
- 高ボラ単一銘柄は5%を通常上限、8%超をリバランス提案閾値として扱う
- PLTR など高ボラティリティ銘柄は、core補強を圧迫しない範囲に限定する
- MSFT は jun_core だが、core不足が大きい月は MSFT より broad market core を優先する
- 指値設定基準値は、先月平均ではなくスクリプト実行時点から直近20営業日（約1ヶ月）の終値平均として扱う
- 指値を提案する場合は、各段について「直近20営業日（約1ヶ月）の終値平均」と「その平均から何%下の指値か」を必ず併記する
- 乖離率は `((指値 / 直近20営業日終値平均) - 1) * 100` のパーセンテージとして扱い、マイナス値で明記する

coreスポット買い出力ルール:
- `【今月のcoreスポット買い提案】` では、提案総額、配分先内訳、実行スケジュールを必ず記載する
- `active_plan_status: approved_pending_execution` は承認済み計画であり、取引実績ではない。注文・約定済みと表現しない
- 承認済みactive planがある場合は、その計画の金額算定ルール、商品、配分、口座、実行方法、実行前確認条件を優先し、別の金額・商品・配分・分割方法を作らない
- 承認済みactive planの実行額は、本文に埋め込まれた確認可能現金から趣味用押し目買い現金1,000,000円を分離した計算結果を使う
- 新規のbroad core購入は、現行戦略どおり全世界株式100%とする。既存S&P500は強制売却しないが、通常の新規購入先にしない
- `plans/recurring/`由来の定期積立は観測済み設定として別記し、承認済み現金再配分計画の商品配分や取引実績と混同しない
- 根拠のない月650,000円の現金流入を仮定しない。毎月の正確な余剰額は不明として扱う
- 税制・NISA枠・商品仕様など変化する情報を判断に使う場合は、公式一次情報を確認し、参照日とURLを示す
- 今月の判断が rule-based なのか discretionary なのかを分けて書く
- `配分先内訳` では銘柄ごとの金額を記載し、合計は提案総額と一致させる
- `execution_method: lump_sum` の場合は分割日程を作らず、`実行前残高確認後にユーザーが手動で一括発注` と記載する
- 証券注文、送金、Calendar登録を実行したと表現しない
- coreスポット買いを見送る場合は、見送り理由を明記し、`実行スケジュールなし` と記載する
- フォーマット例:
```text
【今月のcoreスポット買い提案】
本文の recommended_monthly_core_buy_budget_jpy と同額
配分先内訳
本文の active_plan_product: 100%
実行スケジュール
実行前残高確認後にユーザーが手動で一括発注
```

Codex向け修正要約ルール:
- `【Codex向け修正要約】` は、修正指摘の有無にかかわらず毎回必ず出力する
- must / should / nice_to_have / 修正目的 / 変更すべき仕様 / 影響範囲 / 推奨テスト を省略しない
- 修正提案がない場合は `must: なし` などと明記し、不要な改善案を作らない
- 新規生成物の反映先は `reports/generated/` とし、`data/history/`、`prompts/generated/`、過去スナップショット・レビュー・生成物の書換えを依頼しない
- `must` は現行source of truth違反、算術誤り、危険な外部書込み、または出力へ実害がある機械的不整合に限定する
- 新しい運用・安全・ガバナンス方針は、現行source of truthに根拠がなければ `should` の四半期提案とし、承認済み計画を遡及的に無効化しない
- コードブロックを閉じた後に、外部ファイル、添付状況、再送案内その他の追記をしない

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

## 0. 自己完結ハンドオフ
- handoff_mode: self_contained_single_markdown
- external_files_required: false
- normalized_snapshot: embedded_below
- active_strategy: embedded_below
- active_plans: embedded_below
- recurring_contribution_observation: embedded_below
- market_references: embedded_below
- computed_metrics_and_warnings: embedded_below
- このMarkdown本文だけをレビュー対象にすること
- 添付ファイル、ローカルファイル、Project/GPTの参照ファイルを探さないこと
- 外部表データの再アップロードを要求しないこと
- 本文にない値は不明として扱い、ゼロや推測値で補完しないこと

## 0-1. Active plan金額セマンティクス（最優先）
- active_plan_basis_snapshot_date: 2026-06-28
- active_plan_basis_liquidity_jpy: 13620505
- active_plan_basis_planned_amount_jpy: 12620505
- active_plan_current_snapshot_date: 2026-07-26
- active_plan_current_recalculated_amount_jpy: 12622664
- active_plan_amount_delta_jpy: 2159
- active_plan_amount_difference_expected: true
- active_plan_historical_basis_must_not_be_overwritten: true
- basisは承認時の履歴値、current recalculated amountは今回スナップショットによる再計算値であり、同じ意味の重複フィールドではない
- 基準日または現金が異なる場合の差は期待される。差だけを理由に不整合や統一対象と判定しない
- 承認時のbasis値を現在値で上書きしない。今月はcurrent recalculated amountを実行前残高確認付きの計画額として扱う

## 1. 前提
- snapshot_date: 2026-07-26
- review_target_month: 2026_08
- currency_base: JPY
- total_assets_jpy: 39969688
- liquidity_target_jpy: null
- active_strategy_id: husband_personal_2026-07-25
- strategy_effective_from: 2026-07-25
- active_plan_ids: ['2026-07-25_cash_redeployment']
- holdings_count: 21
- source_role_snapshot: observed_fact
- source_role_active_strategy: approved_policy
- source_role_active_plan: approved_pending_execution
- source_role_candidate_orders: proposal_only
- source_role_recurring_contributions: observed_setting
- 取引実績、承認済み計画、分析上の提案を相互に読み替えないこと
- スナップショットは Money Forward スクリーンショットを一次情報として Codex が OCR・正規化したものとして扱うこと
- ChatGPT は Money Forward スクリーンショットの読取や OCR を担当しないこと。画像読取は Codex 側で完了済みとして扱い、このプロンプト内の構造化データだけをレビューすること
- Money Forward から貼り付けられたテキストがある場合でも、それは補助情報であり、HTML由来でレイアウト・列・階層・並び順が崩れている可能性がある
- OCR・正規化・前月差分の検証警告は後続の警告一覧に含めているため、投資レビューでは警告を前提条件として扱うこと
- 給与で通常生活費300,000円/月と本人分住宅ローン74,171円/月を賄っており、日常生活費に投資資産の売却を前提としていない
- 給与収入額と毎月の正確な余剰額は未記録であり、推測で補完しないこと
- 住宅ローンはペアローンの世帯当初借入額64,900,000円、本人当初借入額32,450,000円、年1.120%としてリスク評価に含めること。これらは現在残高ではない
- 現在の住宅ローン残高が本文に明示されていない場合は不明とし、当初借入額を現在残高と表現しないこと
- 半導体エクスポージャ(Direct): 15.74%
- AIインフラ感応度(Indirect): 1.41%
- 指値設定は前月末または当月初に実施しうるため、snapshot_date が月末でも翌月の指値設定として解釈してよい
- 指値設定基準値は先月平均ではなく、スクリプト実行時点から直近20営業日（約1ヶ月）の終値平均を使う

## 2. この月の snapshot 要約
- LIQUIDITY | liquidity | value_jpy=13622664 | price=null | quantity=null | source_category=預金・現金 | notes=明細は今回の画像に含まれていないため、カテゴリ合計のみ記録。前月の口座別内訳は引き継いでいない。
- 7203 | jun_core | value_jpy=2317600 | price=2897 | quantity=800 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=1892000 | notes=前日比 0円、評価損益率 444.55%。
- 9444 | satellite | value_jpy=349500 | price=233 | quantity=1500 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=-592500 | notes=前日比 0円、評価損益率 -62.90%。
- 2353 | satellite | value_jpy=25800 | price=258 | quantity=100 | source_category=株式（現物） | institution=野村証券 | profit_loss_jpy=-700 | notes=前日比 0円、評価損益率 -2.64%。
- 7201 | satellite | value_jpy=32220 | price=322 | quantity=100 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-4535 | notes=前日比 0円、評価損益率 -12.34%。現在値は整数表示、評価額は画面表示値をそのまま記録。
- SMH | satellite_core | value_jpy=91950 | price=561.19 | quantity=1 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=31387 | notes=前日比 0円、評価損益率 51.82%。
- PLTR | satellite | value_jpy=221544 | price=122.92 | quantity=11 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-51013 | notes=前日比 0円、評価損益率 -18.72%。
- CIBR | satellite_core | value_jpy=1274621 | price=88.4 | quantity=88 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=169319 | notes=前日比 0円、評価損益率 15.32%。
- MSFT | jun_core | value_jpy=562873 | price=381.7 | quantity=9 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-25123 | notes=前日比 0円、評価損益率 -4.27%。
- URA | satellite_core (raw=satellite, reason=symbol_to_bucket) | value_jpy=470590 | price=39.89 | quantity=72 | source_category=株式（現物） | institution=楽天証券 | profit_loss_jpy=-73250 | notes=前日比 0円、評価損益率 -13.47%。
- NISSEI_SOX_1 | satellite_core | value_jpy=4179530 | price=48545 | quantity=860960 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=2819073 | notes=前日比 0円、評価損益率 207.22%。
- NISSEI_SOX_2 | satellite_core | value_jpy=2017792 | price=48545 | quantity=415654 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=1417792 | notes=前日比 0円、評価損益率 236.30%。
- RAKUTEN_PLUS_ALL_COUNTRY_1 | core | value_jpy=2137977 | price=19705 | quantity=1084992 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=587977 | notes=前日比 0円、評価損益率 37.93%。
- RAKUTEN_PLUS_ALL_COUNTRY_2 | core | value_jpy=1669004 | price=19705 | quantity=846995 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=169003 | notes=前日比 0円、評価損益率 11.27%。
- RAKUTEN_PLUS_SP500 | core | value_jpy=211728 | price=19875 | quantity=106530 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=86928 | notes=前日比 0円、評価損益率 69.65%。
- EMAXIS_SLIM_SP500_1 | core | value_jpy=1506234 | price=44669 | quantity=337199 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=78234 | notes=前日比 0円、評価損益率 5.48%。
- EMAXIS_SLIM_SP500_2 | core | value_jpy=1825667 | price=44669 | quantity=408710 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=460667 | notes=前日比 0円、評価損益率 33.75%。
- EMAXIS_SLIM_SP500_3 | core | value_jpy=1022898 | price=44669 | quantity=228995 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=122898 | notes=前日比 0円、評価損益率 13.66%。
- EMAXIS_SLIM_ALL_COUNTRY | core | value_jpy=2349638 | price=38243 | quantity=614397 | source_category=投資信託 | institution=楽天証券 | profit_loss_jpy=107639 | notes=前日比 0円、評価損益率 4.80%。
- PENSION_EMAXIS_SLIM_ALL_COUNTRY | pension | value_jpy=4063372 | price=null | quantity=null | source_category=年金 | account_type=iDeCo | profit_loss_jpy=722677 | notes=取得価額 3,340,695円、現在価値 4,063,372円、評価損益率 21.63%。
- POINTS_MILES | other | value_jpy=16483 | price=null | quantity=null | source_category=ポイント | notes=内訳詳細は今回の画像に含まれていないため、カテゴリ合計のみ記録。

## 3. 現在戦略に基づく資産配分
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| broad_core | 14786518 | 36.99% | 70.00% | -33.01% |
| active_hobby | 12544020 | 31.38% | 30.00% | 1.38% |

## 3-1. 互換用の旧バケット内訳（目標値として使用しない）
| bucket | market_value_jpy | actual_pct | target_pct | delta_pct |
| --- | ---: | ---: | ---: | ---: |
| core | 10723146 | 26.83% | - | - |
| jun_core | 2880473 | 7.21% | - | - |
| liquidity | 13622664 | 34.08% | - | - |
| other | 16483 | 0.04% | - | - |
| pension | 4063372 | 10.17% | - | - |
| satellite | 629064 | 1.57% | - | - |
| satellite_core | 8034483 | 20.10% | - | - |

## 4. 対象銘柄ごとの候補
| symbol | bucket | current_price | snapshot_price_source_date | market_candidate_price_source_date | base_price | avg20_base_price | drawdown_rule | limit_price | avg20_gap_pct | shares | est_cost_jpy | suppressed | suppressed_reason_code | suppressed_reason_text | note_for_chatgpt | explanation |
| --- | --- | ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| CIBR | satellite_core | 88.4000 | 2026-07-26 | 2026-07-24 | 88.8770 | 88.8770 | -5% x 1 | 84.43 | -5.00 | 1 | 13829 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| CIBR | satellite_core | 88.4000 | 2026-07-26 | 2026-07-24 | 88.8770 | 88.8770 | -8% x 1 | 81.77 | -8.00 | 1 | 13393 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| CIBR | satellite_core | 88.4000 | 2026-07-26 | 2026-07-24 | 88.8770 | 88.8770 | -12% x 1 | 78.21 | -12.00 | 1 | 12810 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| URA | satellite_core | 39.8900 | 2026-07-26 | 2026-07-24 | 43.1447 | 43.1447 | -6% x 2 | 40.56 | -5.99 | 2 | 13287 | yes | limit_above_current | Calculated limit price is not below the current price. | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:0,limit_above_current | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| URA | satellite_core | 39.8900 | 2026-07-26 | 2026-07-24 | 43.1447 | 43.1447 | -10% x 2 | 38.83 | -10.00 | 2 | 12720 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| URA | satellite_core | 39.8900 | 2026-07-26 | 2026-07-24 | 43.1447 | 43.1447 | -15% x 2 | 36.67 | -15.01 | 2 | 12012 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,mode_context:normal,mode_priority_weight:0 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite_core', 'actual_pct': Decimal('0.2010'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 0}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 122.9200 | 2026-07-26 | 2026-07-24 | 126.7033 | 126.7033 | -10% x 1 | 114.03 | -10.00 | 1 | 18677 | yes | high_volatility_shallow_suppressed | High-volatility names default to deeper pullbacks before adding. | drawdown_profile:shallow,shallow_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,rule_based_high_volatility_shallow_suppression,mode_context:normal,mode_priority_weight:-1,high_volatility_shallow_suppressed | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12', 'rule_based_high_volatility_shallow_suppression'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0157'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': True, 'reason_code': 'high_volatility_shallow_suppressed', 'reason_text': 'High-volatility names default to deeper pullbacks before adding.'}} |
| PLTR | satellite | 122.9200 | 2026-07-26 | 2026-07-24 | 126.7033 | 126.7033 | -15% x 2 | 107.70 | -15.00 | 2 | 35281 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,mode_context:normal,mode_priority_weight:-1 | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0157'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| PLTR | satellite | 122.9200 | 2026-07-26 | 2026-07-24 | 126.7033 | 126.7033 | -22% x 2 | 98.83 | -22.00 | 2 | 32375 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,high_volatility_name,high_volatility_shallow_threshold_pct:-12,mode_context:normal,mode_priority_weight:-1 | {'rule_based_reason': ['high_volatility_shallow_threshold_pct:-12'], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'satellite', 'actual_pct': Decimal('0.0157'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': -1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 381.7000 | 2026-07-26 | 2026-07-24 | 384.3463 | 384.3463 | -6% x 1 | 361.29 | -6.00 | 1 | 59176 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:1 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0721'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 381.7000 | 2026-07-26 | 2026-07-24 | 384.3463 | 384.3463 | -10% x 2 | 345.91 | -10.00 | 2 | 113314 | no | - | - | drawdown_profile:shallow,shallow_candidate,mode_context:normal,mode_priority_weight:1 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0721'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |
| MSFT | jun_core | 381.7000 | 2026-07-26 | 2026-07-24 | 384.3463 | 384.3463 | -18% x 2 | 315.16 | -18.00 | 2 | 103241 | no | - | - | drawdown_profile:deep,deep_drawdown_candidate,mode_context:normal,mode_priority_weight:1 | {'rule_based_reason': [], 'discretionary_reason': None, 'related_bucket_status': {'bucket': 'jun_core', 'actual_pct': Decimal('0.0721'), 'target_pct': None, 'is_over_target': False}, 'mode_context': {'active_mode': 'normal', 'priority_weight': 1}, 'suppression': {'suppressed': False, 'reason_code': None, 'reason_text': None}} |

## 5. コア定額買い判定材料
- strategy_id: husband_personal_2026-07-25
- active_plan_id: 2026-07-25_cash_redeployment
- active_plan_status: approved_pending_execution
- active_plan_account_type: 特定口座（源泉徴収あり）
- active_plan_execution_amount_rule: max(0, confirmed_available_cash_jpy - 1000000)
- active_plan_target_group: broad_core
- active_plan_product: 楽天・プラス・オールカントリー株式インデックス・ファンド
- active_plan_product_allocation_pct: 100.00%
- active_plan_execution_method: lump_sum
- active_plan_requires_pretrade_balance_confirmation: True
- active_plan_user_executes_order_manually: True
- active_plan_basis_snapshot_date: 2026-06-28
- active_plan_basis_liquidity_jpy: 13620505
- active_plan_basis_planned_amount_jpy: 12620505
- active_plan_current_snapshot_date: 2026-07-26
- active_plan_current_recalculated_amount_jpy: 12622664
- active_plan_amount_delta_jpy: 2159
- active_plan_amount_difference_expected: true
- active_plan_historical_basis_must_not_be_overwritten: true
- core_actual_pct: 36.99%
- core_target_pct: 70.00%
- core_delta_pct: -33.01%
- liquidity_actual_pct: 34.08%
- liquidity_target_pct: null
- cash_excess_pct: 31.58%
- unallocated_liquidity_jpy: 12622664
- reserved_hobby_cash_jpy: 1000000
- core_bucket_total_jpy: 14786518
- monthly_core_budget_policy: {}
- monthly_core_buy_budget_min_jpy: None
- monthly_core_buy_budget_max_jpy: None
- monthly_core_budget_tier: approved_lump_sum_plan
- monthly_core_budget_band: {'min_jpy': 12622664, 'max_jpy': 12622664, 'description': 'Approved transition plan; reconfirm available cash before execution.'}
- recommended_monthly_core_buy_budget_jpy: 12622664
- monthly_core_budget_override_active: True
- monthly_core_budget_override_reason: 2026-07-25_cash_redeployment
- portfolio_management_mode: approved_transition_plan
- rebalance_mode_active: True
- rebalance_mode_reason: 2026-07-25_cash_redeployment
- date_based_core_budget_override_active: False
- nisa_growth_quota_status: None
- taxable_core_spot_buy_required: False
- core_spot_buy_account_type: -
- fixed_core_auto_invest_jpy: None
- baseline_total_core_deployment_target_jpy: None
- baseline_core_spot_buy_jpy: None
- hard_cap_core_spot_buy_jpy: None
- spot_buy_bands: None
- satellite_interaction_policy: None
- core_budget_explanation: {'rule_based_reason': '2026-07-25_cash_redeployment', 'discretionary_reason': None, 'related_bucket_status': {'unallocated_liquidity_jpy': Decimal('12622664'), 'snapshot_date': datetime.date(2026, 7, 26)}, 'mode_context': {'active_mode': 'approved_transition_plan', 'requires_pretrade_balance_confirmation': True, 'basis_planned_amount_jpy': 12620505, 'execution_amount_rule': 'max(0, confirmed_available_cash_jpy - 1000000)'}}
| symbol | quantity | value_jpy | current_price | reference_symbol | suggested_proxy_symbol | reference_current_price | recent_high_21d | recent_high_63d | drawdown_pct_from_recent_high |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |
| RAKUTEN_PLUS_ALL_COUNTRY_1 | 1084992 | 2137977 | 19705 | VT | ACWI | 154.2000 | 157.8100 | 159.3500 | -3.23 |
| RAKUTEN_PLUS_ALL_COUNTRY_2 | 846995 | 1669004 | 19705 | VT | ACWI | 154.2000 | 157.8100 | 159.3500 | -3.23 |
| RAKUTEN_PLUS_SP500 | 106530 | 211728 | 19875 | VOO | VOO | 679.1400 | 693.8600 | 698.2600 | -2.74 |
| EMAXIS_SLIM_SP500_1 | 337199 | 1506234 | 44669 | VOO | VOO | 679.1400 | 693.8600 | 698.2600 | -2.74 |
| EMAXIS_SLIM_SP500_2 | 408710 | 1825667 | 44669 | VOO | VOO | 679.1400 | 693.8600 | 698.2600 | -2.74 |
| EMAXIS_SLIM_SP500_3 | 228995 | 1022898 | 44669 | VOO | VOO | 679.1400 | 693.8600 | 698.2600 | -2.74 |
| EMAXIS_SLIM_ALL_COUNTRY | 614397 | 2349638 | 38243 | ACWI | ACWI | 154.3000 | 157.9700 | 159.9700 | -3.54 |

## 5-1. Coreスポット買い判断材料
- strategy_id: husband_personal_2026-07-25
- active_plan_id: 2026-07-25_cash_redeployment
- active_plan_status: approved_pending_execution
- active_plan_account_type: 特定口座（源泉徴収あり）
- active_plan_execution_amount_rule: max(0, confirmed_available_cash_jpy - 1000000)
- active_plan_target_group: broad_core
- active_plan_product: 楽天・プラス・オールカントリー株式インデックス・ファンド
- active_plan_product_allocation_pct: 100.00%
- active_plan_execution_method: lump_sum
- active_plan_requires_pretrade_balance_confirmation: True
- active_plan_user_executes_order_manually: True
- broad_core_actual_pct: 36.99%
- broad_core_target_pct: 70.00%
- active_hobby_actual_pct: 31.38%
- active_hobby_target_pct: 30.00%
- reserved_hobby_cash_jpy: 1000000
- unallocated_liquidity_jpy: 12622664
- liquidity_actual_pct: 34.08%
- liquidity_target_pct: null
- cash_excess_pct: 31.58%
- core_actual_pct: 36.99%
- core_target_pct: 70.00%
- core_delta_pct: -33.01%
- jun_core_actual_pct: 7.21%
- jun_core_target_pct: null
- jun_core_delta_pct: null
- nisa_growth_quota_status: exhausted
- nisa_exhaustion_adjustment_reason: NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う
- taxable_core_spot_buy_required: True
- account_type: 特定口座（源泉徴収あり）
- taxable_account_note: NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う
- tax_note: NISAより税効率は落ちるが、現在の主問題はcore不足と現金過多であるため、特定口座でのcore積増しを許容する
- fixed_core_auto_invest_amount_jpy: 100000
- current_monthly_core_auto_invest_amount_jpy: 100000
- annualized_core_auto_invest_amount_jpy: 1200000
- recommended_taxable_core_spot_buy_jpy: 12622664
- recommended_monthly_core_buy_budget_jpy: 12622664
- total_monthly_core_deployment_jpy: 12722664
- baseline_total_core_deployment_target_jpy: None
- baseline_core_spot_buy_jpy: None
- hard_cap_core_spot_buy_jpy: None
- monthly_core_budget_band: {'min_jpy': 12622664, 'max_jpy': 12622664, 'description': 'Approved transition plan; reconfirm available cash before execution.'}
- spot_buy_bands: None
- core_spot_buy_allocation_rule: {'source_role': 'approved_active_plan', 'target_group': 'broad_core', 'product': '楽天・プラス・オールカントリー株式インデックス・ファンド', 'product_allocation_pct': 1.0}
- date_based_override_active: False
- active_date_based_override: -
- configuration_warnings: []
- current_cash_jpy: 13622664
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
| VT | -0.04 | 3.39 | -2.29 | -3.23 |
| VOO | 0.51 | 4.28 | -2.12 | -2.74 |
| ACWI | 0.05 | 3.38 | -2.32 | -3.54 |
- portfolio_risk_bucket_summary:
  - core: actual_pct=26.83%, target_pct=null, delta_pct=null
  - jun_core: actual_pct=7.21%, target_pct=null, delta_pct=null
  - liquidity: actual_pct=34.08%, target_pct=null, delta_pct=null
  - other: actual_pct=0.04%, target_pct=null, delta_pct=null
  - pension: actual_pct=10.17%, target_pct=null, delta_pct=null
  - satellite: actual_pct=1.57%, target_pct=null, delta_pct=null
  - satellite_core: actual_pct=20.10%, target_pct=null, delta_pct=null

## 5-2. Core積立設定（毎月固定）
- source_role: observed_setting
- total_monthly_jpy: 100000
- monthly_core_auto_invest_amount_jpy: 100000
- nisa_growth_quota_status: exhausted
- configuration_warnings: []
| day_of_month | fund_name | amount_jpy | settlement_type | account_type | distribution_course |
| ---: | --- | ---: | --- | --- | --- |
| 8 | eMAXIS Slim 全世界株式（オール・カントリー） | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
| 8 | eMAXIS Slim 米国株式（S&P500） | 50000 | クレジットカード決済 | NISAつみたて投資枠 | 再投資型 |
- review_guidance:
  - この設定はplans/recurring由来の観測済み設定であり、取引実績ではない
  - 証券会社での変更確認までは、実際に変更・停止・約定したとみなさない
  - 承認済み現金再配分計画の商品配分や実行額とは分離して評価する

## 5-3. iDeCo積立設定（毎月固定）
- pension_monthly_dca_total_jpy: 55000
- annualized_pension_dca_jpy: 660000
- annualized_pension_dca_pct_of_total_assets: 1.65%
| symbol | fund_name | amount_jpy_per_month | account_type | asset_class |
| --- | --- | ---: | --- | --- |
| IDECO_ALL_COUNTRY | eMAXIS Slim 全世界株式（オール・カントリー） | 55000 | iDeCo | pension |
- pension_review_guidance:
  - iDeCoのオルカン月次積立はpensionとして既存で実行中の前提で評価する
  - tradable coreとは分け、effective_core_including_pension_pctの文脈で補助的に扱う

## 5-4. 暗号資産積立設定（毎週固定）
- crypto_weekly_dca_total_jpy: 4000
- annualized_crypto_dca_jpy: 208000
- annualized_crypto_dca_pct_of_total_assets: 0.52%
| symbol | amount_jpy_per_week |
| --- | ---: |
| BTC | 2000 |
| ETH | 2000 |
- crypto_review_guidance:
  - 暗号資産の週次積立は既存で実行中の前提で評価する
  - 継続・減額・停止の提案が必要な場合は、理由とトリガー条件を明示する

## 6. SOX 判定材料
- proxy_symbol: SMH
- current_price: 561.1900
- recent_high_21d: 655.8900
- recent_high_63d: 668.9100
- drawdown_pct_from_21d_high: -14.44
- drawdown_pct_from_63d_high: -16.10
- buy_zone_rule_text: drawdown from 63d high between -10% and -5%
- within_buy_zone_boolean: False
- near_boundary_boolean: False
- routine_additions_allowed: False
- rebalance_proposal_required: False
- semiconductor_preferred_max_pct: 15.00%
- semiconductor_rebalance_proposal_above_pct: 20.00%
- monthly_buy_budget_jpy: {'min': 100000, 'max': 200000}
- related_bucket_actual_pct: 20.10%
- related_bucket_target_pct: null
- semiconductor_exposure_total_pct: 15.74%
- priority_lowered_boolean: True
- priority_lowered_reason: direct_semiconductor_above_preferred_max
- explanation: {'buy_zone_assessment': {'within_buy_zone': False, 'near_boundary': False, 'drawdown_pct_from_63d_high': Decimal('-16.10'), 'rule': '-10% <= drawdown <= -5%'}, 'bucket_context': {'related_bucket': 'satellite_core', 'related_bucket_actual_pct': Decimal('0.2010'), 'related_bucket_target_pct': None}, 'exposure_context': {'semiconductor_direct_exposure_pct': Decimal('0.1574'), 'indirect_ai_infra_exposure_pct': Decimal('0.0141')}}

## 7. 半導体エクスポージャ内訳
- direct_cap_monitor_pct: 15.74%
- direct_cap_monitor_jpy: 6289272
- direct_plus_indirect_watch_metric_pct: 17.14%
- direct_plus_indirect_watch_metric_jpy: 6852145
- direct_semiconductor_exposure_pct: 15.74%
- indirect_ai_infra_exposure_pct: 1.41%
- indirect_ai_infra_exposure_jpy: 562873
- combined_semiconductor_ai_infra_watch_pct: 17.14%
| symbol | value_jpy | bucket | exposure_type | in_direct | in_indirect | inclusion_reason |
| --- | ---: | --- | --- | --- | --- | --- |
| SMH | 91950 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| MSFT | 562873 | jun_core | indirect_ai_infra | no | yes | matched_indirect_ai_infra_rule |
| NISSEI_SOX_1 | 4179530 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |
| NISSEI_SOX_2 | 2017792 | satellite_core | direct_semiconductor | yes | no | matched_exposure_group_rule |

## 8. 長期シナリオ点検対象
| symbol | bucket | current_value_jpy | portfolio_pct | thesis_id | thesis_status | long_term_thesis_summary | key_risk_if_thesis_breaks | review_priority | web_review_required |
| --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- |
| URA | satellite_core | 470590 | 1.18% | nuclear_revival | inherited_pending_review | 脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。 | 炭素回収技術の量産化・低コスト化; 再エネ＋蓄電の経済性改善; 政策転換; 原子力新設の採算悪化 | high | yes |
| CIBR | satellite_core | 1274621 | 3.19% | persistent_cybersecurity_spending | inherited_pending_review | サイバーセキュリティ支出は構造的に維持・拡大するという仮説。 | 支出成長の鈍化; バリュエーション過熱後の長期低迷 | medium | yes |
| MSFT | jun_core | 562873 | 1.41% | hyperscaler_ai_platform_compounding | inherited_pending_review | クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。 | AI投資回収の停滞; 規制強化; 競争優位の低下 | medium | yes |
| PLTR | satellite | 221544 | 0.55% | defense_ai_gov_software_scaling | inherited_pending_review | 政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。 | 政府需要の鈍化; 競争激化; 収益化の鈍化 | medium | yes |

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
- [warning] broad_core_reinforcement_proposal: Broad core is below the reinforcement proposal threshold: 36.99% < 65.00%
- [info] semiconductor_routine_additions_paused: Direct semiconductor exposure is above the routine-addition limit: 15.74% > 15.00%
- [warning] limit_above_current: URA: Calculated limit price is not below the current price.
- [warning] high_volatility_shallow_suppressed: PLTR: High-volatility names default to deeper pullbacks before adding.
- [warning] core_recurring_plan_conflicts_with_current_strategy: The recorded recurring plan still buys S&P500, while the active strategy routes new broad-core purchases to all-country only. Treat the recurring plan as an observed fact until the user changes it; do not silently mark it updated.
- [info] asset_class_resolved_by_rules: URA: raw asset_class=satellite was resolved to satellite_core by symbol_to_bucket.
- [info] missing_quantity: Holding LIQUIDITY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding LIQUIDITY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding LIQUIDITY is missing current_price; stored as null.
- [info] missing_quantity: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing quantity; stored as null.
- [info] missing_avg_cost: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing avg_cost; stored as null.
- [info] missing_current_price: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing current_price; stored as null.
- [info] missing_quantity: Holding POINTS_MILES is missing quantity; stored as null.
- [info] missing_avg_cost: Holding POINTS_MILES is missing avg_cost; stored as null.
- [info] missing_current_price: Holding POINTS_MILES is missing current_price; stored as null.
- [info] legacy_candidate_heuristic_review_only: Limit-order candidates come from a legacy analytical heuristic, not an approved order plan. They are review material only.

## 11. 生成ロジック上の分離データ
- strategy_context:
  - strategy_id: husband_personal_2026-07-25
  - effective_from: 2026-07-25
  - active_plan_ids: ['2026-07-25_cash_redeployment']
  - reserved_hobby_cash_jpy: 1000000
  - unallocated_liquidity_jpy: 12622664
- monthly_execution_outputs:
  - source_role: calculated_review_material_not_transaction_record
  - review_target_month: 2026_08
  - nisa_growth_quota_status: exhausted
  - fixed_core_auto_invest_amount_jpy: 100000
  - taxable_core_spot_buy_required: True
  - recommended_taxable_core_spot_buy_jpy: 12622664
  - core_spot_buy_account_type: 特定口座（源泉徴収あり）
  - portfolio_management_mode: approved_transition_plan
  - monthly_core_budget_tier: approved_lump_sum_plan
  - recommended_monthly_core_buy_budget_jpy: 12622664
  - monthly_total_core_deployment_jpy: 12722664
  - candidate_count: 12
  - pension_monthly_dca_total_jpy: 55000
  - annualized_pension_dca_jpy: 660000
  - annualized_pension_dca_pct_of_total_assets: 1.65%
  - crypto_weekly_dca_total_jpy: 4000
  - annualized_crypto_dca_jpy: 208000
  - annualized_crypto_dca_pct_of_total_assets: 0.52%
  - taxable_account_note: NISA成長投資枠枯渇のため、2026年5月〜12月のcoreスポット買いは原則として特定口座で行う
  - nisa_exhaustion_adjustment_reason: NISA枠がないからcore購入を弱めるのではなく、iDeCoと暗号資産の既存積立もキャッシュアウトとして考慮しつつ特定口座スポットで補う
- quarterly_rule_review_outputs:
  - no_change: False
  - classification_override_count: 1
  - core_reference_missing_symbols: []
  - core_reference_proxy_suggestions: {}
  - tradable_core_pct: 26.83%
  - effective_core_including_pension_pct: 37.00%
  - cash_normalization_months_estimate:
    - gross_deployment_months: None
    - net_cash_reduction_months: None
    - assumed_monthly_cash_inflow_jpy: None
    - net_cash_reduction_jpy: None
  - direct_cap_monitor_pct: 15.74%
  - direct_plus_indirect_watch_metric_pct: 17.14%
  - direct_semiconductor_exposure_pct: 15.74%
  - combined_semiconductor_ai_infra_watch_pct: 17.14%
  - indirect_ai_infra_exposure_pct: 1.41%

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
- 承認済みactive planがある場合は、その計画額と実行前残高確認条件を優先し、別の金額を作らないこと
- `多めに` `厚めに` `数十万円` `50〜100万円` のような曖昧表現は禁止
- 定期積立額とcoreスポット買い提案額は別項目として明示し、合算値には内訳を付けること
- 承認済みactive planは計画であって取引実績ではない。注文済み・約定済みと表現しないこと
- active planの商品、配分、口座、execution_method、実行前確認条件を優先し、別案を作らないこと
- broad core不足と未配分現金の是正時も、承認済み趣味枠現金1,000,000円は維持すること
- 根拠のない月650,000円の現金流入を計算や提案に使わないこと
- 配分先内訳を明示すること
- active_plan_execution_method がある場合はその実行方法をそのまま明示すること
- 判断根拠は `相場面` / `ポートフォリオ歪み` / `流動性水準` を分けて書くこと
- その判断が `ルール上の判断` か `今月の裁量判断` かを分離すること
- broad market core 商品を優先し、むやみに新規商品を増やさないこと
- 新規のbroad core購入は、承認済み戦略どおり全世界株式100%とすること
- 既存S&P500は強制売却しないが、通常の新規購入先にはしないこと
- 証券注文、送金、Calendar登録を実行したと表現しないこと
- 債券や低リスク商品を提案してもよいが、core equity のスポット買い額は必ず別途提示すること
- `積立しているからスポット買いは不要` とは結論しないこと

【今月の指値提案】
- この『今月』は review_target_month を指す。snapshot_date が前月末でも、対象月を取り違えないこと
- 各銘柄について 0段以上の任意段数で提案してよい
- 0段の場合は『今月は見送り』と明記する
- Python 候補より段数を減らした場合は、その理由が『ルール上の判断』か『今月の裁量判断』かを明記する
- Python 候補より段数を増やした場合も、その理由を明記する
- 承認済みcore計画の資金を削ってまでテーマ銘柄を買わないこと
- 直接半導体比率が15%を超える間は通常買い増しを行わず、20%超ではリバランスを人間へ提案すること
- 高ボラ単一銘柄は5%を通常上限、8%超をリバランス提案閾値として扱うこと
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
- `plans/recurring/`由来の観測済み積立設定を前提にし、active planの商品配分や取引実績とは分けること
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
- must は現行source of truthとの矛盾、算術誤り、危険な外部書込み、またはレビュー出力へ実害がある機械的不整合に限定すること
- 現行source of truthにない新しい運用・安全・ガバナンス方針はshouldの四半期提案とし、承認済み計画を遡及的に無効化しないこと

【Codex向け修正要約】
- このセクションの本文全体を、必ず単一の ```md コードブロックで出力すること
- コードブロック外に Codex向け修正要約を書かないこと
- 問題がない場合でもコードブロックは省略せず、`must: なし` のように明記すること
- must / should / nice_to_have は空欄不可だが、該当なしの場合は `なし` と書いてよい
- 新規生成物の反映先は `reports/generated/` とし、不変履歴や過去生成物の書換えを依頼しないこと
- 出力例:
```md
must:
- なし

should:
- なし

nice_to_have:
- なし

修正目的:
- 現行戦略と生成物の整合性を維持する

変更すべき仕様:
- 新規生成物は reports/generated に限定する
- data/history と prompts/generated は不変履歴として扱う

影響範囲:
- reports/generated/

推奨テスト:
- repository-audit と関連テストを実行する
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
- 承認済みactive planがある場合は、確認済み利用可能現金から趣味枠現金1,000,000円を控除した額を提示してください。
- 金額はその月の portfolio 歪み、相場状況、流動性水準で変動してよいです。
- 定期積立は観測済み設定、active planは承認済み未実行計画として分離してください。
- 税制、NISA枠、商品仕様を判断に使う場合は公式一次情報の参照日とURLを示してください。
- iDeCo55,000円/月とBTC/ETH週次積立は、承認済み現金再配分計画とは別の継続キャッシュアウトとして表示してください。
- coreスポット買いの提案が rule-based なのか discretionary なのかを明示してください。
- cash_excess_pct が大きいほど、core スポット買い額を増やしてください。
- core_delta_pct が大きいほど、core スポット買い額を増やしてください。
- broad market ベースで明確に下落している月は、core スポット買い額を増やしてください。
- 高値圏でも cash_excess と core不足が大きい場合は、一定額は必ず実行してください。
- 互換用の旧バケットを現行戦略の目標値として使わず、broad_core不足是正を優先してください。
- 既存の broad market core 商品を優先し、新規商品追加は最小限にしてください。
- 債券や低リスク商品を提案する場合でも、core equity スポット買い額そのものは別で必ず提示してください。
- `全部債券` `全部現金維持` は不可です。
- 大口支出情報は未記録として扱い、存在を推測しないでください。
- 給与で通常生活費と本人分住宅ローンを賄えている一方、給与額と毎月余剰額は未記録として扱ってください。
- 住宅ローンは世帯当初借入64,900,000円、本人当初借入32,450,000円、年1.120%、返済初期である点を考慮してください。当初借入額を現在残高と表現しないでください。
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
- ルール改善が不要な場合は、その旨を明記してください。

## 14. 必須の Codex 向け修正要約観点
- must / should / nice_to_have は必ず埋めてください。
- 空欄は不可ですが、該当なしの場合は `なし` と明記してください。
- 【Codex向け修正要約】 全体を単一の ```md コードブロックで出力してください。
- 新規生成物は reports/generated/ に限定し、不変履歴の書換えを依頼しないでください。
- monthly review と quarterly rule review を分けて整理してください。
- 修正対象ファイルと必要テストを、Codex が編集に入れる粒度で書いてください。

## 15. 回答前の必須acceptance check
- 外部ファイル名、添付状況、取得失敗、再アップロード案内が最終回答にない
- active planのbasis値とcurrent recalculated amountの差を、基準日差を無視して不整合や統一対象にしていない
- 現行source of truthにない新しい方針をmustへ入れたり、承認済み計画へ遡及適用したりしていない
- 住宅ローンの当初借入額を現在残高と表現していない
- 定期積立の変更提案には現行戦略の商品名を正確に記載し、ユーザー確認前に変更済みと表現していない
- Webの各主張は、それを直接支える公式一次情報へ重複なしでリンクし、事実と推論を分離している
- 【Codex向け修正要約】のコードブロックを閉じた後に何も追記していない
- 上記を満たさない場合は、回答を送信せず修正してから再点検する

指値設定対象月キー: 2026_08
