# 現在の資産と私の方向性から、独立した投資レビューをしてください

引き渡し方式はA：本文完結型です。この本文全体を資産運用Project外の新規Temporary Chatへコピー＆ペーストしてください。添付は不要です。ローカルの元パスは由来を示すもので、開く必要はありません。

依頼日時：2026-10-11T00:13:19+09:00。資産スナップショット基準日：2026-10-10。

過去のレビューや会話を前提にせず、下記の現在の事実と私の方向性から判断してください。目的・生活上の制約・趣味の意向は守り、配分・銘柄・上限は必要なら提案し直してください。今の保有が合理的だと決めつけず、維持する場合にも根拠を示してください。

毎回同じ結論になる必要はありません。違いを作るために結論を変える必要もありません。その時点で利用できる情報とあなたの判断を使ってください。重要な論点、調査順序、分析手法はあなたに任せます。

## 今回は、一番重要と判断する一論点だけを調べてください

最初に対象・基準日・目的・制約を短く確認し、重要だと考える一論点を選んで調べてください。今回は全調査や売買案の確定まで進めず、結論、確認済み事実と直接URL、未確認事項、次に私が送る短い指示だけを簡潔に返してください。次の工程は私が同じ会話で明示的に依頼してから行ってください。

ユーザーの事実は本文から取り、外部の事実は企業・運用会社・指数提供会社・公的機関等の一次情報で確認してください。出典名、直接URL、公表日・データ基準日、確認日、情報の変動性を残してください。調査締切は依頼日時です。基準日の保有評価額と後で確認した価格を混ぜず、推論・仮定・未確認を区別してください。使えない調査・計算能力に依存する数値は作らないでください。

## 最終的に受け取りたいもの

調査を一論点ずつ終えた後、別工程として確認済み情報だけを統合してください。統合時は追加調査や新たな推測をせず、未確認は残してください。

現在の生活を楽しめる持続可能な拠出を比較案で共通にして、目的に沿う行動を一案にまとめてください。資産効率を比較する全世界株式のみの基準案も含め、趣味として正のサテライト配分を持つ意向との違いを説明してください。拠出増加だけで比較結果を改善しないでください。

全売買可能明細を口座別に一件ずつ扱い、何を・いつ・どの口座で・どの方法と数量または金額で保有・売却するか示してください。未保有資産への購入も同じ粒度で示すか、購入しない理由を述べてください。iDeCoは通常の売買可能明細と区別してください。比率は分子・分母・分母定義・測定時点を添え、税・費用・非課税口座の機会価値を考慮してください。値下がりだけを売却理由にしないでください。

依頼時点からの推奨行動期間と、その期間を選んだ根拠を示してください。回答の最後に、最新スナップショットで次回レビューを依頼する時期と理由、早期に見直す条件を提案してください。全売買はユーザー承認前の提案です。

統合の後、さらに別の依頼で、リポジトリ管理を担当するCodexへそのまま貼り付けられる、自己完結したドキュメンテーション依頼用プロンプトを作ってください。必要な結論と根拠を全文に含め、過去の回答を参照させないでください。この最終成果物には次を含めてください。

- 調査目的・対象範囲・基準日・結論、確認済み事実・推論・未確認事項の区別。
- 出典名・直接URL・確認日・変動性、関連する元パス・安定ID・現在の事実との対応。
- Codexへ依頼する追加・更新・維持事項と変更禁止事項。未承認提案だけで戦略・計画の正本や履歴を変更しない条件。
- 売買案の口座・数量または算式・注文種別・指値ルール・時期・期限・部分約定・失効時処理・売却後資金・税確認・承認状態。不明はnullとし、解除方法を併記。
- Codexが回答後に現行戦略・計画・取引・税務・注文仕様を照合すること、既存スキーマ・命名規則の遵守、推測禁止・未解決を解決済みにしない条件。
- YAML parse・schema validation・重複ID・参照整合性・関連テスト・repository-audit等の検証と、終了時に報告する変更ファイル・反映内容・未解決事項・検証結果。

