# Strategy

現在方針と過去方針を再現可能にするため、戦略は版管理します。

- `current.yaml`: 現在有効な戦略版へのポインタ。方針本文を重複して書かない。
- `versions/`: 承認済み戦略の不変版。新方針へ移るときは既存版を書き換えず、新しい版を追加する。
- `theses/`: テーマ・銘柄ごとの検証可能な投資仮説。戦略版から参照する。

運用上の一時的な購入額や実行日は `plans/` に置き、実績や振り返りを戦略本文へ混ぜません。

現行戦略の主目的、運用配分、レビュー前の口座区分ゲート、具体的行動の出力契約は、`current.yaml` が指す戦略版を正とします。本人が選ぶ生活・嗜好条件の正本は`financial/current.yaml`が指す`strategic_profile.objective_configuration.objective_models.maximize_terminal_wealth.lifestyle_constraints`です。新しい本人意向は過去の`purpose.enjoyment_preference`より優先しますが、運用配分や注文計画を自動変更しません。サテライト比率と銘柄が`reviewer_to_propose`の間も、本人の計画前提は維持し、その範囲で独立ChatGPTへ判断を委譲します。
