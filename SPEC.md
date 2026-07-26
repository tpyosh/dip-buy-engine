# codex_prompt_monthly_limit_order_review_system.md

## Goal

毎月の資産スナップショット YAML を入力として、  
**ChatGPT に渡すための月次レビュー用プロンプト**と、  
**ChatGPT の改善提案を Codex に渡すための修正プロンプト**を生成する  
Python CLI プロジェクトを作成したい。

このプロジェクトの思想は以下。

- Python は **厳密計算・構造化・履歴保存** を担当する
- Codex は **Money Forward キャプチャの直接読取・YAML 正規化・検証警告整理** を担当する
- ChatGPT は **その月の最新モデルとして、正規化済みデータのレビュー・提案・改善示唆** を担当する
- 最終判断は必ずユーザが行う
- 証券会社への注文はユーザが手動で行う
- 自動発注は実装しない

このプロジェクトは「売買を自動化するツール」ではなく、  
**月初の指値設定を一貫したルールでレビューし、毎月改善可能な形で運用するための半自動システム** である。

加えて、月次レビューとは独立して、保存済みスナップショットから保有銘柄名だけを抽出し、直近価格変動と信頼性の高いニュースを突き合わせる **ChatGPT向けオンデマンド市場アセスメント依頼プロンプト** を生成する。保有額、数量、取得単価、損益、配分はオンデマンド評価の対象にしない。

> **戦略値のsource of truth:** この文書内の配分・購入額・閾値は、既存機能と履歴を説明する旧仕様または例示を含む。現在有効な戦略値は `strategy/current.yaml` が参照する不変バージョン、期間限定の購入・売却計画は同ファイルの `active_plan_paths` を唯一の参照元とする。実行時に本文中の旧数値へfallbackしてはならない。

---

## Intended monthly workflow

このプロジェクトは、以下の運用を前提に設計すること。

1. ユーザが Codex に Money Forward の資産スクリーンショットを添付する
2. 必要に応じて、Money Forward 画面からコピーしたテキストも Codex に貼る
3. Codex がスクリーンショットを一次情報として OCR し、貼り付けテキストを補助情報として照合する
4. Codex が既存の snapshot YAML 形式に正規化し、`data/normalized/snapshot_YYYY_MM.yaml` を作成または更新する
5. Codex / Python が合計、カテゴリ、通貨、分類、前月差分、重複、OCR由来の不確実性を検証する
6. Python が市場データ取得・ルール計算・比率計算・警告抽出を行い、**ChatGPT 用月次レビュー・提案プロンプト**を生成する
7. ユーザがそのプロンプトだけを ChatGPT に貼る。Money Forward スクリーンショットや OCR 前テキストは ChatGPT に渡さない
8. ChatGPT がその月の最新モデルとして、Codex / Python が正規化・検証した数値を前提に、今月の指値提案・ポートフォリオ診断・購入提案・ルール改善提案を返す
9. ユーザがその提案を参考に最終判断し、証券会社で手動発注する
10. Python は ChatGPT の回答を保存し、改善提案を抽出し、**Codex 向け修正プロンプト**を生成する
11. Python は ChatGPT が決めた coreスポット買い実行スケジュールを、Google Calendarイベント作成用ドラフトとして保存する
12. Codex はそのドラフトを使い、証券会社への自動発注ではなく、手動発注リマインダーとして Google Calendar イベントを作成する
13. ユーザは必要に応じてその修正プロンプトを Codex に渡し、スクリプトを改善する

## Intended on-demand workflow

1. ユーザが保有銘柄のオンデマンド市場アセスメントを依頼する
2. Python は最新の正規化済みスナップショットを保有銘柄リストとして選ぶ。保有銘柄の変更が明示されていなければ最新Money Forward画面は要求しない
3. Python は株式・投資信託・年金の銘柄名だけを抽出し、保有額、数量、取得単価、損益、配分を評価入力から除外する
4. Python は各銘柄または市場参照プロキシの最新日足終値、1日・5日・1か月・3か月リターン、21日・63日高値からの下落率を取得する
5. 取得失敗、未設定銘柄、プロキシ使用、価格の `as_of` を警告または注記として残す
6. Python は `on-demand-run` で ChatGPT向け市場・ニュースアセスメント依頼プロンプトを生成する
7. ChatGPT は企業IR、法定開示、取引所、政府、中央銀行、統計機関等の一次情報と信頼性の高い市場報道をWeb調査する
8. ChatGPT は値動きの事実、市場報道上の背景、自身の推論を分け、因果関係の確度とシナリオ影響を返す
9. ユーザが最終判断し、必要な操作を手動で行う

オンデマンド処理は月次レビュー履歴、README、Google Calendar を更新しない。銘柄リストが古くても価格取得は止めず、リストが古い可能性だけを明示する。価格は最新取得可能な日足終値として扱い、リアルタイム気配値とは表現しない。

