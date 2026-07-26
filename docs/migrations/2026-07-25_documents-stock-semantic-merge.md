# Documents/stock semantic merge — 2026-07-25

## Source

`/Users/tappeiyoshida/Documents/stock`

調査時点で移行元はGitリポジトリではなく、固有ファイルは次の2件だけだった。

| source | semantic destination | treatment |
| --- | --- | --- |
| `AGENTS.md` | `/Users/tappeiyoshida/projects/stock/AGENTS.md` | 住宅ローン参照ルールを維持し、承認済みのsource of truth・履歴・人間承認ルールを追加 |
| `FINANCIAL_ASSUMPTIONS.md` | `/Users/tappeiyoshida/projects/stock/FINANCIAL_ASSUMPTIONS.md` | 住宅ローン条件を保持し、夫個人スコープと生活費・キャッシュフロー前提を追加 |

差分の単純コピーではなく、移行先の責務に合わせて意味を統合した。移行元は今後の正本にせず、削除も行っていない。
