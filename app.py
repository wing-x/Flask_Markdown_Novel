from flask import Flask, request, jsonify, render_template
import anthropic
import os
import json

app = Flask(__name__)

# プロジェクトのベースディレクトリ
BASE_DIR = os.path.join(os.path.dirname(__file__), 'projects')
os.makedirs(BASE_DIR, exist_ok=True)

client = anthropic.Anthropic()

# --- ファイル管理API ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = []
    for name in os.listdir(BASE_DIR):
        if os.path.isdir(os.path.join(BASE_DIR, name)):
            projects.append(name)
    return jsonify(projects)

@app.route('/api/projects', methods=['POST'])
def create_project():
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'プロジェクト名が必要です'}), 400
    
    project_dir = os.path.join(BASE_DIR, name)
    os.makedirs(project_dir, exist_ok=True)
    
    # デフォルトファイルを作成
    defaults = {
        'character.md': '# キャラクター設定\n\n## 主人公\n\n- 名前：\n- 年齢：\n- 外見：\n- 性格：\n- 背景：\n',
        'plot.md': '# プロット\n\n## あらすじ\n\n## 第一章\n\n## 第二章\n\n## 結末\n',
    }
    for filename, content in defaults.items():
        filepath = os.path.join(project_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
    
    return jsonify({'name': name})

@app.route('/api/projects/<project>/files', methods=['GET'])
def list_files(project):
    project_dir = os.path.join(BASE_DIR, project)
    if not os.path.exists(project_dir):
        return jsonify({'error': 'プロジェクトが見つかりません'}), 404
    
    files = []
    for name in sorted(os.listdir(project_dir)):
        if name.endswith('.md'):
            files.append(name)
    return jsonify(files)

@app.route('/api/projects/<project>/files/<filename>', methods=['GET'])
def get_file(project, filename):
    filepath = os.path.join(BASE_DIR, project, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'ファイルが見つかりません'}), 404
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

@app.route('/api/projects/<project>/files/<filename>', methods=['PUT'])
def save_file(project, filename):
    filepath = os.path.join(BASE_DIR, project, filename)
    data = request.json
    content = data.get('content', '')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True})