---

## Human approval and task-scope gate

AIの責務は、Codex / ChatGPTという名称ではなく、ユーザが依頼したタスク種別で決める。

### Normalization / preparation

Money Forwardキャプチャの正規化、欠損検出、計算、レビュー材料の生成だけを依頼された場合、AIはその範囲で停止する。正規化タスクから購入・売却・リバランス提案へ暗黙に拡張しない。

### Strategy / portfolio review

ユーザが明示的に戦略検証、ポートフォリオ診断、売買・リバランス案を求めた場合、AIは以下を満たしたうえで提案できる。

- `strategy/current.yaml` が指す現在戦略を使用する
- 対象期間のactive planと基準日時点のスナップショットを区別する
- 税制、市場価格、商品仕様には最新の一次情報、参照日、出典を持たせる
- 事実、推論、ユーザ確認事項を分離する
- 比率と閾値を現在保有に合わせて後付け調整しない

すべてのタスクで、AIによる証券注文、送金、自動発注、未承認の戦略変更、提案の実績化は禁止する。最終的な採否と発注はユーザが行う。

---

## Core architectural decision

このプロジェクトの最重要方針は以下。

### Python は「計算」と「文脈整理」を担当する
Python が担当すること:

- YAML 入力の読み込みと検証
- `yfinance` による市場データ取得
- 直近20営業日終値平均の計算
- 直近63営業日終値ベース高値の計算
- ルールに基づく一次候補価格の計算
- 現在のポートフォリオ比率計算
- 現金余力チェック
- リスク警告生成
- ChatGPT に渡すためのプロンプト生成
- ChatGPT の回答保存
- ChatGPT の改善提案の抽出
- Codex 用修正プロンプト生成
- coreスポット買い実行スケジュールの Google Calendar イベントドラフト生成
- 履歴保存
- Python の候補値と ChatGPT の最終提案の差分保存
- 最新の保存済みスナップショットから保有銘柄名だけを抽出
- オンデマンド対象を株式・投資信託・年金へ分類
- 各保有商品の1日・5日・1か月・3か月の市場参照データ収集と欠損警告
- ChatGPT向けオンデマンド・アセスメント依頼プロンプト生成

### Codex は「画像読取」と「YAML 正規化」を担当する
Codex が担当すること:

- Money Forward スクリーンショットの読取 / OCR
- OCR 結果と補助テキストの照合
- 既存 snapshot YAML 形式への正規化
- 前月スナップショットとの継続性確認
- OCR 由来の不確実性、重複、分類ミス候補の警告整理
- 正規化済み snapshot を Python CLI に渡すための保存

### ChatGPT は「月次提案」と「改善レビュー」を担当する
ChatGPT が担当すること:

- 今月の指値設定の提案
- SOX投信の買う / 買わない判定
- ポートフォリオの偏り指摘
- 今月の補強優先順位提案
- スクリプト改善余地の指摘
- Codex 向けに使える仕様改善の要約
- オンデマンド依頼では、一次情報と信頼性の高い市場報道を調査し、保有銘柄の値動きの背景、因果関係の確度、長期シナリオへの影響を評価

ChatGPT が担当しないこと:

- Money Forward スクリーンショットの読取 / OCR
- OCR 前の貼り付けテキストからの資産明細確定
- snapshot YAML の作成

### ユーザは必ず最終判断者
- 発注は人間
- 採否判断は人間
- 本ツールは助言補助・構造化補助であり、自動売買ツールではない

---

## Non-goals

この段階では以下は不要。

- 証券会社 API 接続
- 自動発注
- ブラウザ自動操作
- Python 内の独自 OCR エンジン実装
- Web UI
- モバイルアプリ
- 大規模バックテスト基盤
- 機械学習モデルの導入

まずは **CLI ベースで堅く運用できる最小構成** を作ること。

---

## Design principles

### 1. OCR と投資ロジックを切り離す
画像の解釈と YAML 正規化は Codex セッションで行い、Python は正規化済み YAML 入力のみを扱う。
Money Forward からコピーした HTML 由来のテキストは補助情報であり、レイアウト、列、階層、並び順、カテゴリ対応は信用しない。
これにより OCR 揺れや貼り付けテキストの構造崩れで投資判断ロジックが壊れるのを防ぐ。

### 2. Python が数値事実を作り、ChatGPT がレビューする
ChatGPT に価格計算や比率計算を主担当させない。  
数値の再現性は Python 側で担保する。

### 3. 毎月の結果と改善点を必ず保存する
最低限保存するもの:

