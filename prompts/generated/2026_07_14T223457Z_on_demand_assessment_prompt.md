# 保有銘柄の市場動向・ニュース オンデマンドアセスメント依頼

あなたは、金融市場の値動きとニュースの因果関係を慎重に評価する投資アシスタントです。

以下の保有銘柄リストと市場価格データを使い、各銘柄について「直近でどう動いたか」「市場では何が背景として評価されているか」「長期シナリオに影響する変化か、一時的なセンチメントか」をオンデマンドで調査・評価してください。

この依頼の目的は保有資産額、数量、取得単価、含み損益、配分の診断ではありません。それらを推測したり、ポートフォリオ診断に話を広げたりしないでください。スナップショットは保有銘柄の特定にだけ使います。

## 必須の情報調査

- Web検索を行い、プロンプトにある日足価格データより新しい価格が確認できる場合は、その価格と取得時刻を示す。
- 原則として直近 `authoritative_news_lookback_days` 日間を調べ、価格変動に関係し得る重要情報を探す。
- 企業固有要因、業界・指数要因、金利・為替・商品市況、地政学、規制・政策を分けて調査する。
- 株式は企業IR、決算資料、法定開示、取引所、規制当局などの一次情報を優先する。
- 投資信託・年金のプロキシは、指数提供会社、運用会社、中央銀行、政府統計、取引所などの一次情報を優先する。
- 市場参加者の解釈や値動きとの結び付けには、Reuters、AP、Bloomberg、Financial Times、日本経済新聞など、編集体制と取材源が明確な報道を使う。
- 出所不明のSNS投稿、まとめサイト、アフィリエイト記事だけを根拠にしない。

## 因果関係の扱い

- 「価格が下がった」と「特定ニュースが原因で下がった」は別の主張です。時間順序、同業・指数との比較、複数の信頼できる報道を確認してください。
- 市場報道が値動きの背景として明示している場合は `報道で市場要因として扱われている` と書いてください。
- 直接の裏付けがなく、値動きとニュースの時間的一致から推測する場合は `妥当な仮説` とし、断定しないでください。
- 複数要因がある場合は寄与度を無理に数値化せず、主要因・補助要因・無関係の可能性を分けてください。
- 例として地政学的衝突を扱う場合は、政府等の一次発表、原油・金利・為替・VIX、関連指数や同業銘柄の反応、市場概況報道を突き合わせ、単に「戦争だから下落」と結論づけないでください。
- ニュースが見当たらない場合は、無理に物語を作らず `個別材料は確認できず、指数・セクターまたは需給要因の可能性` としてください。

## 評価上の注意

- `yfinance` は最新取得可能な日足終値であり、リアルタイム気配値ではありません。
- `reference_role: proxy` は投資信託・年金と連動性の高いETF・指数等であり、当該商品の基準価額そのものではありません。
- 1日、5日、1か月、3か月の変化を分け、短期ノイズと継続トレンドを区別してください。
- 事実、報道された市場解釈、あなたの推論を明確に分けてください。
- 最終判断と発注はユーザが行います。売買を自動実行しないでください。

## 必須出力形式

【調査時点と市場概況】
- 調査日時とタイムゾーン
- 主要株価指数、金利、為替、原油等のうち今回の銘柄に重要な動き
- 市場全体のリスクオン／リスクオフを示す根拠

【銘柄別アセスメント】

各銘柄について、以下を繰り返してください。

### 銘柄名（symbol）

- 価格動向: 最新確認価格、1日、5日、1か月、3か月の変化
- 重要ニュース: 発生日、事実、情報源
- 市場での評価: 値動きの背景として報道・評価されている要因
- 因果関係の確度: `高い` / `中程度` / `低い` と理由
- シナリオ判定: `一時的センチメント` / `業績・長期シナリオへの影響候補` / `判断材料不足`
- 今後の確認トリガー: 決算、政策、価格水準、指数、金利、商品市況など

【横断テーマ】
- 複数の保有銘柄に共通する市場テーマ
- 同じニュースで動いている銘柄と、個別要因で動いている銘柄の区別
- 株式、投資信託、年金プロキシで反応が異なる理由

【要確認・判断保留】
- 価格データが古い、ニュースとの因果が弱い、プロキシ精度が低いなどの制約
- 追加確認が必要な情報

