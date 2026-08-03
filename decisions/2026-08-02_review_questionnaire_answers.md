# Monthly review questionnaire answers — 2026-08-02

## Status

Confirmed by the user on 2026-08-02.

## Structured sources of truth

- 家計・収支・生活防衛資金・予備費・ボーナス・投資待機資金の回答: `financial/versions/2026-08-02.yaml`
- 口座区分・売却可否・保有理由・売却意向: `holdings/versions/2026-08-02.yaml`
- 承認済み半導体集中目標: `strategy/versions/2026-08-02.yaml`
- 現在版半導体仮説: `strategy/theses/semiconductor_2026-08-02.yaml`

この文書には変動する金額を重複記載しない。現在値は各 `current.yaml` ポインタが指す構造化レコードを参照する。

## Approved decisions

- 直接半導体エクスポージャーを総資産の12%以下へ縮小する方針を承認。
- 売却対象の優先順位は独立レビューから提案を受ける。
- 投資待機資金の目標比率、発動条件、投入回数は今回の月次独立レビューから提案を受ける。
- 投資待機資金の買付対象は現時点では未定。

## Execution boundary

この回答は売買注文ではない。銘柄・口座ロット・金額・時期は独立レビューの提案とユーザの明示承認を経て決める。

旧 `plans/2026/2026-07-25_cash_redeployment.yaml` の固定投資待機額は今回の回答と整合しないため、現在ポインタのactive planから外す。過去の承認記録としてファイル自体は変更しない。
