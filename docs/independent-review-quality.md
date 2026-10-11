# 投資判断を先送りした回答を品質ゲートで検出する

2026-10-11のユーザー依頼に基づく生成アセットの修正です。投資方針の再レビューや売買の承認ではありません。

## 原因は判断の責務と完了条件が空いていたこと

失敗時の生成元は`src/monthly_limit_order_review/independent_review.py`と`prompts/templates/independent_review_template.md`です。`generate-review-prompt`、互換コマンド`monthly-run`、`scripts/render_staged_snapshot_review.py`は共通の生成経路を使います。

旧テンプレートは調査に「今回は全調査や売買案の確定まで進めず」、統合に「追加調査や新たな推測をせず」と指示する一方、一案を選ぶ判断工程を定義していませんでした。「推測」を避ける制約が合理的な推論まで抑え得る構造です。nullには理由・確認方法を求めましたが、判断への重要性・結果別の行動・数量だけが未知の場合の扱いは定義していませんでした。既存テストは入力の正確さ・除外情報・口座ゲート・自己完結性・履歴保護を確認し、投資判断の責務や意思決定価値は確認していませんでした。

ユーザー提供の統合結果は14明細を網羅していても、全件の売却数量・注文条件がnullで、比較判断を後日の再評価へ回しています。この資料から形式上の網羅だけでは不十分だったことを確認できます。第1～10論点の全文と当時の各追加指示は未提供のため、各回答で推論が止まった正確な経路やモデル内部の原因までは断定しません。

## 工程定義を生成元にし、判断を通してから統合する

詳細な工程・出力・完了条件・品質ゲートは`prompts/workflows/independent_review.md`だけに置きます。テンプレートは`{{REVIEW_WORKFLOW}}`を持ち、生成時に全文を埋め込みます。ローカルファイルへのアクセスはChatGPTに要求しません。生成器は工程の欠落・順序違い・未解決のプレースホルダーを拒否します。

共通ルールは`docs/independent-review.md`、リポジトリの実行規則は`AGENTS.md`、操作案内は`README.md`です。旧互換テンプレートや過去の意思決定記録は履歴として維持します。旧生成プロンプト本文を修正せず、新しいディレクトリへ生成します。生成元の対応と出力のSHA-256を`generation_manifest.yaml`へ保存し、既存依頼を置き換える場合は`mark_review_superseded`で状態説明だけを更新します。

調査 → 証拠の充足判定 → 投資判断・行動設計 → 統合 → Codex文書化という責務を設けました。追加調査を禁止する工程でも、判断工程で確認済み事実から推論することは認めます。統合は判断済みの条件付き分析を削除しません。未確認事項によって推奨が変わるかを評価し、判断・数量・税額・執行の未知を分離します。合理的な維持も合格とし、売却やnull削減を強制しません。

## 回答の評価は本文の根拠行に戻って行う

ChatGPTにはMarkdownでの判断と自己点検を求めます。新しい巨大な回答YAMLは要求しません。回答受領後にCodexが、本文と入力を読み、比較・判断・行動時期・不確実性の重要性・条件別行動・本人制約・安全性を確認します。

機械検証には任意の内部評価形式`schemas/independent-review-quality.schema.yaml`を使えます。これはChatGPTの回答形式でも運用の正本でもありません。評価者は本文の根拠行を示し、`checks`の各観点をpass・fail・unknownに分類します。各明細についてはready（具体化できる提案）・conditional（条件付き提案）・hold（合理的な維持）・deferred（判断保留）を区別し、未知の項目の影響・確認担当・方法・必要時期・分岐を記録します。

`src/monthly_limit_order_review/review_quality.py`は、評価注記のスキーマ、回答ハッシュ、根拠行の存在範囲、全売買可能明細の網羅、重複ID、比較や次の操作の欠落、理由なしのnull、条件分岐の欠落、保留等が大半の場合の全件再点検を検証します。必要な観点がfail・unknownなら完了扱いにしません。判断保留が十分に根拠付けられている場合は、その範囲を残した条件付き成果物として受け取れますが、未解決の判断を解決済みにはしません。

評価YAMLの`source_ref`は評価ファイルのディレクトリから回答本文を指します。検証コマンドは読み取り専用です。

```sh
.venv/bin/python -m monthly_limit_order_review.cli check-review-quality \
  --assessment path/to/assessment.yaml \
  --review-input reports/generated/on_demand/YYYY/REQUEST/review_input.yaml
```

終了コードは0が注記の契約を充足、2が品質上の不足、1が構文・スキーマ等のエラーです。この検証は評価注記の整合性を確認するもので、自然文の意味や投資判断の合理性を自動で証明しません。根拠行に別の内容を割り当てた注記や、もっともらしいが誤った比較を検出するには本文との照合が必要です。実際の投資助言の質、税制の正確さ、期待収益の妥当性は別途内容レビューが必要です。

## 失敗資料とA～Gの回帰テスト

