# 小説執筆サポートエディタ

Claude APIと連携した小説執筆サポート用のマークダウンエディタです。単巻小説から長編シリーズまで対応した包括的な執筆環境を提供します。

## 特徴

### 基本機能
- 📝 マークダウンエディタとリアルタイムプレビュー
- 📚 プロジェクト管理（単巻作品・シリーズ作品対応）
- 🗂️ ディレクトリ階層構造対応（部分け管理など）
- 💾 自動保存機能
- ➕ ファイル・フォルダの作成・削除・移動・リネーム

### シリーズ管理機能
- 📖 **シリーズ作品の管理**
  - シリーズ聖典（世界観バイブル）の作成・管理
  - 巻ごとのプロジェクト自動生成
  - 巻間の設定整合性チェック
  - 伏線マスターリスト管理（JSON形式）
  - 過去巻の圧縮サマリー生成
- 🎯 **階層的コンテキスト管理**
  - シリーズレベル：世界設定・キャラクター基本情報・伏線
  - 巻レベル：巻固有の設定・タイムライン・プロット

### Claude AI執筆サポート
- 🤖 **プロット開発**
  - プロット草案からの構造化プロット生成
  - タイムライン自動生成
  - 世界観設定の詳細構築
  - キャラクター自動抽出・プロファイル生成
  - キャッチコピー生成（短・中・長）
  - ネタバレ防止あらすじ生成（短・中・長）

- ✍️ **章本文生成**
  - plot.mdに基づく全章一括生成
  - 部分け構造対応（第一部/第二部など）
  - 3000-5000文字/章の自動調整
  - テキスト形式出力（字下げ対応）
  - "Show, Don't Tell" 原則の自動適用

- 🔍 **品質管理**
  - **整合性チェック（3モード）**
    - 巻内チェック：設定・キャラクター・伏線の矛盾
    - シリーズ横断チェック：過去巻との整合性
    - 表記チェック：誤字・表記揺れ検出
  - **執筆技法チェック**
    - Show, Don't Tell 違反検出
    - 感情の直接説明チェック
    - 説明的会話の検出
    - 視点の一貫性チェック
    - 会話と描写のバランス
    - 五感描写のバランス
    - ペース配分の問題
  - **自動修正機能**
    - 個別章の自動修正（整合性＋技法）
    - 表記揺れの一括修正
    - プロット矛盾の修正

- 🎭 **その他サポート機能**
  - キャラクター対話シミュレーション
  - 文章推敲支援
  - 巻サマリー自動生成（シリーズ継続用）

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Anthropic APIキーの設定

環境変数にAPIキーを設定してください：

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Windowsの場合：
```cmd
set ANTHROPIC_API_KEY=your-api-key-here
```
または環境変数から設定をしてください。

