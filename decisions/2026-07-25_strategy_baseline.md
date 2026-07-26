# Strategy baseline approval — 2026-07-25

## Status

Accepted by the user on 2026-07-25.

## Scope

夫個人の金融資産について、歴史的に形成された旧バケット配分をそのまま現在方針とみなさず、長期方針、期間限定計画、実績、レトロスペクティブを分離する。

## Decision

- 現在有効な完全な方針: `strategy/versions/2026-07-25.yaml`
- 現在版ポインタ: `strategy/current.yaml`
- 半導体仮説: `strategy/theses/semiconductor.yaml`
- 承認済みの期間限定現金再配分: `plans/2026/2026-07-25_cash_redeployment.yaml`

エージェントは理論・統計とユーザ個人の制約に基づいて機械的に比率を評価し、リバランスを提案する。すべての売買は人間が判断・実行する。

## Important interpretation

- 高いリスク負担能力はactive/hobby枠を持つ合理性を支えるが、個別仮説の正しさや無制限の集中を意味しない。
- 半導体は成長サテライトとして維持するが、AIから独立した防御資産とはみなさない。
- 半導体の過去リターンは実績であり、将来の買い増しを単独で正当化しない。
- 過去の月次レビューと当時のルールは履歴として保持し、この決定に合わせて書き換えない。
