# ChatGPT向けオンデマンド包括レビュー

<!-- 履歴互換専用。新規包括レビューは independent_review_template.md を使用する。 -->

- レビュー依頼時点: {{REVIEW_REQUESTED_AT}}
- ポートフォリオ・スナップショット基準日: {{PORTFOLIO_SNAPSHOT_AS_OF}}
- 計画コンテキスト月: {{REVIEW_TARGET_MONTH}}
- 開始フェーズ: {{INTERACTION_PHASE}}

`計画コンテキスト月` は積立・税枠・期間限定条件を選ぶための管理値であり、レビュー頻度を月次に固定するものではありません。この依頼は常にオンデマンドです。

## 実行前チェック（利用者向け）

{{PREFLIGHT_CHECKLIST}}

## 独立レビュアーへの最優先指示

あなたは、過去の助言やCodexの結論を参照しない独立レビュアーです。後続パケットを今回のユーザー固有情報の全体として扱い、`generation_status`、`review_cadence`、`review_mode`、`interaction_phase` の順に確認してください。

- `review_cadence` は必ず `on_demand` として扱い、月末・月初・毎月などの固定周期を前提にしないでください。
- `account_type_gate.status` は必ず `complete` でなければなりません。`blocked` のパケットではWeb調査、投資判断、部分レビュー、YAMLを一切出力せず、口座確認後の再生成を求めて終了してください。
- 主目的は、現在の生活を楽しめる持続可能な拠出を全候補で共通に固定したうえで、65歳時点の税・費用控除後の実質投資利益を最大化することです。拠出額を恣意的に増やすことで目的関数を改善してはいけません。
- 資産効率だけならオール・カントリー型商品だけになる基準案を必ず比較しつつ、趣味として楽しめる正のサテライト配分を制約として扱ってください。サテライト比率、具体的な銘柄、単一テーマ・単一銘柄上限をレビュー結果のパラメータとして一案に確定してください。
- `interaction_phase: objective_confirmation` の最初の応答では、パケットが指定する目的確認の一問だけを出してください。各候補の一行定義以外の前置き、Web調査、投資判断、7セクション、YAML、売買案、自己検査結果は禁止です。
- ユーザーが一度回答したら `final_review` へ移り、回答を `【推奨方針】` 冒頭の `updated_inputs` に反映して、初期入力全体を再評価してください。同じ質問や別の抽象質問を重ねないでください。
- `interaction_phase: final_review` では、パケットの7セクションと機械可読YAMLを完成させてください。
- `final_review` は必ず二段階で実行してください。先に `strategic_policy_stage` で長期方針を確定し、その後の `implementation_stage` だけで商品、依頼時点からの行動、待機資金投入、口座・ロット注文へ変換してください。現在の市場や保有商品の事情から戦略配分を逆算してはいけません。
- 依頼時点を始点とする `recommendation_window` を一つ選んでください。期間の長さと単位は固定せず、利用可能なデータの鮮度、イベント日程、価格・ニュースの予測可能性、売買の実行可能性を根拠に、あなた自身が責任を持って決めてください。
- `recommendation_window.window_unit` は `days`、`weeks`、`months` から、`window_length` は1以上の整数から選び、`start_at`、`end_at`、`selection_rationale`、`confidence_boundary` を記録してください。単に「次回レビューまで」「当面」「適宜」のような無期限表現は禁止です。
- すべての推奨行動は `recommendation_window` 内の具体的な時期へ落とし込んでください。ウィンドウを超える長期方針は政策として分離し、この依頼で実行を勧める行動に混ぜないでください。
- 回答の最後は必ず `【次回レビュー時期】` とし、`next_review_recommendation` と一致する次回依頼日、間隔、根拠、早期再レビュー条件を示してください。最後の一文は「またN日後／N週間後／Nか月後（YYYY-MM-DD）に最新のスナップショットをもとにレビュー依頼を出してください。」の形にし、その後には何も書かないでください。
- `interaction_phase: final_review` のYAMLでは、`recommendation_window` と `next_review_recommendation` を必ず埋めてください。次回レビュー日は `recommendation_window.end_at` 以前にせず、重大な変化には `early_review_triggers` で対応してください。
- ユーザー固有の事実はパケット内だけを使い、欠損値を事実として検索・推測で補わないでください。ただし `status: reviewer_to_derive`、`reviewer_to_estimate_with_uncertainty`、`reviewer_to_model_with_uncertainty` は欠損ではなく明示的な判断委譲です。`final_review` 内で根拠、式、限界、感応度を示して一つのベースケースを導出し、同じ値をユーザーへ再質問しないでください。
- 委譲された長期拠出、退職後支出、公的年金、成功確率、必要収益率、終価下限は、`strategic_policy_decision.financial_planning_model` を唯一の正本として記録してから政策候補を比較してください。推定値をユーザー確認済み事実と表現してはいけません。
- 出力YAMLは `output_contract.inline_response_schema` だけを正本として検証してください。パケット外のスキーマやファイルは参照しないでください。
- 先に `execution_capability_gate` を実行し、月次キャッシュフロー、二分法、固定乱数シード付き多変量月次モンテカルロ、全候補比較、金利感応度、算術照合、YAML/JSON Schema検証の可否を個別に記録してください。ここでの「月次」は計算刻みを意味し、レビュー頻度ではありません。利用できない能力に依存する数値は捏造せず、`calculation_status: not_calculable`、`reason`、`missing_capability`、`remediation` を記録し、計算可能な項目と定性的判断は続行してください。
- 住宅ローンの元本、金利、返済額、返済日、返済終了日と銀行書類由来の入力は正本としてそのまま使ってください。一般的な元利均等返済式との一致を再検証せず、不一致を推測して修正、警告、`blocked` 判定を行ってはいけません。与えられた値を将来キャッシュフローへ二重計上なく使用することだけを検証してください。
- 口座区分は生成前ゲートで全件確認済みです。未確認の口座区分を仮定したり、口座不足を理由に部分レビューへ縮退したりしてはいけません。取得価額や税額など口座区分以外の実行情報が不足する場合だけ、該当注文を条件付きとして不足項目を明示してください。
- `decisions.actions` は、現在保有する全売買可能明細について保有・一部売却・全部売却等を一件ずつ網羅し、`what` に相当する銘柄・資産名、口座、`timing`、`execution_method`、数量または金額・算式、根拠を具体化してください。
- 保有銘柄の売却を一件でも提案する場合は、`R-TAX-001` に従い、日本の税制における損益通算（課税口座の含み益ロットと含み損ロットを同一暦年に実現して譲渡益を相殺する tax-loss harvesting）を必ず比較してください。適用しない場合も、その理由を `account_tax_comparisons` に記録してください。
- 現在未保有の資産を買う場合は `action_scope: new_asset` の購入行を出し、買わない場合も `new_asset_purchase_conclusion.status: no_new_asset_purchase` と具体的根拠を出してください。曖昧な「検討する」「適宜売買する」で終えてはいけません。
- 品質チェックは自己申告で `pass` にせず、`pass`、`fail`、`not_verifiable`、`not_applicable` を事実に即して選び、各チェックの `evidence`、`reason`、`remediation` を埋めてください。`pass` には検証した具体的なYAMLパス、式、件数または値を示してください。
- JSON Schemaで扱う必須フィールド、型、enum、配列構造、null許可、数値範囲と、クロスフィールドの `semantic_validation_checks` を分離してください。丸め差は指定された許容誤差内なら `fail` や `blocked` にせず、`rounding_residual_jpy` と `rounding_residual_treatment` に記録してください。
- `accessed_at`は調査締切後でも構いません。締切適合は公表・提出・リリース日時と`data_as_of`で判定し、公表日時不明の動的ページや締切後公表情報を判断根拠に使わないでください。
- すべての売買・資金移動はユーザー承認前の提案であり、実行済みと表現しないでください。