- 入力 snapshot
- market references
- Python が計算した一次候補
- 生成した ChatGPT 用プロンプト
- ChatGPT の回答
- Python 候補と ChatGPT 提案の差分
- 改善提案
- 生成した Codex 用修正プロンプト
- coreスポット買い実行スケジュールから生成した Google Calendar イベントドラフト
- README の最新月セクションに反映した月次サマリー、購入計画、今月の指値買い設定、ポートフォリオサマリー
- ルート README には月次レビュー履歴を蓄積しない。新規生成物は `reports/generated/`、2026-07以前の旧生成物は `data/history/` と `prompts/generated/` に凍結する

### 4. 改善要求は優先度付きで扱う
ChatGPT が出した改善案はそのまま全部採用しない。  
Python は Codex 用修正プロンプト生成時に、改善要求を以下の3段階で整理すること。

- `must`
- `should`
- `nice_to_have`

### 5. 月次運用とルール変更を分離する
- 月次: 提案運用
- 四半期: ルール見直し
- 年次: 投資思想見直し

毎月ルールを変えすぎないよう、必要なら警告も出せる設計にする。

### 6. テーマエクスポージャは商品単位ではなく実質で見る
SOX投信と SMH は商品が別でも実質的に高相関。  
したがって、**半導体エクスポージャは合算で管理する**。

---

## Expected repo structure

```text
monthly-limit-order-review-system/
  README.md
  pyproject.toml
  requirements.txt

  config/
    buy_rules.yaml
    portfolio_policy.yaml
    tickers.yaml

  data/
    raw/
    normalized/
    history/
      snapshots/
      computations/
      prompts/
      reviews/
      diffs/
      codex_patch_requests/
      on_demand/
        market_data/
        prompts/

  prompts/
    moneyforward_normalization_prompt.md
    templates/
      monthly_review_template.md
      codex_patch_template.md
      moneyforward_monthly_session_start_prompt.md
      on_demand_market_assessment_session_start_prompt.md
      on_demand_assessment_template.md
    generated/
      monthly_review_prompt_YYYY_MM.md
      codex_patch_prompt_YYYY_MM.md
      YYYY_MM_DDTHHMMSSZ_on_demand_assessment_prompt.md

  src/
    monthly_limit_order_review/
      __init__.py
      models.py
      snapshot_loader.py
      market_data.py
      portfolio.py
      rules.py
      prompt_builder.py
      on_demand.py
      review_parser.py
      diff_analyzer.py
      codex_patch_builder.py
      storage.py
      cli.py

  tests/
    test_snapshot_loader.py
    test_market_data.py
    test_portfolio.py
    test_rules.py
    test_prompt_builder.py
    test_review_parser.py
    test_diff_analyzer.py
    test_codex_patch_builder.py
```

---

## Input format assumptions

ユーザは毎月、Codex に Money Forward スクリーンショットを添付する。必要に応じて Money Forward 画面からコピーしたテキストも貼る。
Codex はスクリーンショットを一次情報、既存スナップショットを継続性確認、貼り付けテキストを補助情報として扱い、YAML を作る。Python はその YAML を読む。

Evidence priority:

1. Money Forward screenshots/images: asset names, amounts, categories, account labels, and visual grouping.
2. Existing repository data and previous monthly snapshots: continuity, likely asset identity, existing classifications, and abnormal month-over-month changes.
3. User-pasted Money Forward text copy: auxiliary evidence only. It may confirm labels or numbers, but layout, ordering, grouping, hierarchy, and column association are unreliable.
4. Inference: use only when necessary, mark clearly, and never silently invent missing values.

入力 YAML の想定例:

```yaml
snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 32692503
liquidity_target_jpy: 1000000

holdings:
  - symbol: "7203"
    name: "Toyota Motor"
    source_category: "株式"
    institution: null
    account_type: "特定口座"
    asset_class: "jun_core"
    quantity: 800
    avg_cost: 532
    current_price: 3515
    unit_price: 3515
    profit_loss_jpy: null
    valuation_jpy: 2812000
    market_value_jpy: 2812000
    currency: "JPY"

  - symbol: "MSFT"
    name: "Microsoft"
    asset_class: "jun_core"
    quantity: 4
    avg_cost: 431.42
    current_price: 410.68
    market_value_jpy: 259516
    currency: "USD"

  - symbol: "CIBR"
    name: "First Trust NASDAQ Cybersecurity ETF"
    asset_class: "satellite_core"
    quantity: 88
    avg_cost: 76.66
    current_price: 65.79
    market_value_jpy: 914628
    currency: "USD"

  - symbol: "URA"
    name: "Global X Uranium ETF"
    asset_class: "satellite_core"
    quantity: 66
    avg_cost: 46.19
    current_price: 50.06
    market_value_jpy: 521959
    currency: "USD"

  - symbol: "PLTR"
    name: "Palantir Technologies"
    asset_class: "satellite"
    quantity: 9
    avg_cost: 160.48
    current_price: 152.67
    market_value_jpy: 217069
    currency: "USD"

  - symbol: "SMH"
    name: "VanEck Semiconductor ETF"
    asset_class: "satellite_core"
    quantity: 1
    avg_cost: 369.63
    current_price: 395.35
    market_value_jpy: 62457
    currency: "USD"

  - symbol: "NIKKO_SOX_FUND"
    name: "Nikkei SOX Index Fund"
    asset_class: "satellite_core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 3805203
    currency: "JPY"

  - symbol: "ALL_COUNTRY_FUND"
    name: "All Country Mutual Funds"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 3112034
    currency: "JPY"

  - symbol: "SP500_FUND"
    name: "S&P500 Mutual Funds"
    asset_class: "core"
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 2405995
    currency: "JPY"
```

