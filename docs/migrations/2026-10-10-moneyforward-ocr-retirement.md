# Money ForwardのOCR運用を廃止

2026-10-10のユーザ依頼に基づき、Money ForwardのキャプチャをOCRして資産スナップショットを作る専用運用を廃止した。

## 廃止したアセット

| 旧パス・機能 | 処置 |
| --- | --- |
| `prompts/moneyforward_normalization_prompt.md` | 削除 |
| `prompts/templates/moneyforward_monthly_session_start_prompt.md` | 削除 |
| `tests/test_moneyforward_normalization_prompt.py` | 専用プロンプトの契約テストを削除 |
| `validation.validate_source_evidence` | 画像以外の一次情報に警告する処理を削除 |
| `validation.build_ocr_snapshot_validation_warnings` | `build_snapshot_validation_warnings` へ改名し、汎用のデータ検証を維持 |
| README・SPECのOCR手順、画像優先ルール、テンプレート再作成指示 | 撤去 |
| 入力例・モデル・新規生成物の `ocr_notes` | `normalization_notes` へ変更 |

## 今後の入力と検証

CLIは正規化済みYAMLを受け取る。出典と評価基準日を記録し、残高・カテゴリ・通貨・重複・口座区分・前月差分を検証する。Money Forwardの画像やOCR専用プロンプトは要求しない。

旧スナップショットを読み込む際は、履歴の `ocr_notes` を `normalization_notes` に取り込む。両方がある場合は両方の注記を保持し、同文の重複だけを除く。この互換読取は過去データの注記を失わないために残す。

## 過去の証拠と生成物を保持する

`data/normalized/snapshot_2026_*.yaml`、`data/raw/`、`data/history/`、`prompts/generated/`、`reports/generated/`、過去の計画・判断・振り返りは、当時の出典と判断過程を示す履歴として保持する。そこに残るMoney Forward・OCRの記述は現行手順として再利用しない。過去の生成物を今回の廃止に合わせて再生成・手編集しない。

振り返りや生成済み記録に残る上表の旧パスは、当時の修正対象を示す履歴参照である。廃止したファイルを復活させる指示として扱わない。

取引報告や証券会社の注文画面など、Money ForwardのOCR運用以外の証拠管理は従来どおり扱う。資産残高、取引台帳、承認済み戦略・計画の値はこの廃止によって変更しない。
