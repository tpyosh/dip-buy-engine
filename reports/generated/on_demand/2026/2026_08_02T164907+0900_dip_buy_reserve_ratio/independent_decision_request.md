# ChatGPT向けオンデマンド独立投資判断

あなたは、Codexの判断や過去の助言から独立したセカンドオピニオン担当です。後続の判断パケットに含まれる確認済み事実、ユーザー制約、不明情報だけを開始時点のコンテクストとして使用してください。

## 実行環境

- このプロンプト全体だけを、資産運用Project外の新規Temporary Chatへ渡してください。
- 前月レビュー、既存Project、カスタムメモリ、Codexの会話履歴を参照しないでください。
- Codexは結論、候補値、推奨方向を作っていません。判断パケットの空欄をCodexの意図として推測しないでください。

## 判断方法

- 判断に必要な最新情報をWebで調査してください。統計・投資理論・制度・商品仕様は、研究論文、規制当局、公的機関、指数提供会社、運用会社の調査資料など、判断対象に適した一次情報を優先してください。
- 普遍的なベストプラクティスが存在しない場合は、その事実を明示し、ユーザー制約からどのように結論を導いたかを説明してください。
- 確認済み事実、機械計算、外部調査事実、推論、仮定を分離してください。
- 不足情報を適当に埋めず、確定判断、条件付き判断、算定不能を分けてください。
- 現在の保有額やCodexの既存設定に合うよう、根拠を後付けしないでください。
- 売買や戦略変更は提案に留め、実行済みと表現しないでください。
- 判断対象が投資待機資金に関わる場合は、現金残高の維持自体を目的にしないでください。市場下落時には、対象、金額または算式、時期、根拠を持つ使用案を必ず比較対象に含めてください。

## 提出物

1. ユーザー向けの日本語Markdown
2. Codex向けの `independent_decision_response.yaml`

YAMLは `schemas/independent-decision-response.schema.yaml` の構造に従い、Markdownやコードフェンスを混ぜないでください。使用した各根拠にはタイトル、URL、基準日、根拠として使った内容を付けてください。

---

# 判断パケット

```yaml
schema_version: 1
request_type: on_demand_independent_investment_decision
decision_id: 2026-08-02_dip_buy_reserve_ratio
created_at: '2026-08-02T16:49:07+09:00'
decision_question: '生活防衛資金とは別に保有する相場下落時の投資待機資金について、 総資産に対する目標比率を資産運用のベストプラクティスから決定し、
  基準日時点の目標額を計算してください。

  '
decision_scope: investment_policy_parameter_second_opinion
confirmed_facts:
- name: total_financial_assets_jpy
  value: 39969688
  as_of: '2026-07-26'
  source_role: normalized_snapshot_machine_total
- name: emergency_fund_target_jpy
  value: 2000000
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
- name: monthly_income_after_tax_social_insurance_mortgage_ideco_jpy
  value: 374171
  as_of: '2026-07-25'
  source_role: confirmed_user_condition_not_monthly_expense
- name: monthly_nisa_contribution_jpy
  value: 100000
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
- name: effective_monthly_disposable_income_jpy
  value: 274171
  as_of: '2026-07-25'
  source_role: confirmed_user_condition_not_monthly_expense
- name: ordinary_month_cash_flow
  value: approximately_zero
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
- name: bonus_income
  value: exists_but_amount_frequency_and_timing_unknown
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
- name: near_term_large_outflow
  value: none_currently_expected
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
- name: emergency_liquidation_tolerance
  value: willing_to_sell_all_country_fund_even_during_a_market_decline_if_emergency_cash_is_insufficient
  as_of: '2026-07-25'
  source_role: confirmed_user_condition
user_constraints:
- 生活防衛資金2,000,000円と投資待機資金を分離する
- 投資待機資金の目標額は、レビュー基準日時点の総資産に対する比率で算定する
- 採用比率は資産運用のベストプラクティス、統計、投資理論に基づいて導く
- 投資待機資金の確保・満額維持自体を運用目的にしない
- 月次レビューとオンデマンド・ヘルスチェックで市場下落を確認した場合は、使用案を必ず比較する
- 通常月の給与キャッシュフローから恒常的な追加投資余力を推定しない
- 収入、手取り、可処分所得を月間必須支出の確定値へ代用しない
- 売買・戦略変更は提案に留め、ユーザー確認前に実行済みと扱わない
unknown_information:
- 投資待機資金の具体的な目標比率
- 投資待機資金の買付対象
- 投資待機資金の発動条件
- 各回投入額と投入回数
- 最低残高と補充方法
- ボーナスの金額、支給回数、支給時期
- 月間必須支出額
excluded_context:
- Codexが調査した候補比率または推奨比率
- 過去のChatGPTレビューが提示した現金比率
- 既存計画にある固定額の投資待機資金
- 現在の保有額に都合よく目標比率を合わせる判断
- 買付対象・発動条件・投入計画の同時決定。この依頼は目標比率と目標額だけを対象とする
research_requirements:
- 現金待機の機会損失と、下落時流動性の便益を比較する
- 長期運用、高い損失許容度、通常月収支がおおむねゼロ、生活防衛資金が別枠という条件を反映する
- 研究論文、規制当局、公的機関、運用会社の一次調査など、根拠の追跡可能性が高い情報を優先する
- 特定の万能比率が存在しない場合は明記し、根拠からユーザー条件への推論過程を示す
- 各根拠にタイトル、URL、基準日、採用判断へどう使ったかを付ける
required_outputs:
- 推奨する投資待機資金比率
- 総資産39,969,688円に適用した目標額と完全な算式・丸め規則
- 目的関数、ユーザー制約、根拠、基準日、推論過程
- 比率を再検討すべき条件
- 投資待機資金は下落局面で使う手段であり、残高維持自体を目的にしないことの明示
- 必要なら最大2件の代替比率と、切り替える具体的条件
- 買付対象・発動条件・投入計画は別判断であり、今回は確定しないという明示
- ユーザー向け日本語Markdownとindependent_decision_response.yaml
```
