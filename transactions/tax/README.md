# Annual tax records

`YYYY.yaml`は、その年に確認された売却を確定申告準備へ漏れなく接続するための年次索引です。

- 売却金額、取得費、手数料、税、実現損益の正本は`../ledger.yaml`です。
- 年次ファイルは金額を複製せず、`transaction_ref`と照合状態だけを保持します。
- 売却報告のたびに該当年の`sales`へ追加します。
- 受渡明細や年間取引報告書を受領したら、台帳を更新してからこのファイルの状態と不足項目を更新します。
- `reconciled_to_annual_statement`または`non_taxable_reconciled`になるまで、確定申告用の最終値とは扱いません。