失敗資料は`tests/fixtures/independent_review/2026-10-11_failed_integration/`です。`response.md`は元添付の全文、`assessment.yaml`はCodexによる根拠行付き注記、`README.md`は由来・ハッシュ・未検証範囲です。この資料を次回の独立レビューへ注入しません。

| 要求 | テストで確認する範囲 |
| --- | --- |
| A 判断の消失防止 | 生成工程の順序・欠落拒否、判断済み条件の保存指示、架空の判断・統合例の契約充足、判断工程未確認の検出 |
| B 未確認税務 | 相続特例の未知が他明細を止めない架空例、条件別行動がない注記の拒否 |
| C 含み益と集中 | 比較した維持を受け入れ、税と集中の比較がない注記を拒否 |
| D null | 数量だけの未知を許容し、理由・影響・解除手順のないnullや根拠不足と評価された値を拒否 |
| E 嗜好 | 本人の20%前提の伝達を保持、自動縮小・最適性の断定と評価された注記を拒否 |
| F 意思決定価値 | 全14件を含む実失敗を不合格にし、比較・結果別行動・全件再点検の欠落を検出 |
| G 安全性 | 生成・品質検証で元ファイルを変更せず、未承認昇格と評価された注記を拒否 |

これらは生成アセットと品質契約の回帰テストです。架空例は実際の保有銘柄への推奨ではありません。ChatGPTの再実行による成功率測定や、投資結果の最適性のテストは行っていません。修正後に新規Temporary Chatで実行した回答の内容検証が、モデル動作の確認として残ります。

## 今回の変更ファイルと検証結果

| ファイル | 変更 |
| --- | --- |
| `prompts/workflows/independent_review.md` | 追加。5工程の入出力・完了条件、nullの検証、意思決定価値の品質ゲート |
| `prompts/templates/independent_review_template.md` | 更新。初回の責務を整理し、共通工程定義の埋め込みと判断後の統合へ変更 |
| `src/monthly_limit_order_review/independent_review.py` | 更新。工程順序の検証、工程定義の埋め込み、生成元ハッシュの保存、状態説明 |
| `src/monthly_limit_order_review/review_quality.py` | 追加。根拠行付き評価注記の品質契約を検証 |
| `src/monthly_limit_order_review/cli.py` | 更新。読み取り専用の`check-review-quality`を追加 |
| `schemas/independent-review-quality.schema.yaml` | 追加。Codex内部評価のスキーマ。ChatGPTの回答へは強制しない |
| `AGENTS.md`、`docs/independent-review.md`、`README.md` | 更新。工程の責務と共通生成元・品質評価への参照を整合 |
| `docs/independent-review-quality.md` | 追加。原因・対応関係・評価方法・限界・今回の検証記録 |
| `tests/test_independent_review.py`、`tests/test_cli.py` | 更新。工程欠落拒否、生成元ハッシュ、履歴保護、CLIの生成経路 |
| `tests/test_review_quality.py` | 追加。A～G、維持の正当性、多数保留の全件再点検、根拠・網羅性 |
| `tests/fixtures/independent_review/2026-10-11_failed_integration/response.md`、`assessment.yaml`、`README.md` | 追加。無改変の失敗資料、根拠行付き注記、由来と限界 |
| `reports/generated/on_demand/2026/2026_10_11T172423_054368_independent_review/` | 追加。修正後の依頼本文・入力・状態説明・生成元manifest |
| `reports/generated/on_demand/2026/2026_10_11T142540_629574_independent_review/README.md` | 状態説明のみ更新。旧依頼の再送禁止と新依頼への参照 |

維持したもの：金融・保有メタデータ・戦略・積立・既存計画・証券会社仕様・取引台帳・税務記録・スナップショットの正本、旧依頼本文と旧入力。新旧入力は依頼日時・調査締切以外が一致しています。

重要な指示の変更前後は次のとおりです。

> 変更前：今回は全調査や売買案の確定まで進めず。統合時は追加調査や新たな推測をせず。

> 変更後：推論や条件付き試算を禁止していません。本人承認待ちは提案を作らない理由になりません。統合時の「確認済み情報だけ」は、明示して判断済みの推論・条件付き分析を削除する意味ではありません。

実施した検証（2026-10-11）：

- `pytest -q`：全238件成功。関連する生成・品質テスト26件も成功。
- `repository-audit`：成功、警告0件。`git diff --check`と変更Pythonの`compileall`も成功。
- 入力・評価スキーマの検証、生成本文内YAMLと入力ファイルの一致、生成元・出力ハッシュの一致を確認。
- 元添付と失敗fixtureのバイト一致、旧依頼本文・旧入力の保全、新規依頼への失敗回答の非混入を確認。
- 失敗資料の評価注記を`check-review-quality`で検証し、不足を示す終了コード2を確認。

新依頼はA・本文完結型です。`review_request.md`全文をProject外の新規Temporary Chatへコピー＆ペーストできます。添付は不要です。ChatGPTへ実際に送信した資料はありません。
