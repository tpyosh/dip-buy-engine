# codex_prompt_monthly_limit_order_review_system.md

## Goal

毎月の資産スナップショット YAML を入力として、  
**ChatGPT に渡すための月次レビュー用プロンプト**と、  
**ChatGPT の改善提案を Codex に渡すための修正プロンプト**を生成する  
Python CLI プロジェクトを作成したい。

このプロジェクトの思想は以下。

- Python は **厳密計算・構造化・履歴保存** を担当する
- ChatGPT は **その月の最新モデルとしてレビュー・提案・改善示唆** を担当する
- 最終判断は必ずユーザが行う
- 証券会社への注文はユーザが手動で行う
- 自動発注は実装しない

このプロジェクトは「売買を自動化するツール」ではなく、  
**月初の指値設定を一貫したルールでレビューし、毎月改善可能な形で運用するための半自動システム** である。

---

## Intended monthly workflow

このプロジェクトは、以下の運用を前提に設計すること。

1. ユーザが ChatGPT に Money Forward の資産キャプチャを貼る
2. ChatGPT がそのキャプチャを YAML に正規化する
3. ユーザがその YAML を Python スクリプトに入力する
4. Python が市場データ取得・ルール計算・比率計算・警告抽出を行い、**ChatGPT 用月次レビュー・提案プロンプト**を生成する
5. ユーザがそのプロンプトを ChatGPT に貼る
6. ChatGPT がその月の最新モデルとして、今月の指値提案・ポートフォリオ診断・ルール改善提案を返す
7. ユーザがその提案を参考に最終判断し、証券会社で手動発注する
8. Python は ChatGPT の回答を保存し、改善提案を抽出し、**Codex 向け修正プロンプト**を生成する
9. ユーザは必要に応じてその修正プロンプトを Codex に渡し、スクリプトを改善する

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
- 履歴保存
- Python の候補値と ChatGPT の最終提案の差分保存

### ChatGPT は「月次提案」と「改善レビュー」を担当する
ChatGPT が担当すること:

- 今月の指値設定の提案
- SOX投信の買う / 買わない判定
- ポートフォリオの偏り指摘
- 今月の補強優先順位提案
- スクリプト改善余地の指摘
- Codex 向けに使える仕様改善の要約

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
- 完全自動 OCR
- Web UI
- モバイルアプリ
- 大規模バックテスト基盤
- 機械学習モデルの導入

まずは **CLI ベースで堅く運用できる最小構成** を作ること。

---

## Design principles

### 1. OCR と投資ロジックを切り離す
画像の解釈は ChatGPT 側に任せ、Python は YAML 入力のみを扱う。  
これにより OCR 揺れで投資判断ロジックが壊れるのを防ぐ。

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

  prompts/
    moneyforward_normalization_prompt.md
    templates/
      monthly_review_template.md
      codex_patch_template.md
    generated/
      monthly_review_prompt_YYYY_MM.md
      codex_patch_prompt_YYYY_MM.md

  src/
    monthly_limit_order_review/
      __init__.py
      models.py
      snapshot_loader.py
      market_data.py
      portfolio.py
      rules.py
      prompt_builder.py
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

ユーザは毎月、ChatGPT に Money Forward キャプチャを貼り、YAML を作る。  
Python はその YAML を読む。

入力 YAML の想定例:

```yaml
snapshot_date: "2026-03-07"
currency_base: "JPY"
total_assets_jpy: 32692503
liquidity_target_jpy: 1000000

holdings:
  - symbol: "7203"
    name: "Toyota Motor"
    asset_class: "jun_core"
    quantity: 800
    avg_cost: 532
    current_price: 3515
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

---

## Required output artifacts

### 1. Monthly review prompt
生成ファイル例:

```text
prompts/generated/monthly_review_prompt_2026_03.md
```

### 2. Codex patch prompt
生成ファイル例:

```text
prompts/generated/codex_patch_prompt_2026_03.md
```

### 3. Structured computation artifact
生成ファイル例:

```text
data/history/computations/2026_03_computation.yaml
```

### 4. Structured diff artifact
生成ファイル例:

```text
data/history/diffs/2026_03_python_vs_chatgpt.yaml
```

---

## Exact ChatGPT output contract

Python が生成する月次レビュー用プロンプトでは、ChatGPT に以下の形式で出力させること。

```text
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
  --snapshot data/normalized/snapshot_2026_03.yaml \
  --output prompts/generated/monthly_review_prompt_2026_03.md
```

### 2. Ingest ChatGPT review

```bash
python -m monthly_limit_order_review.cli ingest-review \
  --snapshot data/normalized/snapshot_2026_03.yaml \
  --review-text data/history/reviews/chatgpt_review_2026_03.txt
```

### 3. Generate Codex patch prompt

```bash
python -m monthly_limit_order_review.cli generate-codex-patch \
  --snapshot data/normalized/snapshot_2026_03.yaml \
  --review-text data/history/reviews/chatgpt_review_2026_03.txt \
  --output prompts/generated/codex_patch_prompt_2026_03.md
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

---

## Required prompt templates to create in the project

### 1. `prompts/moneyforward_normalization_prompt.md`

```text
あなたは資産スナップショット正規化アシスタントです。

以下の Money Forward キャプチャから、投資判断ロジックで使えるように資産情報を YAML に変換してください。

ルール:
- 推測を最小化する
- 読み取れない値は null にする
- 通貨は JPY / USD を明記する
- 同一カテゴリの複数ファンドは合算せず、原則として1行ずつ残す
- ただし後段でまとめるため、asset_class は必ず付与する
- 出力は YAML のみ
- 余計な説明文は不要

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
- total_assets_jpy
- holdings:
  - symbol
  - name
  - asset_class
  - quantity
  - avg_cost
  - current_price
  - market_value_jpy
  - currency
```

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

## Additional investor-grade default logic

以下のデフォルト改善を入れてよい。

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