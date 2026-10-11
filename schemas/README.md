# Record schemas

新規包括レビューの入力契約は`independent-review-input.schema.yaml`です。現在の事実とユーザーの方向性を検証し、以前の配分・仮説・計画・評価を入力の正本へ含めません。ChatGPTの回答型は固定せず、統合後の自己完結したCodex向け文書化依頼を受け取ります。以下の`review-packet.schema.yaml`と月次回答スキーマの説明は履歴互換用です。ヘルスチェック・家計・口座・取引・税務等のスキーマは継続使用します。

このディレクトリは、手書き・外部入力レコードと、ChatGPTへ渡す閉じたレビュー・パケットの必須項目をJSON Schema形式で定義します。

実行時の詳細な整合性は `repository-audit` と各ローダーでも検証します。戦略、計画、スナップショット、取引、レトロスペクティブに加え、`review-packet.schema.yaml` は生成物 `review_packet.yaml` のallowlist境界、生成前ブロック、対話フェーズ、出力契約を定義します。`monthly-review-response.schema.yaml` と `health-check-response.schema.yaml` はChatGPTからCodexへ渡すYAMLファイルを定義します。月次スキーマは生成時にclosed review packetの `output_contract.inline_response_schema` へ完全インライン化し、独立レビュー実行時はパケット内コピーだけを出力契約として使います。月次回答の取り込み時は、必須フィールド、型、enum、配列構造、null許可、数値範囲をJSON Schemaで検証し、ID一意性、有限候補集合、単一選択、feasibility、配分算式、対象coverage、資金源照合、売却明細照合、戦略から実装への順序を `semantic_validation_checks` とローダーで別途検証します。月次YAMLには、現金要件の導出状態、売買ごとの根拠監査、入力・テンプレート不足を返す `prompt_feedback` を含めます。confirmedの現金条件との不一致や、未確認仮定に依存する `executable` 提案は金額にかかわらず取り込み時に拒否します。生成パケットとAI回答は入力事実の正本ではありません。

`financial-context.schema.yaml` は収入・支出・ボーナス・生活防衛資金・ローン等の版管理レコード、`holding-metadata.schema.yaml` は口座区分・売却可否・保有意図の版管理レコードを定義します。現在値はそれぞれ `financial/current.yaml` と `holdings/current.yaml` のポインタから読み、Markdown、プロンプト、Pythonコードへ数値を重複保存しません。

`transaction.schema.yaml`は確認済み取引と売却時の税務追跡項目、`annual-tax-record.schema.yaml`は取引金額を複製せず年次の確定申告準備・年間資料突合状態を管理する索引を定義します。売却取引は必ず両者を`transaction_id`で接続します。

`broker-order-capability.schema.yaml`は、証券会社の注文画面で証拠から確認できた入力項目・選択肢・銘柄固有値の流用禁止範囲を定義します。現在使用する版は`brokers/`配下の`current.yaml`から解決します。

`review-packet.schema.yaml` の `account_type_gate` は、売買可能な全明細をNISA・特定口座・一般口座へ分類できることを生成前条件とします。不足時は `generation_status: blocked_missing_account_types` とし、部分レビューやChatGPT回答を生成しません。月次回答の `decisions.actions` は現在保有する全明細の行動を網羅し、未保有資産の購入案または購入なしの結論を分離して記録します。

`independent-decision-request.schema.yaml` と `independent-decision-response.schema.yaml` は過去の個別判断パケットとの互換用です。新しい投資判断はレビュー時期で分岐せず、`review-packet.schema.yaml` によるオンデマンド包括レビューへ集約します。互換用requestにはCodexの結論や候補値を含めず、responseはリクエストと同じ `decision_id` と `user_confirmation_required: true` の承認ゲートを維持します。

月次とオンデマンドの両回答は `dip_buy_liquidity_deployment_review` を必須とします。現行政策で戦術的待機資金が無効・0%なら、`reserve_status: unavailable`、`use_option.considered: false`、`use_option.status: not_applicable`、`selected_action: not_applicable`とします。戦術的待機資金が有効または政策レビュー中で、市場下落中かつ利用可能または不明な場合だけ、`use_option.considered` は `true`で、対象、金額または算式、時期、根拠が必要です。`reserve_maintenance_is_objective`は常に`false`です。

月次パケットが `proposal_requested_from_current_review` を指定した場合、独立ChatGPTは総資産比0、2.5、5、7.5、10%の投資待機資金候補を比較してから、正本 `strategic_policy_decision.tactical_liquidity_policy` に一つの目標比率、買付対象、発動条件、分割投入、最低残高、補充・終了方法を提案します。生活防衛資金は別枠です。`cash_assessment` と `dip_buy_liquidity_deployment_review` は正本パスを参照し、`decisions.policy_refs` は `policy_id` だけを参照します。提案は `requires_user_approval: true` とし、承認前は家計入力の確定値へ反映しません。

オンデマンドパケットの `review_mode` は `on_demand_operational_review` または `strategic_policy_second_opinion` のどちらか一つです。前者には乖離点検用の `approved_policy` を含め、未承認の比率・閾値を新規決定しません。後者では現行目標へのアンカリングを避けるため `approved_policy: null` とし、`strategic_policy_stage` で投資待機資金5候補、暗号資産積立3候補、other比率5候補、株式・債券スリーブ11候補に加えてサテライト比率と具体的銘柄を比較し、一つの政策案を選びます。その後だけ `implementation_stage` で商品、推奨行動ウィンドウ内の投入、口座・ロットへ変換します。`recommendation_window` の期間単位と長さは独立ChatGPTが根拠を示して選び、`next_review_recommendation` で次回依頼日と早期再レビュー条件を返します。口座区分は生成前に全件確認済みであり、`complete_with_execution_blocks` は税額、取得価額、ロット詳細など後段の不足だけに使用します。品質チェックは `pass` を自己申告せず、`fail`、`not_verifiable`、`not_applicable` と証拠を使い分けます。

計算前には `execution_capability_gate` で月次キャッシュフロー、二分法、固定シード付き多変量月次モンテカルロ、11候補比較、金利感応度、算術照合、Schema検証の可否を個別確認します。利用不能な能力に依存する数値は `not_calculable` とし、金額±10円、比率±0.02ポイント、確率・収益率・ボラティリティ±0.01ポイントの明示的な照合許容差を使います。銀行書類由来の住宅ローン値は正本として使い、一般的な返済式による再検証や推定不一致を理由とする警告・blocked判定は行いません。