---

## Asset bucket semantics

このプロジェクトではバケットを以下で扱う。

- `liquidity`
- `core`
- `jun_core`
- `satellite_core`
- `satellite`
- `pension`
- `other`

意味:

- `liquidity`: 現金・預金・すぐ使える余力
- `core`: オルカン、S&P500 など長期中核
- `jun_core`: トヨタ、MSFT などコアに近いが個別・集中リスクを持つ準コア
- `satellite_core`: SOX, SMH, URA, CIBR などテーマ性はあるが比較的主力寄り
- `satellite`: PLTR その他の高ボラ・高テーマ性銘柄
- `pension`: 年金資産
- `other`: 上記に綺麗に入らないもの

---

## Required configuration files

### `config/buy_rules.yaml`

```yaml
base_price_method:
  type: "mean_close"
  lookback_trading_days: 20

limit_order_rules:
  CIBR:
    tranches:
      - drawdown_pct: -5
        shares: 1
      - drawdown_pct: -8
        shares: 1
      - drawdown_pct: -12
        shares: 1

  URA:
    tranches:
      - drawdown_pct: -6
        shares: 2
      - drawdown_pct: -10
        shares: 2
      - drawdown_pct: -15
        shares: 2

  PLTR:
    tranches:
      - drawdown_pct: -10
        shares: 1
      - drawdown_pct: -15
        shares: 2
      - drawdown_pct: -22
        shares: 2

  MSFT:
    tranches:
      - drawdown_pct: -6
        shares: 1
      - drawdown_pct: -10
        shares: 2
      - drawdown_pct: -18
        shares: 2

sox_buy_judgement:
  proxy_symbol: "SMH"
  method: "drawdown_from_recent_high_close"
  lookback_trading_days: 63
  buy_zone_min_pct: -10
  buy_zone_max_pct: -5
  monthly_buy_budget_jpy:
    min: 100000
    max: 200000

execution:
  order_expiration: "month_end"
  round_price:
    usd_decimals: 2
    jpy_decimals: 0
```

### `config/portfolio_policy.yaml`

```yaml
portfolio_buckets:
  liquidity:
    target_pct: 0.10
    min_jpy: 1000000
    preferred_pct_range: [0.05, 0.15]
    hard_max_pct: 0.20

  core:
    target_pct: 0.45
    preferred_pct_range: [0.35, 0.55]

  jun_core:
    target_pct: 0.20
    preferred_pct_range: [0.10, 0.30]

  satellite_core:
    target_pct: 0.15
    preferred_pct_range: [0.10, 0.25]

  satellite:
    target_pct: 0.10
    preferred_pct_range: [0.00, 0.15]

symbol_to_bucket:
  "7203": "jun_core"
  "MSFT": "jun_core"
  "ALL_COUNTRY_FUND": "core"
  "SP500_FUND": "core"
  "NIKKO_SOX_FUND": "satellite_core"
  "SMH": "satellite_core"
  "URA": "satellite_core"
  "CIBR": "satellite_core"
  "PLTR": "satellite"

risk_limits:
  satellite_plus_satellite_core_max_pct: 0.25
  satellite_max_pct: 0.15
  single_high_vol_name_max_pct: 0.05
  pltr_max_total_assets_pct: 0.03
  semi_exposure_max_pct_of_total_assets: 0.18

satellite_subtargets:
  semiconductor_combined: 0.40
  URA: 0.25
  CIBR: 0.20
  PLTR: 0.15

cash_policy:
  hard_floor_jpy: 1000000
  preferred_total_assets_pct_range: [0.05, 0.10]
```

### `config/tickers.yaml`

```yaml
yfinance_symbols:
  CIBR: "CIBR"
  URA: "URA"
  PLTR: "PLTR"
  MSFT: "MSFT"
  SMH: "SMH"
  TOYOTA_US_PROXY: "TM"
  VT: "VT"
  VOO: "VOO"
  SOXX: "SOXX"
  USDJPY: "USDJPY=X"
```

