# Review inputs

外部レビューの原文をCLIへ取り込む前に保存する領域です。

- ファイル名例: `YYYY_MM_chatgpt_review.txt`
- 原文は受領したまま保存し、構造化結果は`reports/generated/monthly/YYYY_MM/review_response.yaml`へ生成する。
- 外部レビューは提案であり、戦略、計画、取引実績のsource of truthではない。
- 売買可能な全明細の口座区分ゲートがcompleteでないレビュー原文は、旧テキスト形式を含めCLIへ取り込まない。