【参照情報】
- 各事実の出典名、記事・発表日、URL
- 同一ニュースの転載を複数ソースとして数えない

以下が保有銘柄リストと価格変動データです。

## 1. アセスメント依頼時点とデータの役割
- requested_at: 2026-07-14T22:34:57Z
- requested_at_local: 2026-07-15T07:34:57+09:00
- timezone: Asia/Tokyo
- holdings_inventory_snapshot_date: 2026-06-28
- holdings_inventory_age_days: 17
- holdings_inventory_status: fresh
- holdings_inventory_usage: 銘柄名の特定だけに使用し、保有額・数量・取得単価・損益・配分は評価しない
- market_price_basis: yfinance latest available daily close; intraday real-time quote is not guaranteed
- authoritative_news_lookback_days: 14
- computation_generated_at: 2026-07-14T22:34:57Z
- holdings_inventory_source: {'primary_source': 'moneyforward_screenshots_in_user_message', 'auxiliary_source': None, 'screenshot_count': 6, 'snapshot_date_basis': 'No visible date in screenshots; used session current date 2026-06-28.'}

## 2. アセスメント対象
- stocks_count: 9
- investment_funds_count: 9
- pension_count: 1
- ignored_non_investment_symbols: ['LIQUIDITY', 'POINTS_MILES']

## 3. 株式
| symbol | name | reference_symbol | reference_role | current_price | return_1d_pct | return_5d_pct | return_1m_pct | return_3m_pct | drawdown_21d_pct | drawdown_63d_pct | currency | market_as_of | market_age_days |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| 7203 | トヨタ自動車 | 7203.T | direct | 2839.0000 | 1.18 | -3.63 | -2.19 | -14.46 | -3.63 | -16.30 | JPY | 2026-07-14 | 1 |
| 9444 | トーシンホールディングス | 9444.T | direct | 259.0000 | 5.28 | 4.86 | 15.11 | -22.92 | -6.83 | -30.56 | JPY | 2026-07-14 | 1 |
| 2353 | 日本駐車場開発 | 2353.T | direct | 263.0000 | 0.77 | 1.54 | 5.62 | -6.07 | 0.00 | -6.07 | JPY | 2026-07-14 | 1 |
| 7201 | 日産自動車 | 7201.T | direct | 305.1000 | 0.00 | -5.19 | -14.51 | -14.25 | -13.54 | -23.53 | JPY | 2026-07-14 | 1 |
| SMH | ヴァンエック・半導体株ETF | SMH | direct | 600.3100 | 2.51 | 3.24 | -1.50 | 35.41 | -10.26 | -10.26 | USD | 2026-07-14 | 1 |
| PLTR | パランティア・テクノロジーズ | PLTR | direct | 133.7200 | 2.83 | -0.48 | 2.01 | 1.02 | -0.73 | -16.76 | USD | 2026-07-14 | 1 |
| CIBR | ファーストトラスト ナスダック サイバーセキュリティ ETF | CIBR | direct | 94.7300 | 3.15 | 2.73 | 10.83 | 49.91 | 0.00 | 0.00 | USD | 2026-07-14 | 1 |
| MSFT | マイクロソフト | MSFT | direct | 384.9300 | -1.55 | -1.01 | -1.39 | 0.15 | -3.71 | -16.41 | USD | 2026-07-14 | 1 |
| URA | グローバルX ウラニウム ETF | URA | direct | 41.5500 | 2.04 | -0.48 | -7.32 | -20.37 | -13.55 | -28.68 | USD | 2026-07-14 | 1 |

