# 小説執筆サポートエディタ

Claude APIと連携した小説執筆サポート用のマークダウンエディタです。

## 特徴

- 📝 マークダウンエディタとリアルタイムプレビュー
- 🤖 Claude APIによる執筆サポート機能
  - キャラクター設定の自動生成
  - プロット展開案の提案
  - 文章の推敲支援
  - 設定の整合性チェック
  - キャラクター対話のシミュレーション
- 📚 プロジェクト管理機能
- 🗂️ テンプレートファイル（character.md、plot.md、worldbuilding.md、timeline.md）の自動生成
- 💾 自動保存機能

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

APIキーは[Anthropic Console](https://console.anthropic.com/)で取得できます。

### 3. アプリケーションの起動

```bash
python app.py
```

ブラウザで `http://localhost:5000` にアクセスしてください。

## 使い方

### プロジェクトの作成

1. サイドバーの「+ 新規」ボタンをクリック
2. プロジェクト名を入力して「作成」をクリック
3. 自動的に以下のテンプレートファイルが生成されます：
   - `character.md` - キャラクター設定用
   - `plot.md` - プロット管理用
   - `worldbuilding.md` - 世界観設定用
   - `timeline.md` - タイムライン管理用
   - `chapter01.md` - 第1章（本文用）

### ファイルの編集

1. サイドバーからプロジェクトを選択
2. ファイル一覧から編集したいファイルをクリック
3. 左側のエディタで編集すると、右側にプレビューが表示されます
4. 変更は自動的に保存されます（3秒後）
5. 手動保存する場合は「💾 保存」ボタンをクリック

### Claude機能の使用

#### キャラクター生成
1. 「キャラクター生成」ボタンをクリック
2. テキストエリアにキャラクターの要望を入力（例：「20代の女性、明るい性格で剣士」）
3. Claudeが詳細なキャラクタープロファイルを提案
4. 「エディタに挿入」ボタンで現在のファイルに挿入

#### プロット展開案
1. plot.mdやchapterファイルで「プロット展開案」をクリック
2. 現在の状況や希望する展開を入力
3. Claudeが3つの異なる展開パターンを提案

#### 文章推敲
1. 改善したいテキストを選択（またはエディタに入力）
2. 「文章推敲」ボタンをクリック
3. Claudeが改善案を提示

#### 整合性チェック
1. 「整合性チェック」ボタンをクリック
2. プロジェクト全体の設定ファイルを分析
3. 矛盾点や改善点を指摘

#### 対話シミュレーション
1. 「対話シミュレーション」ボタンをクリック
2. シチュエーションを入力（例：「主人公と敵対者が初めて出会う場面」）
3. キャラクター設定に基づいた自然な会話を生成

## ファイル構造

```
novel_editor/
├── app.py                  # Flaskアプリケーション
├── requirements.txt        # Python依存関係
├── templates/
│   └── index.html         # メインHTML
├── static/
│   ├── css/
│   │   └── style.css      # スタイルシート
│   └── js/
│       └── app.js         # JavaScriptアプリケーション
└── projects/              # プロジェクトデータ（自動生成）
    └── [プロジェクト名]/
        ├── character.md
        ├── plot.md
        ├── worldbuilding.md
        ├── timeline.md
        └── chapter01.md
```

## API エンドポイント

### プロジェクト管理
- `GET /api/projects` - プロジェクト一覧取得
- `POST /api/projects` - 新規プロジェクト作成
- `GET /api/projects/<project_name>/files` - ファイル一覧取得

### ファイル操作
- `GET /api/files/<file_path>` - ファイル内容取得
- `PUT /api/files/<file_path>` - ファイル保存

### Claude API連携
- `POST /api/claude/generate` - コンテンツ生成
  - リクエストボディ：
    ```json
    {
      "type": "character|plot|improve|consistency|dialogue",
      "context": "追加情報",
      "project": "プロジェクト名"
    }
    ```

## カスタマイズ

### テンプレートの追加

`app.py`の`TEMPLATES`辞書に新しいテンプレートを追加できます：

```python
TEMPLATES = {
    "character.md": "...",
    "plot.md": "...",
    "your_template.md": "テンプレート内容"
}
```

### プロンプトのカスタマイズ

`app.py`の`claude_generate()`関数内の`prompts`辞書を編集することで、Claudeへの指示をカスタマイズできます。

## トラブルシューティング

### APIキーエラー
- 環境変数`ANTHROPIC_API_KEY`が正しく設定されているか確認
- APIキーが有効か確認

### ファイルが保存されない
- `projects/`ディレクトリへの書き込み権限を確認
- ブラウザのコンソールでエラーを確認

### Claude機能が動作しない
- APIクレジットが残っているか確認
- ネットワーク接続を確認
- ブラウザのコンソールでエラーメッセージを確認

## ライセンス

このプロジェクトはサンプルコードです。自由に改変・使用してください。

## 今後の拡張案

- [ ] 章の自動追加機能
- [ ] エクスポート機能（EPUB、PDF）
- [ ] 複数ユーザー対応
- [ ] バージョン管理機能
- [ ] キャラクター関係図の可視化
- [ ] ストーリーアークの視覚化
- [ ] 音声入力機能
- [ ] テーマ切り替え（ダークモード）