@app.route('/api/projects/<project>/files/<filename>', methods=['POST'])
def create_file(project, filename):
    """新規ファイルを作成（既存の場合はそのまま返す）"""
    project_dir = os.path.join(BASE_DIR, project)
    os.makedirs(project_dir, exist_ok=True)
    filepath = os.path.join(BASE_DIR, project, filename)
    
    created = False
    if not os.path.exists(filepath):
        # ファイル名に応じたテンプレートを使用
        template = get_template(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        created = True
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return jsonify({'content': content, 'created': created})

def get_template(filename):
    """ファイル名に応じたテンプレートを返す"""
    templates = {
        'timeline.md': (
            '# タイムライン\n\n'
            '## 物語前史\n\n'
            '- \n\n'
            '## 第一幕\n\n'
            '| 時期 | 出来事 | 関連キャラクター |\n'
            '|------|--------|------------------|\n'
            '|      |        |                  |\n\n'
            '## 第二幕\n\n'
            '| 時期 | 出来事 | 関連キャラクター |\n'
            '|------|--------|------------------|\n'
            '|      |        |                  |\n\n'
            '## 第三幕\n\n'
            '| 時期 | 出来事 | 関連キャラクター |\n'
            '|------|--------|------------------|\n'
            '|      |        |                  |\n\n'
            '## 伏線メモ\n\n'
            '- \n'
        ),
        'worldbuilding.md': (
            '# 世界観設定\n\n'
            '## 基本設定\n\n'
            '- 時代・時期：\n'
            '- 舞台：\n'
            '- 技術レベル：\n\n'
            '## 社会・文化\n\n'
            '### 政治体制\n\n\n'
            '### 文化・風習\n\n\n'
            '## 地理\n\n'
            '### 主要な場所\n\n\n'
            '## 歴史\n\n'
            '### 重要な出来事\n\n\n'
            '## 特殊なルール・法則\n\n'
            '### 魔法・能力（該当する場合）\n\n\n'
            '### その他のルール\n\n\n'
            '## 経済・産業\n\n\n'
            '## 宗教・信仰\n\n'
        ),
        'character.md': (
            '# キャラクター設定\n\n'
            '## 主人公\n\n'
            '- 名前：\n- 年齢：\n- 外見：\n- 性格：\n- 背景：\n\n'
            '## サブキャラクター\n\n'
        ),
        'plot.md': (
            '# プロット\n\n'
            '## あらすじ\n\n\n'
            '## 第一章\n\n\n'
            '## 第二章\n\n\n'
            '## 結末\n\n'
        ),
    }
    return templates.get(filename, f'# {filename.replace(".md", "")}\n\n')

# --- プロジェクトコンテキスト取得 ---

def get_project_context(project):
    """プロジェクト内の主要ファイルを読み込んでコンテキストを作成"""
    project_dir = os.path.join(BASE_DIR, project)
    context = {}
    for fname in ['character.md', 'plot.md', 'worldbuilding.md', 'timeline.md']:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                context[fname] = f.read()
    return context

# --- Claude API ---

@app.route('/api/claude/generate', methods=['POST'])
def generate():
    data = request.json
    action = data.get('action')
    project = data.get('project', '')
    current_content = data.get('current_content', '')
    extra_context = data.get('context', '')
    
    project_context = get_project_context(project) if project else {}
    
    ctx_text = '\n\n'.join(
        f'## {k}\n{v}' for k, v in project_context.items()
    )
    
    prompts = {
        'generate_character': f"""以下のプロジェクト設定を参考に、詳細なキャラクタープロファイルを提案してください。

{ctx_text}

追加の要望: {extra_context}

以下を含む詳細なキャラクタープロファイルを作成してください：
- 基本情報（名前、年齢、外見）
- 性格と価値観
- 背景・過去
- 動機と目標
- 他キャラクターとの関係
- 特技・能力
- セリフ例""",

        'plot_development': f"""以下のプロジェクト設定を参考に、プロット展開案を提案してください。

{ctx_text}

現在の内容:
{current_content}

追加の要望: {extra_context}

以下を含むプロット展開を提案してください：
- 次の展開案（複数）
- 伏線の提案
- クライマックスへの道筋
- 読者を引きつけるポイント""",

        'generate_timeline': f"""以下のプロジェクト設定を参考に、詳細な物語タイムラインを作成してください。

{ctx_text}

追加の要望: {extra_context}

以下を含むタイムラインを作成してください：
- 物語前史（重要な背景事件）
- 各幕・章の主要イベント
- キャラクターの成長段階
- 伏線の配置と回収タイミング
- 時系列表（マークダウン表形式で）""",

        'generate_worldbuilding': f"""以下のプロジェクト設定を参考に、詳細な世界観設定を作成してください。

{ctx_text}

追加の要望: {extra_context}

以下の要素を含む世界観を構築してください：
- 世界の基本設定（時代、場所、技術レベル）
- 社会・文化・政治体制
- 地理的特徴と主要な場所
- 歴史的背景
- 独自のルールや法則
- 魔法や特殊能力（該当する場合）
- 宗教・信仰体系
- 経済システム""",

        'refine_text': f"""以下の文章を推敲してください。

{current_content}

追加の指示: {extra_context}

改善案を提示してください。元の文章の雰囲気は保ちつつ、より魅力的な表現にしてください。""",

        'consistency_check': f"""以下のプロジェクト設定の整合性をチェックしてください。

{ctx_text}

矛盾点、設定の穴、改善すべき点を指摘してください。""",

        'dialogue_simulation': f"""以下のキャラクター設定を参考に、指定されたシーンの対話を生成してください。

{ctx_text}

シーン・状況: {extra_context}

自然で、各キャラクターの個性が出た対話を書いてください。""",
    }
    
    prompt = prompts.get(action, extra_context)
    if not prompt:
        return jsonify({'error': '不明なアクション'}), 400
    
    message = client.messages.create(
        model='claude-opus-4-5',
        max_tokens=2000,
        messages=[{'role': 'user', 'content': prompt}]
    )
    
    return jsonify({'result': message.content[0].text})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
