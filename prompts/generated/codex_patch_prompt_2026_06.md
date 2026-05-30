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

現在の問題:
- must: なし
- should: README.md に最新月の月次サマリー・coreスポット購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する
- should: README.md の最新月セクション内の見やすい位置に「今月の指値買い設定」を追加または更新し、銘柄、指値、株数、見送り対象、主な理由を一覧化する
- should: snapshot_price と candidate current_price の価格ソース日付が異なる可能性があるため、出力に `snapshot_price_source_date` と `market_candidate_price_source_date` のような区別を追加する
- should: CIBR のように satellite_core over target で浅い候補が suppressed される場合、eligible deep candidate が生成されないなら「今月は eligible deep candidate なし」と明示する
- should: EMAXIS_SLIM_SP500_1 と EMAXIS_SLIM_ALL_COUNTRY の large_month_over_month_change について、購入・売却・口座グルーピング変更・OCR誤読のどれが原因か README.md または検証ログに確認結果を残す
- should: README.md 更新時は既存の `## Monthly Review: YYYY_MM` を `2026_06` の内容に置換し、ルートREADMEに月次レビュー履歴を蓄積せず、過去月の `Monthly Review` セクションを残さない
- nice_to_have: liquidity_floor_jpy または emergency_fund_floor_jpy を設定ファイルに持たせ、住宅ローン初期・大口支出不明時の coreスポット買い上限判断を安定させる
- nice_to_have: coreスポット買いスケジュールを自動生成する場合、配分先内訳と日付別実行額の合計一致チェックをテストに追加する
- nice_to_have: satellite_core over target 時の CIBR / URA / SOX の deep threshold を銘柄別に設定できるようにする
- nice_to_have: コード修正提案が少ない月でも README.md に最新月の運用要約と指値買い設定を確実に反映する
- nice_to_have: 月次レビューで snapshot 価格と候補生成用価格の混同を避ける
- nice_to_have: over target のテーマ銘柄について、浅い候補を suppressed した後に買える候補が存在するのか、存在しないのかを明確にする
- nice_to_have: 前月比で大きく変化した core 投信の値が、実取引によるものかOCR/正規化由来かを追跡可能にする
- nice_to_have: README.md の最新月セクションに、月次サマリー、coreスポット買い計画、今月の指値買い設定、ポートフォリオサマリーを追加または更新する
- nice_to_have: 今月の指値買い設定は、銘柄、指値、20営業日平均、平均比乖離率、株数、見送り対象、主な理由を表で記載する
- nice_to_have: price 系フィールドは、Money Forward snapshot由来の評価価格と、市場データ由来の候補生成価格を区別して出力する
- nice_to_have: over target bucket で shallow candidate を suppressed した場合、deep candidate が生成されていない理由を出力する
- nice_to_have: README.md
- nice_to_have: monthly review 出力生成ロジック
- nice_to_have: limit order candidate 生成ロジック
- nice_to_have: price source / validation 出力
- nice_to_have: month-over-month validation log
- nice_to_have: README.md の見出し、表、Mermaid が壊れないことを確認する
- nice_to_have: coreスポット買いの配分先内訳合計と実行スケジュール合計が一致することを確認する
- nice_to_have: CIBR のような over target 銘柄で shallow candidate が suppressed され、deep candidate がない場合に「eligible deep candidate なし」と出ることを確認する
- nice_to_have: snapshot価格とcandidate価格のソース日付が別フィールドで出力されることを確認する
- nice_to_have: large_month_over_month_change が出た銘柄について、検証警告がREADME.mdまたはログに反映されることを確認する
- diff_observation: CIBR price_delta=n/a
- diff_observation: MSFT price_delta=-4.25
- diff_observation: PLTR price_delta=-8.23
- diff_observation: URA price_delta=0.00

修正目的:
- ChatGPT の改善提案を、既存の CLI 月次ワークフローを壊さずに反映する。
- Python 候補値と ChatGPT 提案との差分保存を継続しつつ、レビュー品質を高める。

