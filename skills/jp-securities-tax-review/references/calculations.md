# 計算補助の入力契約

Python 3.10以降、外部依存なし。ネット接続、ファイル探索、入力の書換え、結果保存を行わず、指定したJSONまたは標準入力を読み、標準出力へJSONを返す。案件データをスキルディレクトリへ置かない。以下のコマンドはスキルのルートを基準に示す。

```sh
python3 scripts/tax_math.py aggregate /指定された案件ワークスペース/input.json
python3 scripts/tax_math.py offset /指定された案件ワークスペース/scenario.json
python3 scripts/tax_math.py estimate /指定された案件ワークスペース/estimate.json
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*.py' -v
```

金額・税率は小数文字列。float、指数表記、NaN、重複JSONキー、未知の区分や年度不一致を拒否する。計算精度はCLIでDecimal 80桁、入力は整数部24桁、小数部12桁まで。入力・出力・適用ルールIDを案件内に保存すれば計算を再現できる。`verified`等は呼び出し元の証憑検証結果であり、スクリプトが証憑の真正性を認証する意味ではない。

## aggregate：円建て明細の集計

トップレベルは`year`（課税年の整数）、`scope_complete`（対象口座・期間の網羅確認）、`records`。

全明細に以下を持たせる。

- `id`：案件内の明細ID。`economic_id`：原資料の約定／支払等を表す案件内一意ID。同じ経済取引を別資料から取り込んでも同じIDへ正規化する。
- `year`：約定年ではなく、計上ルールを検証して決めた課税年。
- `account_id`：匿名ID。`account_type`：`specified_withholding`、`specified_no_withholding`、`general`、`nisa`、`ideco`。
- `tax_group`：`listed`、`general`、`nisa`、`ideco`、`other`。口座のNISA／iDeCoと区分を一致させる。
- `kind`：`sale`、`dividend`、`return_capital`、`unrealized`。
- `status`：4確度のいずれか。検証済み／暫定には`evidence_refs`（案件資料ID・ページ／欄等の配列）が必須。
- `sale`は`proceeds_jpy`、`acquisition_cost_jpy`、`selling_cost_jpy`を非負の円建て文字列またはnullで持つ。取得費は対象商品のルールで別途計算・検証済みとし、購入手数料込み。未知の費用をゼロにしない。
- 他のkindは`amount_jpy`。配当は税引前の対象所得額、元本払戻は別項目、未実現損益は符号付き。課税配当の適格性はここで自動認定しない。

口座・口座種別・税区分・kindごとに純額、利益・損失（正の額）、入力ID・出典を返す。未知の行がある群の全額はnullで、既知小計を別に返す。`scope_complete=false`でも全額はnull。暫定入力の集計は暫定。明細のない群を暗黙のゼロ行にしない。NISA等を課税群と合算しない。

年次報告書の合計を明細として追加しない。別の突合表で`statement_value - transaction_sum = difference`を計算し、出典・欄・期間を残す。純額のみの報告書から総利益と総損失を作らない。この補助はCSV変換、円換算、単価平均、企業行動、明細の法的分類を行わない。

## offset：適格性を検証した選択シナリオ

当年の上場株式等だけの通常通算モデル。一般株式、NISA、iDeCo、相対取引等による特例対象外損失の混在、特殊控除、総合課税配当は対象外。対象外部分は別に公式様式で計算する。`offset`の拒否を案件全体の分析停止理由にしない。

トップレベルは`year`、`scope_complete=true`（そのシナリオに選択した口座内の全対象所得を確認済み）、`rules`、`accounts`、`carryovers`。

`rules`は`year`、`verified=true`、`loss_order="oldest_first"`、`income_order="sales_then_distributions"`、`evidence_refs`。順序・適用範囲を対象年の付表・記載要領で検証してから投入する。別ルールを無理にこのモデルへ合わせない。

`accounts`の各要素は次のとおり。

- `account_id`、課税口座の`account_type`、`tax_group="listed"`、`all_losses_eligible=true`（対象損失の特例適格性を確認した意味）。
- `net_sales_jpy`：口座の年間譲渡純損益。口座内で配当と通算する前の値。
- `eligible_distributions_jpy`：同口座内の対象配当等の税引前額。不存在を資料で確認した場合だけ`"0"`。
- `declare_sales`、`declare_distributions`：申告選択の真偽値。選択した所得区分の一部分だけを入力しない。どちらも選択しない口座は投入しない。
- `distribution_method`：配当等を含める場合`"separate"`。その他の所得はこのモデル外で比較する。
- `status`、`evidence_refs`。未知入力は拒否。暫定年中資料なら暫定結果。

源泉徴収あり口座の損失を選び、同口座の対象配当等が正なのに配当を選ばない入力は拒否する。譲渡純額の未知をゼロにして配当だけの案を作らず、その案用に根拠ある値を用意する。

`carryovers`は年別にまとめ、各要素に`id`、`loss_year`、`expiry_year=loss_year+3`、`remaining_jpy`（当年開始前の残高）、`filing_verified=true`、`status="verified"`、`evidence_refs`を持たせる。損失年以後、当年直前までの連続申告、当初額、各年使用額との突合を先に行う。申告未確認の候補損失は別の未確認表に置き、適用案へ投入しない。`carryovers=[]`は利用可能損失を確認した結果ゼロの場合、または「繰越を使わない」と明記した比較案だけ。

当年純損失を対象配当等へ当てた後、古い繰越から譲渡益→配当等の順で控除し、当年残、年末失効、翌年利用可能額を返す。期限経過分は使用せず失効表示する。当年新規残は申告条件付きの潜在繰越額。所得控除前の額であり、最終課税標準や税額と呼ばない。

## estimate：明示した率・丸めによる条件付き概算

トップレベルは`year`、`mode="conditional_marginal_estimate"`、`status`、`evidence_refs`、非負の`taxable_income_jpy`、`components`。入力の基礎額を算出したルール・仮定も出典へ接続する。

各componentは`id`、`jurisdiction`（`national`／`resident`）、`base`（`income`または先行componentのID）、`rate`（割合の文字列）、`rounding`（`none`／`floor`）、`rounding_quantum_jpy`（無丸めは`"0"`、切捨単位は正数）、`rule_refs`を持つ。

例えば**法定丸め前の限界税負担の比較用**に、2026年は本体`income×0.15`、復興税`本体×0.021`、住民税`income×0.05`を別componentにする。2027年は復興税`本体×0.011`と防衛税`本体×0.01`に分ける。これは率の恒久設定ではなく、実行時に対象年を確認して明示入力する。

結果は常に暫定で`is_final_tax=false`。基礎額の千円未満、税額・納付額の端数、復興税等の計算基礎、取引／支払ごとの源泉徴収の丸めを一つのfloor設定で済ませない。No.2507の源泉税の1円未満切捨てを申告全体へ転用しない。所得控除、外国税額控除、その他税額控除、高額所得特例、他所得との関係は対象年公式様式／作成コーナー等で別途計算し突合する。

源泉徴収・還付は自動計算しない。公式計算で得た税額と、申告対象所得だけに対応する**口座内精算後の**国税／住民税をそれぞれ突合する。国税の申告還付と住民税の後日精算は別時点の資金移動として記録する。申告しない所得の税額と徴収済額はそのシナリオの総負担比較に残し、申告分だけの税額が全体税額のように見えないようにする。
