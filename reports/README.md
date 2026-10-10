# Generated reports

`reports/generated/` は、計算結果、allowlist型レビュー・パケット、レビュー依頼、レビュー構造化結果、提案差分、カレンダードラフトなどの自動生成物を置く領域です。

Money ForwardのOCR運用は2026-10-10に廃止しました。過去の生成物に残るOCR手順・専用プロンプトへの参照は再利用しません。[廃止記録](../docs/migrations/2026-10-10-moneyforward-ocr-retirement.md)を参照してください。

- 生成物は事実データ、戦略、計画、取引実績のsource of truthではない。
- 月次生成物は `reports/generated/monthly/YYYY_MM/` にまとめる。
- `review_packet.yaml` はChatGPTへ渡してよい情報境界の監査用で、`review_request.md` は同じパケットから生成する。
- `review_packet.yaml` 自体はChatGPTへ追加添付せず、`review_request.md` 冒頭のブラインド実行チェックに従う。
- オンデマンド生成物は `reports/generated/on_demand/YYYY/<timestamp>/` にまとめ、依頼を `health_check_request.md`、完了結果を `health_check_response.yaml` とする。
- 月次外の新しい投資判断は、同じオンデマンド領域に判断パケットと `independent_decision_request.md` を生成し、Project外のTemporary Chatへ委譲する。Codexの結論、候補値、推奨方向を判断パケットへ含めない。
- 独立回答の `independent_decision_response.yaml` は元の `decision_request.yaml` と照合して契約検証する。検証通過だけでは戦略・計画へ反映せず、ユーザ承認を別途必要とする。
- 月次の機械取り込み入力は `review_response.yaml` とし、人間向けMarkdownから値を推測して生成しない。YAMLには `cash_assessment`、根拠監査付き `decisions.actions`、入力・テンプレート不足を返す `prompt_feedback` を含める。
- 月次・オンデマンドとも、全売買可能明細の口座区分がNISA・特定口座・一般口座のいずれかに確定するまで、ChatGPT向けレビュー依頼とレビュー出力を生成しない。生成停止ファイルはレビュー依頼ではない。
- 2026-08-09より前に生成済みのレビュー依頼・回答は、新しい口座区分ゲートを再通過しない限り現在レビューとして再利用・再取込しない。
- 月次 `decisions.actions` は現在保有する全売買可能明細を一件ずつ網羅し、銘柄、口座、売却・保有、時期、方法、数量または金額・算式を持つ。現在未保有資産の購入案、または新規購入なしの結論も必須とする。
- 月次 `review_response.yaml` とオンデマンド `health_check_response.yaml` は `dip_buy_liquidity_deployment_review` を必須とする。下落局面では、投資待機資金を使う案を比較せずに使用見送りとした回答を取り込まない。
- 2026-07以前の既存生成物は移動・書換えせず、`legacy-index.yaml`から参照する。
- 生成物を手編集せず、入力または生成コードを修正して再生成する。
