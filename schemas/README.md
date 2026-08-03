# Record schemas

このディレクトリは、手書き・外部入力レコードと、ChatGPTへ渡す閉じたレビュー・パケットの必須項目をJSON Schema形式で定義します。

実行時の詳細な整合性は `repository-audit` と各ローダーでも検証します。戦略、計画、スナップショット、取引、レトロスペクティブに加え、`review-packet.schema.yaml` は生成物 `review_packet.yaml` のallowlist境界、生成前ブロック、対話フェーズ、出力契約を定義します。`monthly-review-response.schema.yaml` と `health-check-response.schema.yaml` はChatGPTからCodexへ渡すYAMLファイルを定義します。月次YAMLには、現金要件の導出状態、売買ごとの根拠監査、入力・テンプレート不足を返す `prompt_feedback` を含めます。confirmedの現金条件との不一致や、未確認仮定に依存する `executable` 提案は金額にかかわらず取り込み時に拒否します。生成パケットとAI回答は入力事実の正本ではありません。

`financial-context.schema.yaml` は収入・支出・ボーナス・生活防衛資金・ローン等の版管理レコード、`holding-metadata.schema.yaml` は口座区分・売却可否・保有意図の版管理レコードを定義します。現在値はそれぞれ `financial/current.yaml` と `holdings/current.yaml` のポインタから読み、Markdown、プロンプト、Pythonコードへ数値を重複保存しません。

`independent-decision-request.schema.yaml` と `independent-decision-response.schema.yaml` は、月次外の新しい投資判断を独立Temporary Chatへ委譲する汎用経路を定義します。requestにはCodexの結論や候補値を含めず、確認済み事実、ユーザー制約、不明情報、除外コンテクスト、調査要件、出力要件だけを入れます。responseはリクエストと同じ `decision_id` を必須とし、`user_confirmation_required: true` の承認ゲートを持ちます。

月次とオンデマンドの両回答は `dip_buy_liquidity_deployment_review` を必須とします。市場下落中で投資待機資金が利用可能または不明な場合、`use_option.considered` は `true` で、対象、金額または算式、時期、根拠が必要です。`reserve_maintenance_is_objective` は常に `false` です。

月次パケットが `proposal_requested_from_current_review` を指定した場合、独立ChatGPTは正本 `strategic_policy_decision.tactical_liquidity_policy` に目標比率、買付対象、発動条件、分割投入、補充・終了方法を提案します。`cash_assessment` と `dip_buy_liquidity_deployment_review` は正本パスを参照し、`decisions.policy_refs` は `policy_id` だけを参照します。提案は `requires_user_approval: true` とし、承認前は家計入力の確定値へ反映しません。

月次パケットの `review_mode` は `monthly_operational_review` または `strategic_policy_second_opinion` のどちらか一つです。前者には乖離点検用の `approved_policy` を含め、未承認の比率・閾値を新規決定しません。後者では現行目標へのアンカリングを避けるため `approved_policy: null` とし、`strategic_decision_objective`、三層の `capital_layers`、標準候補比較、`decision_axes`、`decision_quality_checks` に従って一つの政策案を選びます。人間向け回答は6セクション、Codex向けYAMLは `updated_inputs` と戦略判断の構造化フィールドを持ちます。
