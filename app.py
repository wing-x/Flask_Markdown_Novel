import os
import json
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from anthropic import Anthropic
from pathlib import Path

app = Flask(__name__)
CORS(app)

# プロジェクトのルートディレクトリ
PROJECTS_DIR = Path("projects")
PROJECTS_DIR.mkdir(exist_ok=True)

# Anthropic APIクライアント（環境変数からAPIキーを取得）
# 使用時は環境変数 ANTHROPIC_API_KEY を設定してください
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# テンプレート定義
TEMPLATES = {
    "character.md": """# キャラクター設定

## 基本情報
- 名前: 
- 年齢: 
- 性別: 
- 職業: 

## 外見
- 身長: 
- 体格: 
- 髪型・髪色: 
- 目の色: 
- 特徴的な外見: 

## 性格
- 基本的な性格: 
- 長所: 
- 短所: 
- 癖・口癖: 

## 背景
- 生い立ち: 
- 家族構成: 
- 重要な過去の出来事: 

## 目標・動機
- 物語における目標: 
- その目標を持つ理由: 

## 人間関係
- 

## その他
- 
""",
    "plot.md": """# プロット

## 概要
- タイトル: 
- ジャンル: 
- テーマ: 
- 一行あらすじ: 

## 主要な登場人物
- 

## ストーリーライン

### 序盤（導入）
- 

### 中盤（展開）
- 

### 終盤（結末）
- 

## 重要なシーン
1. 
2. 
3. 

## 伏線・謎
- 

## 解決すべき課題
- 
""",
    "worldbuilding.md": """# 世界観設定

## 世界の基本設定
- 時代・時期: 
- 場所・地域: 
- 技術レベル: 
- 魔法・特殊能力: 

## 社会・文化
- 政治体制: 
- 経済システム: 
- 宗教・信仰: 
- 言語・方言: 

## 地理
- 主要な場所: 
- 気候: 
- 地形の特徴: 

## 歴史
- 重要な歴史的出来事: 

## ルール・制約
- この世界独自のルール: 
- タブー: 

## その他
- 
""",
    "timeline.md": """# タイムライン

## 物語開始前
- 

## 第1章
- 

## 第2章
- 

## 第3章
- 

## メモ
- 
"""
}


@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')


@app.route('/api/projects', methods=['GET'])
def get_projects():
    """プロジェクト一覧を取得"""
    projects = []
    for project_dir in PROJECTS_DIR.iterdir():
        if project_dir.is_dir():
            projects.append({
                'name': project_dir.name,
                'path': str(project_dir)
            })
    return jsonify(projects)


@app.route('/api/projects', methods=['POST'])
def create_project():
    """新規プロジェクトを作成"""
    data = request.json
    project_name = data.get('name')
    
    if not project_name:
        return jsonify({'error': 'プロジェクト名が必要です'}), 400
    
    project_path = PROJECTS_DIR / project_name
    
    if project_path.exists():
        return jsonify({'error': 'プロジェクトは既に存在します'}), 400
    
    # プロジェクトディレクトリ作成
    project_path.mkdir()
    
    # テンプレートファイル作成
    for filename, content in TEMPLATES.items():
        (project_path / filename).write_text(content, encoding='utf-8')
    
    # 第1章のファイルを作成
    (project_path / "chapter01.md").write_text("# 第1章\n\n", encoding='utf-8')
    
    return jsonify({
        'message': 'プロジェクトを作成しました',
        'name': project_name
    })


@app.route('/api/projects/<project_name>/files', methods=['GET'])
def get_files(project_name):
    """プロジェクト内のファイル一覧を取得"""
    project_path = PROJECTS_DIR / project_name
    
    if not project_path.exists():
        return jsonify({'error': 'プロジェクトが見つかりません'}), 404
    
    files = []
    for file_path in sorted(project_path.glob('*.md')):
        files.append({
            'name': file_path.name,
            'path': str(file_path.relative_to(PROJECTS_DIR))
        })
    
    return jsonify(files)


@app.route('/api/files/<path:file_path>', methods=['GET'])
def get_file(file_path):
    """ファイル内容を取得"""
    full_path = PROJECTS_DIR / file_path
    
    if not full_path.exists():
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    
    content = full_path.read_text(encoding='utf-8')
    return jsonify({
        'content': content,
        'path': file_path
    })


@app.route('/api/files/<path:file_path>', methods=['PUT'])
def save_file(file_path):
    """ファイルを保存"""
    data = request.json
    content = data.get('content', '')
    
    full_path = PROJECTS_DIR / file_path
    
    # ディレクトリが存在しない場合は作成
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    full_path.write_text(content, encoding='utf-8')
    
    return jsonify({'message': '保存しました'})


@app.route('/api/claude/generate', methods=['POST'])
def claude_generate():
    """Claude APIを使用してコンテンツを生成"""
    data = request.json
    prompt_type = data.get('type')
    context = data.get('context', '')
    project_name = data.get('project')
    
    # プロジェクトの関連ファイルを読み込む
    project_context = ""
    if project_name:
        project_path = PROJECTS_DIR / project_name
        if project_path.exists():
            # character.md, plot.md, worldbuilding.mdを読み込む
            for context_file in ['character.md', 'plot.md', 'worldbuilding.md']:
                file_path = project_path / context_file
                if file_path.exists():
                    content = file_path.read_text(encoding='utf-8')
                    project_context += f"\n\n## {context_file}の内容:\n{content}"
    
    # プロンプトを生成
    prompts = {
        'character': f"""以下のプロジェクト設定を参考に、魅力的なキャラクターを提案してください。

{project_context}

ユーザーの要望:
{context}

キャラクター設定のテンプレートに従って、詳細なプロフィールを作成してください。
既存のキャラクターや世界観との整合性を保ちながら、独自性のあるキャラクターにしてください。""",
        
        'plot': f"""以下のプロジェクト設定を参考に、ストーリーの展開案を提案してください。

{project_context}

現在の状況:
{context}

3つの異なる展開パターンを提示してください。それぞれの展開の利点と、物語への影響も説明してください。""",
        
        'improve': f"""以下のテキストを改善してください。

{context}

より読みやすく、魅力的な文章にしてください。改善のポイントも説明してください。""",
        
        'consistency': f"""以下のプロジェクト設定に矛盾や問題がないかチェックしてください。

{project_context}

追加の確認内容:
{context}

矛盾点、不明瞭な点、改善すべき点を指摘してください。""",
        
        'dialogue': f"""以下の設定に基づいて、キャラクター同士の対話を生成してください。

{project_context}

シチュエーション:
{context}

各キャラクターの性格や口調を反映した自然な会話を作成してください。"""
    }
    
    if prompt_type not in prompts:
        return jsonify({'error': '無効なリクエストタイプです'}), 400
    
    try:
        # Claude APIを呼び出し
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompts[prompt_type]}
            ]
        )
        
        response_text = message.content[0].text
        
        return jsonify({
            'response': response_text
        })
    
    except Exception as e:
        return jsonify({'error': f'API呼び出しエラー: {str(e)}'}), 500


@app.route('/api/claude/stream', methods=['POST'])
def claude_stream():
    """Claude APIをストリーミングで呼び出し（サーバーサイドイベント）"""
    data = request.json
    prompt = data.get('prompt', '')
    
    def generate():
        try:
            with client.messages.stream(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return app.response_class(generate(), mimetype='text/event-stream')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
