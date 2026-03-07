この Python CLI プロジェクトを修正してください。

目的:
- 月次の押し目買いレビュー支援システムの改善

今回の修正理由:
- ChatGPT の月次レビューで改善点が指摘されたため

現在の問題:
- must: portfolio.py に半導体エクスポージャ警告の説明を追加
- should: review_parser.py で理由抽出を安定化
- nice_to_have: README に四半期見直し運用を追記
- diff_observation: MSFT price_delta=-0.43
- diff_observation: PLTR price_delta=n/a

修正目的:
- ChatGPT の改善提案を、既存の CLI 月次ワークフローを壊さずに反映する。
- Python 候補値と ChatGPT 提案との差分保存を継続しつつ、レビュー品質を高める。

優先度別修正要求:
- must:
  - portfolio.py に半導体エクスポージャ警告の説明を追加
- should:
  - review_parser.py で理由抽出を安定化
- nice_to_have:
  - README に四半期見直し運用を追記
  - 修正目的: 警告とレビューの整合性を上げる

修正対象ファイル:
- src/monthly_limit_order_review/portfolio.py
- src/monthly_limit_order_review/review_parser.py
- README.md
- tests/test_portfolio.py
- tests/test_review_parser.py

仕様差分:
- 半導体エクスポージャ警告の説明をより詳細にする
- レビュー理由の抽出精度を上げる
- 四半期見直し運用の説明を README に追記する

追加 / 更新テスト:
- tests/test_portfolio.py
- tests/test_review_parser.py

後方互換性の注意点:
- 自動発注は追加しない
- YAML 入力と CLI ベース運用を維持する
- 既存の生成物パス規約を壊さない