優先度別修正要求:
- must:
  - なし
- should:
  - README.md に最新月の月次サマリー・coreスポット購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する
  - README.md の最新月セクション内の見やすい位置に「今月の指値買い設定」を追加または更新し、銘柄、指値、株数、見送り対象、主な理由を一覧化する
  - snapshot_price と candidate current_price の価格ソース日付が異なる可能性があるため、出力に `snapshot_price_source_date` と `market_candidate_price_source_date` のような区別を追加する
  - CIBR のように satellite_core over target で浅い候補が suppressed される場合、eligible deep candidate が生成されないなら「今月は eligible deep candidate なし」と明示する
  - EMAXIS_SLIM_SP500_1 と EMAXIS_SLIM_ALL_COUNTRY の large_month_over_month_change について、購入・売却・口座グルーピング変更・OCR誤読のどれが原因か README.md または検証ログに確認結果を残す
  - README.md 更新時は既存の `## Monthly Review: YYYY_MM` を `2026_06` の内容に置換し、ルートREADMEに月次レビュー履歴を蓄積せず、過去月の `Monthly Review` セクションを残さない
- nice_to_have:
  - liquidity_floor_jpy または emergency_fund_floor_jpy を設定ファイルに持たせ、住宅ローン初期・大口支出不明時の coreスポット買い上限判断を安定させる
  - coreスポット買いスケジュールを自動生成する場合、配分先内訳と日付別実行額の合計一致チェックをテストに追加する
  - satellite_core over target 時の CIBR / URA / SOX の deep threshold を銘柄別に設定できるようにする
  - コード修正提案が少ない月でも README.md に最新月の運用要約と指値買い設定を確実に反映する
  - 月次レビューで snapshot 価格と候補生成用価格の混同を避ける
  - over target のテーマ銘柄について、浅い候補を suppressed した後に買える候補が存在するのか、存在しないのかを明確にする
  - 前月比で大きく変化した core 投信の値が、実取引によるものかOCR/正規化由来かを追跡可能にする
  - README.md の最新月セクションに、月次サマリー、coreスポット買い計画、今月の指値買い設定、ポートフォリオサマリーを追加または更新する
  - 今月の指値買い設定は、銘柄、指値、20営業日平均、平均比乖離率、株数、見送り対象、主な理由を表で記載する
  - price 系フィールドは、Money Forward snapshot由来の評価価格と、市場データ由来の候補生成価格を区別して出力する
  - over target bucket で shallow candidate を suppressed した場合、deep candidate が生成されていない理由を出力する
  - README.md
  - monthly review 出力生成ロジック
  - limit order candidate 生成ロジック
  - price source / validation 出力
  - month-over-month validation log
  - README.md の見出し、表、Mermaid が壊れないことを確認する
  - coreスポット買いの配分先内訳合計と実行スケジュール合計が一致することを確認する
  - CIBR のような over target 銘柄で shallow candidate が suppressed され、deep candidate がない場合に「eligible deep candidate なし」と出ることを確認する
  - snapshot価格とcandidate価格のソース日付が別フィールドで出力されることを確認する
  - large_month_over_month_change が出た銘柄について、検証警告がREADME.mdまたはログに反映されることを確認する

修正対象ファイル:
- README.md
- src/monthly_limit_order_review/review_parser.py
- tests/test_review_parser.py