---

## Why these default portfolio policies

デフォルトの思想は以下。

- 生活費相当の流動性は最低 100 万円を残す
- ただし 100 万円は「目標」ではなく「下限」
- 長期の主軸は `core`
- トヨタや MSFT は強いが個別株なので `jun_core`
- SOX/SMH/URA/CIBR は `satellite_core`
- PLTR は明示的に `satellite`
- 半導体は SOX投信と SMH を合算し、テーマ集中として扱う

この初期値は完全な正解ではなく、  
**運用の安定性と偏り抑制を優先した保守的なデフォルト** である。

---

## Functional requirements

### A. Snapshot loading
実装対象:

- YAML を読み込む
- バリデーションする
- 欠損値を許容しつつ警告する
- 内部モデルに変換する

### B. Market data fetching
実装対象:

- `yfinance` で履歴データ取得
- 直近20営業日終値平均
- 直近63営業日終値ベース高値
- 現在値
- 為替が必要なら `USDJPY=X`

### C. Portfolio analysis
実装対象:

- バケット比率計算
- 目標比率との差計算
- 半導体エクスポージャ合算
- サテライト過多警告
- PLTR 比率上限警告
- 現金余力警告
- 個別集中警告

### D. Rule-based candidate calculation
実装対象:

- 設定ファイルの階段ルールに従って一次候補価格を計算
- これは最終提案ではなく、ChatGPT にレビューさせる「候補群」
- 候補価格・候補株数・基準値・現在値を出す
- 必要なら抑制フラグも出す

### E. Monthly ChatGPT prompt generation
実装対象:

- ユーザがそのまま ChatGPT に貼れる Markdown プロンプトを生成
- プロンプトには計算結果・警告・候補値・期待出力形式を含める
- プロンプトは決定的で再現性のある構造にする

### F. Review ingestion and parsing
実装対象:

- ユーザが保存した ChatGPT の回答テキストを読む
- 改善提案セクションを抽出
- must / should / nice_to_have に整理
- Python 候補と ChatGPT 提案の差分を構造化保存

### G. Codex patch prompt generation
実装対象:

- ChatGPT の改善提案から Codex 用修正プロンプトを生成
- 修正対象・意図・仕様差分・必要テストを明記
- 抽象論ではなく編集可能な粒度にする

### H. History storage
最低限保存するもの:

- snapshot
- market references
- portfolio analysis
- candidate orders
- monthly review prompt
- chatgpt review
- python vs chatgpt diff
- codex patch request
- core spot buy Google Calendar event drafts
- timestamped on-demand prompt
- on-demand held-symbol market data, inventory age, and market-reference collection status

### I. On-demand ChatGPT assessment prompt generation

実装対象:

- 最新の読み取り可能なスナップショットを自動選択し、holdings の銘柄名だけを使う
- 古いスナップショットでも処理を止めず、保有銘柄リストが古い可能性を表示する
- holdings を株式・投資信託・年金に分類し、現金・ポイント等は除外する
- 保有額、数量、取得単価、損益、配分をプロンプトに含めない
- 取得可能な保有商品ごとに最新日足終値、1日・5日・1か月・3か月リターン、21日・63日高値からのドローダウンを整理する
- 未設定銘柄、取得失敗、`as_of` の差を警告として残す
- ChatGPT が一次情報と信頼性の高い市場報道をWeb調査し、価格変動の背景と因果関係の確度を評価するMarkdownプロンプトを生成する
- 月次用README、月次計算履歴、Google Calendarを更新しない

---

## Required output artifacts

### 1. Monthly review prompt
生成ファイル例:

```text
reports/generated/monthly/2026_03/review_request.md
```

### 2. Codex patch prompt
生成ファイル例:

```text
reports/generated/monthly/2026_03/codex_patch_request.md
```

### 3. Structured computation artifact
生成ファイル例:

```text
reports/generated/monthly/2026_03/computation.yaml
```

### 4. Structured diff artifact
生成ファイル例:

```text
reports/generated/monthly/2026_03/proposal_diff.yaml
```

### 5. Core spot buy Google Calendar event draft
生成ファイル例:

```text
reports/generated/monthly/2026_03/calendar_events.yaml
```

### 6. On-demand assessment prompt and held-symbol market data

生成ファイル例:

```text
reports/generated/on_demand/2026/2026_07_14T083000Z/assessment_request.md
reports/generated/on_demand/2026/2026_07_14T083000Z/market_data.yaml
```

---

## Exact ChatGPT output contract

Python が生成する月次レビュー用プロンプトでは、ChatGPT に以下の形式で出力させること。

```text
【今月のcoreスポット買い提案】
- 今月の推奨スポット買い総額
- 配分先内訳
- 実行スケジュール
- Google Calendar イベント作成に使える具体日付、ファンド名、金額

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
```