判断方法や回答YAMLの型を先に固定する必要はありません。後段のリポジトリ整合性・構造化・注文入力時確認はCodexが担当します。

## 現在の事実とユーザーの方向性

金額・通貨・数量・確認日・未確認値は以下のとおりです。これは現在の入力であり、推奨配分や過去の助言ではありません。
株式数量は株、投資信託数量は口、投資信託単価は1万口あたり円、米国株単価はUSDです。円評価額は記録値を使用し、別資料の価格や為替を混ぜて再計算しないでください。銀行書類由来の住宅ローンも記載値と基準日をそのまま使ってください。

```yaml
schema_version: 1
packet_type: fresh_snapshot_independent_review
requested_at: '2026-10-11T00:13:19+09:00'
research_cutoff_at: '2026-10-11T00:13:19+09:00'
portfolio_snapshot:
  source_ref: data/normalized/snapshot_2026_10.yaml
  stable_id: snapshot_2026-10-10
  as_of: '2026-10-10'
  currency_base: JPY
  total_assets_jpy: 37695573
  category_totals_jpy:
    預金・現金: 2245005
    株式（現物）: 5156496
    投資信託: 26213967
    年金: 4063372
    ポイント: 16733
  observation_basis:
    snapshot_date_basis: ユーザが指定した基準日。Money Forward画面に日付・各口座更新日時の表示はない。
    valuation_basis: Money Forward表示値を全体・カテゴリ・保有明細へ統一。証券会社CSVの異なる数量・価格・評価額はbroker_observationへ別記し合算しない。
    broker_export_time_basis: 楽天CSVの出力時刻はファイル名由来。個別商品の現在値(更新日)は空欄。野村CSVの基準日も空欄。
    usd_jpy_reference:
      value: 158.31
      displayed_at: 10/10 05:59
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv
      scope: 楽天CSVの参考為替。Money Forwardへ適用した為替とは断定しない。
  holdings:
  - symbol: LIQUIDITY
    name: 預金・現金
    source_category: 預金・現金
    institution: null
    account_type: null
    quantity: null
    avg_cost: null
    current_price: null
    unit_price: null
    profit_loss_jpy: null
    market_value_jpy: 2245005
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_cash.png
    acquired_on: null
    observed_on: '2026-10-10'
    components:
    - name: PayPay
      institution: PayPay
      market_value_jpy: -130485
      currency: JPY
      quantity: null
    - name: Suica
      institution: モバイルSuica（モバイルSuica ID）
      market_value_jpy: 1915
      currency: JPY
      quantity: null
    - name: 普通
      institution: 三菱UFJ銀行
      market_value_jpy: 2263963
      currency: JPY
      quantity: null
    - name: 円預金(普通預金)
      institution: 楽天銀行
      market_value_jpy: 8284
      currency: JPY
      quantity: null
    - name: 米ドル
      institution: 楽天証券
      market_value_jpy: 959
      currency: USD
      quantity: null
    - name: MRF
      institution: 野村証券
      market_value_jpy: 369
      currency: JPY
      quantity: null
    - name: 預り金
      institution: 楽天証券
      market_value_jpy: 100000
      currency: JPY
      quantity: null
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv
      foreign_deposit:
        quantity: 6.06
        currency: USD
        exchange_rate_jpy_per_usd: 158.31
        market_value_jpy: 959
      jpy_deposit_jpy: 0
      nomura_mrf_jpy: 369
      notes: Money Forwardの楽天証券預り金100,000円に対して楽天CSVの円預り金は0円。二つを合算せず原因は未確認。
  - symbol: '7203'
    name: トヨタ自動車
    source_category: 株式（現物）
    institution: 野村証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 800
    avg_cost: 532
    current_price: 2911
    unit_price: null
    profit_loss_jpy: 1902800
    market_value_jpy: 2328400
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_equities.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/nomura.csv#L13
      observed_on: '2026-10-10'
      product_name: トヨタ自動車
      account_label: 特定
      quantity: 800
      order_quantity: null
      sellable_quantity_round_lot: 800
      avg_cost: 532
      current_price: 2910.5
      price_as_of: null
      acquisition_cost_jpy: 425600
      market_value_jpy: 2328400
      profit_loss_jpy: 1902800
  - symbol: PLTR
    name: パランティア・テクノロジーズ
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 11
    avg_cost: 151.22
    current_price: 203.33
    unit_price: null
    profit_loss_jpy: 94549
    market_value_jpy: 354231
    currency: USD
    source_ref: data/raw/evidence/2026-10-10/moneyforward_equities.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L27
      observed_on: '2026-10-10'
      product_name: パランティア・テクノロジーズ
      account_label: 特定
      quantity: 11
      quantity_unit: 株
      avg_cost: 151.2236
      price_unit: USD
      current_price: 209.05
      current_price_updated_on: null
      market_value_jpy: 364041
      market_value_foreign_displayed: 2,299.55 USD
      profit_loss_jpy: 104359
      profit_loss_pct_displayed: 40.18
  - symbol: CIBR
    name: ファーストトラスト ナスダック サイバーセキュリティ ETF
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 74
    avg_cost: 76.66
    current_price: 108.47
    unit_price: null
    profit_loss_jpy: 403113
    market_value_jpy: 1271281
    currency: USD
    source_ref: data/raw/evidence/2026-10-10/moneyforward_equities.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L28
      observed_on: '2026-10-10'
      product_name: ファーストトラスト ナスダック サイバーセキュリティETF
      account_label: 特定
      quantity: 74
      quantity_unit: 株
      avg_cost: 76.6571
      price_unit: USD
      current_price: 110
      current_price_updated_on: null
      market_value_jpy: 1288643
      market_value_foreign_displayed: 8,140.00 USD
      profit_loss_jpy: 420475
      profit_loss_pct_displayed: 48.43
  - symbol: MSFT
    name: マイクロソフト
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 9
    avg_cost: 398.74
    current_price: 532.71
    unit_price: null
    profit_loss_jpy: 193035
    market_value_jpy: 759335
    currency: USD
    source_ref: data/raw/evidence/2026-10-10/moneyforward_equities.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L29
      observed_on: '2026-10-10'
      product_name: マイクロソフト
      account_label: 特定
      quantity: 9
      quantity_unit: 株
      avg_cost: 398.7366
      price_unit: USD
      current_price: 535.07
      current_price_updated_on: null
      market_value_jpy: 762362
      market_value_foreign_displayed: 4,815.63 USD
      profit_loss_jpy: 196062
      profit_loss_pct_displayed: 34.62
  - symbol: URA
    name: グローバルX ウラニウム ETF
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 72
    avg_cost: 46.1
    current_price: 38.87
    unit_price: null
    profit_loss_jpy: -70557
    market_value_jpy: 443248
    currency: USD
    source_ref: data/raw/evidence/2026-10-10/moneyforward_equities.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L30
      observed_on: '2026-10-10'
      product_name: グローバルX ウラニウム ETF
      account_label: 特定
      quantity: 72
      quantity_unit: 株
      avg_cost: 46.0991
      price_unit: USD
      current_price: 38.9
      current_price_updated_on: null
      market_value_jpy: 443394
      market_value_foreign_displayed: 2,800.80 USD
      profit_loss_jpy: -70411
      profit_loss_pct_displayed: -13.7
  - symbol: NISSEI_SOX_1
    name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    source_category: 投資信託
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 860960
    avg_cost: 15802
    current_price: 47901
    unit_price: null
    profit_loss_jpy: 2763627
    market_value_jpy: 4124084
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L31
      observed_on: '2026-10-10'
      product_name: ニッセイSOX指数インデックスファンド(米国半導体株)＜購入・換金手数料なし＞
      account_label: 特定
      quantity: 860960
      quantity_unit: 口
      avg_cost: 15801.63
      price_unit: 円
      current_price: 47901
      current_price_updated_on: null
      market_value_jpy: 4124084
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 2763627
      profit_loss_pct_displayed: 203.13
  - symbol: NISSEI_SOX_2
    name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISA成長投資枠
    quantity: 415654
    avg_cost: 14435
    current_price: 47901
    unit_price: null
    profit_loss_jpy: 1391024
    market_value_jpy: 1991024
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L32
      observed_on: '2026-10-10'
      product_name: ニッセイSOX指数インデックスファンド(米国半導体株)＜購入・換金手数料なし＞
      account_label: NISA成長投資枠
      quantity: 415654
      quantity_unit: 口
      avg_cost: 14435.08
      price_unit: 円
      current_price: 47901
      current_price_updated_on: null
      market_value_jpy: 1991024
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 1391024
      profit_loss_pct_displayed: 231.83
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_1
    name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISAつみたて投資枠
    quantity: 1162027
    avg_cost: 14630
    current_price: 19635
    unit_price: null
    profit_loss_jpy: 581640
    market_value_jpy: 2281640
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L33
      observed_on: '2026-10-10'
      product_name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
      account_label: NISAつみたて投資枠
      quantity: 1212957
      quantity_unit: 口
      avg_cost: 14839.77
      price_unit: 円
      current_price: 19635
      current_price_updated_on: null
      market_value_jpy: 2381641
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 581641
      profit_loss_pct_displayed: 32.31
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_2
    name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISA成長投資枠
    quantity: 846995
    avg_cost: 17710
    current_price: 19635
    unit_price: null
    profit_loss_jpy: 163074
    market_value_jpy: 1663075
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L34
      observed_on: '2026-10-10'
      product_name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
      account_label: NISA成長投資枠
      quantity: 846995
      quantity_unit: 口
      avg_cost: 17709.67
      price_unit: 円
      current_price: 19635
      current_price_updated_on: null
      market_value_jpy: 1663075
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 163074
      profit_loss_pct_displayed: 10.87
  - symbol: RAKUTEN_PLUS_SP500
    name: 楽天・プラス・S&P500インデックス・ファンド(楽天・プラス・S&P500)
    source_category: 投資信託
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 106530
    avg_cost: 11715
    current_price: 20130
    unit_price: null
    profit_loss_jpy: 89645
    market_value_jpy: 214445
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L35
      observed_on: '2026-10-10'
      product_name: 楽天・プラス・Ｓ＆Ｐ５００インデックス・ファンド(楽天・プラス・Ｓ＆Ｐ５００)
      account_label: 特定
      quantity: 106530
      quantity_unit: 口
      avg_cost: 11715.01
      price_unit: 円
      current_price: 20130
      current_price_updated_on: null
      market_value_jpy: 214445
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 89645
      profit_loss_pct_displayed: 71.83
  - symbol: EMAXIS_SLIM_SP500_1
    name: eMAXIS Slim 米国株式(S&P500)
    source_category: 投資信託
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 337199
    avg_cost: 42349
    current_price: 45246
    unit_price: null
    profit_loss_jpy: 97691
    market_value_jpy: 1525691
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L36
      observed_on: '2026-10-10'
      product_name: eMAXIS Slim 米国株式(S&P500)
      account_label: 特定
      quantity: 337199
      quantity_unit: 口
      avg_cost: 42348.88
      price_unit: 円
      current_price: 45246
      current_price_updated_on: null
      market_value_jpy: 1525691
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 97691
      profit_loss_pct_displayed: 6.84
  - symbol: EMAXIS_SLIM_SP500_2
    name: eMAXIS Slim 米国株式(S&P500)
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISAつみたて投資枠
    quantity: 419748
    avg_cost: 33711
    current_price: 45246
    unit_price: null
    profit_loss_jpy: 484192
    market_value_jpy: 1899192
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L37
      observed_on: '2026-10-10'
      product_name: eMAXIS Slim 米国株式(S&P500)
      account_label: NISAつみたて投資枠
      quantity: 419748
      quantity_unit: 口
      avg_cost: 33710.7
      price_unit: 円
      current_price: 45246
      current_price_updated_on: null
      market_value_jpy: 1899192
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 484192
      profit_loss_pct_displayed: 34.21
  - symbol: EMAXIS_SLIM_SP500_3
    name: eMAXIS Slim 米国株式(S&P500)
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISA成長投資枠
    quantity: 228995
    avg_cost: 39302
    current_price: 45246
    unit_price: null
    profit_loss_jpy: 136111
    market_value_jpy: 1036111
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L38
      observed_on: '2026-10-10'
      product_name: eMAXIS Slim 米国株式(S&P500)
      account_label: NISA成長投資枠
      quantity: 228995
      quantity_unit: 口
      avg_cost: 39302.17
      price_unit: 円
      current_price: 45246
      current_price_updated_on: null
      market_value_jpy: 1036111
      market_value_foreign_displayed: '-'
      profit_loss_jpy: 136111
      profit_loss_pct_displayed: 15.12
  - symbol: EMAXIS_SLIM_ALL_COUNTRY
    name: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)
    source_category: 投資信託
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 3012072
    avg_cost: 38305
    current_price: 38109
    unit_price: null
    profit_loss_jpy: -59025
    market_value_jpy: 11478705
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_funds.png
    acquired_on: null
    observed_on: '2026-10-10'
    broker_observation:
      source_ref: data/raw/evidence/2026-10-10/rakuten.csv#L39
      observed_on: '2026-10-10'
      product_name: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)
      account_label: 特定
      quantity: 3012072
      quantity_unit: 口
      avg_cost: 38304.96
      price_unit: 円
      current_price: 38109
      current_price_updated_on: null
      market_value_jpy: 11478705
      market_value_foreign_displayed: '-'
      profit_loss_jpy: -59025
      profit_loss_pct_displayed: -0.51
  - symbol: PENSION_EMAXIS_SLIM_ALL_COUNTRY
    name: eMAXIS Slim 全世界株式(オール・カントリー)
    source_category: 年金
    institution: null
    account_type: iDeCo
    quantity: null
    avg_cost: null
    current_price: null
    unit_price: null
    profit_loss_jpy: 722677
    market_value_jpy: 4063372
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_pension_points.png
    acquired_on: null
    observed_on: '2026-10-10'
  - symbol: POINTS_MILES
    name: ポイント
    source_category: ポイント
    institution: null
    account_type: null
    quantity: null
    avg_cost: null
    current_price: null
    unit_price: null
    profit_loss_jpy: null
    market_value_jpy: 16733
    currency: JPY
    source_ref: data/raw/evidence/2026-10-10/moneyforward_pension_points.png
    acquired_on: null
    observed_on: '2026-10-10'
    components:
    - name: ANAマイレージ(マイル)
      point_type: null
      institution: ANAマイレージ
      quantity: 786
      conversion_rate: 1.0
      market_value_jpy: 786
      expires_on: null
    - name: Tポイント
      point_type: Tポイント
      institution: Vポイント（Yahoo! JAPAN ID）
      quantity: 7
      conversion_rate: 1.0
      market_value_jpy: 7
      expires_on: '2024-12-22'
    - name: 通常ポイント
      point_type: Amazonポイント
      institution: Amazon.co.jp
      quantity: 7
      conversion_rate: 1.0
      market_value_jpy: 7
      expires_on: '2027-09-27'
    - name: 楽天ポイント
      point_type: 楽天ポイント
      institution: 楽天市場(my Rakuten)
      quantity: 15933
      conversion_rate: 1.0
      market_value_jpy: 15933
      expires_on: '2027-09-30'
financial_facts:
  source_ref: financial/versions/2026-08-29-v4.yaml
  stable_id: husband_personal_financial_context_2026-08-29-v4
  confirmed_at: '2026-08-29'
  values:
    scope:
      owner: husband
      portfolio: personal_financial_assets
      excludes:
      - wife_personal_financial_assets
      mortgage_risk_scope: household_pair_loan_with_husband_share
    cash_flow:
      regular_month:
        income_after_tax_social_insurance_mortgage_ideco_jpy:
          value: 374171
          as_of: '2026-07-25'
          certainty: confirmed_user_value
          is_expense_value: false
        nisa_contribution_jpy:
          value: 100000
          as_of: '2026-07-25'
          certainty: confirmed_user_value
          is_expense_value: false
        disposable_after_nisa_jpy:
          value: 274171
          formula: income_after_tax_social_insurance_mortgage_ideco_jpy - nisa_contribution_jpy
          as_of: '2026-07-25'
          certainty: machine_calculation_from_confirmed_values
          is_expense_value: false
        essential_expenses_jpy:
          value: 250000
          as_of: '2026-08-02'
          certainty: confirmed_user_estimate
        balance:
          value: approximately_zero
          as_of: '2026-07-25'
          certainty: confirmed_user_description
      bonus:
        take_home_reference_jpy: 2000000
        amount_qualifier: approximately_slightly_below_reference
        certainty: rough_user_estimate
        annual_frequency: 1
        payment_months:
        - 1
        allocation_policy: unplanned_discretionary_spending_from_surplus
        typical_uses:
        - travel
        - discretionary_purchases
    cash_requirements:
      emergency_fund:
        target_jpy: 2000000
        status: confirmed_user_target
        permitted_fallback: sell_all_country_fund_even_during_market_decline_if_needed
      contingency_reserve:
        enabled: false
        target_jpy: 0
        status: confirmed_not_required
      near_term_large_expenses:
        horizon_years: 3
        confirmed_items:
        - item_id: near_term_large_purchase_reserve_2026
          description: 近々予定している大型購入（購入内容・実施日は未指定）
          amount_jpy: 467987
          funding_account: 三菱UFJ銀行 普通預金
          scheduled_date: null
          status: confirmed_reserve_required
          investment_treatment: excluded_from_investable_cash
          confirmed_at: '2026-08-29'
        unplanned_travel:
          expected: true
          committed_amount_jpy: null
          scheduled_date: null
          funding_policy: pay_from_bonus_or_other_realized_surplus
          treatment: not_a_confirmed_large_expense
    mortgage:
      evidence:
        document: 名古屋銀行 ご返済予定表
        created_at: '2026-06-29'
      household_total:
        original_principal_jpy: 64900000
        annual_interest_rate: 0.0112
        fixed_or_variable: variable
        loan_date: '2024-09-27'
        maturity_date: '2064-09-27'
        monthly_payment_jpy: 148342
        annual_payment_jpy: 1780104
        bonus_payment_jpy: 0
        scheduled_balance_after_2026_07_27_jpy: 62520685
      husband_share:
        allocation_pct: 0.5
        original_principal_jpy: 32450000
        monthly_payment_jpy: 74171
        annual_payment_jpy: 890052
    unknown_information:
    - ボーナスの正確な手取り額
    - 未計画旅行の金額と時期
    - 公的年金の個人別確定見込額
    - 相続の本人取り分、実際の時期および税引後額
    personal_profile:
      date_of_birth: '1992-01-07'
      tax_residency: Japan
      planning_end_age: 100
      expected_withdrawal_start: '2057-01-07'
      earliest_possible_asset_use_date: '2057-01-07'
    human_capital:
      education: graduate_school
      employment_status: full_time_employee
      occupation: automotive_software_engineer
      income_stability: high
      income_stability_reason: user_identified_only_singularity_as_material_risk
      expected_salary_continuation_years: 30
      planned_retirement_age: 65
      retirement_age_certainty: rough_user_plan_subject_to_future_conditions
      known_long_leave_or_unemployment_risk: none_identified_by_user
    expected_future_cash_flows:
      employment_income:
        expected_continuation_years: 30
        planned_retirement_age: 65
        certainty: rough_user_plan_subject_to_future_conditions
      bonus:
        future_amount_jpy: null
        status: unknown
      inheritance:
        source_owner: father
        source_estimated_total_assets_jpy: 100000000
        estimate_qualifier: approximately
        reported_beneficiaries:
        - user
        - mother
        - younger_sister
        user_is_beneficiary: true
        user_share_jpy: null
        possible_timing_within_years: 20
        timing_certainty: speculative_user_estimate
    leverage_allowed: false
user_directions:
  source_ref: strategy/versions/2026-08-09-v2.yaml
  stable_id: husband_personal_2026-08-09-v2
  confirmed_at: '2026-08-09'
  values:
    statement: 今の生活を楽しみつつ無理のない範囲で運用し、65歳時点での投資利益を最大化する
    target_age: 65
    target_date: '2057-01-07'
    lifestyle_constraint: '日常生活、旅行、趣味その他の現在の生活の楽しみを不当に削る拠出を前提にせず、 家計・住宅ローン・生活防衛資金と両立する持続可能な拠出だけを使う。

      '
    positive_satellite_allocation_required: true
holding_user_intents:
  source_ref: holdings/versions/2026-08-14-v4.yaml
  stable_id: holding_metadata_2026-08-14-v4
  confirmed_at: '2026-08-14'
  values:
    '7203':
      user_intent:
        holding_reason: 祖父から相続した株式をそのまま保有。トヨタ株としての積極的な保有理由はない
        disposition: sell_if_rationally_justified
        sell_condition: 合理的な理由があれば売却してよい
        confirmed_at: '2026-08-02'
observed_recurring_settings:
  source_ref: plans/recurring/versions/2026-08-09.yaml
  stable_id: recurring_contributions_observed_2026-08-09
  confirmed_at: '2026-08-09'
  values:
    total_monthly_jpy: 100000
    nisa_growth_quota_status: exhausted
    plans:
    - day_of_month: null
      fund_name: 全世界株式（正式商品名未確認）
      amount_jpy: 100000
      settlement_type: null
      account_type: NISAつみたて投資枠
      distribution_course: null
    pension_monthly_dca:
    - symbol: IDECO_ALL_COUNTRY
      fund_name: eMAXIS Slim 全世界株式（オール・カントリー）
      amount_jpy_per_month: 55000
      account_type: iDeCo
      asset_class: pension
    crypto_weekly_dca: []
account_type_gate:
  status: complete
  checked_holding_count: 14
data_quality_notes:
- カテゴリ合計37,695,573円は資産総額と一致。
- 株式明細合計5,156,495円はカテゴリ表示額より1円少ない。
- 投資信託明細合計26,213,967円はカテゴリ表示額と一致。
- 全明細合計37,695,572円は資産総額より1円少ない。総資産の0.1%未満の許容差であり残差用の架空資産を追加しない。
- 預金・現金7明細とポイント4明細はそれぞれカテゴリ表示額と一致。PayPayの負数も表示どおり保持する。
- 楽天・プラス・オールカントリーのNISAつみたて枠はCSVが50,930口、100,001円多い。単なる価格丸め差として処理しない。
- 楽天の米国株4明細はCSVが合計30,345円多い。価格更新の差を観測したが、画面同期時刻がないため原因は断定しない。
- 楽天の円預り金はMoney Forwardが100,000円、CSVが0円。投資信託の差との因果関係を推定しない。
- 楽天CSVの米国株明細合計は米国株カテゴリ合計より2円少ない。投資信託明細合計はCSVの投資信託カテゴリ合計と一致。保有商品明細合計は保有商品の評価額合計より2円少ない。
- Tポイントの期限は画面上2024/12/22。基準日より過去だが失効・利用可否は未確認のため7円を削除しない。
- 取得日・各口座の同期日時・数量差の発生原因・CSVにない注文状況は未確認。
```
