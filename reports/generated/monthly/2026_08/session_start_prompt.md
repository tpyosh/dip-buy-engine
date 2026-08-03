# ChatGPT向け月次独立レビュー

- 対象月: 2026_08
- ポートフォリオ・スナップショット基準日: 2026-07-26
- 開始フェーズ: final_review

## 実行前チェック（利用者向け）

- [ ] ChatGPTの資産運用プロジェクト内では実行しない
- [ ] プロジェクト外の新規Temporary Chatなど、過去会話を参照しない環境で実行する
- [ ] 前月のレビュースレッドを再利用しない
- [ ] このレビュー・パケット以外のファイルを添付しない
- [ ] 独立レビューへ影響するカスタム指示を無効化するか、影響しないことを確認する

## 独立レビュアーへの最優先指示

あなたは、過去の助言やCodexの結論を参照しない独立レビュアーです。後続パケットを今回のユーザー固有情報の全体として扱い、`generation_status`、`review_mode`、`interaction_phase` の順に確認してください。

- `interaction_phase: objective_confirmation` の最初の応答では、パケットが指定する目的確認の一問だけを出してください。各候補の一行定義以外の前置き、Web調査、投資判断、6セクション、YAML、売買案、自己検査結果は禁止です。
- ユーザーが一度回答したら `final_review` へ移り、回答を `【推奨方針】` 冒頭の `updated_inputs` に反映して、初期入力全体を再評価してください。同じ質問や別の抽象質問を重ねないでください。
- `interaction_phase: final_review` では、パケットの6セクションと機械可読YAMLを完成させてください。
- ユーザー固有の事実はパケット内だけを使い、欠損値を事実として検索・推測で補わないでください。ただし `status: reviewer_to_derive`、`reviewer_to_estimate_with_uncertainty`、`reviewer_to_model_with_uncertainty` は欠損ではなく明示的な判断委譲です。`final_review` 内で根拠、式、限界、感応度を示して一つのベースケースを導出し、同じ値をユーザーへ再質問しないでください。
- 委譲された長期拠出、退職後支出、公的年金、成功確率、必要収益率、終価下限は、`strategic_policy_decision.financial_planning_model` を唯一の正本として記録してから政策候補を比較してください。推定値をユーザー確認済み事実と表現してはいけません。
- すべての売買・資金移動はユーザー承認前の提案であり、実行済みと表現しないでください。

---

# 自己完結型レビュー・パケット

- handoff_mode: closed_review_packet
- このパケット外のユーザー固有情報、過去会話、Project/GPTメモリを使用しないでください。
- 不明値を確認済み事実として推測で埋めず、事実と外部調査による一般情報を分離してください。明示されたreviewer_to_derive系の項目は、推定値・根拠・限界・感応度を示して導出してください。

## 1. モードと対話フェーズ
```yaml
generation_status: ready
review_mode: strategic_policy_second_opinion
interaction_phase: final_review
required_first_response: 【推奨方針】から始める
```

