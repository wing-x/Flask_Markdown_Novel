# _shared — 複数スキル共通リファレンス

このディレクトリは**スキルではない**。`novel-write` / `novel-check` / `novel-fix` などの既存スキルから参照される共通リファレンス・テンプレート置き場。

## 基本思想

> **「入れる情報を増やすより、入れない情報を選ぶ」**

Claude に全プロットと全設定を渡して書かせるのではなく、必要最小限の情報だけを渡して執筆精度を最大化する。設計メモ (「読者への効果」「伏線メモ」「設計意図」) は執筆時のコンテキストに入れず、執筆後のレビュー時にのみ参照する。

## 構成

```
_shared/
├── README.md                             (このファイル)
├── references/
│   ├── style-rules.md                    (汎用スタイルルール・具体例付き)
│   ├── forbidden-patterns.md             (禁止語彙・禁止パターン集)
│   ├── monologue-guidelines.md           (内心モノローグの書き方)
│   ├── dialogue-guidelines.md            (台詞の書き方)
│   └── consistency-checklist.md          (整合性チェック項目・汎用版)
└── templates/
    ├── writing-contract.md               (部単位の執筆契約テンプレ)
    └── handoff-document.md               (部間ハンドオフテンプレ)
```

## どのスキルから参照されるか

| ファイル | 参照元スキル | 参照タイミング |
|---|---|---|
| `references/style-rules.md` | novel-write / novel-check / novel-fix | 本文生成時・事後チェック時・修正時 |
| `references/forbidden-patterns.md` | novel-write / novel-check / novel-fix | 同上 |
| `references/monologue-guidelines.md` | novel-write / novel-check | 内心描写を書く/チェックするとき |
| `references/dialogue-guidelines.md` | novel-write / novel-check | 台詞を書く/チェックするとき |
| `references/consistency-checklist.md` | novel-check / novel-check-plot | 整合性チェック時 |
| `templates/writing-contract.md` | novel-plot (モードF・部分割) | 部単位プロット完成時 |
| `templates/handoff-document.md` | novel-write / novel-plot | 部の執筆完了時 |

## 作品固有ルールとの関係

ここに置くのは**完全に汎用な**ルール (日本語 Web 小説全般に通用するもの)。作品固有の追加ルールは各プロジェクトの `projects/{作品名}/style_notes.md` や `check_notes.md` 等に書き、スキル側で合成して使う。