## On-demand ChatGPT output contract

オンデマンド・プロンプトでは、ChatGPT に以下の見出しを必須とする。

```text
【調査時点と市場概況】
【銘柄別アセスメント】
【横断テーマ】
【要確認・判断保留】
【参照情報】
```

- 各銘柄について最新確認価格、1日・5日・1か月・3か月の変化を出す
- 重要ニュースの発生日、事実、情報源を示す
- `市場での評価` として、値動きの背景として報道されている要因を示す
- 因果関係の確度を `高い` / `中程度` / `低い` で示し、理由を書く
- 長期シナリオへの影響か、一時的センチメントか、判断材料不足かを分ける
- 値動きの事実、報道された市場解釈、ChatGPTの推論を区別する
- Web参照日時とURLを記載する
- 個別材料が確認できない場合は無理に原因を作らない

---

## Diff requirement between Python proposal and ChatGPT proposal

このプロジェクトでは、Python の一次候補と ChatGPT の最終提案の差分を  
**毎月必ず保存する** こと。

最低限比較する項目:

- 銘柄
- Python 候補価格
- ChatGPT 推奨価格
- 差分率
- Python 候補株数
- ChatGPT 推奨株数
- 差分理由の要約
- ChatGPT が追加した警告
- ChatGPT が削除した候補

理由:
- 月次改善を感覚論にしないため
- ChatGPT の判断傾向を蓄積するため
- Codex 用修正要求を具体化するため

---

## Data models

Pydantic または dataclass で最低限以下を定義すること。

```python
Holding
PortfolioSnapshot
BucketAllocation
MarketReference
TrancheRule
CandidateOrder
PortfolioWarning
MonthlyComputation
PromptArtifact
ReviewFeedback
ProposalDiff
CodexPatchRequest
```

---

## CLI requirements

### 1. Generate monthly review prompt

```bash
python -m monthly_limit_order_review.cli generate-review-prompt \
  --snapshot data/normalized/snapshot_2026_03.yaml
```

### 2. Ingest ChatGPT review

```bash
python -m monthly_limit_order_review.cli ingest-review \
  --snapshot data/normalized/snapshot_2026_03.yaml \
  --review-text reports/review_inputs/2026_03_chatgpt_review.txt
```

### 3. Generate Codex patch prompt

```bash
python -m monthly_limit_order_review.cli generate-codex-patch \
  --snapshot data/normalized/snapshot_2026_03.yaml \
  --review-text reports/review_inputs/2026_03_chatgpt_review.txt
```

### 4. Optional combined workflow

```bash
python -m monthly_limit_order_review.cli monthly-run \
  --snapshot data/normalized/snapshot_2026_03.yaml
```

このコマンドは少なくとも以下を行ってよい。

- market data fetch
- computation save
- review prompt generation

ただし ChatGPT 呼び出し自体は行わないこと。

### 5. Generate on-demand assessment prompt

```bash
python -m monthly_limit_order_review.cli on-demand-run \
  --news-lookback-days 14
```

`--snapshot` を省略した場合は、`data/normalized/snapshot_*.yaml` のうち `snapshot_date` が最も新しい読み取り可能なファイルを保有銘柄リストとして使う。`--inventory-max-age-days` は古い可能性を表示する閾値であり、価格取得をブロックしない。`--news-lookback-days` はChatGPTに依頼するニュース調査期間とする。

このコマンドは以下だけを行う。

- 銘柄名と市場参照データだけを含む専用アーティファクトの生成
- オンデマンド・プロンプトの生成
- `reports/generated/on_demand/` へのタイムスタンプ付き履歴保存

README、月次アーティファクト、Google Calendar は更新しない。

---

## Prompt builder requirements

月次レビュー用プロンプトは、少なくとも以下のセクションを持つこと。

1. 前提
2. この月の snapshot 要約
3. 現在の資産配分
4. 対象銘柄ごとの
   - 現在値
   - 基準値
   - 一次候補価格
   - 候補株数
5. SOX 判定材料
6. 警告一覧
7. ChatGPT に期待する出力形式
8. 必須のルール改善レビュー
9. 必須の Codex 向け修正要約

オンデマンド・プロンプトは、少なくとも以下のセクションを持つこと。

1. 依頼時点と、保存済みスナップショットは銘柄名特定だけに使うという説明
2. 株式・投資信託・年金の対象件数
3. 株式
4. 投資信託
5. 年金
6. 各銘柄・プロキシの最新価格、1日・5日・1か月・3か月リターン、ドローダウン、`as_of`
7. 価格取得状況・警告・不確実性
8. 一次情報と信頼性の高い市場報道を使う調査指示
9. 因果関係を断定しすぎないための出力形式