## 2. 入力データ
```yaml
date_context:
  review_target_month: '2026_08'
  portfolio_snapshot_as_of: '2026-07-26'
  market_reference_as_of: '2026-08-03'
  packet_generated_at: '2026-08-03T13:34:24Z'
  research_cutoff_at: '2026-08-03T13:34:24Z'
  decision_date: null
strategic_required_inputs:
  date_of_birth: '1992-01-07'
  user_age: 34
  user_age_as_of: '2026-07-26'
  tax_residency: Japan
  investment_horizon_years: 66
  planning_end_age: 100
  expected_withdrawal_start: '2057-01-07'
  earliest_possible_asset_use_date: '2057-01-07'
  planned_contributions:
    status: reviewer_to_derive
    decision_owner: independent_monthly_reviewer
    user_capacity_statement: 余裕はある
    observed_commitments_ref: plans/recurring/current.yaml
    decision_scope:
    - sustainable_net_contribution_amount
    - continuation_period
    - account_and_asset_allocation
    - continuation_or_change_of_current_nisa_ideco_and_crypto_contributions
    constraints:
    - distinguish_new_savings_from_temporary_redeployment_of_existing_cash
    - do_not_treat_the_observed_750000_jpy_monthly_setting_as_salary_funded_without_evidence
    - use_confirmed_cash_flow_mortgage_and_emergency_fund_constraints
    - select_one_concrete_base_case_and_do_not_return_the_choice_to_the_user
  current_recurring_commitments:
    core_monthly_total_jpy: 100000
    core_monthly_plans:
    - day_of_month: 8
      fund_name: eMAXIS Slim 全世界株式（オール・カントリー）
      amount_jpy: 50000
      settlement_type: クレジットカード決済
      account_type: NISAつみたて投資枠
      distribution_course: 再投資型
    - day_of_month: 8
      fund_name: eMAXIS Slim 米国株式（S&P500）
      amount_jpy: 50000
      settlement_type: クレジットカード決済
      account_type: NISAつみたて投資枠
      distribution_course: 再投資型
    pension_monthly_total_jpy: 55000
    pension_monthly_plans:
    - symbol: IDECO_ALL_COUNTRY
      fund_name: eMAXIS Slim 全世界株式（オール・カントリー）
      amount_jpy_per_month: 55000
      account_type: iDeCo
      asset_class: pension
    crypto_weekly_total_jpy: 4000
    crypto_weekly_plans:
    - symbol: BTC
      amount_jpy_per_week: 2000
    - symbol: ETH
      amount_jpy_per_week: 2000
    nisa_growth_quota_status: exhausted
    source: plans/recurring/versions/2026-03-01.yaml
    as_of: '2026_08'
  expected_future_cash_flows:
    status: reviewer_to_model_with_uncertainty
    decision_owner: independent_monthly_reviewer
    items:
      employment_income:
        expected_continuation_years: 30
        planned_retirement_age: 65
        certainty: rough_user_plan_subject_to_future_conditions
      bonus:
        future_amount_jpy: null
        status: unknown
        modeling_rule: reviewer_selects_and_documents_base_case_treatment
      inheritance:
        source_owner: father
        source_estimated_total_assets_jpy: 100000000
        estimate_qualifier: approximately
        reported_beneficiaries:
        - user
        - mother
        - younger_sister
        user_is_beneficiary: true
        user_share_jpy: null
        possible_timing_within_years: 20
        timing_certainty: speculative_user_estimate
        modeling_rule: do_not_infer_a_legal_share; choose_a_conservative_base_case_and_show_sensitivity
  human_capital_assumptions:
    education: graduate_school
    employment_status: full_time_employee
    occupation: automotive_software_engineer
    income_stability: high
    income_stability_reason: user_identified_only_singularity_as_material_risk
    expected_salary_continuation_years: 30
    planned_retirement_age: 65
    retirement_age_certainty: rough_user_plan_subject_to_future_conditions
    known_long_leave_or_unemployment_risk: none_identified_by_user
  liabilities:
    mortgage_outstanding_jpy: 62520685
    user_share_jpy: 31260342
    interest_rate: 0.0112
    fixed_or_variable: variable
    remaining_term_years: 38.17
    annual_repayment_jpy: 890052
    balance_as_of: '2026-07-27'
  pension_and_other_future_assets:
    status: reviewer_to_estimate_with_uncertainty
    decision_owner: independent_monthly_reviewer
    items:
    - type: japanese_public_employee_pension
      employment_assumption: full_time_employee_from_age_24_through_age_65
      expected_benefit_jpy: null
      benefit_frequency: null
      status: amount_unknown
      modeling_rule: use_current_official_Japanese_sources_and_available_user_facts;
        disclose_data_gaps_and_sensitivity
strategic_decision_objective:
  primary_objective: minimize_risk_for_required_return
  objective_question: 長期政策の主目的を一つ選んでください。選択肢に不足パラメータが示される場合は、同じ回答でその値も指定してください。
  objective_models:
    maximize_terminal_wealth:
      label: 最終資産額の最大化
      horizon_years: null
      planned_contributions: null
      return_basis: null
      statistic: null
      downside_quantile_pct: null
      leverage_allowed: null
      required_parameters:
      - horizon_years
      - planned_contributions
      - return_basis
      - statistic
      - leverage_allowed
      primary_objective_fit_rule: 同一の拠出・期間・名目/実質・レバレッジ条件で、指定された期待値、中央値または下方分位の終価が最大の候補を最良とする
      offered: false
    minimize_risk_for_required_return:
      label: 必要収益を満たす最小リスク
      target_return_pct: null
      target_return_derivation:
        status: reviewer_to_derive
        decision_owner: independent_monthly_reviewer
        method: derive the real required return from current investable assets, reviewer-derived
          sustainable contributions, retirement spending, public pension, planning
          end age, terminal asset floor, and documented treatment of inheritance
        evidence_requirements:
        - packet_confirmed_cash_flow_and_asset_values
        - official_pension_and_inflation_sources
        - explicit_formula_and_assumption_date
        sensitivity_required: true
        base_case_required: true
      return_basis: real
      horizon_years: 66
      accumulation_horizon_years: 31
      withdrawal_horizon_years: 35
      success_probability_pct: null
      success_probability_derivation:
        status: reviewer_to_derive
        decision_owner: independent_monthly_reviewer
        method: select a planning success probability using cited financial-planning
          or retirement-income evidence and the user's confirmed lifetime sufficiency
          objective
        evidence_requirements:
        - verifiable_financial_planning_or_retirement_income_evidence
        - rationale_connected_to_lifetime_sufficiency_objective
        sensitivity_required: true
        base_case_required: true
      retirement_spending_derivation:
        status: reviewer_to_derive
        decision_owner: independent_monthly_reviewer
        method: derive a current-JPY retirement spending base case from confirmed
          essential expenses, observed discretionary bonus use, inflation assumptions,
          and the stated goal; do not present it as a user-confirmed preference
        evidence_requirements:
        - packet_confirmed_current_spending_and_bonus_facts
        - official_or_primary_inflation_and_retirement_spending_evidence
        sensitivity_required: true
        base_case_required: true
      public_pension_derivation:
        status: reviewer_to_derive
        decision_owner: independent_monthly_reviewer
        method: estimate a transparent range and one base case from official Japanese
          pension information and the confirmed employment period; do not claim Nenkin
          Net precision
        evidence_requirements:
        - official_Japanese_pension_sources
        - explicit_limitations_from_missing_wage_history
        sensitivity_required: true
        base_case_required: true
      terminal_asset_floor_derivation:
        status: reviewer_to_derive
        decision_owner: independent_monthly_reviewer
        method: derive a terminal floor that supports longevity and late-life uncertainty
          without inventing an unconfirmed bequest motive
        evidence_requirements:
        - planning_end_age_and_lifetime_sufficiency_objective
        - explicit_late_life_uncertainty_rationale
        sensitivity_required: true
        base_case_required: true
      required_parameters:
      - target_return_pct
      - return_basis
      - horizon_years
      - success_probability_pct
      offer_rule: 必須パラメータは確認済み数値または明示的なreviewer_to_derive契約を持つこと。導出契約がある項目はfinal_review内で根拠、式、感応度と一つのベースケースを提示し、ユーザーへ再質問しない
      primary_objective_fit_rule: 目標収益と成功確率を満たす候補のうち、推定ボラティリティまたは指定下方リスクが最小の候補を最良とする
      offered: true
    maximize_ex_ante_sharpe_ratio:
      label: リスク当たり収益の最大化
      metric: ex_ante_sharpe_ratio
      risk_free_rate_definition: null
      return_basis: null
      horizon_years: null
      required_parameters:
      - risk_free_rate_definition
      - return_basis
      - horizon_years
      primary_objective_fit_rule: 同一の無リスク金利定義、名目/実質区分、期間で計算したex_ante_sharpe_ratioが最大の候補を最良とする
      offered: false
  selection_rule: 同一の資本市場前提で全候補を比較し、選択されたobjective_modelsのprimary_objective_fit_ruleに従って一案を選ぶ
  tie_breaker: 適合度が実質同等なら、推定総コスト、売買回転率、実装複雑性が低い順に選ぶ
candidate_methodology:
  candidate_range:
  - candidate_id: GE100_B0
    global_equity_pct: 100
    bonds_pct: 0
  - candidate_id: GE90_B10
    global_equity_pct: 90
    bonds_pct: 10
  - candidate_id: GE80_B20
    global_equity_pct: 80
    bonds_pct: 20
  - candidate_id: GE70_B30
    global_equity_pct: 70
    bonds_pct: 30
  range_rationale_required: true
  boundary_extension_rule: minimize_risk_for_required_returnで最適候補がGE70_B30境界に達した場合だけ、GE60_B40を一度追加して同じ前提で再比較する
  global_equity_index: null
  bond_index: null
  bond_instrument_type: null
  estimation_period: null
  assumptions_as_of: null
  inflation_assumption_pct: null
  return_basis: null
  tax_cost_treatment: null
  major_drawdown_definition: null
  rebalancing_frequency: null
  required_candidate_fields:
  - candidate_id
  - global_equity_pct
  - bonds_pct
  - expected_nominal_return_pct
  - expected_real_return_pct
  - expected_volatility_pct
  - equity_bond_correlation
  - estimated_major_drawdown_pct
  - primary_objective_fit_value
  - primary_objective_fit_formula
  - assumptions_ref
  - selected
capital_layers:
  household_reserve:
    purpose: emergency_and_confirmed_spending
    strategic_allocation_treatment: exclude_from_long_term_investable_portfolio
  tactical_liquidity:
    purpose: temporary_dip_buying_overlay
    strategic_allocation_treatment: not_a_permanent_asset_class; state explicitly
      how undeployed cash relates to policy numerator and denominator
  long_term_investable_portfolio:
    purpose: strategic_asset_allocation
    strategic_allocation_treatment: determine equity, bond, and other policy weights
      independently within this layer
  prohibited_residual_rule: 必要現金または総現金比率を総資産から控除した残額を、そのまま目標株式額・株式比率として採用しない
  required_views:
  - policy_allocation_within_investable_portfolio
  - household_total_asset_allocation
asset_class_definitions:
  core:
    core_satellite_group: core
    included_in_long_term_investable_portfolio: true
    tradable: true
    household_allocation_category: equity
    cap_treatment: core_policy
  jun_core:
    core_satellite_group: satellite
    included_in_long_term_investable_portfolio: true
    tradable: true
    household_allocation_category: equity
    cap_treatment: counts_toward_total_satellite_and_relevant_theme_caps
  satellite_core:
    core_satellite_group: satellite
    included_in_long_term_investable_portfolio: true
    tradable: true
    household_allocation_category: equity
    cap_treatment: counts_toward_total_satellite_and_relevant_theme_caps
  satellite:
    core_satellite_group: satellite
    included_in_long_term_investable_portfolio: true
    tradable: true
    household_allocation_category: equity
    cap_treatment: counts_toward_total_satellite_and_security_or_theme_caps
  pension:
    core_satellite_group: core
    included_in_long_term_investable_portfolio: true
    tradable: false
    household_allocation_category: equity
    cap_treatment: core_policy; iDeCoは長期配分へ含めるが直接売買不可
  other:
    core_satellite_group: excluded
    included_in_long_term_investable_portfolio: false
    tradable: false
    household_allocation_category: excluded_other
    cap_treatment: excluded_from_policy_allocation_denominator
  liquidity:
    core_satellite_group: excluded
    included_in_long_term_investable_portfolio: false
    tradable: true
    household_allocation_category: cash_pending_layer_assignment
    cap_treatment: split_between_household_reserve_and_tactical_liquidity
allocation_denominators:
  household_total_assets_jpy: 39969688
  long_term_investable_portfolio_jpy: null
  policy_allocation_denominator_jpy: null
  household_reserve_jpy: 2000000
  tactical_liquidity_jpy: null
  excluded_other_assets_jpy: 16483
  ideco_treatment: pension asset_classとして長期運用資産と政策配分分母に含めるが、直接の売買・資金移動対象にはしない
  crypto_treatment:
    current_balance_status: not_present_in_portfolio_snapshot
    snapshot_scope: excluded
    policy_scope: excluded_until_balance_and_classification_are_confirmed
    recurring_contribution_is_not_current_balance: true
  calculation_status: blocked_pending_tactical_liquidity_policy
market_decline_rule:
  status: not_configured
  deployment_target: null
  trigger_index: null
  same_broad_index_required: true
  reference_high_definition: null
  price_basis: null
  lookback_period: null
  fx_treatment: null
  theme_or_sector_decline_is_trigger: false
  unavailable_data_result: unclear
direct_semiconductor_limit:
  status: policy_to_reconsider
  limit_pct: 12
  denominator: household_total_assets_jpy
  priority: 家計用現金と法的・口座制約を満たした後、サテライト総枠・単一テーマ枠のうち最も厳しい上限を優先する
  strategic_review_note: 戦略モードでは12%を不変条件とせず、根拠と他のアクティブリスク上限との整合性を再評価する。新上限はユーザー承認まで提案扱い
user_decision_preferences:
  wants_concrete_policy_recommendation: true
  wants_decision_based_on_investment_theory: true
  does_not_want_unrequested_evaluation_axes: true
  does_not_want_generic_theory_without_decision: true
  expects_independent_reviewer_to_select_one_base_case: true
active_risk_policy:
  satellites_allowed: null
  total_satellite_cap_pct: null
  single_theme_cap_pct: null
  single_security_cap_pct: null
  exceptions: []
  missing_policy_rule: 未設定ならテーマごとに場当たり的な上限を作らず、戦略判断モードで全項目を同時に提案する
approved_policy: null
selected_sources:
- source_id: normalized_snapshot
  source_ref: data/normalized/snapshot_2026_08.yaml
  role: observed_current_portfolio
  as_of: '2026-07-26'
- source_id: financial_assumptions
  source_ref: financial/versions/2026-08-03-v2.yaml
  role: explicit_user_conditions_and_confirmed_contracts
  as_of: '2026-07-26'
- source_id: holding_metadata
  source_ref: holdings/versions/2026-08-02.yaml
  role: confirmed_holding_metadata
  as_of: '2026-07-26'
- source_id: current_recurring_settings
  source_ref: plans/recurring/versions/2026-03-01.yaml
  role: observed_recurring_commitments
  as_of: '2026_08'
- source_id: market_reference_collection
  source_ref: embedded_market_reference_collection
  role: calculated_market_reference_facts
  as_of: '2026-08-03'
- source_id: investment_thesis_records
  source_ref: strategy/theses/index.yaml
  role: documented_investment_story_context
  as_of: '2026-07-26'
confirmed_user_conditions:
- condition_id: financial_condition_01
  statement: '税金、社会保険料、住宅ローン、iDeCo拠出後の月次収入: 374,171円。この値は支出額ではない'
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_02
  statement: 'NISA月次積立額: 100,000円。この値は支出額ではない'
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_03
  statement: '通常月の実質可処分収入: 274,171円。この値は支出額ではない'
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_04
  statement: '月間必須支出額: 250,000円'
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_05
  statement: 通常月の収支はおおむねプラスマイナスゼロ
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_06
  statement: ボーナスは年1回、支給月は[1]、手取りは2,000,000円をやや下回る程度の粗い見積もり
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_07
  statement: ボーナスの使途は固定せず、旅行や裁量支出を実現した黒字の範囲で行う
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_08
  statement: '生活防衛資金の目標額: 2,000,000円'
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_09
  statement: 緊急時は、相場下落中でもオール・カントリー型の投資信託を売却して資金化することを許容する
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_10
  statement: 生活防衛資金とは別の予備費は確保しない
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_11
  statement: 今後1～3年以内の金額・時期が確定した大型支出はない
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_12
  statement: 旅行は予定するが金額・時期は未確定で、ボーナス等の実現黒字から支出する
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_13
  statement: 投資待機資金は市場下落時に使う手段であり、残高維持自体を目的にしない
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_14
  statement: 投資待機資金の目標比率は今回の月次独立レビューから提案を受ける
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_15
  statement: 投資待機資金の買付対象は未定
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_16
  statement: 投資待機資金の発動条件は今回の月次独立レビューから提案を受ける
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_17
  statement: 投資待機資金の投入回数は今回の月次独立レビューから提案を受ける
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: financial_condition_18
  statement: 市場下落時は投資待機資金を使う選択肢を必ず比較する
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
  status: confirmed
- condition_id: approved_direct_semiconductor_max_pct
  statement: 直接半導体エクスポージャーを総資産の12.00%以下へ縮小する方針にユーザが同意済み。売却対象の優先順位は独立レビューから提案を受ける
  source: decisions/2026-08-02_review_questionnaire_answers.md
  as_of: '2026-08-02'
  status: confirmed
  upper_bound_pct: 12
  denominator: household_total_assets_jpy
- condition_id: confirmed_portfolio_execution_clearance
  statement: 未反映注文、出金予定、拘束資金はいずれもない
  source: holdings/versions/2026-08-02.yaml
  as_of: '2026-08-02'
  status: confirmed
- condition_id: observed_core_recurring_settings
  statement: 現在記録されているcore定期積立設定を、実行済み取引ではなく継続中の設定として扱う
  source: plans/recurring/versions/2026-03-01.yaml
  as_of: '2026_08'
  status: observed_setting
- condition_id: observed_pension_recurring_settings
  statement: 現在記録されているiDeCo月次積立設定
  source: plans/recurring/versions/2026-03-01.yaml
  as_of: '2026_08'
  status: observed_setting
- condition_id: observed_crypto_recurring_settings
  statement: 現在記録されている暗号資産週次積立設定
  source: plans/recurring/versions/2026-03-01.yaml
  as_of: '2026_08'
  status: observed_setting
allowed_quantitative_facts:
  cash_requirement_inputs:
    information_priority:
    - confirmed_user_condition
    - observed_packet_fact
    - machine_calculation
    - evidence_based_inference
    - explicit_assumption
    monthly_cash_flow:
      after_tax_social_insurance_mortgage_ideco_income_jpy: 374171
      nisa_monthly_contribution_jpy: 100000
      effective_monthly_disposable_income_jpy: 274171
      monthly_essential_expenses_jpy: 250000
      ordinary_month_balance: approximately_zero
      bonus_income:
        take_home_reference_jpy: 2000000
        amount_qualifier: approximately_slightly_below_reference
        annual_frequency: 1
        payment_months:
        - 1
        certainty: rough_user_estimate
      income_values_are_not_expense_values: true
    emergency_fund:
      target_jpy: 2000000
      status: confirmed_user_target
      monthly_essential_expenses_jpy: 250000
      required_months: 8
      spending_months: 8
      derivation: confirmed_user_target
    near_term_confirmed_expenses:
      amount_jpy: 0
      status: confirmed_no_scheduled_large_expense
    contingency_reserve:
      amount_jpy: 0
      status: confirmed_not_required
    dip_buy_liquidity:
      status: proposal_requested_from_current_review
      target_jpy: null
      target_ratio: null
      amount_calculation_policy: portfolio_snapshot_total_assets_jpy * approved_target_ratio
      decision_owner: current_monthly_independent_review_then_user_approval
      purchase_target: null
      activation_condition: null
      tranche_amount_jpy: null
      tranche_count: null
      minimum_balance_jpy: null
      replenishment_method: null
      unknown_reason: 投資待機資金の目標比率; 投資待機資金の買付対象; 投資待機資金の発動条件; 投資待機資金の投入回数と各回投入額; 投資待機資金の最低残高と補充方法
    result:
      cash_target_status: confirmed_minimum_only
      minimum_confirmed_cash_jpy: 2000000
      total_cash_target_jpy: null
      spending_months: 8
      maximum_cash_target_jpy: null
      derivation_rule: emergency_fund + near_term_confirmed_expenses + explicit_contingency_reserve
        + approved_ratio_based_dip_buy_liquidity
    prohibited_substitutions:
    - 収入、手取り、可処分所得、NISA積立額、通常月の残額を月間必須支出へ代用しない
    - 資産総額から月間支出または月間必須支出を推定しない
    - 生活防衛資金、確定支出、予備費を総資産比率または目標株式比率から逆算しない
    - 投資待機資金の確保・満額維持自体をレビュー目的にしない
    - 市場下落時に投資待機資金を使う選択肢を省略しない
  portfolio_totals:
    currency_base: JPY
    total_assets_jpy: 39969688
    liquidity_jpy: 13622664
    liquidity_pct: 34.08
    equity_like_jpy: 26330541
    equity_like_pct: 65.88
    core_like_jpy: 14786518
    core_like_pct: 36.99
    satellite_like_jpy: 11544020
    satellite_like_pct: 28.88
    classification_note: equity_likeはliquidity/other以外、core_likeはcore+pension、satellite_likeはjun_core+satellite_core+satelliteを機械集計
  category_totals:
  - category: ポイント
    market_value_jpy: 16483
    portfolio_pct: 0.04
  - category: 年金
    market_value_jpy: 4063372
    portfolio_pct: 10.17
  - category: 投資信託
    market_value_jpy: 16920468
    portfolio_pct: 42.33
  - category: 株式（現物）
    market_value_jpy: 5346701
    portfolio_pct: 13.38
  - category: 預金・現金
    market_value_jpy: 13622664
    portfolio_pct: 34.08
  asset_class_allocations:
  - asset_class: core
    market_value_jpy: 10723146
    portfolio_pct: 26.83
  - asset_class: jun_core
    market_value_jpy: 2880473
    portfolio_pct: 7.21
  - asset_class: liquidity
    market_value_jpy: 13622664
    portfolio_pct: 34.08
  - asset_class: other
    market_value_jpy: 16483
    portfolio_pct: 0.04
  - asset_class: pension
    market_value_jpy: 4063372
    portfolio_pct: 10.17
  - asset_class: satellite
    market_value_jpy: 1099654
    portfolio_pct: 2.75
  - asset_class: satellite_core
    market_value_jpy: 7563893
    portfolio_pct: 18.92
  holdings:
  - symbol: LIQUIDITY
    name: 預金・現金
    human_label: 預金・現金
    asset_class: liquidity
    source_category: 預金・現金
    institution: null
    account_type: null
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 13622664
    profit_loss_jpy: null
    currency: JPY
    portfolio_pct: 34.08
  - symbol: '7203'
    name: トヨタ自動車
    human_label: トヨタ自動車
    asset_class: jun_core
    source_category: 株式（現物）
    institution: 野村証券
    account_type: null
    quantity: 800
    avg_cost: 532
    current_price: 2897
    market_value_jpy: 2317600
    profit_loss_jpy: 1892000
    currency: JPY
    portfolio_pct: 5.8
  - symbol: '9444'
    name: トーシンホールディングス
    human_label: トーシンホールディングス
    asset_class: satellite
    source_category: 株式（現物）
    institution: 野村証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 1500
    avg_cost: 628
    current_price: 233
    market_value_jpy: 349500
    profit_loss_jpy: -592500
    currency: JPY
    portfolio_pct: 0.87
  - symbol: '2353'
    name: 日本駐車場開発
    human_label: 日本駐車場開発
    asset_class: satellite
    source_category: 株式（現物）
    institution: 野村証券
    account_type: 一般口座
    quantity: 100
    avg_cost: 265
    current_price: 258
    market_value_jpy: 25800
    profit_loss_jpy: -700
    currency: JPY
    portfolio_pct: 0.06
  - symbol: '7201'
    name: 日産自動車
    human_label: 日産自動車
    asset_class: satellite
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 100
    avg_cost: 368
    current_price: 322
    market_value_jpy: 32220
    profit_loss_jpy: -4535
    currency: JPY
    portfolio_pct: 0.08
  - symbol: SMH
    name: ヴァンエック・半導体株ETF
    human_label: ヴァンエック・半導体株ETF
    asset_class: satellite_core
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 1
    avg_cost: 369.63
    current_price: 561.19
    market_value_jpy: 91950
    profit_loss_jpy: 31387
    currency: USD
    portfolio_pct: 0.23
  - symbol: PLTR
    name: パランティア・テクノロジーズ
    human_label: パランティア・テクノロジーズ
    asset_class: satellite
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 11
    avg_cost: 151.22
    current_price: 122.92
    market_value_jpy: 221544
    profit_loss_jpy: -51013
    currency: USD
    portfolio_pct: 0.55
  - symbol: CIBR
    name: ファーストトラスト ナスダック サイバーセキュリティ ETF
    human_label: ファーストトラスト ナスダック サイバーセキュリティ ETF
    asset_class: satellite_core
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 88
    avg_cost: 76.66
    current_price: 88.4
    market_value_jpy: 1274621
    profit_loss_jpy: 169319
    currency: USD
    portfolio_pct: 3.19
  - symbol: MSFT
    name: マイクロソフト
    human_label: マイクロソフト
    asset_class: jun_core
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 9
    avg_cost: 398.74
    current_price: 381.7
    market_value_jpy: 562873
    profit_loss_jpy: -25123
    currency: USD
    portfolio_pct: 1.41
  - symbol: URA
    name: グローバルX ウラニウム ETF
    human_label: グローバルX ウラニウム ETF
    asset_class: satellite
    source_category: 株式（現物）
    institution: 楽天証券
    account_type: null
    quantity: 72
    avg_cost: 46.1
    current_price: 39.89
    market_value_jpy: 470590
    profit_loss_jpy: -73250
    currency: USD
    portfolio_pct: 1.18
  - symbol: NISSEI_SOX_1
    name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    asset_class: satellite_core
    source_category: 投資信託
    institution: 楽天証券
    account_type: 特定口座（源泉徴収あり）
    quantity: 860960
    avg_cost: 15802
    current_price: 48545
    market_value_jpy: 4179530
    profit_loss_jpy: 2819073
    currency: JPY
    portfolio_pct: 10.46
  - symbol: NISSEI_SOX_2
    name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    asset_class: satellite_core
    source_category: 投資信託
    institution: 楽天証券
    account_type: NISA（2024年以降・枠区分未確認）
    quantity: 415654
    avg_cost: 14435
    current_price: 48545
    market_value_jpy: 2017792
    profit_loss_jpy: 1417792
    currency: JPY
    portfolio_pct: 5.05
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_1
    name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    human_label: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 1084992
    avg_cost: 14286
    current_price: 19705
    market_value_jpy: 2137977
    profit_loss_jpy: 587977
    currency: JPY
    portfolio_pct: 5.35
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_2
    name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    human_label: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 846995
    avg_cost: 17710
    current_price: 19705
    market_value_jpy: 1669004
    profit_loss_jpy: 169003
    currency: JPY
    portfolio_pct: 4.18
  - symbol: RAKUTEN_PLUS_SP500
    name: 楽天・プラス・S&P500インデックス・ファンド(楽天・プラス・S&P500)
    human_label: 楽天・プラス・S&P500インデックス・ファンド(楽天・プラス・S&P500)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 106530
    avg_cost: 11715
    current_price: 19875
    market_value_jpy: 211728
    profit_loss_jpy: 86928
    currency: JPY
    portfolio_pct: 0.53
  - symbol: EMAXIS_SLIM_SP500_1
    name: eMAXIS Slim 米国株式(S&P500)
    human_label: eMAXIS Slim 米国株式(S&P500)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 337199
    avg_cost: 42349
    current_price: 44669
    market_value_jpy: 1506234
    profit_loss_jpy: 78234
    currency: JPY
    portfolio_pct: 3.77
  - symbol: EMAXIS_SLIM_SP500_2
    name: eMAXIS Slim 米国株式(S&P500)
    human_label: eMAXIS Slim 米国株式(S&P500)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 408710
    avg_cost: 33398
    current_price: 44669
    market_value_jpy: 1825667
    profit_loss_jpy: 460667
    currency: JPY
    portfolio_pct: 4.57
  - symbol: EMAXIS_SLIM_SP500_3
    name: eMAXIS Slim 米国株式(S&P500)
    human_label: eMAXIS Slim 米国株式(S&P500)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 228995
    avg_cost: 39302
    current_price: 44669
    market_value_jpy: 1022898
    profit_loss_jpy: 122898
    currency: JPY
    portfolio_pct: 2.56
  - symbol: EMAXIS_SLIM_ALL_COUNTRY
    name: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)
    human_label: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)
    asset_class: core
    source_category: 投資信託
    institution: 楽天証券
    account_type: null
    quantity: 614397
    avg_cost: 36491
    current_price: 38243
    market_value_jpy: 2349638
    profit_loss_jpy: 107639
    currency: JPY
    portfolio_pct: 5.88
  - symbol: PENSION_EMAXIS_SLIM_ALL_COUNTRY
    name: eMAXIS Slim 全世界株式(オール・カントリー)
    human_label: eMAXIS Slim 全世界株式(オール・カントリー)
    asset_class: pension
    source_category: 年金
    institution: null
    account_type: iDeCo
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 4063372
    profit_loss_jpy: 722677
    currency: JPY
    portfolio_pct: 10.17
  - symbol: POINTS_MILES
    name: ポイント
    human_label: ポイント
    asset_class: other
    source_category: ポイント
    institution: null
    account_type: null
    quantity: null
    avg_cost: null
    current_price: null
    market_value_jpy: 16483
    profit_loss_jpy: null
    currency: JPY
    portfolio_pct: 0.04
  security_story_review_targets:
  - symbol: '2353'
    name: 日本駐車場開発
    instrument_type: individual_stock
    thesis_recorded: false
    thesis_id: null
    thesis_status: missing
    thesis_summary: null
    invalidation_conditions: []
    review_priority: high
    thesis_source_ref: null
    user_holding_reason: 誤って一般口座で購入し、税務処理の手間を避けたい。少額保有
    user_disposition: sell_when_at_a_loss_preferred
    user_sell_condition: 含み損の状態での売却を希望
    holding_metadata_confirmed_at: '2026-08-02'
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: ユーザの現在の保有意図を制約として、最新の一次情報から暫定ストーリーを再構成し、売買判断を示す
  - symbol: '7201'
    name: 日産自動車
    instrument_type: individual_stock
    thesis_recorded: false
    thesis_id: null
    thesis_status: missing
    thesis_summary: null
    invalidation_conditions: []
    review_priority: high
    thesis_source_ref: null
    user_holding_reason: 趣味で保有していたが、現在は関心を失っている
    user_disposition: sell_allowed
    user_sell_condition: 売却してよい
    holding_metadata_confirmed_at: '2026-08-02'
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: ユーザの現在の保有意図を制約として、最新の一次情報から暫定ストーリーを再構成し、売買判断を示す
  - symbol: '7203'
    name: トヨタ自動車
    instrument_type: individual_stock
    thesis_recorded: false
    thesis_id: null
    thesis_status: missing
    thesis_summary: null
    invalidation_conditions: []
    review_priority: high
    thesis_source_ref: null
    user_holding_reason: 祖父から相続した株式をそのまま保有。トヨタ株としての積極的な保有理由はない
    user_disposition: sell_if_rationally_justified
    user_sell_condition: 合理的な理由があれば売却してよい
    holding_metadata_confirmed_at: '2026-08-02'
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: ユーザの現在の保有意図を制約として、最新の一次情報から暫定ストーリーを再構成し、売買判断を示す
  - symbol: '9444'
    name: トーシンホールディングス
    instrument_type: individual_stock
    thesis_recorded: false
    thesis_id: null
    thesis_status: missing
    thesis_summary: null
    invalidation_conditions: []
    review_priority: high
    thesis_source_ref: null
    user_holding_reason: 考慮不要。継続保有理由はない
    user_disposition: sell_requested
    user_sell_condition: 売却提案を希望
    holding_metadata_confirmed_at: '2026-08-02'
    sell_order_available: true
    unreflected_orders: false
    planned_withdrawals: false
    restricted_funds: false
    required_assessment: ユーザの現在の保有意図を制約として、最新の一次情報から暫定ストーリーを再構成し、売買判断を示す
  - symbol: CIBR
    name: ファーストトラスト ナスダック サイバーセキュリティ ETF
    instrument_type: etf
    thesis_recorded: true
    thesis_id: persistent_cybersecurity_spending
    thesis_status: inherited_pending_review
    thesis_summary: サイバーセキュリティ支出は構造的に維持・拡大するという仮説。
    invalidation_conditions:
    - 支出成長の鈍化
    - バリュエーション過熱後の長期低迷
    review_priority: medium
    thesis_source_ref: strategy/theses/cibr.yaml
    user_holding_reason: null
    user_disposition: null
    user_sell_condition: null
    holding_metadata_confirmed_at: null
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: 既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する
  - symbol: SMH
    name: ヴァンエック・半導体株ETF
    instrument_type: etf
    thesis_recorded: true
    thesis_id: semiconductor_structural_growth_2026-08-02
    thesis_status: active
    thesis_summary: 半導体需要と産業の価値プールは長期的に拡大する可能性が高い
    invalidation_conditions:
    - AI設備投資縮小時に非AI用途から十分な代替需要が確認できない
    - 過剰供給でmargin、free cash flow、ROICがフルサイクルで悪化する
    - 指数集中度上昇により産業全体への分散投資ではなくなる
    review_priority: medium
    thesis_source_ref: strategy/theses/semiconductor_2026-08-02.yaml
    user_holding_reason: null
    user_disposition: null
    user_sell_condition: null
    holding_metadata_confirmed_at: null
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: 既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する
  - symbol: URA
    name: グローバルX ウラニウム ETF
    instrument_type: etf
    thesis_recorded: true
    thesis_id: nuclear_revival
    thesis_status: inherited_pending_review
    thesis_summary: '脱炭素、電力需要増、エネルギー安全保障を背景に、 原子力需要が中長期で再評価されるという仮説。

      '
    invalidation_conditions:
    - 炭素回収技術の量産化・低コスト化
    - 再エネ＋蓄電の経済性改善
    - 政策転換
    - 原子力新設の採算悪化
    review_priority: high
    thesis_source_ref: strategy/theses/ura.yaml
    user_holding_reason: null
    user_disposition: null
    user_sell_condition: null
    holding_metadata_confirmed_at: null
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: 既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する
  - symbol: MSFT
    name: マイクロソフト
    instrument_type: individual_stock
    thesis_recorded: true
    thesis_id: hyperscaler_ai_platform_compounding
    thesis_status: inherited_pending_review
    thesis_summary: 'クラウド・AI基盤・企業ソフトウェアの複合優位により、 長期で利益成長が継続するという仮説。

      '
    invalidation_conditions:
    - AI投資回収の停滞
    - 規制強化
    - 競争優位の低下
    review_priority: medium
    thesis_source_ref: strategy/theses/msft.yaml
    user_holding_reason: null
    user_disposition: null
    user_sell_condition: null
    holding_metadata_confirmed_at: null
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: 既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する
  - symbol: PLTR
    name: パランティア・テクノロジーズ
    instrument_type: individual_stock
    thesis_recorded: true
    thesis_id: defense_ai_gov_software_scaling
    thesis_status: inherited_pending_review
    thesis_summary: '政府・防衛・大企業向けの高付加価値ソフトウェア需要が継続し、 AI時代のプラットフォーム企業として拡大するという仮説。

      '
    invalidation_conditions:
    - 政府需要の鈍化
    - 競争激化
    - 収益化の鈍化
    review_priority: medium
    thesis_source_ref: strategy/theses/pltr.yaml
    user_holding_reason: null
    user_disposition: null
    user_sell_condition: null
    holding_metadata_confirmed_at: null
    sell_order_available: null
    unreflected_orders: null
    planned_withdrawals: null
    restricted_funds: null
    required_assessment: 既存仮説を最新の一次情報と照合し、健全性と売買判断を記録する
  thematic_fund_review_targets:
  - theme_review_id: nissei_sox_index_fund
    product_name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    member_symbols:
    - NISSEI_SOX_1
    - NISSEI_SOX_2
    story_review_scope: product_and_underlying_index_once
    underlying_index: null
    underlying_index_status: requires_primary_source_research
    account_lot_review_scope: each_member_separately
    account_lots:
    - symbol: NISSEI_SOX_1
      human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>（特定口座（源泉徴収あり））
      account_type: 特定口座（源泉徴収あり）
      market_value_jpy: 4179530
      profit_loss_jpy: 2819073
    - symbol: NISSEI_SOX_2
      human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>（NISA（2024年以降・枠区分未確認））
      account_type: NISA（2024年以降・枠区分未確認）
      market_value_jpy: 2017792
      profit_loss_jpy: 1417792
    required_assessment: 商品・指数ストーリーを一度評価し、口座・ロットごとの税務・執行判断を分離する
  same_product_account_groups:
  - product_name: eMAXIS Slim 米国株式(S&P500)
    human_label: eMAXIS Slim 米国株式(S&P500)（口座区分未確認の3明細）
    symbols:
    - EMAXIS_SLIM_SP500_1
    - EMAXIS_SLIM_SP500_2
    - EMAXIS_SLIM_SP500_3
    account_separation_status: unverified
    members:
    - symbol: EMAXIS_SLIM_SP500_1
      human_label: eMAXIS Slim 米国株式(S&P500)（評価額1,506,234円の明細・口座区分未確認）
      institution: 楽天証券
      account_type: null
      market_value_jpy: 1506234
      avg_cost: 42349
      profit_loss_jpy: 78234
    - symbol: EMAXIS_SLIM_SP500_2
      human_label: eMAXIS Slim 米国株式(S&P500)（評価額1,825,667円の明細・口座区分未確認）
      institution: 楽天証券
      account_type: null
      market_value_jpy: 1825667
      avg_cost: 33398
      profit_loss_jpy: 460667
    - symbol: EMAXIS_SLIM_SP500_3
      human_label: eMAXIS Slim 米国株式(S&P500)（評価額1,022,898円の明細・口座区分未確認）
      institution: 楽天証券
      account_type: null
      market_value_jpy: 1022898
      avg_cost: 39302
      profit_loss_jpy: 122898
    decision_note: 経済的エクスポージャーは合算して評価するが、売却・移管・一本化は口座区分と税引後結果を確認してロット単位で判断する
  - product_name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
    symbols:
    - NISSEI_SOX_1
    - NISSEI_SOX_2
    account_separation_status: separate_accounts_confirmed
    members:
    - symbol: NISSEI_SOX_1
      human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>（特定口座（源泉徴収あり））
      institution: 楽天証券
      account_type: 特定口座（源泉徴収あり）
      market_value_jpy: 4179530
      avg_cost: 15802
      profit_loss_jpy: 2819073
    - symbol: NISSEI_SOX_2
      human_label: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>（NISA（2024年以降・枠区分未確認））
      institution: 楽天証券
      account_type: NISA（2024年以降・枠区分未確認）
      market_value_jpy: 2017792
      avg_cost: 14435
      profit_loss_jpy: 1417792
    decision_note: 経済的エクスポージャーは合算して評価するが、売却・移管・一本化は口座区分と税引後結果を確認してロット単位で判断する
  - product_name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
    human_label: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)（口座区分未確認の2明細）
    symbols:
    - RAKUTEN_PLUS_ALL_COUNTRY_1
    - RAKUTEN_PLUS_ALL_COUNTRY_2
    account_separation_status: unverified
    members:
    - symbol: RAKUTEN_PLUS_ALL_COUNTRY_1
      human_label: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)（評価額2,137,977円の明細・口座区分未確認）
      institution: 楽天証券
      account_type: null
      market_value_jpy: 2137977
      avg_cost: 14286
      profit_loss_jpy: 587977
    - symbol: RAKUTEN_PLUS_ALL_COUNTRY_2
      human_label: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)（評価額1,669,004円の明細・口座区分未確認）
      institution: 楽天証券
      account_type: null
      market_value_jpy: 1669004
      avg_cost: 17710
      profit_loss_jpy: 169003
    decision_note: 経済的エクスポージャーは合算して評価するが、売却・移管・一本化は口座区分と税引後結果を確認してロット単位で判断する
  market_references:
  - symbol: CIBR
    reference_symbol: CIBR
    as_of: '2026-08-03'
    currency: USD
    current_price: 92.015
    mean_close_20d: 89.8808
    recent_high_21d: 94.73
    recent_high_63d: 94.73
    return_21d_pct: 1.48
    return_63d_pct: 33.82
    drawdown_from_21d_high_pct: -2.87
    drawdown_from_63d_high_pct: -2.87
  - symbol: URA
    reference_symbol: URA
    as_of: '2026-08-03'
    currency: USD
    current_price: 39.05
    mean_close_20d: 41.5937
    recent_high_21d: 43.88
    recent_high_63d: 58.26
    return_21d_pct: -9.67
    return_63d_pct: -30.07
    drawdown_from_21d_high_pct: -11.01
    drawdown_from_63d_high_pct: -32.97
  - symbol: PLTR
    reference_symbol: PLTR
    as_of: '2026-08-03'
    currency: USD
    current_price: 124.94
    mean_close_20d: 125.443
    recent_high_21d: 134.85
    recent_high_63d: 160.65
    return_21d_pct: -3.37
    return_63d_pct: -13.28
    drawdown_from_21d_high_pct: -7.35
    drawdown_from_63d_high_pct: -22.23
  - symbol: MSFT
    reference_symbol: MSFT
    as_of: '2026-08-03'
    currency: USD
    current_price: 485.194
    mean_close_20d: 392.3805
    recent_high_21d: 485.194
    recent_high_63d: 485.194
    return_21d_pct: 24.25
    return_63d_pct: 17.07
    drawdown_from_21d_high_pct: 0
    drawdown_from_63d_high_pct: 0
  - symbol: SMH
    reference_symbol: SMH
    as_of: '2026-08-03'
    currency: USD
    current_price: 525.75
    mean_close_20d: 587.246
    recent_high_21d: 611.03
    recent_high_63d: 668.91
    return_21d_pct: -11.23
    return_63d_pct: 3.12
    drawdown_from_21d_high_pct: -13.96
    drawdown_from_63d_high_pct: -21.4
  - symbol: USDJPY
    reference_symbol: USDJPY=X
    as_of: '2026-08-03'
    currency: JPY
    current_price: 156.403
    mean_close_20d: 162.168
    recent_high_21d: 163.864
    recent_high_63d: 163.864
    return_21d_pct: -3.13
    return_63d_pct: -0.81
    drawdown_from_21d_high_pct: -4.55
    drawdown_from_63d_high_pct: -4.55
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_1
    reference_symbol: VT
    as_of: '2026-08-03'
    currency: USD
    current_price: 156.37
    mean_close_20d: 155.6353
    recent_high_21d: 157.81
    recent_high_63d: 159.35
    return_21d_pct: 0.13
    return_63d_pct: 3.26
    drawdown_from_21d_high_pct: -0.91
    drawdown_from_63d_high_pct: -1.87
  - symbol: RAKUTEN_PLUS_ALL_COUNTRY_2
    reference_symbol: VT
    as_of: '2026-08-03'
    currency: USD
    current_price: 156.37
    mean_close_20d: 155.6353
    recent_high_21d: 157.81
    recent_high_63d: 159.35
    return_21d_pct: 0.13
    return_63d_pct: 3.26
    drawdown_from_21d_high_pct: -0.91
    drawdown_from_63d_high_pct: -1.87
  - symbol: RAKUTEN_PLUS_SP500
    reference_symbol: VOO
    as_of: '2026-08-03'
    currency: USD
    current_price: 690.33
    mean_close_20d: 684.0323
    recent_high_21d: 693.86
    recent_high_63d: 698.26
    return_21d_pct: 0.8
    return_63d_pct: 4.2
    drawdown_from_21d_high_pct: -0.51
    drawdown_from_63d_high_pct: -1.14
  - symbol: EMAXIS_SLIM_SP500_1
    reference_symbol: VOO
    as_of: '2026-08-03'
    currency: USD
    current_price: 690.33
    mean_close_20d: 684.0323
    recent_high_21d: 693.86
    recent_high_63d: 698.26
    return_21d_pct: 0.8
    return_63d_pct: 4.2
    drawdown_from_21d_high_pct: -0.51
    drawdown_from_63d_high_pct: -1.14
  - symbol: EMAXIS_SLIM_SP500_2
    reference_symbol: VOO
    as_of: '2026-08-03'
    currency: USD
    current_price: 690.33
    mean_close_20d: 684.0323
    recent_high_21d: 693.86
    recent_high_63d: 698.26
    return_21d_pct: 0.8
    return_63d_pct: 4.2
    drawdown_from_21d_high_pct: -0.51
    drawdown_from_63d_high_pct: -1.14
  - symbol: EMAXIS_SLIM_SP500_3
    reference_symbol: VOO
    as_of: '2026-08-03'
    currency: USD
    current_price: 690.33
    mean_close_20d: 684.0323
    recent_high_21d: 693.86
    recent_high_63d: 698.26
    return_21d_pct: 0.8
    return_63d_pct: 4.2
    drawdown_from_21d_high_pct: -0.51
    drawdown_from_63d_high_pct: -1.14
  - symbol: EMAXIS_SLIM_ALL_COUNTRY
    reference_symbol: ACWI
    as_of: '2026-08-03'
    currency: USD
    current_price: 156.64
    mean_close_20d: 155.768
    recent_high_21d: 157.97
    recent_high_63d: 159.97
    return_21d_pct: 0.31
    return_63d_pct: 3.28
    drawdown_from_21d_high_pct: -0.84
    drawdown_from_63d_high_pct: -2.08
  concentration_metrics:
    largest_positions:
    - symbol: NISSEI_SOX_1
      name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
      market_value_jpy: 4179530
      portfolio_pct: 10.46
    - symbol: PENSION_EMAXIS_SLIM_ALL_COUNTRY
      name: eMAXIS Slim 全世界株式(オール・カントリー)
      market_value_jpy: 4063372
      portfolio_pct: 10.17
    - symbol: EMAXIS_SLIM_ALL_COUNTRY
      name: eMAXIS Slim 全世界株式(オール・カントリー)(オルカン)
      market_value_jpy: 2349638
      portfolio_pct: 5.88
    - symbol: '7203'
      name: トヨタ自動車
      market_value_jpy: 2317600
      portfolio_pct: 5.8
    - symbol: RAKUTEN_PLUS_ALL_COUNTRY_1
      name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
      market_value_jpy: 2137977
      portfolio_pct: 5.35
    - symbol: NISSEI_SOX_2
      name: ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>
      market_value_jpy: 2017792
      portfolio_pct: 5.05
    - symbol: EMAXIS_SLIM_SP500_2
      name: eMAXIS Slim 米国株式(S&P500)
      market_value_jpy: 1825667
      portfolio_pct: 4.57
    - symbol: RAKUTEN_PLUS_ALL_COUNTRY_2
      name: 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー)
      market_value_jpy: 1669004
      portfolio_pct: 4.18
    - symbol: EMAXIS_SLIM_SP500_1
      name: eMAXIS Slim 米国株式(S&P500)
      market_value_jpy: 1506234
      portfolio_pct: 3.77
    - symbol: CIBR
      name: ファーストトラスト ナスダック サイバーセキュリティ ETF
      market_value_jpy: 1274621
      portfolio_pct: 3.19
    direct_semiconductor_exposure_jpy: 6289272
    direct_semiconductor_exposure_pct: 15.74
    indirect_ai_infra_exposure_jpy: 562873
    indirect_ai_infra_exposure_pct: 1.41
    exposure_components:
    - symbol: SMH
      market_value_jpy: 91950
      portfolio_pct: null
      included_in_direct_semiconductor_exposure: true
      included_in_indirect_ai_infra_exposure: false
    - symbol: MSFT
      market_value_jpy: 562873
      portfolio_pct: null
      included_in_direct_semiconductor_exposure: false
      included_in_indirect_ai_infra_exposure: true
    - symbol: NISSEI_SOX_1
      market_value_jpy: 4179530
      portfolio_pct: null
      included_in_direct_semiconductor_exposure: true
      included_in_indirect_ai_infra_exposure: false
    - symbol: NISSEI_SOX_2
      market_value_jpy: 2017792
      portfolio_pct: null
      included_in_direct_semiconductor_exposure: true
      included_in_indirect_ai_infra_exposure: false
    calculation_note: 現在評価額を総資産で割った機械計算。目標値、上限、売買提案は含まない
  recurring_commitments:
    core_monthly_total_jpy: 100000
    core_monthly_plans:
    - day_of_month: 8
      fund_name: eMAXIS Slim 全世界株式（オール・カントリー）
      amount_jpy: 50000
      settlement_type: クレジットカード決済
      account_type: NISAつみたて投資枠
      distribution_course: 再投資型
    - day_of_month: 8
      fund_name: eMAXIS Slim 米国株式（S&P500）
      amount_jpy: 50000
      settlement_type: クレジットカード決済
      account_type: NISAつみたて投資枠
      distribution_course: 再投資型
    pension_monthly_total_jpy: 55000
    pension_monthly_plans:
    - symbol: IDECO_ALL_COUNTRY
      fund_name: eMAXIS Slim 全世界株式（オール・カントリー）
      amount_jpy_per_month: 55000
      account_type: iDeCo
      asset_class: pension
    crypto_weekly_total_jpy: 4000
    crypto_weekly_plans:
    - symbol: BTC
      amount_jpy_per_week: 2000
    - symbol: ETH
      amount_jpy_per_week: 2000
    nisa_growth_quota_status: exhausted
    source: plans/recurring/versions/2026-03-01.yaml
    as_of: '2026_08'
  data_quality_notes:
    ocr_notes:
    - スクリーンショット内に取得日が見えないため、セッション日付 2026-07-26 を snapshot_date とした。
    - 預金・現金とポイントは明細が画像に含まれないため、カテゴリ合計だけを集約holdingとして記録した。内訳は前月値から補完していない。
    - 米国上場銘柄のcurrent_priceは画面表示値を記録し、通貨は銘柄と前月スナップショットの継続性からUSDとした。評価額と評価損益は画面表示どおりJPYで記録した。
    - 株式（現物）の明細表示値合計は 5,346,698円で、カテゴリ合計 5,346,701円との差は -3円。Money Forwardの表示丸め差として扱う。
    validation_notes:
    - カテゴリ合計の合算は総資産 39,969,688円 と一致。
    - 投資信託の明細合計はカテゴリ合計 16,920,468円 と一致。
    - 年金は詳細1行が確認でき、取得価額 3,340,695円、現在価値 4,063,372円、評価損益 722,677円、評価損益率 21.63%。
    - 株式（現物）の明細合計とカテゴリ合計の3円差は許容範囲内の表示丸め差として分離した。
    - 前月スナップショットとの差分は保有状態の変化としてのみ記録し、注文、約定、入出金または積立実行を示す取引実績には変換しない。
    validation_findings:
    - code: missing_account_type
      severity: warning
      message: '7203: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - '7203'
    - code: missing_account_type
      severity: warning
      message: '7201: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - '7201'
    - code: missing_account_type
      severity: warning
      message: 'SMH: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - SMH
    - code: missing_account_type
      severity: warning
      message: 'PLTR: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - PLTR
    - code: missing_account_type
      severity: warning
      message: 'CIBR: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - CIBR
    - code: missing_account_type
      severity: warning
      message: 'MSFT: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - MSFT
    - code: missing_account_type
      severity: warning
      message: 'URA: account_type is unknown. Do not select a sale lot, consolidate
        same-name holdings, or optimize taxes until the account is verified.'
      related_symbols:
      - URA
    - code: missing_account_type
      severity: warning
      message: 'RAKUTEN_PLUS_ALL_COUNTRY_1: account_type is unknown. Do not select
        a sale lot, consolidate same-name holdings, or optimize taxes until the account
        is verified.'
      related_symbols:
      - RAKUTEN_PLUS_ALL_COUNTRY_1
    - code: missing_account_type
      severity: warning
      message: 'RAKUTEN_PLUS_ALL_COUNTRY_2: account_type is unknown. Do not select
        a sale lot, consolidate same-name holdings, or optimize taxes until the account
        is verified.'
      related_symbols:
      - RAKUTEN_PLUS_ALL_COUNTRY_2
    - code: missing_account_type
      severity: warning
      message: 'RAKUTEN_PLUS_SP500: account_type is unknown. Do not select a sale
        lot, consolidate same-name holdings, or optimize taxes until the account is
        verified.'
      related_symbols:
      - RAKUTEN_PLUS_SP500
    - code: missing_account_type
      severity: warning
      message: 'EMAXIS_SLIM_SP500_1: account_type is unknown. Do not select a sale
        lot, consolidate same-name holdings, or optimize taxes until the account is
        verified.'
      related_symbols:
      - EMAXIS_SLIM_SP500_1
    - code: missing_account_type
      severity: warning
      message: 'EMAXIS_SLIM_SP500_2: account_type is unknown. Do not select a sale
        lot, consolidate same-name holdings, or optimize taxes until the account is
        verified.'
      related_symbols:
      - EMAXIS_SLIM_SP500_2
    - code: missing_account_type
      severity: warning
      message: 'EMAXIS_SLIM_SP500_3: account_type is unknown. Do not select a sale
        lot, consolidate same-name holdings, or optimize taxes until the account is
        verified.'
      related_symbols:
      - EMAXIS_SLIM_SP500_3
    - code: missing_account_type
      severity: warning
      message: 'EMAXIS_SLIM_ALL_COUNTRY: account_type is unknown. Do not select a
        sale lot, consolidate same-name holdings, or optimize taxes until the account
        is verified.'
      related_symbols:
      - EMAXIS_SLIM_ALL_COUNTRY
    - code: same_product_cross_account_split
      severity: info
      message: 'ニッセイSOX指数インデックスファンド(米国半導体株)<購入・換金手数料なし>: same product is held across
        different account types (特定口座（源泉徴収あり）, NISA（2024年以降・枠区分未確認）). This is an account-level
        split and must not be labeled redundant duplication.'
      related_symbols:
      - NISSEI_SOX_1
      - NISSEI_SOX_2
    - code: account_separation_unverified
      severity: warning
      message: '楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー): same product appears
        in multiple rows but one or more account_type values are unknown. Treat the
        rows as potentially intentional NISA/taxable separation, not redundant duplication.'
      related_symbols:
      - RAKUTEN_PLUS_ALL_COUNTRY_1
      - RAKUTEN_PLUS_ALL_COUNTRY_2
    - code: account_separation_unverified
      severity: warning
      message: 'eMAXIS Slim 米国株式(S&P500): same product appears in multiple rows but
        one or more account_type values are unknown. Treat the rows as potentially
        intentional NISA/taxable separation, not redundant duplication.'
      related_symbols:
      - EMAXIS_SLIM_SP500_1
      - EMAXIS_SLIM_SP500_2
      - EMAXIS_SLIM_SP500_3
    - code: missing_quantity
      severity: info
      message: Holding LIQUIDITY is missing quantity; stored as null.
      related_symbols: []
    - code: missing_avg_cost
      severity: info
      message: Holding LIQUIDITY is missing avg_cost; stored as null.
      related_symbols: []
    - code: missing_current_price
      severity: info
      message: Holding LIQUIDITY is missing current_price; stored as null.
      related_symbols: []
    - code: missing_quantity
      severity: info
      message: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing quantity; stored
        as null.
      related_symbols: []
    - code: missing_avg_cost
      severity: info
      message: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing avg_cost; stored
        as null.
      related_symbols: []
    - code: missing_current_price
      severity: info
      message: Holding PENSION_EMAXIS_SLIM_ALL_COUNTRY is missing current_price; stored
        as null.
      related_symbols: []
    - code: missing_quantity
      severity: info
      message: Holding POINTS_MILES is missing quantity; stored as null.
      related_symbols: []
    - code: missing_avg_cost
      severity: info
      message: Holding POINTS_MILES is missing avg_cost; stored as null.
      related_symbols: []
    - code: missing_current_price
      severity: info
      message: Holding POINTS_MILES is missing current_price; stored as null.
      related_symbols: []
unknown_information:
- item: financial_unknown_01
  reason: ボーナスの正確な手取り額
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_02
  reason: 未計画旅行の金額と時期
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_03
  reason: 投資待機資金の目標比率
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_04
  reason: 投資待機資金の買付対象
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_05
  reason: 投資待機資金の発動条件
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_06
  reason: 投資待機資金の投入回数と各回投入額
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_07
  reason: 投資待機資金の最低残高と補充方法
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_08
  reason: 公的年金の個人別確定見込額
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: financial_unknown_09
  reason: 相続の本人取り分、実際の時期および税引後額
  source: financial/versions/2026-08-03-v2.yaml
  as_of: '2026-07-26'
- item: liquidity_target_jpy
  reason: 正規化スナップショットに現金目標額が記録されていない
  source: normalized_snapshot
  as_of: '2026-07-26'
- item: liquidity_account_breakdown
  reason: 現金は集約値で、口座別の利用可能額がパケットにない
  source: normalized_snapshot
  as_of: '2026-07-26'
- item: tradable_holding_account_types
  reason: '売買可能資産の口座区分が未確認: 7201, 7203, CIBR, EMAXIS_SLIM_ALL_COUNTRY, EMAXIS_SLIM_SP500_1,
    EMAXIS_SLIM_SP500_2, EMAXIS_SLIM_SP500_3, MSFT, PLTR, RAKUTEN_PLUS_ALL_COUNTRY_1,
    RAKUTEN_PLUS_ALL_COUNTRY_2, RAKUTEN_PLUS_SP500, SMH, URA。口座区分を確認するまで、売却ロット、一本化、口座間移管を確定しない'
  source: normalized_snapshot
  as_of: '2026-07-26'
- item: same_product_account_separation
  reason: '同一商品の複数明細について口座区分が未確認: eMAXIS Slim 米国株式(S&P500) (EMAXIS_SLIM_SP500_1, EMAXIS_SLIM_SP500_2,
    EMAXIS_SLIM_SP500_3); 楽天・プラス・オールカントリー株式インデックス・ファンド(楽天・プラス・オールカントリー) (RAKUTEN_PLUS_ALL_COUNTRY_1,
    RAKUTEN_PLUS_ALL_COUNTRY_2)。商品名の一致だけを重複・一本化の根拠にしない'
  source: normalized_snapshot
  as_of: '2026-07-26'
- item: individual_stock_etf_investment_theses
  reason: '投資仮説・棄却条件が正本に未記録の個別株・ETF: 2353, 7201, 7203, 9444。レビュー対象から除外せず、一次情報から暫定ストーリーを再構成し、買い増しはユーザが保有理由を確認するまで確定しない'
  source: strategy/theses/index.yaml
  as_of: '2026-07-26'
- item: sale_tax_and_transaction_costs
  reason: 売却税、取得ロット、手数料の確定値はパケットにない
  source: review_packet_boundary
  as_of: '2026-07-26'
- item: risk_target_parameters
  reason: 未承認の投資待機資金比率など必要入力がない指標は算定不能として扱う。目標株式比率と目標コア・サテライト比率は、導出可能な現金要件を先に確保した後で評価する。確認済みの集中上限はconfirmed_user_conditionsを優先する
  source: review_scope
  as_of: '2026-07-26'
excluded_information:
- 過去の会話、前月以前のレビュー回答、プロジェクト内メモリ
- 現行戦略の目標比率・閾値（政策配分を現在保有に合わせて後付けしないため）
- Codexの過去評価、過去推奨、承認済みまたは保留中の売買計画
- Pythonがルールから生成した候補注文、推奨予算、抑制判断
- 今回selected_sourcesに選ばれていない履歴、取引記録、意思決定記録
- レビューに無関係なファイル名、添付メタデータ、取得失敗、再アップロード履歴
- パケット外のProject/GPT参照ファイル、カスタムメモリ、周辺会話
```