## 4. 投資信託
| symbol | name | reference_symbol | reference_role | current_price | return_1d_pct | return_5d_pct | return_1m_pct | return_3m_pct | drawdown_21d_pct | drawdown_63d_pct | currency | market_as_of | market_age_days |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| NISSEI_SOX_1 | ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし> | SOXX | proxy | 567.9200 | 2.58 | 2.94 | -3.24 | 44.38 | -13.30 | -13.30 | USD | 2026-07-14 | 1 |
| NISSEI_SOX_2 | ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし> | SOXX | proxy | 567.9200 | 2.58 | 2.94 | -3.24 | 44.38 | -13.30 | -13.30 | USD | 2026-07-14 | 1 |
| RAKUTEN_PLUS_ALL_COUNTRY_1 | 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー) | VT | proxy | 156.7800 | 0.62 | 0.28 | 0.75 | 7.09 | -1.22 | -1.61 | USD | 2026-07-14 | 1 |
| RAKUTEN_PLUS_ALL_COUNTRY_2 | 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー) | VT | proxy | 156.7800 | 0.62 | 0.28 | 0.75 | 7.09 | -1.22 | -1.61 | USD | 2026-07-14 | 1 |
| RAKUTEN_PLUS_SP500 | 楽天・プラス・S&P500インデックス・ファンド(楽天・プラス・S&P500) | VOO | proxy | 691.1000 | 0.38 | 0.59 | 1.90 | 9.57 | -0.40 | -1.03 | USD | 2026-07-14 | 1 |
| EMAXIS_SLIM_SP500_1 | eMAXIS Slim 米国株式(S&P500) | VOO | proxy | 691.1000 | 0.38 | 0.59 | 1.90 | 9.57 | -0.40 | -1.03 | USD | 2026-07-14 | 1 |
| EMAXIS_SLIM_SP500_2 | eMAXIS Slim 米国株式(S&P500) | VOO | proxy | 691.1000 | 0.38 | 0.59 | 1.90 | 9.57 | -0.40 | -1.03 | USD | 2026-07-14 | 1 |
| EMAXIS_SLIM_SP500_3 | eMAXIS Slim 米国株式(S&P500) | VOO | proxy | 691.1000 | 0.38 | 0.59 | 1.90 | 9.57 | -0.40 | -1.03 | USD | 2026-07-14 | 1 |
| EMAXIS_SLIM_ALL_COUNTRY | eMAXIS Slim 全世界株式(オール・カントリー)(オルカン) | ACWI | proxy | 156.9400 | 0.64 | 0.31 | 0.71 | 7.19 | -0.70 | -1.89 | USD | 2026-07-14 | 1 |

## 5. 年金
| symbol | name | reference_symbol | reference_role | current_price | return_1d_pct | return_5d_pct | return_1m_pct | return_3m_pct | drawdown_21d_pct | drawdown_63d_pct | currency | market_as_of | market_age_days |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| PENSION_EMAXIS_SLIM_ALL_COUNTRY | eMAXIS Slim 全世界株式(オール・カントリー) | ACWI | proxy | 156.9400 | 0.64 | 0.31 | 0.71 | 7.19 | -0.70 | -1.89 | USD | 2026-07-14 | 1 |

## 6. 価格取得状況・警告・不確実性
- market_reference_collection: {'requested_symbols': ['2353', '7201', '7203', '9444', 'CIBR', 'EMAXIS_SLIM_ALL_COUNTRY', 'EMAXIS_SLIM_SP500_1', 'EMAXIS_SLIM_SP500_2', 'EMAXIS_SLIM_SP500_3', 'MSFT', 'NISSEI_SOX_1', 'NISSEI_SOX_2', 'PENSION_EMAXIS_SLIM_ALL_COUNTRY', 'PLTR', 'RAKUTEN_PLUS_ALL_COUNTRY_1', 'RAKUTEN_PLUS_ALL_COUNTRY_2', 'RAKUTEN_PLUS_SP500', 'SMH', 'URA'], 'already_available_symbols': [], 'fetched_symbols': ['2353', '7201', '7203', '9444', 'CIBR', 'EMAXIS_SLIM_ALL_COUNTRY', 'EMAXIS_SLIM_SP500_1', 'EMAXIS_SLIM_SP500_2', 'EMAXIS_SLIM_SP500_3', 'MSFT', 'NISSEI_SOX_1', 'NISSEI_SOX_2', 'PENSION_EMAXIS_SLIM_ALL_COUNTRY', 'PLTR', 'RAKUTEN_PLUS_ALL_COUNTRY_1', 'RAKUTEN_PLUS_ALL_COUNTRY_2', 'RAKUTEN_PLUS_SP500', 'SMH', 'URA'], 'missing_mapping_symbols': [], 'failed_symbols': {}}
- なし
- holdings_inventory_note: 元スナップショットにはOCR注記がありますが、保有銘柄名以外は評価に使わないでください