仕様差分:
- must: なし
- should: README.md に最新月の月次サマリー・coreスポット購入計画・今月の指値買い設定・ポートフォリオサマリーを反映する
- should: README.md の最新月セクション内の見やすい位置に「今月の指値買い設定」を追加または更新し、銘柄、指値、株数、見送り対象、主な理由を一覧化する
- should: snapshot_price と candidate current_price の価格ソース日付が異なる可能性があるため、出力に `snapshot_price_source_date` と `market_candidate_price_source_date` のような区別を追加する
- should: CIBR のように satellite_core over target で浅い候補が suppressed される場合、eligible deep candidate が生成されないなら「今月は eligible deep candidate なし」と明示する
- should: EMAXIS_SLIM_SP500_1 と EMAXIS_SLIM_ALL_COUNTRY の large_month_over_month_change について、購入・売却・口座グルーピング変更・OCR誤読のどれが原因か README.md または検証ログに確認結果を残す
- should: README.md 更新時は既存の `## Monthly Review: YYYY_MM` を `2026_06` の内容に置換し、ルートREADMEに月次レビュー履歴を蓄積せず、過去月の `Monthly Review` セクションを残さない
- nice_to_have: liquidity_floor_jpy または emergency_fund_floor_jpy を設定ファイルに持たせ、住宅ローン初期・大口支出不明時の coreスポット買い上限判断を安定させる
- nice_to_have: coreスポット買いスケジュールを自動生成する場合、配分先内訳と日付別実行額の合計一致チェックをテストに追加する
- nice_to_have: satellite_core over target 時の CIBR / URA / SOX の deep threshold を銘柄別に設定できるようにする
- nice_to_have: コード修正提案が少ない月でも README.md に最新月の運用要約と指値買い設定を確実に反映する
- nice_to_have: 月次レビューで snapshot 価格と候補生成用価格の混同を避ける
- nice_to_have: over target のテーマ銘柄について、浅い候補を suppressed した後に買える候補が存在するのか、存在しないのかを明確にする
- nice_to_have: 前月比で大きく変化した core 投信の値が、実取引によるものかOCR/正規化由来かを追跡可能にする
- nice_to_have: README.md の最新月セクションに、月次サマリー、coreスポット買い計画、今月の指値買い設定、ポートフォリオサマリーを追加または更新する
- nice_to_have: 今月の指値買い設定は、銘柄、指値、20営業日平均、平均比乖離率、株数、見送り対象、主な理由を表で記載する
- nice_to_have: price 系フィールドは、Money Forward snapshot由来の評価価格と、市場データ由来の候補生成価格を区別して出力する
- nice_to_have: over target bucket で shallow candidate を suppressed した場合、deep candidate が生成されていない理由を出力する
- nice_to_have: README.md
- nice_to_have: monthly review 出力生成ロジック
- nice_to_have: limit order candidate 生成ロジック
- nice_to_have: price source / validation 出力
- nice_to_have: month-over-month validation log
- nice_to_have: README.md の見出し、表、Mermaid が壊れないことを確認する
- nice_to_have: coreスポット買いの配分先内訳合計と実行スケジュール合計が一致することを確認する
- nice_to_have: CIBR のような over target 銘柄で shallow candidate が suppressed され、deep candidate がない場合に「eligible deep candidate なし」と出ることを確認する
- nice_to_have: snapshot価格とcandidate価格のソース日付が別フィールドで出力されることを確認する
- nice_to_have: large_month_over_month_change が出た銘柄について、検証警告がREADME.mdまたはログに反映されることを確認する
- diff_observation: CIBR price_delta=n/a
- diff_observation: MSFT price_delta=-4.25
- diff_observation: PLTR price_delta=-8.23
- diff_observation: URA price_delta=0.00

追加 / 更新テスト:
- tests/test_review_parser.py

後方互換性の注意点:
- 自動発注は追加しない。
- YAML 入力と CLI ベースの運用を維持する。
- 既存の生成物パス規約を変更する場合は README とテストも更新する。

Python 候補 vs ChatGPT 提案の差分:
- CIBR: python_price=70.76 | chatgpt_price=None | price_diff_pct=None | python_shares=1 | chatgpt_shares=0 | removed=True
- MSFT: python_price=394.06 | chatgpt_price=377.30 | price_diff_pct=-4.25 | python_shares=1 | chatgpt_shares=2 | removed=False
- PLTR: python_price=118.80 | chatgpt_price=109.02 | price_diff_pct=-8.23 | python_shares=2 | chatgpt_shares=2 | removed=False
- URA: python_price=45.38 | chatgpt_price=45.38 | price_diff_pct=0.00 | python_shares=2 | chatgpt_shares=2 | removed=False