## 3. 正規ルール台帳
同じ規則を別の表現で上書きせず、判断根拠ではrule_idを参照してください。
```yaml
rule_registry:
- rule_id: R-PHASE-001
  applies_to: all
  rule: objective_confirmationでは目的確認の一問だけを出力し、Web調査、投資判断、6セクション、YAML、売買案、quality checksを出力しない。回答後はfinal_reviewへ移る
- rule_id: R-MODE-001
  applies_to: all
  rule: 一つのreview_modeだけを適用し、月次運用判断と戦略判断を混在させない
- rule_id: R-OBJECTIVE-001
  applies_to: strategic_policy_second_opinion
  rule: primary_objectiveと対応するprimary_objective_fit_formulaで全候補を比較し、一つのベースケースを選ぶ
- rule_id: R-PLANNING-001
  applies_to: strategic_policy_second_opinion
  rule: reviewer_to_derive、reviewer_to_estimate_with_uncertainty、reviewer_to_model_with_uncertaintyは明示的な判断委譲として扱う。final_review内で根拠、式、限界、感応度と一つのベースケースを導出し、ユーザーへ再質問しない。導出値はfinancial_planning_modelだけを正本とする
- rule_id: R-CASH-001
  applies_to: all
  rule: 家計用現金、戦術的待機資金、長期運用資産を分離し、必要現金の残余から長期株式比率を逆算しない
- rule_id: R-CASH-002
  applies_to: all
  rule: tactical_liquidity_policyの正本はstrategic_policy_decision.tactical_liquidity_policyだけとし、cash_assessmentとdecisionsはID参照だけにする
- rule_id: R-MARKET-001
  applies_to: all
  rule: 市場下落判定は投入対象と同じ広範指数を使う。テーマ・セクター下落は発動条件にせず、必要データを確認できなければunclearとする
- rule_id: R-RESEARCH-001
  applies_to: final_review
  rule: 外部調査はresearch_cutoff_atまでの判断材料に使うが、portfolio_snapshot_as_ofの評価額を再評価しない
- rule_id: R-STORY-001
  applies_to: final_review
  rule: security_story_review_targetsとthematic_fund_review_targetsを全件評価し、価格変動だけを売却理由にしない
- rule_id: R-THEME-001
  applies_to: final_review
  rule: 同一テーマ投信は商品・指数ストーリーを一度だけ評価し、口座・ロット別の税務と執行判断を別配列へ記録する
- rule_id: R-TRADE-001
  applies_to: final_review
  rule: 売買・資金移動は算式、型付き入力、仮定への依存、税・口座、最大影響、実行時期を示し、承認済み根拠のない金額閾値は追加しない
- rule_id: R-ID-001
  applies_to: final_review
  rule: 人間向け回答では正式名称を使い、machine_id・symbol・銘柄コードはCodex向けYAMLの識別子フィールドに限定する
- rule_id: R-DELIVERY-001
  applies_to: final_review
  rule: ファイル生成可能ならreview_response.yamlを添付する。不可なら6セクション後の区切り線直後にYAMLコードブロックを一つだけ置く。YAMLファイル本体にはコードフェンスや説明文を入れない
- rule_id: R-QUALITY-001
  applies_to: final_review
  rule: quality checkがfailなら回答を修正し、修正不能ならfinal_reviewを提出せずblockedとして不足とremediationを返す
```

