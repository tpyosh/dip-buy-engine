# Transactions

`transactions/ledger.yaml` は、確認済みの注文・約定・入出金実績のsource of truthです。

- 計画や提案を実績として記録しない。
- 約定日、数量、価格、通貨、口座区分、税区分、手数料、根拠資料を可能な範囲で保持する。
- 不明な値は`null`とし、スナップショット差分から取引を推定して確定しない。
- 過去の概要しか分からない事象は`unverified/`へ置き、確認済み台帳に混ぜない。

## 売却と確定申告用記録

- 金額・日付・口座・損益の正本は`ledger.yaml`に置く。
- 対象年の確定申告準備状況は`tax/YYYY.yaml`に置き、売却ごとに`transaction_ref`で台帳へ接続する。年次ファイルへ金額を重複転記しない。
- 証券会社や取引サービスの画面・明細から確認した事実は`evidence/`へ保存または転記し、台帳の`source_evidence`から参照する。
- 売却報告を受けた時点で、約定情報が一部しかなくても台帳と年次記録へ追加する。未知値は`null`、不足項目は`tax_record.missing_fields`へ記録する。
- 受渡明細が出たら、取得費、手数料、源泉徴収税、実現損益、純受取額を台帳へ追記する。
- 年間取引報告書等が発行されたら、取引単位・口座年間合計を突合し、年次記録の状態を`reconciled_to_annual_statement`へ更新する。

状態の意味:

| 状態 | 意味 |
|---|---|
| `fill_recorded` | 約定は確認済みだが、税務項目または正式な約定日・受渡日が不足 |
| `settlement_recorded` | 受渡情報と純受取額まで確認済み |
| `tax_details_recorded` | 取得費・手数料・税・実現損益まで確認済み |
| `reconciled_to_annual_statement` | 年間取引報告書等との突合まで完了 |
| `non_taxable_reconciled` | NISA等の非課税取引として年間確認済み |

確定申告の準備では、対象年の`tax/YYYY.yaml`を入口にし、未解決の`missing_fields`と未取得の年間資料を確認する。