---

## Review parser requirements

多少の見出しブレがあっても以下を抽出できるようにすること。

- 今月の指値提案
- SOX 判定
- ポートフォリオ診断
- ルール改善レビュー
- Codex 向け修正要約
- must / should / nice_to_have

抽出に失敗した場合は黙って無視せず、警告を出すこと。

---

## Codex patch prompt requirements

Codex 向け修正プロンプトは、抽象論ではなく  
**そのまま編集作業に入れる粒度** にすること。

悪い例:
- 改善してください
- より良くしてください

良い例:
- `portfolio.py` に半導体エクスポージャ合算計算を追加
- `portfolio_policy.yaml` に `semi_exposure_max_pct_of_total_assets` を追加
- `rules.py` に `PLTR` の浅い押し目候補抑制条件を追加
- `test_portfolio.py` に半導体集中警告テストを追加

Codex 向け修正プロンプトには以下を含めること。

- 現在の問題
- 修正目的
- 優先度
- 修正対象ファイル
- 仕様差分
- 追加 / 更新テスト
- 後方互換性の注意点
- README 更新が必要な場合は、最新月セクションの見やすい位置に「今月の指値買い設定」を含めること
- README 更新時は既存の `## Monthly Review: YYYY_MM` を最新月の内容に置換し、過去月の `Monthly Review` セクションをルートREADMEに残さないこと

---

## Required prompt templates to create in the project

### 1. `prompts/moneyforward_normalization_prompt.md`

```text
あなたは資産スナップショット正規化アシスタントです。

Money Forward スクリーンショットを一次情報として OCR し、投資判断ロジックで使えるように資産情報を YAML に変換してください。
Money Forward からコピーされたテキストがある場合は、補助情報としてだけ使ってください。

ルール:
- スクリーンショットを一次情報として扱う
- 貼り付けテキストは HTML 由来でレイアウト、列、階層、並び順、カテゴリ対応が崩れている可能性がある
- 推測を最小化する
- 読み取れない値は null にする
- 通貨は JPY / USD を明記する
- 同一カテゴリの複数ファンドは合算せず、原則として1行ずつ残す
- ただし後段でまとめるため、asset_class は必ず付与する
- 画像とテキストが矛盾する場合は画像を優先し、矛盾を ocr_notes または validation_notes に残す

asset_class の候補:
- liquidity
- core
- jun_core
- satellite_core
- satellite
- pension
- other

必要項目:
- snapshot_date
- currency_base
- total_assets_jpy
- category_totals_jpy
- source_evidence
- ocr_notes
- validation_notes
- holdings:
  - symbol
  - name
  - source_category
  - institution
  - account_type
  - asset_class
  - quantity
  - avg_cost
  - current_price
  - unit_price
  - profit_loss_jpy
  - valuation_jpy
  - market_value_jpy
  - currency
  - notes
```

### 1-1. `prompts/templates/moneyforward_monthly_session_start_prompt.md`

将来の月次レビュー開始時に Codex に貼る日本語テンプレートを保存すること。テンプレートは、Money Forward スクリーンショット添付から始め、Codex が OCR、正規化、検証、ChatGPT 月次レビュー依頼プロンプト生成まで実施する前提を明記する。

### 1-2. `prompts/templates/on_demand_market_assessment_session_start_prompt.md`

オンデマンド依頼時に Codex に貼る日本語テンプレートを保存すること。最新の保存済みスナップショットから保有銘柄名だけを抽出し、保有額・数量・損益・配分を使わず、`on-demand-run` で直近価格変動を取得してChatGPT向けプロンプトを作ることを明記する。月次README、月次履歴、Google Calendarを更新しないことも明記する。

### 2. Monthly review template

Python がこのテンプレートに埋め込んで `monthly_review_prompt` を作ること。  
テンプレートファイルとしても保存すること。

```text
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
```

### 2-1. On-demand assessment template

ChatGPT が依頼時点のWeb情報を調査し、保有銘柄の直近価格変動と重要ニュースを突き合わせるテンプレートを保存すること。日足終値をリアルタイム価格と誤認しないこと、一次情報を優先すること、市場解釈には信頼性の高い報道を使うこと、値動きとニュースの因果関係を断定しすぎないこと、出典URLと参照日時を出すことを必須とする。

### 3. Codex patch template

Python が改善提案を埋め込んで `codex_patch_prompt` を作ること。  
テンプレートファイルとしても保存すること。

```text
この Python CLI プロジェクトを修正してください。

目的:
- 月次の押し目買いレビュー支援システムの改善

今回の修正理由:
- ChatGPT の月次レビューで改善点が指摘されたため

優先度別修正要求:
- must:
- should:
- nice_to_have:

守るべき制約:
- 自動発注は実装しない
- YAML 入力を前提にする
- CLI ベースを維持する
- 既存の月次ワークフローを壊さない
- テストを更新する

期待する作業:
- 必要ファイルの修正
- 必要テストの追加
- README 更新
```