## 4. 外部調査契約
```yaml
phase: final_review_only
required_for:
- capital_market_assumptions
- financial_planning_assumptions
- public_pension_estimation
- retirement_spending_and_success_probability
- tax_and_account_rules
- product_specifications
- security_story_reviews
- thematic_fund_reviews
preferred_source_types:
- academic_primary_research
- government_or_regulator
- index_provider
- fund_manager
- issuer_ir_or_filing
source_required_fields:
- title
- publisher
- url
- publication_date
- accessed_at
- source_type
- claim_supported
portfolio_valuation_rule: 外部情報は判断根拠にだけ使い、portfolio_snapshot_as_ofの価格・為替・評価額・比率を更新しない
```

## 5. 出力スキーマと配送契約
```yaml
interaction_phase: final_review
objective_confirmation:
  response_type: one_objective_question_only
  optional_content: 各選択肢の一行定義
  forbidden:
  - web_research
  - investment_decision
  - six_human_sections
  - yaml
  - trade_proposals
  - decision_quality_checks
  transition: ユーザーの一回答をupdated_inputsへ反映し、同じ初期入力全体でfinal_reviewを再実行する
final_review:
  required_sections:
  - 【推奨方針】
  - 【採用した決定規則】
  - 【具体的な売買・資金移動】
  - 【実行後配分】
  - 【実行前確認事項】
  - 【Codex向け改善フィードバック】
  updated_inputs_location: 【推奨方針】の冒頭。独立見出しは禁止
  general_explanation_max_pct: 20
  delivery:
    schema_ref: schemas/monthly-review-response.schema.yaml
    preferred: attach_review_response_yaml
    fallback: six_sections_then_delimiter_then_one_yaml_code_block
    yaml_file_transport: コードフェンスなしの純粋なYAMLファイル
    chat_transport: 区切り線後の一つのyamlコードブロック
response_identity:
  schema_version: 2
  artifact_type: monthly_review_response
  review_mode: strategic_policy_second_opinion
  interaction_phase: final_review
  review_target_month: '2026_08'
  portfolio_snapshot_as_of: '2026-07-26'
canonical_paths:
  tactical_liquidity_policy: strategic_policy_decision.tactical_liquidity_policy
  current_deployment_evaluation: dip_buy_liquidity_deployment_review
  cash_policy_reference: cash_assessment.tactical_liquidity_policy_ref
  decision_references: decisions.policy_refs
array_schemas:
  candidate_comparison:
  - candidate_id
  - global_equity_pct
  - bonds_pct
  - expected_nominal_return_pct
  - expected_real_return_pct
  - expected_volatility_pct
  - equity_bond_correlation
  - estimated_major_drawdown_pct
  - primary_objective_fit_value
  - primary_objective_fit_formula
  - assumptions_ref
  - selected
  source:
  - title
  - publisher
  - url
  - publication_date
  - accessed_at
  - source_type
  - claim_supported
  empirical_evidence:
  - evidence_id
  - claim
  - source
  - observed_market_or_population
  - observation_period
  - result
  - limitations
  - decision_supported
  security_story_source:
  - title
  - publisher
  - url
  - publication_date
  - accessed_at
  - source_type
  - claim_supported
  thematic_fund_review:
  - theme_review_id
  - product_name
  - member_symbols
  - index_story
  - material_facts
  - story_health
  - decision
  - decision_rationale
  - sources
  - account_lot_reviews
  order_proposal:
  - proposal_id
  - symbol
  - account_type
  - side
  - status
  - quantity
  - amount_jpy
  - formula
  - inputs
  - tax_and_account_analysis_ref
  - rationale
  - requires_user_approval
  execution_check:
  - check_id
  - status
  - evidence
  - blocking_action_ids
  prompt_feedback:
  - feedback_id
  - category
  - severity
  - problem
  - recommended_change
  - affected_path
  before_after_allocation:
  - view
  - category
  - before_pct
  - after_pct
  - target_pct
  - calculation_status
  account_tax_comparison:
  - comparison_id
  - symbol
  - account_type
  - cost_basis_jpy
  - unrealized_gain_loss_jpy
  - tax_treatment
  - nisa_impact
  - estimated_after_tax_proceeds_jpy
  - decision
  - sources
root_fields:
- schema_version
- artifact_type
- review_mode
- interaction_phase
- review_target_month
- portfolio_snapshot_as_of
- market_reference_as_of
- packet_generated_at
- research_cutoff_at
- decision_date
- strategic_policy_decision
- decision_axes
- empirical_evidence
- human_summary
- cash_assessment
- dip_buy_liquidity_deployment_review
- security_story_reviews
- thematic_fund_reviews
- before_after_allocation
- account_tax_comparisons
- decisions
- codex_handoff
- decision_quality_checks
response_skeleton:
  schema_version: 2
  artifact_type: monthly_review_response
  review_mode: strategic_policy_second_opinion
  interaction_phase: final_review
  review_target_month: '2026_08'
  portfolio_snapshot_as_of: '2026-07-26'
  market_reference_as_of: <packet value>
  packet_generated_at: <packet value>
  research_cutoff_at: <packet value>
  decision_date: <YYYY-MM-DD>
  strategic_policy_decision:
    status: <proposed|not_applicable|blocked>
    objective: <objective_id|null>
    updated_inputs:
      newly_confirmed: []
      superseded_assumptions: []
      decisions_now_unblocked: []
      decisions_still_blocked: []
    financial_planning_model:
      status: <derived|not_applicable|blocked>
      return_basis: null
      current_age: null
      withdrawal_start_age: null
      planning_end_age: null
      retirement_spending_current_jpy_per_month: null
      retirement_spending_derivation: null
      public_pension_annual_current_jpy: null
      public_pension_estimation_method: null
      long_term_contribution_policy:
        annual_net_contribution_jpy: null
        contribution_end_age: null
        allocation_rule: null
        rationale: null
      inheritance_included_in_base_case: null
      inheritance_base_case_jpy: null
      inheritance_treatment: null
      terminal_asset_floor_current_jpy: null
      success_probability_pct: null
      success_probability_rationale: null
      target_return_pct: null
      target_return_formula: null
      sensitivity_cases: []
      source_refs: []
    recommended_policy:
      policy_id: <id>
      investable_equity_pct: null
      investable_bond_pct: null
      investable_other_pct: null
      core_policy: null
      satellite_policy: null
      rebalancing_rule: null
      transition_deadline: null
    policy_allocation_within_investable_portfolio:
      equity_pct: null
      bond_pct: null
      other_pct: null
    household_total_asset_allocation:
      equity_pct: null
      bond_pct: null
      household_reserve_pct: null
      tactical_liquidity_pct: null
      excluded_other_pct: null
    tactical_liquidity_policy:
      policy_id: <id>
      status: <proposed|approved_unchanged|not_applicable|blocked>
      initial_target_pct_of_total_assets: null
      target_jpy: null
      deployment_asset: null
      trigger_index: null
      reference_high_definition: null
      price_basis: null
      lookback_period: null
      fx_treatment: null
      tranches: null
      amount_per_tranche: null
      refill_rule: null
      termination_rule: null
      policy_allocation_treatment: null
      rationale: <string>
      source_refs: []
      requires_user_approval: true
    active_risk_policy:
      policy_id: <id>
      satellites_allowed: null
      total_satellite_cap_pct: null
      single_theme_cap_pct: null
      single_security_cap_pct: null
      exceptions: []
    direct_semiconductor_limit:
      policy_id: <id>
      status: <hard_constraint|policy_to_reconsider|explicit_exception>
      limit_pct: null
      denominator: household_total_assets_jpy
      priority: <string>
      rationale: <string>
    candidate_methodology: <object matching array_schemas and packet assumptions>
    candidate_comparison: []
  decision_axes:
    user_confirmed_facts: []
    packet_confirmed_facts: []
    empirical_market_evidence: []
    mathematically_derived_constraints: []
    reviewer_assumptions: []
  empirical_evidence: []
  human_summary:
    overall_assessment: <string>
    priority_actions: []
  cash_assessment:
    emergency_fund_target_jpy: null
    emergency_fund_status: <enum>
    monthly_essential_expenses_jpy: null
    spending_months: null
    near_term_confirmed_expenses_jpy: null
    contingency_reserve_jpy: null
    tactical_liquidity_policy_ref: strategic_policy_decision.tactical_liquidity_policy
    dip_buy_liquidity_status: <enum>
    minimum_confirmed_cash_jpy: null
    maximum_calculable_cash_jpy: null
    total_cash_target_status: <enum>
    total_cash_target_jpy: null
    derivation_notes: []
  dip_buy_liquidity_deployment_review:
    policy_ref: strategic_policy_decision.tactical_liquidity_policy
    reserve_status: <available|unavailable|unknown>
    market_decline_status: <declining|not_declining|unclear>
    trigger_index_matches_deployment_target: null
    theme_or_sector_decline_used_as_trigger: false
    market_evidence: []
    use_option:
      considered: false
      status: <enum>
      target: null
      amount_jpy: null
      formula: <string>
      timing: null
      rationale: <string>
    selected_action: <enum>
    selection_rationale: <string>
    reserve_maintenance_is_objective: false
  security_story_reviews: []
  thematic_fund_reviews: []
  before_after_allocation: []
  account_tax_comparisons: []
  decisions:
    policy_refs: []
    portfolio_diagnosis: []
    rule_refs: []
    order_proposals: []
    actions: []
  codex_handoff:
    execution_checks: []
    prompt_feedback: []
    repository_changes:
      must: []
      should: []
      nice_to_have: []
  decision_quality_checks: []
```

