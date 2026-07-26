# Full responsibility migration — 2026-07-26

## Scope

戦略、事実、計画、実績、レトロスペクティブ、生成物を分離し、旧履歴を変更せず今後の書込先と参照先を切り替える。

## Migration table

| Legacy source | New responsibility | Treatment |
| --- | --- | --- |
| `config/core_recurring_contributions.yaml` | `plans/recurring/` | 内容を期間付き観測記録へ移し、旧ファイルはポインタ化 |
| `config/portfolio_policy.yaml`の目標・リスク値 | `strategy/versions/` | 旧値は過去再現用に残し、現行計算では不使用 |
| `config/portfolio_policy.yaml#long_term_thesis` | `strategy/theses/` | 半導体以外は`inherited_pending_review`として分離 |
| `config/allocation_rules.yaml` | active planまたは旧月fallback | 現行戦略月では使用停止 |
| `config/buy_rules.yaml` | 分析ヒューリスティック | 承認済み注文計画ではないことを明示 |
| `data/history/` | `reports/generated/` | 既存は凍結、新規出力だけ新構造へ |
| `prompts/generated/` | `reports/generated/` | 既存は凍結、新規出力だけ新構造へ |
| スナップショット差分で示唆された取引 | `transactions/` | 推定で台帳化せず、確認済みのみ正本へ |
| 既存ChatGPTレビュー | `retrospectives/index.yaml` | 完全なレトロスペクティブではないと分類 |
| チャット添付の過去証拠 | `data/raw/index.yaml` | リポジトリ外であることを欠損として記録 |

## Compatibility

- 過去の生成物と正規化済みスナップショットのパスは変更しない。
- 2026-07より前の月次計算は旧設定fallbackで再現する。
- 2026-07以降は`strategy/current.yaml`とactive planを優先する。
- 定期積立の旧configパスは、新しい観測記録へのポインタとして残す。

## Rollback

1. 新規出力先を旧`data/history/`と`prompts/generated/`へ戻す。
2. CLIの定期積立ローダーを旧config直読みに戻す。
3. 新規ディレクトリは参照を外すだけにし、履歴・戦略版・取引台帳は削除しない。
4. ロールバックしても、移行後に追加された確認済み取引を旧生成物へ混ぜない。