---

## Legacy investor-grade default logic

以下は初期実装時のデフォルト改善であり、過去計算の再現用に残す。現在の半導体・高ボラティリティ銘柄・留保現金の閾値は `strategy/current.yaml` が参照する戦略版を使用する。

### A. 半導体エクスポージャ合算
- `NIKKO_SOX_FUND + SMH` を半導体エクスポージャとして扱う
- 総資産比が高すぎる場合は警告

### B. PLTRの扱いは厳しめ
- `PLTR` は `satellite` 固定
- 総資産 3% 超で警告
- 既存比率が高く損失も大きい場合、浅い押し目候補は抑制候補にできる設計余地を持つ

### C. 現金100万円は下限
- `100万円` は hard floor
- 可能なら総資産比 `5〜10%` も併記
- 下限は割っていなくても、推奨帯を外れていれば注意喚起

### D. ルール変更の抑制
- 毎月の改善提案は歓迎
- ただしルール変更は四半期単位でまとめる運用が望ましい
- 必要なら「今月は観察のみ、即変更は不要」という分類もできるようにする

---

## Important coding constraints

- Python 3.11+
- 利用可ライブラリは最小限
- `pandas`, `pydantic`, `pyyaml`, `yfinance` は利用可
- ログを出す
- エラーは明確に出す
- 丸め規則を統一する
- 将来拡張を見越し、計算層・分析層・プロンプト生成層・レビュー解析層を分離する
- `Decimal` 利用を検討し、雑な浮動小数比較を避ける
- 黙ってフォールバックしない
- 営業日不足やデータ取得失敗は明示する

---

## Tests to implement

最低限以下を書くこと。

1. snapshot YAML が正しく読める
2. 必須項目不足で警告が出る
3. 20営業日終値平均が正しく計算できる
4. 63営業日終値高値が正しく計算できる
5. バケット比率が正しく計算できる
6. 半導体エクスポージャ合算が正しく計算できる
7. PLTR 比率上限警告が出る
8. 現金余力警告が出る
9. 一次候補価格がルール通り計算される
10. ChatGPT 用レビュー・プロンプトが必要要素を含む
11. ChatGPT レビューから must / should / nice_to_have を抽出できる
12. Python 候補と ChatGPT 提案の差分が保存される
13. Codex 用修正プロンプトが必要要素を含む
14. 最新の読み取り可能なスナップショットを保有銘柄リストとして自動選択できる
15. holdings を株式・投資信託・年金に分類できる
16. 現在保有する3資産の市場参照リクエストを作れる
17. オンデマンド・プロンプトに1日・5日・1か月・3か月リターン、`as_of`、ニュース調査要件、因果関係の確度が含まれる
18. `on-demand-run` が月次履歴とREADMEを更新せず、専用履歴だけを保存する
19. オンデマンド・プロンプトに保有額、数量、取得単価、損益、配分が含まれない

---

## README requirements

README には必ず以下を含めること。

- プロジェクトの目的
- 毎月のワークフロー
- ChatGPT と Codex の役割分担
- 入力 YAML の作り方
- 主要コマンド
- 生成物一覧
- 履歴ファイルの説明
- 差分保存の意味
- オンデマンド市場・ニュース調査ワークフロー、保有状況診断との分離、月次処理との副作用分離
- 注意事項
  - 最終判断は人間
  - 発注は人間
  - 本ツールは助言補助・構造化補助である

---

## Deliverables

Codex は以下を作成すること。

1. Python CLI プロジェクト一式
2. モデル定義
3. YAML ローダー
4. 市場データ取得
5. ポートフォリオ分析
6. 一次候補計算
7. ChatGPT 用月次レビュー・プロンプト生成
8. ChatGPT レビュー取り込み
9. Python vs ChatGPT 差分保存
10. Codex 用修正プロンプト生成
11. 設定ファイル
12. テスト
13. README
14. サンプル入力ファイル
15. サンプル出力ファイル
16. オンデマンド保有銘柄抽出・価格変動取得・プロンプト生成
17. オンデマンド開始テンプレートと専用履歴保存

---

## What Codex should do first

以下の順で実装すること。

1. モデル定義
2. YAML ローダー
3. 市場データ取得
4. ポートフォリオ分析
5. 一次候補計算
6. 月次レビュー・プロンプト生成
7. レビュー取り込み
8. 差分保存
9. Codex 用修正プロンプト生成
10. テスト
11. README

勝手に GUI 化や Web 化はしないこと。  
まずは CLI で、再現性高く、壊れにくく、月次運用しやすいものを作ること。