## 6. 検証契約
```yaml
quality_check_schema:
  required_fields:
  - check_id
  - status
  - evidence
  - remediation
  status_enum:
  - pass
  - fail
  - not_applicable
required_check_ids:
- target_equity_ratio_is_not_cash_residual
- strategic_cash_and_tactical_cash_are_separated
- one_primary_policy_is_selected
- policy_is_derived_from_stated_objective
- age_and_horizon_are_considered_when_relevant
- age_is_not_replaced_by_an_unexamined_rule_of_thumb
- empirical_rules_have_verifiable_support
- statistical_average_is_not_presented_as_a_certain_outcome
- no_persona_generated_investment_lore
- no_numeric_threshold_is_based_only_on_expert_sounding_language
- subjective_axes_are_used_only_when_explicitly_authorized
- no_unrequested_psychological_or_lifestyle_axes
- no_ad_hoc_concentration_limit
- no_arbitrary_partial_sale
- every_general_statement_supports_a_decision
- transition_plan_matches_policy_portfolio
- prior_recommendations_are_explicitly_superseded_when_changed
- delegated_financial_planning_inputs_are_derived_not_reasked
- derived_financial_planning_values_have_evidence_and_sensitivity
phase_rule: objective_confirmationでは全件not_applicable。final_reviewでは適用対象をpassとし、failを残したまま提出しない
static_reference_checks:
- no_undefined_packet_reference
- no_deprecated_date_alias
- no_unapproved_material_trade_threshold
- one_canonical_tactical_liquidity_policy
- allocation_percentages_total_100
- no_machine_ids_in_human_sections
interaction_phase_at_generation: final_review
```