APIキーは[Anthropic Console](https://console.anthropic.com/)で取得できます。

### 3. アプリケーションの起動

```bash
python app.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## 使い方

### 単巻プロジェクトの作成

1. サイドバーの「+ 新規プロジェクト」ボタンをクリック
2. プロジェクト名を入力して「作成」をクリック
3. 自動的に以下のテンプレートファイルが生成されます：
   - `character.md` - キャラクター設定用
   - `plot.md` - プロット管理用

### シリーズプロジェクトの作成

1. サイドバーの「+ 新規シリーズ」ボタンをクリック
2. シリーズ名を入力（例：「異世界冒険記」）
3. シリーズ聖典ファイルが自動生成されます：
   - `bible.md` - 世界の基本ルール・固有名詞辞典
   - `characters_master.md` - シリーズ全体のキャラクター管理
   - `foreshadowing.md` - 伏線マスターリスト
   - `series_summary.md` - 巻別サマリー（自動更新）
4. 「+ 新規巻」で各巻のプロジェクトを作成
   - 命名規則：`{シリーズ名}_vol{番号}_{巻タイトル}`
   - 各巻は通常のプロジェクト機能を持ちつつ、シリーズ設定を自動参照

### ファイルの編集

1. サイドバーからプロジェクト/シリーズを選択
2. ファイル一覧から編集したいファイルをクリック
3. 左側のエディタで編集すると、右側にプレビューが表示されます
4. 変更は自動的に保存されます
5. 手動保存する場合は「💾 保存」ボタンをクリック

### 推奨ワークフロー

#### ステップ1：プロット草案作成
1. `plot_draft.md`を作成（手動またはClaude補助）
2. プロット展開案機能で大まかな流れを決定（短編/中編/長編選択可）

#### ステップ2：設定資料の自動生成
1. 「プロット→構造化プロット」ボタン
   - plot_draft.md → plot.md へ変換
   - 章ごとの詳細サマリー（500-1000字）を生成
2. 「プロット→タイムライン」ボタン
   - イベント表・伏線配置を自動生成
3. 「プロット→世界観設定」ボタン
   - 世界観の詳細を構造化
4. 「プロット→キャラクター抽出」ボタン
   - 登場人物リストを自動抽出
5. 各キャラクターの詳細プロファイルを生成

#### ステップ3：章本文の執筆
1. plot.mdを確認（章構造が正しいか）
2. 「章本文生成」ボタンをクリック
3. 全章が自動生成されます：
   - chapter01.txt, chapter02.txt...
   - プロローグ/エピローグ（plot.mdに記載がある場合）
   - 各章3000-5000文字
   - テキスト形式（全角スペース字下げ）

#### ステップ4：品質チェックと修正
1. 「整合性チェック」を実行
   - スコープ選択：巻内 / シリーズ横断 / 表記チェック
   - 整合性問題と執筆技法の問題を検出
2. 問題のある章を「章修正」で自動修正
   - または手動で修正
3. 表記揺れがある場合は「表記修正」で一括修正

#### ステップ5：プロモーション素材生成
1. 「キャッチコピー生成」
   - 短・中・長の3種 × 3バリエーション
2. 「あらすじ生成」
   - ネタバレなし保証
   - 短（200-300字）/ 中（400-600字）/ 長（800-1200字）

#### ステップ6（シリーズのみ）：巻サマリー生成
1. 巻完成後、「巻サマリー生成」を実行
2. 全章を読み込み、1000-1500字に圧縮
3. series_summary.mdに自動追記
4. 次巻執筆時に過去巻の要約として活用

### 個別機能の詳細

#### キャラクター生成
- 基本情報・外見・性格・背景・目標・人間関係を構造化
- シリーズの場合、シリーズ設定と巻設定の両方を考慮

#### 対話シミュレーション
1. シチュエーションを入力（例：「主人公と敵対者が初めて出会う場面」）
2. character.mdに基づいた自然な会話を生成

#### 文章推敲
- 選択テキストの改善案を提示
- 文体・語彙・リズムの向上

#### 伏線管理（シリーズのみ）
1. シリーズファイル一覧から`foreshadowing.md`を開く
2. 「+ 新規伏線」で追加（自動ID付与：F-001, F-002...）
3. 状態管理：未回収 / 回収済み / 意図的放置
4. 整合性チェック時に伏線の未回収・矛盾を自動検出

## ファイル構造

```
novel_editor/
├── app.py                  # Flaskアプリケーション（3148行、37エンドポイント）
├── requirements.txt        # Python依存関係
├── templates/
│   └── index.html         # メインHTML
├── static/
│   ├── css/
│   │   └── style.css      # スタイルシート
│   └── js/
│       └── app.js         # JavaScriptアプリケーション
└── projects/              # プロジェクトデータ（自動生成）
    ├── [単巻プロジェクト名]/
    │   ├── character.md
    │   ├── plot.md
    │   ├── plot_draft.md  # プロット草案（任意）
    │   ├── timeline.md    # タイムライン（任意）
    │   ├── worldbuilding.md  # 世界観設定（任意）
    │   ├── chapter01.txt  # 第1章本文
    │   ├── chapter02.txt
    │   └── ...
    │
    └── _series_[シリーズ名]/  # シリーズフォルダ（_series_プレフィックス）
        ├── _meta.json          # シリーズメタデータ
        ├── bible.md            # 世界設定バイブル
        ├── characters_master.md  # キャラクターマスター
        ├── foreshadowing.md    # 伏線マスターリスト
        ├── foreshadowing.json  # 伏線データ（自動生成）
        └── series_summary.md   # 巻別サマリー（自動更新）
```

### 各巻のプロジェクト構造（シリーズ作品）
シリーズに属する各巻は `projects/` 直下に通常プロジェクトとして配置：
```
projects/
└── [シリーズ名]_vol1_[巻タイトル]/
    ├── character.md       # この巻のキャラクター変化
    ├── plot.md
    ├── plot_draft.md
    ├── worldbuilding.md   # この巻の新要素
    ├── timeline.md
    ├── chapter01.txt
    └── ...
```
※シリーズ設定は自動的に参照される（命名規則により検出）

## API エンドポイント（全37個）

### プロジェクト管理（11エンドポイント）
- `GET /` - メインインターフェース
- `GET /api/projects` - プロジェクト一覧取得
- `POST /api/projects` - 新規プロジェクト作成
- `GET /api/projects/<project>/files` - ファイル一覧取得（階層構造対応）
- `GET /api/projects/<project>/files/<path:filename>` - ファイル内容取得
- `PUT /api/projects/<project>/files/<path:filename>` - ファイル保存
- `POST /api/projects/<project>/files/<path:filename>` - ファイル作成
- `DELETE /api/projects/<project>/files/<path:filename>` - ファイル削除
- `POST /api/projects/<project>/rename` - ファイル/ディレクトリのリネーム
- `POST /api/projects/<project>/directories` - ディレクトリ作成
- `POST /api/projects/<project>/move` - ファイル移動

### シリーズ管理（11エンドポイント）
- `GET /api/series` - シリーズ一覧取得
- `POST /api/series` - 新規シリーズ作成
- `GET /api/series/<series>/volumes` - シリーズの巻一覧
- `POST /api/series/<series>/volumes` - 新規巻作成
- `GET /api/series/<series>/files/<filename>` - シリーズバイブルファイル取得
- `PUT /api/series/<series>/files/<filename>` - シリーズバイブルファイル保存
- `POST /api/series/<series>/files/<filename>` - シリーズバイブルファイル作成
- `GET /api/series/<series>/foreshadowing` - 伏線一覧取得
- `POST /api/series/<series>/foreshadowing` - 伏線作成
- `PUT /api/series/<series>/foreshadowing/<item_id>` - 伏線更新
- `DELETE /api/series/<series>/foreshadowing/<item_id>` - 伏線削除

### Claude AI - プロット開発（7エンドポイント）
- `POST /api/claude/draft_to_plot` - プロット草案→構造化プロット変換
- `POST /api/claude/plot_draft_to_timeline` - プロット草案→タイムライン生成
- `POST /api/claude/plot_draft_to_worldbuilding` - プロット草案→世界観設定生成
- `POST /api/claude/plot_draft_to_characters` - プロット草案→キャラクターリスト抽出
- `POST /api/claude/generate_character_from_draft` - 詳細キャラクタープロファイル生成
- `POST /api/claude/generate_catchcopy` - キャッチコピー生成（短・中・長×3）
- `POST /api/claude/generate_spoiler_free_synopsis` - ネタバレなしあらすじ生成

### Claude AI - 執筆支援（2エンドポイント）
- `POST /api/claude/generate_chapters` - 全章本文生成（plot.md基準、部構造対応）
- `POST /api/claude/generate` - 汎用生成（キャラ・プロット・推敲・対話など）

### Claude AI - 品質管理（6エンドポイント）
- `POST /api/claude/consistency_check` - 整合性チェック（巻内/シリーズ/表記）
- `POST /api/claude/fix_chapter_file` - 個別章の自動修正
- `POST /api/claude/fix_notation_issues` - 表記揺れ一括修正
- `POST /api/claude/fix_plot_inconsistencies` - プロット矛盾修正
- `POST /api/claude/generate_volume_summary` - 巻サマリー生成（シリーズ用）
- `POST /api/claude/context_debug` - コンテキスト構築デバッグ

### 主要リクエスト形式例

#### 章本文生成
```json
{
  "project": "my_novel",
  "series": "my_series"  // optional
}
```

#### 整合性チェック
```json
{
  "project": "my_novel",
  "scope": "volume",  // volume / series / notation
  "series": "my_series"
}
```

#### 汎用生成
```json
{
  "action": "generate_character",  // character / plot_draft / refine_text / dialogue_simulation
  "project": "my_novel",
  "series": "my_series",
  "context": "追加の要望",
  "current_content": "現在の内容",
  "length": "中編"  // 短編 / 中編 / 長編（plot_draftの場合）
}
```

## 技術仕様

### AI モデル
- **使用モデル**: claude-sonnet-4-6 (Anthropic)
- **タイムアウト**:
  - 標準操作: 600秒（10分）
  - 章生成: 1800秒（30分）
  - 簡易操作: 60秒
- **最大トークン数**:
  - プロット生成: 30,000トークン
  - 章生成: 20,000トークン
  - 整合性チェック: 16,000トークン

### コンテキスト管理
- **シリーズバイブル**: 最大約20,000文字
- **巻設定**: 最大約10,000文字
- **ファイル別制限**: 2,000-5,000文字（超過時はトリミング）
- **巻サマリー**: 1,000-1,500文字/巻

### 出力仕様
- **章本文フォーマット**: プレーンテキスト（.txt）
  - マークダウン記号なし（#, *, _ 等は使用不可）
  - 段落開始：全角スペース1つで字下げ
  - 目標文字数: 3,000-5,000文字/章
- **設定ファイルフォーマット**: マークダウン（.md）

### ストリーミング対応
以下のエンドポイントはServer-Sent Events (SSE)でリアルタイム進捗を返却：
- 整合性チェック（全スコープ）
- 巻サマリー生成

## カスタマイズ

### シリーズバイブルテンプレートの編集
`app.py`の`SERIES_BIBLE_TEMPLATES`辞書を編集：
```python
SERIES_BIBLE_TEMPLATES = {
    'bible.md': '...',
    'characters_master.md': '...',
    'foreshadowing.md': '...',
    'series_summary.md': '...'
}
```

### プロンプトのカスタマイズ
各Claude APIエンドポイント内のプロンプト文字列を編集：
- `claude_generate()` - 汎用生成のプロンプト（2700行付近）
- `generate_chapters()` - 章生成プロンプト（1500行付近）
- `run_consistency_check()` - 整合性チェックプロンプト（1900行付近）

## トラブルシューティング

### APIキーエラー
- 環境変数`ANTHROPIC_API_KEY`が正しく設定されているか確認
- APIキーが有効か、[Anthropic Console](https://console.anthropic.com/)で確認
- Windowsの場合、システム環境変数として設定後に再起動

### ファイルが保存されない
- `projects/`ディレクトリへの書き込み権限を確認
- ブラウザのコンソール（F12）でネットワークエラーを確認
- ファイルパスに使用できない文字（\, /, :, *, ?, ", <, >, |）が含まれていないか確認

### Claude機能が動作しない・タイムアウト
- APIクレジットが残っているか確認
- ネットワーク接続を確認
- 長編の場合、タイムアウト設定を延長（app.py内の`timeout`パラメータ）
- 大量の章を生成する場合は分割して実行

### 整合性チェックで問題が検出されない
- plot.md や character.md に十分な情報が記載されているか確認
- シリーズ作品の場合、bible.md や characters_master.md が充実しているか確認
- scope パラメータが適切か確認（巻内 / シリーズ / 表記）

### シリーズ設定が反映されない
- 巻プロジェクトの命名規則を確認：`{シリーズ名}_vol{番号}_{タイトル}`
- シリーズフォルダのプレフィックスを確認：`_series_{シリーズ名}`
- `/api/claude/context_debug` で実際のコンテキストを確認

## ライセンス

このプロジェクトはMITライセンスです。自由に改変・使用してください。

## 既に実装済みの機能

- ✅ シリーズ作品の管理システム
- ✅ 伏線マスターリスト（JSON管理）
- ✅ プロット草案からの自動生成ワークフロー
- ✅ 整合性チェック（3モード：巻内/シリーズ/表記）
- ✅ 執筆技法チェック（Show, Don't Tell等）
- ✅ 自動修正機能（章/表記/プロット）
- ✅ ネタバレ防止あらすじ生成
- ✅ 巻サマリー自動圧縮（シリーズ継続用）
- ✅ 部分け構造対応（第一部/第二部...）
- ✅ ディレクトリ階層管理
- ✅ ファイル移動・リネーム機能
- ✅ 字下げテキスト出力

## 今後の拡張案

- [ ] キャラクター関係図の可視化（グラフ表示）
- [ ] ストーリーアークの視覚化（タイムライン図）
- [ ] エクスポート機能（EPUB、PDF、縦書きHTML）
- [ ] バージョン管理機能（Gitライク）
- [ ] 複数ユーザー対応（認証・共同編集）
- [ ] テーマ切り替え（ダークモード）
- [ ] 音声入力機能（音声→テキスト変換）
- [ ] 文字数・執筆進捗の可視化ダッシュボード
- [ ] AIによる章タイトル提案
- [ ] 感情曲線の自動分析・視覚化
