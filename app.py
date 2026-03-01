from flask import Flask, request, jsonify, render_template
import anthropic
import os
import json
import shutil

app = Flask(__name__)

# プロジェクトのベースディレクトリ
BASE_DIR = os.path.join(os.path.dirname(__file__), 'projects')
os.makedirs(BASE_DIR, exist_ok=True)

client = anthropic.Anthropic()

# シリーズ関連定数
SERIES_PREFIX = '_series_'

# キャラクター生成チャットセッション管理
character_chat_sessions = {}

def get_series_dir(series_name):
    return os.path.join(BASE_DIR, SERIES_PREFIX + series_name)

def get_series_meta(series_name):
    meta_path = os.path.join(get_series_dir(series_name), '_meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'volumes': []}

def save_series_meta(series_name, meta):
    meta_path = os.path.join(get_series_dir(series_name), '_meta.json')
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

# シリーズ聖典ファイルのデフォルトテンプレート
SERIES_BIBLE_TEMPLATES = {
    'bible.md': (
        '# 世界設定バイブル\n\n'
        '## 世界の基本ルール\n\n'
        '（この世界で絶対に変わらない法則・ルールを記述）\n\n'
        '## 固有名詞辞典\n\n'
        '| 名称 | 読み | 説明 |\n'
        '|------|------|------|\n'
        '|      |      |      |\n\n'
        '## 地理・場所\n\n\n'
        '## 歴史・年表（シリーズ全体）\n\n\n'
        '## 社会・文化・制度\n\n\n'
        '## 特殊能力・魔法体系（該当する場合）\n\n'
    ),
    'characters_master.md': (
        '# キャラクターマスターシート\n\n'
        '> 各キャラの「変わらない核」のみを記録。巻ごとの変化は series_summary.md で管理する。\n\n'
        '---\n\n'
        '## 主要キャラクター\n\n'
        '### キャラ名\n\n'
        '- **役割**: \n'
        '- **外見**（不変の特徴）: \n'
        '- **性格の核**: \n'
        '- **口癖・話し方**: \n'
        '- **初登場**: 第○巻\n'
        '- **セリフサンプル**:\n'
        '  - 「」\n'
        '  - 「」\n\n'
        '---\n\n'
        '## サブキャラクター\n\n'
    ),
    'foreshadowing.md': (
        '# 伏線マスターリスト\n\n'
        '| ID | 内容 | 登場巻/章 | 状態 | 回収予定 | 関連キャラ |\n'
        '|----|------|-----------|------|----------|------------|\n'
        '| F-001 | （例）主人公の父が残した古地図 | 1巻2章 | 未回収 | 7巻以降 | 主人公、師匠 |\n\n'
        '---\n\n'
        '## 状態の定義\n\n'
        '- **未回収**: まだ解決していない\n'
        '- **回収済み**: 解決した（巻/章を記載）\n'
        '- **意図的放置**: 読者への謎として維持\n\n'
        '---\n\n'
        '## 巻をまたぐ布石メモ\n\n'
        '（次巻以降で使う予定の設定や展開の種）\n\n'
    ),
    'series_summary.md': (
        '# シリーズ巻別サマリー\n\n'
        '> 各巻を書き終えたら「巻サマリー自動生成」で追記する。\n'
        '> 過去巻はこのサマリーのみをコンテキストに使う（本文は参照しない）。\n\n'
        '---\n\n'
        '## 第1巻 タイトル\n\n'
        '**あらすじ（300字以内）**:\n\n\n'
        '**この巻で起きた主要な変化**:\n'
        '- キャラクターの変化:\n'
        '- 世界情勢の変化:\n'
        '- 解決した伏線:\n'
        '- 新たに張った伏線:\n\n'
        '**各キャラの巻末状態**:\n'
        '- キャラ名: \n\n'
        '---\n\n'
    ),
}

# --- ファイル管理API ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/projects', methods=['GET'])
def list_projects():
    projects = []
    for name in os.listdir(BASE_DIR):
        # _series_ プレフィックスのシリーズフォルダは除外
        if os.path.isdir(os.path.join(BASE_DIR, name)) and not name.startswith(SERIES_PREFIX):
            projects.append(name)
    return jsonify(sorted(projects))

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
        'character.md': '# キャラクター設定\n\n## 主人公\n\n- 名前：\n- 役割：(メインキャラクター / サブキャラクター)\n- 年齢：\n- 外見：\n- 性格：\n- 背景：\n',
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

    def scan_directory(path, prefix=''):
        """ディレクトリを再帰的にスキャンして構造を返す"""
        items = []
        for name in sorted(os.listdir(path)):
            full_path = os.path.join(path, name)
            relative_path = os.path.join(prefix, name) if prefix else name

            if os.path.isdir(full_path):
                # ディレクトリの場合
                items.append({
                    'name': name,
                    'path': relative_path,
                    'type': 'directory',
                    'children': scan_directory(full_path, relative_path)
                })
            elif name.endswith('.md') or name.endswith('.txt'):
                # .mdファイルまたは.txtファイルの場合
                items.append({
                    'name': name,
                    'path': relative_path,
                    'type': 'file'
                })
        return items

    structure = scan_directory(project_dir)
    return jsonify(structure)

@app.route('/api/projects/<project>/files/<path:filename>', methods=['GET'])
def get_file(project, filename):
    filepath = os.path.join(BASE_DIR, project, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'ファイルが見つかりません'}), 404

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

@app.route('/api/projects/<project>/files/<path:filename>', methods=['PUT'])
def save_file(project, filename):
    filepath = os.path.join(BASE_DIR, project, filename)
    data = request.json
    content = data.get('content', '')

    # ディレクトリが存在しない場合は作成
    file_dir = os.path.dirname(filepath)
    if file_dir and not os.path.exists(file_dir):
        os.makedirs(file_dir, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True})

@app.route('/api/projects/<project>/files/<path:filename>', methods=['POST'])
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

@app.route('/api/projects/<project>/files/<path:filename>', methods=['DELETE'])
def delete_file(project, filename):
    """ファイルを削除"""
    filepath = os.path.join(BASE_DIR, project, filename)
    if not os.path.exists(filepath):
        return jsonify({'error': 'ファイルが見つかりません'}), 404

    try:
        if os.path.isdir(filepath):
            shutil.rmtree(filepath)
        else:
            os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project>/rename', methods=['POST'])
def rename_file(project):
    """ファイルまたはディレクトリをリネーム"""
    data = request.json
    old_path = data.get('old_path', '')
    new_path = data.get('new_path', '')

    if not old_path or not new_path:
        return jsonify({'error': 'パスが指定されていません'}), 400

    old_filepath = os.path.join(BASE_DIR, project, old_path)
    new_filepath = os.path.join(BASE_DIR, project, new_path)

    if not os.path.exists(old_filepath):
        return jsonify({'error': '元のファイルが見つかりません'}), 404

    if os.path.exists(new_filepath):
        return jsonify({'error': '同名のファイルが既に存在します'}), 400

    try:
        # 新しいパスのディレクトリが存在しない場合は作成
        new_dir = os.path.dirname(new_filepath)
        if new_dir and not os.path.exists(new_dir):
            os.makedirs(new_dir, exist_ok=True)

        os.rename(old_filepath, new_filepath)
        return jsonify({'success': True, 'new_path': new_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project>/directories', methods=['POST'])
def create_directory(project):
    """ディレクトリを作成"""
    data = request.json
    dir_path = data.get('path', '')

    if not dir_path:
        return jsonify({'error': 'パスが指定されていません'}), 400

    full_path = os.path.join(BASE_DIR, project, dir_path)

    if os.path.exists(full_path):
        return jsonify({'error': '同名のディレクトリが既に存在します'}), 400

    try:
        os.makedirs(full_path, exist_ok=True)
        return jsonify({'success': True, 'path': dir_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project>/move', methods=['POST'])
def move_file(project):
    """ファイルを移動"""
    data = request.json
    source_path = data.get('source', '')
    dest_path = data.get('destination', '')

    if not source_path or not dest_path:
        return jsonify({'error': 'パスが指定されていません'}), 400

    source_filepath = os.path.join(BASE_DIR, project, source_path)
    dest_filepath = os.path.join(BASE_DIR, project, dest_path)

    if not os.path.exists(source_filepath):
        return jsonify({'error': '元のファイルが見つかりません'}), 404

    if os.path.exists(dest_filepath):
        return jsonify({'error': '移動先に同名のファイルが既に存在します'}), 400

    try:
        # 移動先のディレクトリが存在しない場合は作成
        dest_dir = os.path.dirname(dest_filepath)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)

        os.rename(source_filepath, dest_filepath)
        return jsonify({'success': True, 'new_path': dest_path})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
            '- 名前：\n- 役割：(メインキャラクター / サブキャラクター)\n- 年齢：\n- 外見：\n- 性格：\n- 背景：\n\n'
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

# --- シリーズ管理API ---

@app.route('/api/series', methods=['GET'])
def list_series():
    """シリーズ一覧を返す"""
    series_list = []
    for name in sorted(os.listdir(BASE_DIR)):
        if os.path.isdir(os.path.join(BASE_DIR, name)) and name.startswith(SERIES_PREFIX):
            series_name = name[len(SERIES_PREFIX):]
            series_list.append(series_name)
    return jsonify(series_list)

@app.route('/api/series', methods=['POST'])
def create_series():
    """新規シリーズを作成"""
    data = request.json
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'シリーズ名が必要です'}), 400

    series_dir = get_series_dir(name)
    if os.path.exists(series_dir):
        return jsonify({'error': '同名のシリーズが既に存在します'}), 400

    os.makedirs(series_dir, exist_ok=True)

    # 聖典ファイルをデフォルトで作成
    for fname, content in SERIES_BIBLE_TEMPLATES.items():
        fpath = os.path.join(series_dir, fname)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

    # メタ情報を初期化
    save_series_meta(name, {'volumes': []})

    return jsonify({'name': name})

@app.route('/api/series/<series>/volumes', methods=['GET'])
def list_volumes(series):
    """シリーズの巻一覧を返す"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404
    meta = get_series_meta(series)
    return jsonify(meta.get('volumes', []))

@app.route('/api/series/<series>/volumes', methods=['POST'])
def create_volume(series):
    """シリーズに新規巻を追加（通常プロジェクトとして作成し、メタ登録する）"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    data = request.json
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': '巻のタイトルが必要です'}), 400

    # 巻番号を自動採番
    meta = get_series_meta(series)
    volumes = meta.get('volumes', [])
    order = len(volumes) + 1

    # プロジェクト名：シリーズ名_vol<N>_タイトル
    project_name = f'{series}_vol{order:02d}_{title}'
    project_dir = os.path.join(BASE_DIR, project_name)

    if os.path.exists(project_dir):
        return jsonify({'error': f'プロジェクト「{project_name}」が既に存在します'}), 400

    os.makedirs(project_dir, exist_ok=True)

    # デフォルトファイルを作成
    defaults = {
        'character.md': '# キャラクター設定\n\n> シリーズ共通キャラはシリーズ聖典(characters_master.md)を参照\n> この巻固有の設定・変化のみここに記録する\n\n## この巻での変化・追加設定\n\n',
        'plot.md': f'# プロット - 第{order}巻「{title}」\n\n## あらすじ\n\n## 第一章\n\n## 結末\n',
        'worldbuilding.md': '# 世界観設定（この巻固有）\n\n> シリーズ共通設定はシリーズ聖典(bible.md)を参照\n> この巻で新登場の場所・組織・ルールのみここに記録する\n\n',
        'timeline.md': f'# タイムライン - 第{order}巻\n\n## この巻の出来事\n\n| 時期 | 出来事 | 関連キャラクター |\n|------|--------|------------------|\n|      |        |                  |\n\n## 伏線メモ（この巻）\n\n',
    }
    for filename, content in defaults.items():
        fpath = os.path.join(project_dir, filename)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)

    # メタに登録
    volumes.append({
        'order': order,
        'title': title,
        'project_name': project_name
    })
    meta['volumes'] = volumes
    save_series_meta(series, meta)

    return jsonify({'order': order, 'title': title, 'project_name': project_name})

@app.route('/api/series/<series>/files/<filename>', methods=['GET'])
def get_series_file(series, filename):
    """シリーズ聖典ファイルを取得"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    fpath = os.path.join(series_dir, filename)
    if not os.path.exists(fpath):
        return jsonify({'error': 'ファイルが見つかりません'}), 404

    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content})

@app.route('/api/series/<series>/files/<filename>', methods=['PUT'])
def save_series_file(series, filename):
    """シリーズ聖典ファイルを保存"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    data = request.json
    content = data.get('content', '')

    fpath = os.path.join(series_dir, filename)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    return jsonify({'success': True})

@app.route('/api/series/<series>/files/<filename>', methods=['POST'])
def create_series_file(series, filename):
    """シリーズ聖典ファイルを新規作成（存在する場合はそのまま返す）"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    fpath = os.path.join(series_dir, filename)
    created = False
    if not os.path.exists(fpath):
        template = SERIES_BIBLE_TEMPLATES.get(filename, f'# {filename.replace(".md", "")}\n\n')
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(template)
        created = True

    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    return jsonify({'content': content, 'created': created})


# --- 伏線管理API（JSON） ---

def get_foreshadowing_path(series_name):
    return os.path.join(get_series_dir(series_name), 'foreshadowing.json')

def load_foreshadowing(series_name):
    fpath = get_foreshadowing_path(series_name)
    if not os.path.exists(fpath):
        return {}
    with open(fpath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_foreshadowing(series_name, data):
    fpath = get_foreshadowing_path(series_name)
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def next_foreshadowing_id(data):
    """F-001 形式の次のIDを生成"""
    if not data:
        return 'F-001'
    nums = []
    for k in data.keys():
        try:
            nums.append(int(k.split('-')[1]))
        except Exception:
            pass
    return f'F-{(max(nums) + 1):03d}' if nums else 'F-001'

@app.route('/api/series/<series>/foreshadowing', methods=['GET'])
def get_foreshadowing(series):
    """伏線一覧を取得"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404
    data = load_foreshadowing(series)
    items = list(data.values())
    # status / introduced_volume でソート
    items.sort(key=lambda x: (
        {'open': 0, 'abandoned': 1, 'resolved': 2}.get(x.get('status', 'open'), 0),
        x.get('introduced_volume', 0)
    ))
    return jsonify(items)

@app.route('/api/series/<series>/foreshadowing', methods=['POST'])
def create_foreshadowing(series):
    """伏線を新規追加"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    req = request.json
    summary = req.get('summary', '').strip()
    if not summary:
        return jsonify({'error': '伏線の内容（summary）は必須です'}), 400

    data = load_foreshadowing(series)
    new_id = next_foreshadowing_id(data)

    item = {
        'id': new_id,
        'summary': summary,
        'introduced_volume': req.get('introduced_volume', 1),
        'introduced_chapter': req.get('introduced_chapter', ''),
        'status': req.get('status', 'open'),
        'resolve_target': req.get('resolve_target', ''),
        'resolved_volume': req.get('resolved_volume', ''),
        'resolved_chapter': req.get('resolved_chapter', ''),
        'related_characters': req.get('related_characters', []),
        'notes': req.get('notes', ''),
    }
    data[new_id] = item
    save_foreshadowing(series, data)
    return jsonify(item), 201

@app.route('/api/series/<series>/foreshadowing/<item_id>', methods=['PUT'])
def update_foreshadowing(series, item_id):
    """伏線を更新"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    data = load_foreshadowing(series)
    if item_id not in data:
        return jsonify({'error': f'{item_id} が見つかりません'}), 404

    req = request.json
    item = data[item_id]
    for field in ['summary', 'introduced_volume', 'introduced_chapter',
                  'status', 'resolve_target', 'resolved_volume',
                  'resolved_chapter', 'related_characters', 'notes']:
        if field in req:
            item[field] = req[field]

    data[item_id] = item
    save_foreshadowing(series, data)
    return jsonify(item)

@app.route('/api/series/<series>/foreshadowing/<item_id>', methods=['DELETE'])
def delete_foreshadowing(series, item_id):
    """伏線を削除"""
    series_dir = get_series_dir(series)
    if not os.path.exists(series_dir):
        return jsonify({'error': 'シリーズが見つかりません'}), 404

    data = load_foreshadowing(series)
    if item_id not in data:
        return jsonify({'error': f'{item_id} が見つかりません'}), 404

    del data[item_id]
    save_foreshadowing(series, data)
    return jsonify({'success': True, 'deleted_id': item_id})

# --- プロジェクトコンテキスト取得 ---

def detect_series_from_project(project_name):
    """プロジェクト名からシリーズ名を自動検出する。
    命名規則: {series}_vol{N}_{title} → series名を返す。
    シリーズに属さない場合は None を返す。
    """
    import re
    # _vol01_ / _vol1_ 形式を検出
    m = re.match(r'^(.+?)_vol\d+_', project_name)
    if m:
        candidate = m.group(1)
        series_dir = get_series_dir(candidate)
        if os.path.isdir(series_dir):
            return candidate
    return None


def _read_and_trim(fpath, char_limit):
    """ファイルを読み込み、char_limit を超える場合は後半を省略する"""
    if not os.path.exists(fpath):
        return None
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    if len(content) > char_limit:
        content = content[:char_limit] + f'\n\n... （{len(content) - char_limit}字省略）'
    return content


def get_series_context(series_name, char_limit_total=20000):
    """シリーズ聖典を読み込む。
    - bible.md / characters_master.md / foreshadowing.md / series_summary.md
    - 各ファイルを均等に char_limit_total へ収める
    """
    series_dir = get_series_dir(series_name)
    files = ['bible.md', 'characters_master.md', 'foreshadowing.md', 'series_summary.md']
    per_file_limit = char_limit_total // len(files)

    context = {}
    for fname in files:
        fpath = os.path.join(series_dir, fname)
        content = _read_and_trim(fpath, per_file_limit)
        if content:
            context[f'[シリーズ聖典] {fname}'] = content
    return context


def get_volume_context(project, include_plot=True, char_limit_total=10000):
    """巻固有のコンテキストを読み込む。
    - character.md / worldbuilding.md / timeline.md（+ オプションで plot.md）
    - plot.md は他より長いため別枠で扱う
    """
    project_dir = os.path.join(BASE_DIR, project)
    support_files = ['character.md', 'worldbuilding.md', 'timeline.md']
    per_file_limit = char_limit_total // len(support_files)

    context = {}
    for fname in support_files:
        fpath = os.path.join(project_dir, fname)
        content = _read_and_trim(fpath, per_file_limit)
        if content:
            context[f'[この巻の設定] {fname}'] = content

    if include_plot:
        fpath = os.path.join(project_dir, 'plot.md')
        # plot.md はあらすじ部分のみに絞る（最大4000字）
        content = _read_and_trim(fpath, 4000)
        if content:
            context['[この巻のプロット] plot.md'] = content

    return context


def build_context_text(project, series=None, include_plot=True):
    """Claude に渡すコンテキストテキストを組み立てる。
    - シリーズ所属のプロジェクトなら、シリーズ聖典（~2万字）＋巻固有設定（~1万字）
    - 単体プロジェクトなら従来どおり全ファイル（上限付き）
    Returns:
        ctx_text (str), context_summary (str)
    """
    # シリーズを自動検出（明示的に渡されない場合）
    if series is None:
        series = detect_series_from_project(project)

    context = {}

    if series:
        # ① シリーズ聖典（共通・最大2万字）
        context.update(get_series_context(series, char_limit_total=20000))
        # ② 巻固有設定（最大1万字）
        context.update(get_volume_context(project, include_plot=include_plot, char_limit_total=10000))
        summary = f'シリーズ「{series}」／巻プロジェクト「{project}」の階層コンテキストを使用'
    else:
        # 単体プロジェクト：従来どおりだが文字数上限を設ける
        project_dir = os.path.join(BASE_DIR, project)
        for fname in ['character.md', 'worldbuilding.md', 'timeline.md']:
            fpath = os.path.join(project_dir, fname)
            content = _read_and_trim(fpath, 3000)
            if content:
                context[fname] = content
        if include_plot:
            fpath = os.path.join(project_dir, 'plot.md')
            content = _read_and_trim(fpath, 4000)
            if content:
                context['plot.md'] = content
        summary = f'単体プロジェクト「{project}」のコンテキストを使用'

    ctx_text = '\n\n'.join(f'## {k}\n{v}' for k, v in context.items())
    return ctx_text, summary


def get_project_context(project):
    """後方互換用ラッパー（既存呼び出し箇所が残る場合に備える）"""
    project_dir = os.path.join(BASE_DIR, project)
    context = {}
    for fname in ['character.md', 'plot.md', 'worldbuilding.md', 'timeline.md']:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                context[fname] = f.read()
    return context

# --- Claude API ---

def generate_plot_template(draft_content):
    """plot_draft.mdの構造を解析して動的なプロットテンプレートを生成"""
    import re

    # 数字を漢数字に変換
    def num_to_kanji(n):
        kanji_map = ['', '一', '二', '三', '四', '五', '六', '七', '八', '九']
        if n <= 9:
            return kanji_map[n]
        elif n == 10:
            return '十'
        elif n < 20:
            return '十' + kanji_map[n - 10]
        elif n < 100:
            tens = n // 10
            ones = n % 10
            return kanji_map[tens] + '十' + (kanji_map[ones] if ones > 0 else '')
        else:
            return str(n)  # 100以上は数字で返す

    # plot_draftから構造を解析
    # 部構造（## 第一部「...」 または ## ■ 第一部... など）- タイトルも取得
    # タイトルはオプショナル（「」や『』で囲まれている場合と囲まれていない場合の両方に対応）
    part_pattern = re.compile(r'^##\s+(?:■\s+)?第([一二三四五六七八九十\d]+)部[「『]([^」』]+)[」』]', re.MULTILINE)
    # 章構造（## 第1章「...」 または ### 第1章「...」 など）- タイトルも取得
    chapter_pattern = re.compile(r'^#{2,3}\s+第(\d+|[一二三四五六七八九十]+)章(?:[「『]([^」』\n]+)[」』])?', re.MULTILINE)
    # エピローグ
    epilogue_pattern = re.compile(r'^###\s+エピローグ', re.MULTILINE)

    # 部構造を検出
    parts = list(part_pattern.finditer(draft_content))
    chapters = list(chapter_pattern.finditer(draft_content))
    has_epilogue = epilogue_pattern.search(draft_content) is not None

    template = "# プロット\n\n## あらすじ\n\n"

    if parts:
        # 部構造がある場合
        KANJI_TO_NUM = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        }

        for i, part_match in enumerate(parts):
            part_num_str = part_match.group(1)
            part_title = part_match.group(2) if part_match.group(2) else ""
            part_num = int(part_num_str) if part_num_str.isdigit() else KANJI_TO_NUM.get(part_num_str, i + 1)

            # この部の範囲を取得
            part_start = part_match.start()
            part_end = parts[i + 1].start() if i + 1 < len(parts) else len(draft_content)
            part_content = draft_content[part_start:part_end]

            # この部内の章を検出（マッチオブジェクトも取得）
            part_chapter_matches = list(chapter_pattern.finditer(part_content))

            # 部の見出しを追加（タイトルがあれば含める）
            if part_title.strip():
                template += f"\n## 第{num_to_kanji(part_num)}部「{part_title.strip()}」\n\n"
            else:
                template += f"\n## 第{num_to_kanji(part_num)}部\n\n"

            for ch_match in part_chapter_matches:
                ch_num_str = ch_match.group(1)
                ch_title = ch_match.group(2) if ch_match.group(2) else ""

                if ch_num_str.isdigit():
                    ch_num = int(ch_num_str)
                else:
                    # 漢数字を数値に変換
                    if '十' in ch_num_str:
                        parts_split = ch_num_str.split('十')
                        tens = KANJI_TO_NUM.get(parts_split[0], 1) if parts_split[0] else 1
                        ones = KANJI_TO_NUM.get(parts_split[1], 0) if len(parts_split) > 1 and parts_split[1] else 0
                        ch_num = tens * 10 + ones
                    else:
                        ch_num = KANJI_TO_NUM.get(ch_num_str, 0)

                # 章の見出しを追加（タイトルがあれば含める）
                if ch_title.strip():
                    template += f"\n### 第{num_to_kanji(ch_num)}章「{ch_title.strip()}」\n\n"
                else:
                    template += f"\n### 第{num_to_kanji(ch_num)}章\n\n"

    else:
        # 部構造がない場合は通常の章のみ
        KANJI_TO_NUM = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        }

        # finditer()を使ってマッチオブジェクトを取得
        chapter_matches = list(chapter_pattern.finditer(draft_content))

        if chapter_matches:
            # 章番号とタイトルを取得して出力
            for ch_match in chapter_matches:
                ch_num_str = ch_match.group(1)
                ch_title = ch_match.group(2) if ch_match.group(2) else ""

                if ch_num_str.isdigit():
                    ch_num = int(ch_num_str)
                else:
                    # 漢数字を数値に変換
                    if '十' in ch_num_str:
                        parts_split = ch_num_str.split('十')
                        tens = KANJI_TO_NUM.get(parts_split[0], 1) if parts_split[0] else 1
                        ones = KANJI_TO_NUM.get(parts_split[1], 0) if len(parts_split) > 1 and parts_split[1] else 0
                        ch_num = tens * 10 + ones
                    else:
                        ch_num = KANJI_TO_NUM.get(ch_num_str, 0)

                # 章の見出しを追加（タイトルがあれば含める）
                if ch_title.strip():
                    template += f"\n## 第{num_to_kanji(ch_num)}章「{ch_title.strip()}」\n\n"
                else:
                    template += f"\n## 第{num_to_kanji(ch_num)}章\n\n"
        else:
            # 章が見つからない場合はデフォルトで5章生成
            for i in range(1, 6):
                template += f"\n## 第{num_to_kanji(i)}章\n\n"

    # エピローグを追加
    if has_epilogue:
        template += "\n## エピローグ\n\n"

    # 結末を追加
    template += "\n## 結末\n"

    return template

@app.route('/api/claude/draft_to_plot', methods=['POST'])
def draft_to_plot():
    """plot_draft.md の内容を読み込み、テンプレートに沿った plot.md を生成・保存する"""
    import re

    data = request.json
    project = data.get('project', '')
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot_draft.md を読み込む
    draft_path = os.path.join(project_dir, 'plot_draft.md')
    if not os.path.exists(draft_path):
        return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read().strip()

    if not draft_content or draft_content == '# plot_draft':
        return jsonify({'error': 'plot_draft.md に内容が書かれていません'}), 400

    # plot_draft.mdの構造を解析して動的にテンプレートを生成
    plot_template = generate_plot_template(draft_content)

    prompt = f"""以下の「プロット草稿」を読み込み、指定された「出力テンプレート」の各セクションを埋めてください。

## プロット草稿
{draft_content}

## 出力テンプレート（この構造を厳守し、マークダウン形式で出力すること）
{plot_template}

### 指示
- テンプレートの見出し（# ## など）はそのまま維持してください
- **テンプレートに記載された章のみを出力してください。勝手に章を追加しないこと**
- 草稿の内容を適切に各セクションへ振り分けてください
- **各章の粗筋は500～1000文字程度で記述してください**
  - 主要な出来事、登場人物の行動、会話の要点、感情の動きを含めてください
  - 具体的なシーン描写や重要な伏線を明記してください
  - 章の冒頭・中盤・結末の流れがわかるように構成してください
- あらすじは全体の物語を簡潔にまとめてください（300～500文字程度）
- 結末セクションは物語の締めくくりとして200～400文字程度で記述してください
- 草稿に記載のない項目は、文脈から自然に補完してください
- 出力はテンプレートのマークダウンのみとし、説明文や前置きは一切不要です"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=30000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0  # 10分のタイムアウト
    )

    generated = message.content[0].text.strip()

    # plot.md として保存
    plot_path = os.path.join(project_dir, 'plot.md')
    with open(plot_path, 'w', encoding='utf-8') as f:
        f.write(generated)

    return jsonify({'content': generated, 'saved': True})

@app.route('/api/claude/plot_draft_to_timeline', methods=['POST'])
def plot_draft_to_timeline():
    """plot_draft.md からタイムラインを生成して timeline.md に保存する"""
    data = request.json
    project = data.get('project', '')
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot_draft.md を読み込む
    draft_path = os.path.join(project_dir, 'plot_draft.md')
    if not os.path.exists(draft_path):
        return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read().strip()

    if not draft_content or draft_content == '# plot_draft':
        return jsonify({'error': 'plot_draft.md に内容が書かれていません'}), 400

    prompt = f"""以下のプロット展開案を読み込み、詳細なタイムラインを作成してください。

## プロット展開案
{draft_content}

## 出力形式

以下の形式に厳密に従って、タイムラインを作成してください：

# タイムライン

## 物語前史

- [重要な背景事件]
- [キャラクターの過去の出来事]

## 第一幕（または第一部）

| 時期 | 出来事 | 関連キャラクター |
|------|--------|------------------|
| [時期] | [出来事の詳細] | [キャラクター名] |

## 第二幕（または第二部）

| 時期 | 出来事 | 関連キャラクター |
|------|--------|------------------|
| [時期] | [出来事の詳細] | [キャラクター名] |

（プロットの構造に応じて幕/部の数を調整）

## 伏線メモ

| 伏線 | 設置時期 | 回収時期 | 備考 |
|------|----------|----------|------|
| [伏線の内容] | [章/場面] | [章/場面] | [詳細] |

## キャラクター成長の段階

### [キャラクター名]
- 物語開始時：[状態]
- 転換点1（第○章）：[変化]
- 転換点2（第○章）：[変化]
- 物語終了時：[状態]

### 指示事項

1. プロット展開案の章構成に基づいて、時系列を整理してください
2. 各出来事の時期を具体的に記述してください
3. 伏線の設置と回収のタイミングを明確にしてください
4. 主要キャラクターの成長段階を追跡してください
5. マークダウン形式で出力し、上記のフォーマットを厳守してください"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=10000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0
    )

    generated = message.content[0].text.strip()

    # timeline.md として保存
    timeline_path = os.path.join(project_dir, 'timeline.md')
    with open(timeline_path, 'w', encoding='utf-8') as f:
        f.write(generated)

    return jsonify({'content': generated, 'saved': True})

@app.route('/api/claude/plot_draft_to_worldbuilding', methods=['POST'])
def plot_draft_to_worldbuilding():
    """plot_draft.md から世界観設定を生成して worldbuilding.md に保存する"""
    data = request.json
    project = data.get('project', '')
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot_draft.md を読み込む
    draft_path = os.path.join(project_dir, 'plot_draft.md')
    if not os.path.exists(draft_path):
        return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read().strip()

    if not draft_content or draft_content == '# plot_draft':
        return jsonify({'error': 'plot_draft.md に内容が書かれていません'}), 400

    prompt = f"""以下のプロット展開案を読み込み、物語の舞台となる世界観設定を作成してください。

## プロット展開案
{draft_content}

## 出力形式

以下の形式に厳密に従って、世界観設定を作成してください：

# 世界観設定

## 基本設定

- 時代・時期：[時代設定]
- 舞台：[場所の説明]
- 技術レベル：[現代/未来/過去など]

## 社会・文化

### 政治体制
[政治体制の説明]

### 文化・風習
[文化や風習の説明]

### 教育制度（該当する場合）
[教育制度の説明]

## 地理

### 主要な場所

**[場所名1]**
- 説明：[詳細]
- 物語での役割：[役割]

**[場所名2]**
- 説明：[詳細]
- 物語での役割：[役割]

## 歴史

### 重要な出来事
[過去の重要な出来事]

## 特殊なルール・法則

### [該当する特殊要素があれば記載]
[説明]

### その他のルール
[社会のルールや慣習]

## 経済・産業

[経済状況や主要産業]

## 宗教・信仰

[宗教や信仰について]

## 物語固有の設定

[この物語特有の世界観要素]

### 指示事項

1. プロット展開案から読み取れる世界観要素を抽出してください
2. 物語の舞台となる場所や組織について具体的に記述してください
3. プロットで言及されている社会構造や制度を詳細化してください
4. 物語のテーマや雰囲気に合った世界観を構築してください
5. マークダウン形式で出力し、上記のフォーマットを厳守してください"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=10000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0
    )

    generated = message.content[0].text.strip()

    # worldbuilding.md として保存
    worldbuilding_path = os.path.join(project_dir, 'worldbuilding.md')
    with open(worldbuilding_path, 'w', encoding='utf-8') as f:
        f.write(generated)

    return jsonify({'content': generated, 'saved': True})

@app.route('/api/claude/plot_draft_to_characters', methods=['POST'])
def plot_draft_to_characters():
    """plot_draft.md から追加キャラクターリストを抽出する"""
    data = request.json
    project = data.get('project', '')
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot_draft.md を読み込む
    draft_path = os.path.join(project_dir, 'plot_draft.md')
    if not os.path.exists(draft_path):
        return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read().strip()

    if not draft_content or draft_content == '# plot_draft':
        return jsonify({'error': 'plot_draft.md に内容が書かれていません'}), 400

    prompt = f"""以下のプロット展開案から、「登場人物の追加設定」セクションに記載されているキャラクターの名前を全て抽出してください。

## プロット展開案
{draft_content}

## 抽出方法

1. 「## 登場人物の追加設定」というセクションを探してください
2. その配下にある「###」で始まる見出しからキャラクター名を抽出してください
3. キャラクター名は通常「名前（読み仮名）」の形式で記載されています
4. 読み仮名の部分は除外し、漢字表記の名前のみを抽出してください

例：「### 東條 蒼（とうじょう あおい）」→「東條 蒼」

## 出力形式

キャラクター名のみをJSON配列形式で出力してください。
例: ["東條 蒼", "瀬川 文子", "神谷 遥"]

- キャラクター名のみを抽出し、説明文は含めないでください
- 読み仮名や職業などの補足情報は含めないでください
- 「登場人物の追加設定」セクションが存在しない場合は空の配列 [] を返してください
- JSON配列のみを出力し、他の説明文は一切不要です"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=60.0
    )

    generated = message.content[0].text.strip()

    # JSON形式のレスポンスをパース
    try:
        import json
        import re

        # ```json などのマークダウンコードブロックを除去
        json_match = re.search(r'\[.*\]', generated, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            characters = json.loads(json_str)
            return jsonify({'characters': characters})
        else:
            characters = json.loads(generated)
            return jsonify({'characters': characters})
    except Exception as e:
        # デバッグ用にエラーメッセージを返す
        return jsonify({'characters': [], 'debug': generated, 'error': str(e)})

@app.route('/api/character/list', methods=['POST'])
def list_characters_from_file():
    """character.md からキャラクター名のリストを抽出する"""
    data = request.json
    project = data.get('project', '')

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)
    character_path = os.path.join(project_dir, 'character.md')

    if not os.path.exists(character_path):
        return jsonify({'characters': []})

    with open(character_path, 'r', encoding='utf-8') as f:
        character_content = f.read().strip()

    if not character_content:
        return jsonify({'characters': []})

    # Claude APIを使ってキャラクター名を抽出
    prompt = f"""以下のキャラクター設定ファイルから、登場するすべてのキャラクター名を抽出してください。

{character_content}

キャラクター名のみをJSON配列形式で出力してください。
例: ["太郎", "花子", "次郎"]

- キャラクター名のみを抽出し、説明文は含めないでください
- 見出し（##など）の後に記載されているキャラクター名を抽出してください
- JSON配列のみを出力し、他の説明文は一切不要です"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=1000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=60.0
    )

    generated = message.content[0].text.strip()

    # JSON形式のレスポンスをパース
    try:
        import json
        import re

        # ```json などのマークダウンコードブロックを除去
        json_match = re.search(r'\[.*\]', generated, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            characters = json.loads(json_str)
            return jsonify({'characters': characters})
        else:
            characters = json.loads(generated)
            return jsonify({'characters': characters})
    except Exception as e:
        return jsonify({'characters': [], 'debug': generated, 'error': str(e)})

@app.route('/api/claude/generate_character_from_draft', methods=['POST'])
def generate_character_from_draft():
    """plot_draft.md の情報を元に特定のキャラクターの詳細設定を生成する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None   # ★
    character_name = data.get('character_name', '')

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not character_name:
        return jsonify({'error': 'キャラクター名が指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot_draft.md を読み込む
    draft_path = os.path.join(project_dir, 'plot_draft.md')
    if not os.path.exists(draft_path):
        return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

    with open(draft_path, 'r', encoding='utf-8') as f:
        draft_content = f.read().strip()

    # ★ シリーズ聖典があれば追加コンテキストとして使う
    series_ctx_text = ''
    if series or detect_series_from_project(project):
        s = series or detect_series_from_project(project)
        series_ctx, _ = build_context_text(project, series=s, include_plot=False)
        if series_ctx:
            series_ctx_text = f'\n\n## シリーズ共通設定（既存キャラクターとの整合性を保つこと）\n{series_ctx}'

    # 既存のcharacter.mdを読み込む
    character_path = os.path.join(project_dir, 'character.md')
    existing_characters_text = ''
    if os.path.exists(character_path):
        with open(character_path, 'r', encoding='utf-8') as f:
            existing_characters_content = f.read().strip()
            if existing_characters_content:
                existing_characters_text = f"""

## 既存キャラクター情報
以下は既に作成されているキャラクターです。これらとの関係性や整合性を考慮してください：

{existing_characters_content}
"""

    prompt = f"""以下のプロット展開案から「{character_name}」というキャラクターの情報を抽出し、詳細なキャラクタープロファイルを作成してください。
{series_ctx_text}

## プロット展開案
{draft_content}

{existing_characters_text}

## 出力形式

以下のフォーマットに厳密に従って、詳細なキャラクタープロファイルを作成してください：

# キャラクター設定

## 基本情報
- 名前: {character_name}
- 役割: (プロットから判断してメインキャラクターまたはサブキャラクター)
- 年齢: (プロットに記載があれば使用、なければ推測)
- 性別: (プロットから判断)
- 職業: (プロットから判断)

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
- (プロットから読み取れる他キャラクターとの関係を記載)

## その他
- (プロットに記載されている追加情報)

### 指示事項

1. プロット展開案に記載されている{character_name}の情報を最大限活用してください
2. プロットに記載がない項目は、物語の世界観とテーマに合わせて自然に補完してください
3. キャラクターの物語での役割を明確にしてください
4. マークダウン形式で出力し、説明文や前置きは不要です"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=5000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=300.0
    )

    generated = message.content[0].text.strip()

    return jsonify({'result': generated})

@app.route('/api/claude/character_chat_start', methods=['POST'])
def character_chat_start():
    """キャラクター生成のチャットセッションを開始する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None
    character_name = data.get('character_name', '')
    character_role = data.get('character_role', '')  # 新規作成モード用
    mode = data.get('mode', 'from_draft')  # from_draft, new, edit_existing

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    # 新規作成モードでキャラクター名が指定されていない場合は後で生成
    if mode == 'from_draft' and not character_name:
        return jsonify({'error': 'キャラクター名が指定されていません'}), 400

    # 既存キャラクター修正モードではキャラクター名が必須
    if mode == 'edit_existing' and not character_name:
        return jsonify({'error': 'キャラクター名が指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # シリーズ聖典があれば追加コンテキストとして使う
    series_ctx_text = ''
    if series or detect_series_from_project(project):
        s = series or detect_series_from_project(project)
        series_ctx, _ = build_context_text(project, series=s, include_plot=False)
        if series_ctx:
            series_ctx_text = f'\n\n## シリーズ共通設定（既存キャラクターとの整合性を保つこと）\n{series_ctx}'

    # 既存のcharacter.mdを読み込む
    character_path = os.path.join(project_dir, 'character.md')
    existing_characters = ''
    if os.path.exists(character_path):
        with open(character_path, 'r', encoding='utf-8') as f:
            existing_characters = f.read().strip()

    character_info_section = ""
    if existing_characters:
        character_info_section = f"""

## 既存キャラクター情報
以下は既に作成されているキャラクターです。必要に応じて参照し、関係性や整合性を考慮してください：

{existing_characters}
"""

    # モードに応じてプロンプトを構築
    if mode == 'new':
        # 新規作成モード
        plot_path = os.path.join(project_dir, 'plot.md')
        plot_content = ''
        if os.path.exists(plot_path):
            with open(plot_path, 'r', encoding='utf-8') as f:
                plot_content = f.read().strip()

        plot_info_section = f"## プロット情報\n{plot_content}" if plot_content else ""

        system_prompt = f"""あなたは小説のキャラクター設定を作成するアシスタントです。
ユーザーと対話しながら、{character_role}の詳細なプロファイルを作成します。

{series_ctx_text}

{plot_info_section}

{character_info_section}

## 役割
1. {character_role}として魅力的なキャラクタープロファイルの初案を提示してください
2. キャラクター名も含めて提案してください
3. ユーザーが既存キャラクターとの関係性を指定した場合（例：「主人公のライバル」）、既存キャラクター情報を参照して整合性のあるキャラクターを作成してください
4. ユーザーからの修正要望に応じて、キャラクター設定を調整してください
5. 常に以下のフォーマットでキャラクター情報を出力してください："""

        initial_user_message = f'{character_role}のキャラクター設定を提案してください。キャラクター名も含めて提案してください。'

    elif mode == 'edit_existing':
        # 既存キャラクター修正モード
        system_prompt = f"""あなたは小説のキャラクター設定を修正・改善するアシスタントです。
ユーザーと対話しながら、「{character_name}」というキャラクターの設定を修正します。

{series_ctx_text}

## 既存キャラクター情報
{existing_characters}

## 役割
1. 上記の既存キャラクター情報から「{character_name}」の現在の設定を抽出して提示してください
2. ユーザーからの修正要望（例：「年齢を変更」「性格をもっと明るく」など）に応じて設定を調整してください
3. 他のキャラクターとの整合性を保ちながら修正してください
4. 常に以下のフォーマットでキャラクター情報を出力してください："""

        initial_user_message = f'「{character_name}」の現在の設定を提示してください。'

    else:
        # plot_draftから生成モード
        draft_path = os.path.join(project_dir, 'plot_draft.md')
        if not os.path.exists(draft_path):
            return jsonify({'error': 'plot_draft.md がプロジェクト内に見つかりません'}), 404

        with open(draft_path, 'r', encoding='utf-8') as f:
            draft_content = f.read().strip()

        system_prompt = f"""あなたは小説のキャラクター設定を作成するアシスタントです。
ユーザーと対話しながら、「{character_name}」というキャラクターの詳細なプロファイルを作成します。

以下のプロット展開案を参考にしてください：
{series_ctx_text}

## プロット展開案
{draft_content}

{character_info_section}

## 役割
1. プロット展開案から{character_name}の情報を抽出し、詳細なキャラクタープロファイルの初案を提示してください
2. 既存キャラクター情報がある場合は、それらとの関係性や整合性を考慮してください
3. ユーザーからの修正要望に応じて、キャラクター設定を調整してください
4. 常に以下のフォーマットでキャラクター情報を出力してください："""

        initial_user_message = f'{character_name}のキャラクター設定を提案してください。'

    # 共通のフォーマット部分を追加
    system_prompt += """

# キャラクター設定

## 基本情報
- 名前:
- 役割:
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
- (他キャラクターとの関係)

## その他
- (追加情報)

## 指示事項
- ユーザーの修正要望には柔軟に対応してください
- 修正時は、変更した部分を明確にしてください
- 物語の世界観との整合性を保ってください"""

    # 初回のキャラクター情報を生成
    initial_message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=5000,
        system=system_prompt,
        messages=[{'role': 'user', 'content': initial_user_message}],
        timeout=300.0
    )

    initial_response = initial_message.content[0].text.strip()

    # セッションIDを生成
    import time
    session_name = character_name if character_name else character_role
    session_id = f"{project}_{session_name}_{int(time.time())}"

    # セッション情報を保存
    character_chat_sessions[session_id] = {
        'project': project,
        'series': series,
        'character_name': character_name if character_name else '新規キャラクター',
        'system_prompt': system_prompt,
        'messages': [
            {'role': 'user', 'content': initial_user_message},
            {'role': 'assistant', 'content': initial_response}
        ]
    }

    return jsonify({
        'session_id': session_id,
        'response': initial_response
    })

@app.route('/api/claude/character_chat_continue', methods=['POST'])
def character_chat_continue():
    """キャラクター生成チャットを継続する"""
    data = request.json
    session_id = data.get('session_id', '')
    user_message = data.get('message', '')

    if not session_id or session_id not in character_chat_sessions:
        return jsonify({'error': '無効なセッションIDです'}), 400

    if not user_message:
        return jsonify({'error': 'メッセージが空です'}), 400

    session = character_chat_sessions[session_id]

    # メッセージ履歴に追加
    session['messages'].append({'role': 'user', 'content': user_message})

    # Claude APIを呼び出し
    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=5000,
        system=session['system_prompt'],
        messages=session['messages'],
        timeout=300.0
    )

    response = message.content[0].text.strip()

    # レスポンスをメッセージ履歴に追加
    session['messages'].append({'role': 'assistant', 'content': response})

    return jsonify({'response': response})

@app.route('/api/claude/character_chat_finalize', methods=['POST'])
def character_chat_finalize():
    """チャットで作成したキャラクター情報を確定して保存する"""
    data = request.json
    session_id = data.get('session_id', '')

    if not session_id or session_id not in character_chat_sessions:
        return jsonify({'error': '無効なセッションIDです'}), 400

    session = character_chat_sessions[session_id]

    # 最終的なキャラクター情報を取得（最後のアシスタントのメッセージ）
    final_character_info = None
    for msg in reversed(session['messages']):
        if msg['role'] == 'assistant':
            final_character_info = msg['content']
            break

    if not final_character_info:
        return jsonify({'error': 'キャラクター情報が見つかりません'}), 400

    # セッションを削除
    del character_chat_sessions[session_id]

    return jsonify({
        'result': final_character_info,
        'message': 'キャラクター情報を確定しました'
    })

@app.route('/api/claude/character_chat_cancel', methods=['POST'])
def character_chat_cancel():
    """キャラクター生成チャットをキャンセルする"""
    data = request.json
    session_id = data.get('session_id', '')

    if not session_id or session_id not in character_chat_sessions:
        return jsonify({'error': '無効なセッションIDです'}), 400

    # セッションを削除
    del character_chat_sessions[session_id]

    return jsonify({'message': 'チャットセッションをキャンセルしました'})

@app.route('/api/claude/generate_catchcopy', methods=['POST'])
def generate_catchcopy():
    """plot.md の内容を読み込み、魅力的なキャッチコピーを生成して catchcopy.md に保存する"""
    data = request.json
    project = data.get('project', '')
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot.md を読み込む
    plot_path = os.path.join(project_dir, 'plot.md')
    if not os.path.exists(plot_path):
        return jsonify({'error': 'plot.md がプロジェクト内に見つかりません'}), 404

    with open(plot_path, 'r', encoding='utf-8') as f:
        plot_content = f.read().strip()

    if not plot_content or plot_content == '# プロット':
        return jsonify({'error': 'plot.md に内容が書かれていません'}), 400

    prompt = f"""以下のプロットを読み込み、この物語の魅力を端的に表現するキャッチコピーを複数提案してください。

## プロット
{plot_content}

### 指示
- 物語の核心となるテーマやコンセプトを捉えたキャッチコピーを提案してください
- 以下の3つのタイプでそれぞれ3案ずつ、計9案を提案してください：
  1. **短編型（10〜20文字程度）**: インパクト重視の短いコピー
  2. **中編型（20〜40文字程度）**: 物語の雰囲気を伝えるコピー
  3. **長編型（40〜60文字程度）**: ストーリーの魅力を具体的に伝えるコピー
- それぞれのコピーに簡単な解説（なぜこのコピーを選んだか）を添えてください
- 出力はマークダウン形式で、以下のフォーマットに従ってください：

# キャッチコピー案

## 短編型（10〜20文字）

### 案1
[キャッチコピー]

**解説**: [解説文]

### 案2
[キャッチコピー]

**解説**: [解説文]

### 案3
[キャッチコピー]

**解説**: [解説文]

## 中編型（20〜40文字）

### 案1
[キャッチコピー]

**解説**: [解説文]

### 案2
[キャッチコピー]

**解説**: [解説文]

### 案3
[キャッチコピー]

**解説**: [解説文]

## 長編型（40〜60文字）

### 案1
[キャッチコピー]

**解説**: [解説文]

### 案2
[キャッチコピー]

**解説**: [解説文]

### 案3
[キャッチコピー]

**解説**: [解説文]"""

    message = client.messages.create(
        model='claude-opus-4-6',
        max_tokens=10000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0
    )

    generated = message.content[0].text.strip()

    # catchcopy.md として保存
    catchcopy_path = os.path.join(project_dir, 'catchcopy.md')
    with open(catchcopy_path, 'w', encoding='utf-8') as f:
        f.write(generated)

    return jsonify({'content': generated, 'saved': True})


def kanji_to_number(kanji_str, kanji_map):
    """漢数字を数値に変換する関数"""
    if '十' in kanji_str:
        parts = kanji_str.split('十')
        # 「十」だけの場合は10
        if kanji_str == '十':
            return 10
        # 「十五」のような場合（10 + 5 = 15）
        if not parts[0]:
            tens = 1
        else:
            tens = kanji_map.get(parts[0], 1)

        if len(parts) > 1 and parts[1]:
            ones = kanji_map.get(parts[1], 0)
        else:
            ones = 0

        return tens * 10 + ones
    else:
        # 単純な一桁の漢数字
        return kanji_map.get(kanji_str, 0)

@app.route('/api/claude/generate_chapters', methods=['POST'])
def generate_chapters():
    """plot.md の各章を解析し、chapter01.txt, chapter02.txt ... として本文を生成・保存する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None   # ★ フロントから渡されたシリーズ名
    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    project_dir = os.path.join(BASE_DIR, project)

    # plot.md を読み込む
    plot_path = os.path.join(project_dir, 'plot.md')
    if not os.path.exists(plot_path):
        return jsonify({'error': 'plot.md がプロジェクト内に見つかりません'}), 404

    with open(plot_path, 'r', encoding='utf-8') as f:
        plot_content = f.read().strip()

    # ★ 階層コンテキストを構築（plot.md は章ごとのプロンプトで個別に渡すため除外）
    ctx_text, ctx_summary = build_context_text(project, series=series, include_plot=False)

    # 後続ロジックで char_ctx / world_ctx として使えるよう整形
    char_ctx = ''
    world_ctx = ''
    # 従来の extra_ctx 互換：ctx_text から character/worldbuilding を取り出す（なければ全体を使う）
    import re as _re
    m_char = _re.search(r'## \[この巻の設定\] character\.md\n([\s\S]+?)(?=\n## |\Z)', ctx_text)
    m_world = _re.search(r'## \[この巻の設定\] worldbuilding\.md\n([\s\S]+?)(?=\n## |\Z)', ctx_text)
    m_char_single = _re.search(r'## character\.md\n([\s\S]+?)(?=\n## |\Z)', ctx_text)
    m_world_single = _re.search(r'## worldbuilding\.md\n([\s\S]+?)(?=\n## |\Z)', ctx_text)

    if m_char:
        char_ctx = m_char.group(1).strip()
    elif m_char_single:
        char_ctx = m_char_single.group(1).strip()

    if m_world:
        world_ctx = m_world.group(1).strip()
    elif m_world_single:
        world_ctx = m_world_single.group(1).strip()

    # シリーズ聖典の内容はキャラ・世界観コンテキストに追記する
    if ctx_text:
        char_ctx = ctx_text + ('\n\n---\n\n' + char_ctx if char_ctx else '')
        world_ctx = world_ctx  # world_ctx は ctx_text に含まれているので上書き不要

    # --- plot.md から章セクションを動的に抽出 ---
    import re

    KANJI_TO_NUM = {
        '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
        '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
    }

    # 部構造があるかチェック（## 第一部 など）
    part_pattern = re.compile(r'^##\s+第([一二三四五六七八九十\d]+)部', re.MULTILINE)
    has_parts = part_pattern.search(plot_content) is not None

    chapters = []  # [(filepath, title, body, is_ending, is_epilogue, part_num), ...]

    if has_parts:
        # 部構造がある場合：各部を検出してその配下の章を処理
        parts_list = list(part_pattern.finditer(plot_content))

        for part_idx, part_match in enumerate(parts_list):
            part_num_str = part_match.group(1)
            part_num = int(part_num_str) if part_num_str.isdigit() else kanji_to_number(part_num_str, KANJI_TO_NUM)

            # この部の範囲を取得
            part_start = part_match.end()
            part_end = parts_list[part_idx + 1].start() if part_idx + 1 < len(parts_list) else len(plot_content)

            # エピローグと結末の開始位置も考慮
            epilogue_match = re.search(r'^##\s+エピローグ', plot_content[part_start:], re.MULTILINE)
            ending_match = re.search(r'^##\s+結末', plot_content[part_start:], re.MULTILINE)

            if epilogue_match and part_start + epilogue_match.start() < part_end:
                part_end = part_start + epilogue_match.start()
            if ending_match and part_start + ending_match.start() < part_end:
                part_end = min(part_end, part_start + ending_match.start())

            part_content = plot_content[part_start:part_end]

            # この部配下の章を検出（### 第◯章）
            chapter_pattern = re.compile(r'^###\s+第(\d+|[一二三四五六七八九十]+)章', re.MULTILINE)
            section_pattern = re.compile(r'^(###\s+.+)$', re.MULTILINE)
            section_splits = list(section_pattern.finditer(part_content))

            # 部のディレクトリ名
            part_dir = f'part{part_num:02d}'

            for i, match in enumerate(section_splits):
                heading = match.group(1).strip()
                body_start = match.end()
                body_end = section_splits[i + 1].start() if i + 1 < len(section_splits) else len(part_content)
                body = part_content[body_start:body_end].strip()

                ch_match = chapter_pattern.match(heading)
                if ch_match:
                    num_str = ch_match.group(1)
                    if num_str.isdigit():
                        chapter_num = int(num_str)
                    else:
                        chapter_num = kanji_to_number(num_str, KANJI_TO_NUM)

                    filepath = os.path.join(part_dir, f'chapter{chapter_num:02d}.txt')
                    chapters.append((filepath, heading, body, False, False, part_num))

        # エピローグと結末は部の外（プロジェクトルート）
        epilogue_pattern = re.compile(r'^##\s+エピローグ', re.MULTILINE)
        ending_pattern = re.compile(r'^##\s+結末', re.MULTILINE)

        epilogue_match = epilogue_pattern.search(plot_content)
        if epilogue_match:
            body_start = epilogue_match.end()
            ending_match = ending_pattern.search(plot_content[body_start:])
            body_end = body_start + ending_match.start() if ending_match else len(plot_content)
            body = plot_content[body_start:body_end].strip()
            chapters.append(('epilogue.txt', '## エピローグ', body, False, True, None))

        ending_match = ending_pattern.search(plot_content)
        if ending_match:
            body = plot_content[ending_match.end():].strip()
            chapters.append(('chapter_end.txt', '## 結末', body, True, False, None))

    else:
        # 部構造がない場合：従来通り
        chapter_pattern = re.compile(r'^##\s+第([一二三四五六七八九十\d]+)章', re.MULTILINE)
        epilogue_pattern = re.compile(r'^##\s+エピローグ', re.MULTILINE)
        ending_pattern = re.compile(r'^##\s+結末', re.MULTILINE)
        section_pattern = re.compile(r'^(##\s+.+)$', re.MULTILINE)

        section_splits = list(section_pattern.finditer(plot_content))

        for i, match in enumerate(section_splits):
            heading = match.group(1).strip()
            body_start = match.end()
            body_end = section_splits[i + 1].start() if i + 1 < len(section_splits) else len(plot_content)
            body = plot_content[body_start:body_end].strip()

            ch_match = chapter_pattern.match(heading)
            if ch_match:
                num_str = ch_match.group(1)
                if num_str.isdigit():
                    chapter_num = int(num_str)
                else:
                    chapter_num = kanji_to_number(num_str, KANJI_TO_NUM)

                filepath = f'chapter{chapter_num:02d}.txt'
                chapters.append((filepath, heading, body, False, False, None))
                continue

            if epilogue_pattern.match(heading):
                chapters.append(('epilogue.txt', heading, body, False, True, None))
                continue

            if ending_pattern.match(heading):
                chapters.append(('chapter_end.txt', heading, body, True, False, None))

    if not chapters:
        return jsonify({'error': 'plot.md に章が見つかりません'}), 400

    # あらすじを取得（コンテキスト補強用、簡潔版）
    synopsis_match = re.search(r'## あらすじ\n+([\s\S]+?)(?=\n##|$)', plot_content)
    synopsis = synopsis_match.group(1).strip() if synopsis_match else ''
    # コスト削減：あらすじを1000文字以内に制限
    if len(synopsis) > 1000:
        synopsis = synopsis[:1000] + '...'

    # ★ char_ctx / world_ctx は build_context_text で既に設定済み

    created_files = []

    for filepath, title, body, is_ending, is_epilogue, part_num in chapters:
        if is_ending:
            section_label = '結末'
            writing_note = '物語の締めくくりとして、伏線の回収・感情の解放・余韻の残る文章を意識してください'
        elif is_epilogue:
            section_label = 'エピローグ'
            writing_note = '物語の後日談として、登場人物たちのその後や心境の変化を描いてください'
        else:
            section_label = '章'
            writing_note = '物語の流れを自然につなぎ、読者を次章へ引き込む終わり方を意識してください'

        # シリーズ情報バナー（シリーズ所属の場合のみ）
        series_banner = f'【シリーズ】{series}\n' if series else ''

        # プロンプト：階層コンテキスト対応（通常の小説形式で出力）
        prompt = f"""あなたはプロの小説家です。以下のプロットから{section_label}の本文を執筆してください。

【重要】プロットに書かれた内容を必ず全て含めてください。プロットの展開、シーン、登場人物の行動、会話の要点などを省略せず、すべて本文に反映させることが最優先です。

{series_banner}
【設定・コンテキスト（シリーズ聖典・巻固有設定）】
{char_ctx if char_ctx else '（未設定）'}

【あらすじ（この巻）】
{synopsis if synopsis else '（未設定）'}

【この{section_label}のタイトル】
{title}

【この{section_label}のプロット（必ず全て忠実に本文化すること）】
{body}

【執筆上の指示】
1. プロットに記載された出来事・シーン・セリフの要点は必ず全て描写すること
2. プロットの順序を守り、場面を飛ばさないこと
3. プロットに書かれていない大きな展開は追加しないこと
4. 情景描写・心理描写・会話文を自然に組み合わせ、プロットを豊かに肉付けすること
5. 分量目安：3000〜5000字（プロットのボリュームに応じて調整）
6. {writing_note}
7. 【重要】マークダウン記法は一切使用しないこと（#見出し、**太字**、_斜体_などは使わない）
8. 【重要】通常の小説形式で出力すること（Webサイトに直接投稿できる形式）
9. 【重要】各段落の先頭は全角スペース1文字で字下げすること（例：「　彼は立ち上がった。」）
10. 章タイトルは通常のテキストとして記述すること（例：「第一章　出会い」）
11. 本文のみ出力（前置き・後置きの説明は一切不要）

【確認】
執筆前に、プロットに書かれた全ての要素（出来事、人物の行動、会話、場面転換など）をリストアップし、それらを全て本文に含めてください。"""

        # max_tokensを増やして十分な長さの本文を生成（3000〜5000字 ≒ 8000〜12000トークン程度）
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=20000,  # プロットに忠実な長めの本文を生成するため増量
            messages=[{'role': 'user', 'content': prompt}],
            timeout=1800.0  # 30分のタイムアウト
        )

        chapter_text = message.content[0].text.strip()

        # ファイルパスの完全パスを作成し、必要に応じてディレクトリを作成
        full_path = os.path.join(project_dir, filepath)
        file_dir = os.path.dirname(full_path)
        if file_dir and not os.path.exists(file_dir):
            os.makedirs(file_dir, exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(chapter_text)

        created_files.append({
            'filename': filepath,
            'title': title,
            'is_ending': is_ending,
            'is_epilogue': is_epilogue,
            'part_num': part_num
        })

    return jsonify({'created': created_files, 'count': len(created_files)})


# --- 表記揺れチェック関数 ---

def run_notation_check(project_dir, project, series):
    """chapter全体の表記揺れをチェックする"""
    import re
    from flask import stream_with_context, Response

    # --- 全chapter*.txtファイルを収集 ---
    chapter_files = []
    chapter_pat = re.compile(r'chapter\d+\.txt$', re.IGNORECASE)

    # ルート直下
    for fname in sorted(os.listdir(project_dir)):
        if chapter_pat.match(fname):
            chapter_files.append(os.path.join(project_dir, fname))
        elif fname == 'epilogue.txt' or fname == 'chapter_end.txt':
            chapter_files.append(os.path.join(project_dir, fname))

    # part*/chapter*.txt
    for dname in sorted(os.listdir(project_dir)):
        dpath = os.path.join(project_dir, dname)
        if os.path.isdir(dpath) and dname.startswith('part'):
            for fname in sorted(os.listdir(dpath)):
                if chapter_pat.match(fname):
                    chapter_files.append(os.path.join(dpath, fname))

    if not chapter_files:
        return jsonify({'error': 'chapter*.txtが見つかりません'}), 404

    # --- 章本文を結合（長すぎる場合は各章から抜粋） ---
    CHAPTER_CHAR_LIMIT = 3000   # 1章あたりの文字数上限
    chapters_text_parts = []
    for fpath in chapter_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        label = os.path.relpath(fpath, project_dir)

        # 長すぎる場合は冒頭と末尾のみ
        if len(content) > CHAPTER_CHAR_LIMIT:
            half = CHAPTER_CHAR_LIMIT // 2
            content = content[:half] + f'\n\n... （中略） ...\n\n' + content[-half:]

        chapters_text_parts.append(f'### {label}\n{content}')

    chapters_combined = '\n\n---\n\n'.join(chapters_text_parts)

    # --- 設定ファイルから固有名詞リストを取得 ---
    reference_terms = []

    # character.md から人物名を抽出
    char_path = os.path.join(project_dir, 'character.md')
    if os.path.exists(char_path):
        with open(char_path, 'r', encoding='utf-8') as f:
            char_content = f.read()
            reference_terms.append(f'【登場人物】\n{char_content[:1000]}')

    # worldbuilding.md から用語を抽出
    world_path = os.path.join(project_dir, 'worldbuilding.md')
    if os.path.exists(world_path):
        with open(world_path, 'r', encoding='utf-8') as f:
            world_content = f.read()
            reference_terms.append(f'【世界観・用語】\n{world_content[:1000]}')

    # シリーズ聖典からも参照
    if series:
        series_dir = get_series_dir(series)

        chars_master_path = os.path.join(series_dir, 'characters_master.md')
        if os.path.exists(chars_master_path):
            with open(chars_master_path, 'r', encoding='utf-8') as f:
                content = f.read()
                reference_terms.append(f'【シリーズ共通キャラクター】\n{content[:1500]}')

        bible_path = os.path.join(series_dir, 'bible.md')
        if os.path.exists(bible_path):
            with open(bible_path, 'r', encoding='utf-8') as f:
                content = f.read()
                reference_terms.append(f'【シリーズ世界設定】\n{content[:1500]}')

    reference_text = '\n\n'.join(reference_terms) if reference_terms else '（参考設定なし）'

    # --- プロンプト構築 ---
    prompt = f"""あなたは長編小説の校閲担当編集者です。
以下の全章テキストを読み込み、**表記揺れ**を徹底的にチェックしてください。

## 表記揺れチェックの対象

### 1. 固有名詞の表記揺れ
- **人物名**: 「太郎」と「たろう」、「サトウ」と「佐藤」など
- **地名**: 「東京」と「トーキョー」、「江戸」と「エド」など
- **組織名**: 「騎士団」と「ナイツ」など

### 2. 一般用語の表記揺れ
- **漢字・ひらがな**: 「出来る」と「できる」、「無い」と「ない」など
- **カタカナ・英語**: 「コンピューター」と「コンピュータ」、「サーバー」と「サーバ」など
- **送り仮名**: 「行なう」と「行う」、「問い合わせ」と「問合せ」など

### 3. 数字・単位の表記
- **算用数字と漢数字**: 「1人」と「一人」、「3日」と「三日」など
- **単位**: 「メートル」と「m」、「キロ」と「kg」など

### 4. 記号・括弧の統一
- **三点リーダー**: 「...」と「…」と「‥」
- **ダッシュ**: 「—」と「―」と「ー」
- **括弧**: 「（）」と「()」

## 参考：この作品の固有名詞・用語設定
{reference_text}

## 全章テキスト（全{len(chapter_files)}ファイル）
{chapters_combined}

---

## 出力フォーマット（厳守）

# 表記揺れチェック結果

## 🔴 重大な表記揺れ（固有名詞）
（同一の人物・地名・組織が複数の表記で記載されている場合）

- **[キャラ名]**
  - 揺れている表記: 「○○」（chapter01.txt）、「××」（chapter05.txt）
  - 推奨統一表記: 「○○」
  - 理由: 設定ファイルでは「○○」と記載されている

（問題がなければ「問題なし ✅」と記載）

---

## 🟡 一般用語の表記揺れ
（漢字・ひらがな・カタカナの表記が統一されていない場合）

- **[用語]**
  - 揺れている表記: 「できる」（15箇所）、「出来る」（3箇所）
  - 推奨統一表記: 「できる」（補助動詞はひらがな推奨）

（問題がなければ「問題なし ✅」と記載）

---

## 📝 数字・記号の表記揺れ
（数字や記号の表記が統一されていない場合）

- **[数字]**
  - 揺れている表記: 「3人」（10箇所）、「三人」（2箇所）
  - 推奨: 小説では基本的に漢数字を推奨

（問題がなければ「問題なし ✅」と記載）

---

## 📊 サマリー
- 重大な表記揺れ（固有名詞）: ○件
- 一般用語の表記揺れ: ○件
- 数字・記号の表記揺れ: ○件
- 総合評価: （A: 問題なし / B: 軽微な揺れあり / C: 要修正 / D: 重大な揺れあり）

コメント: （全体の印象・特記事項を2〜3文で）

---

【重要】
- 各項目で具体的なファイル名と該当箇所を明示してください
- 推奨統一表記を必ず提示してください
- 設定ファイルとの整合性を優先してください
"""

    # --- ストリーミングで返す ---
    def generate_stream():
        try:
            with client.messages.stream(
                model='claude-opus-4-6',
                max_tokens=16000,
                messages=[{'role': 'user', 'content': prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'chunk': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate_stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# --- 整合性チェック専用API ---

@app.route('/api/claude/consistency_check', methods=['POST'])
def run_consistency_check():
    """シリーズ・巻の整合性チェックを実行する。
    scope: 'volume' = この巻のみ / 'series' = シリーズ全体（過去巻との照合）
    ストリーミングレスポンスで結果を返す。
    """
    import re
    from flask import stream_with_context, Response

    data    = request.json
    project = data.get('project', '')
    series  = data.get('series', '') or None
    scope   = data.get('scope', 'volume')   # 'volume' or 'series' or 'notation'
    target_file = data.get('target_file', '')  # 特定ファイルを対象にする場合

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not series:
        series = detect_series_from_project(project)

    project_dir = os.path.join(BASE_DIR, project)

    # --- 表記揺れチェックの場合は別処理 ---
    if scope == 'notation':
        return run_notation_check(project_dir, project, series)

    # --- 巻メタ情報 ---
    vol_order = '?'
    vol_title = project
    if series:
        meta = get_series_meta(series)
        vol_info = next((v for v in meta.get('volumes', []) if v['project_name'] == project), None)
        if vol_info:
            vol_order = vol_info['order']
            vol_title  = vol_info['title']

    # --- コンテキスト収集 ---

    # ① シリーズ聖典（スコープ問わず使用）
    series_ctx_parts = []
    if series:
        series_dir = get_series_dir(series)

        bible_path = os.path.join(series_dir, 'bible.md')
        if os.path.exists(bible_path):
            content = _read_and_trim(bible_path, 5000)
            series_ctx_parts.append(f'### [世界設定バイブル]\n{content}')

        chars_path = os.path.join(series_dir, 'characters_master.md')
        if os.path.exists(chars_path):
            content = _read_and_trim(chars_path, 5000)
            series_ctx_parts.append(f'### [キャラクターマスター]\n{content}')

    # ② 過去巻サマリー（series スコープのみ）
    past_summaries = ''
    if scope == 'series' and series:
        summary_path = os.path.join(get_series_dir(series), 'series_summary.md')
        past_summaries = _read_and_trim(summary_path, 6000) or '（まだサマリーが記録されていません）'

    # ③ 伏線マスターリスト
    foreshadowing_ctx = ''
    if series:
        fs_data = load_foreshadowing(series)
        if fs_data:
            lines = []
            for item in fs_data.values():
                status_label = {'open': '未回収', 'resolved': '回収済み', 'abandoned': '意図的放置'}.get(item['status'], item['status'])
                lines.append(
                    f"- [{item['id']}] {item['summary']} "
                    f"（登場:第{item.get('introduced_volume','?')}巻 {item.get('introduced_chapter','')} ／ "
                    f"状態:{status_label} ／ 回収予定:{item.get('resolve_target','未設定')}）"
                )
            foreshadowing_ctx = '\n'.join(lines)
        else:
            foreshadowing_ctx = '（伏線はまだ登録されていません）'

    # ④ この巻の設定ファイル
    volume_ctx_parts = []
    for fname in ['character.md', 'worldbuilding.md', 'timeline.md', 'plot.md']:
        fpath = os.path.join(project_dir, fname)
        content = _read_and_trim(fpath, 3000)
        if content:
            volume_ctx_parts.append(f'### [この巻: {fname}]\n{content}')

    # ⑤ 対象ファイル（指定がある場合）or chapter サンプル
    target_ctx = ''
    if target_file:
        fpath = os.path.join(project_dir, target_file)
        content = _read_and_trim(fpath, 4000)
        if content:
            target_ctx = f'### [チェック対象ファイル: {target_file}]\n{content}'
    else:
        # chapter*.txt の最初と最後の1章ずつをサンプルとして含める
        import re as _re
        chapter_pat = _re.compile(r'chapter\d+\.txt$', _re.IGNORECASE)
        ch_files = sorted([f for f in os.listdir(project_dir) if chapter_pat.match(f)])
        samples = []
        if ch_files:
            samples.append(ch_files[0])
            if len(ch_files) > 1:
                samples.append(ch_files[-1])
        for cf in samples:
            content = _read_and_trim(os.path.join(project_dir, cf), 2000)
            if content:
                target_ctx += f'\n\n### [章サンプル: {cf}]\n{content}'

    # --- プロンプト構築 ---
    scope_label = 'シリーズ全体（過去巻との照合を含む）' if scope == 'series' else 'この巻のみ'

    series_section = ''
    if series_ctx_parts:
        series_section = '## シリーズ聖典\n\n' + '\n\n'.join(series_ctx_parts)

    past_section = ''
    if scope == 'series' and past_summaries:
        past_section = f'## 過去巻のサマリー\n\n{past_summaries}'

    volume_section = '## この巻の設定ファイル\n\n' + '\n\n'.join(volume_ctx_parts) if volume_ctx_parts else ''
    target_section = f'## チェック対象\n\n{target_ctx}' if target_ctx else ''

    prompt = f"""あなたは長編小説シリーズの専任編集者です。
以下の資料を読み込み、**{scope_label}** の視点で整合性と文章品質をチェックしてください。

【重要】このチェックでは以下の2つの側面を評価します：
1. **ストーリーの整合性**: 設定・キャラクター・伏線の矛盾チェック
2. **小説としての品質**: 文章表現・描写技法・物語展開の質的評価

特に「Show, Don't Tell（見せる、説明しない）」の原則に基づき、
読者を物語に没入させる描写ができているかを厳密にチェックしてください。

チェックスコープ: {scope_label}
対象: 第{vol_order}巻「{vol_title}」{"（シリーズ: " + series + "）" if series else ""}

{series_section}

{past_section}

## 伏線マスターリスト
{foreshadowing_ctx}

{volume_section}

{target_section}

---

## チェック指示

以下の観点で問題・懸念事項を洗い出し、**必ず下記のフォーマット**で出力してください。

【特に重視すべき点】
- 「彼は怒っていた」「彼女は悲しそうだった」などの感情の直接説明を見つけること
- キャラクターが不自然に設定を説明するセリフ（説明台詞）を指摘すること
- 描写が抽象的で具体性に欠ける箇所を特定すること
- 視覚描写に偏り、音・匂い・触感・味覚が欠けている箇所を指摘すること

### チェック観点
1. **設定の矛盾**: 世界観・ルール・固有名詞の表記ゆれ・前後矛盾
2. **キャラクターの逸脱**: 性格・口調・能力がマスターシートや過去巻と食い違っていないか
3. **伏線の問題**: 回収されないまま放置されている伏線、矛盾する伏線の扱い
4. **過去巻との齟齬**: {"過去巻サマリーと今巻の設定・イベントが矛盾していないか" if scope == "series" else "（この巻スコープではスキップ）"}
5. **文章ルールの問題**: 以下の一般的な小説執筆ルールに違反していないかチェック

   【基本的な文章ルール】
   - マークダウン記法の混入（#見出し、**太字**、_斜体_、`コード`など）
   - 不自然な改行や空白行の過剰使用
   - 読点（、）の適切な使用
   - 文末表現の多様性（「〜た。」ばかりになっていないか）

   【小説としてのルール（Show, Don't Tell原則）】
   - **説明的すぎる地の文**:
     ❌ 悪い例: 「彼は怒っていた」「彼女は美しかった」
     ⭕ 良い例: 「彼の拳が震え、歯を食いしばる音が聞こえた」「道行く人々が振り返り、彼女の姿を目で追った」

   - **感情の直接説明**:
     ❌ 悪い例: 「悲しかった」「嬉しかった」「不安になった」
     ⭕ 良い例: 「胸が締め付けられ、視界が滲んだ」「思わず笑みがこぼれ、足取りが軽くなった」「心臓の鼓動が早まり、手のひらに汗が滲む」

   - **情報の羅列・説明台詞**:
     ❌ 悪い例: 「この街は100年前に建てられた要塞都市で、現在は商業の中心地となっている」
     ❌ 悪い例: 「君も知っての通り、この魔法は王族にしか使えないんだ」（相手が知っていることを説明する不自然なセリフ）
     ⭕ 良い例: 物語の進行の中で、キャラクターの行動や会話を通じて自然に情報を提示する

   【視点と時制】
   - 視点の統一（三人称・一人称が混在していないか）
   - 時制の統一（過去形・現在形が不自然に混在していないか）
   - 視点人物以外の内面描写が混入していないか（三人称単視点の場合）

   【会話と描写のバランス】
   - 地の文と会話文のバランス（会話のみが続きすぎていないか）
   - 会話文の記号（「」『』の使い分けが適切か）
   - セリフが説明的すぎないか（キャラクターが不自然に設定を説明していないか）
   - 会話の前後に適切な描写（動作・表情・間）があるか

   【描写の質】
   - 五感描写のバランス（視覚に偏りすぎていないか）
   - 具体性のある描写（「美しい」「大きい」などの抽象語に頼りすぎていないか）
   - 比喩・暗喩の適切な使用
   - 冗長な表現や同じ表現の繰り返し

   【ペースと緊張感】
   - シーンの緩急（重要なシーンが駆け足になっていないか）
   - 不要な描写で物語が停滞していないか
   - 章の終わりに引きがあるか（次を読みたくなる終わり方か）

6. **推奨改善**: 重大ではないが品質向上につながる提案

### 出力フォーマット（厳守）

## 整合性チェック結果
**チェックスコープ**: {scope_label}
**対象**: 第{vol_order}巻「{vol_title}」

---

### 🔴 重大な矛盾・エラー
（設定と明確に矛盾する問題。必ず修正が必要）

- **[カテゴリ]** 問題の説明。該当箇所: ○○。推奨対処: ○○。

（問題がなければ「問題なし ✅」と記載）

---

### 🟡 注意・要確認
（矛盾の可能性があるが確認が必要な事項、または表記ゆれ）

- **[カテゴリ]** 問題の説明。

（問題がなければ「問題なし ✅」と記載）

---

### 📝 文章ルールの問題
（小説執筆ルールに関する問題点）

#### 基本的な文章ルール
- **[表記・記法]** 問題の説明。該当箇所と改善案。

#### Show, Don't Tell（描写の質）
- **[説明過多]** 問題の説明。
  - 該当箇所: 「〜」
  - 問題点: なぜこれが説明的か
  - 改善例: 「〜」（行動・表情・五感で描写）

- **[感情の直接説明]** 問題の説明。
  - 該当箇所: 「〜」
  - 改善例: 「〜」（身体感覚や具体的な反応で表現）

- **[説明台詞]** キャラクターが不自然に設定を説明している箇所。
  - 該当箇所: 「〜」
  - 問題点: なぜこのセリフが不自然か
  - 改善案: 物語の中で自然に情報を提示する方法

#### 視点と時制
- **[視点の問題]** 問題の説明。

#### 会話と描写のバランス
- **[会話の問題]** 問題の説明。

#### ペースと緊張感
- **[ペース配分]** 問題の説明。

（問題がなければ「問題なし ✅」と記載）

---

### 🟢 改善提案
（必須ではないが、品質・整合性向上のための提案）

- **[カテゴリ]** 提案内容。

（提案がなければ「特になし ✅」と記載）

---

### 📊 サマリー
- 重大な問題: ○件
- 要確認事項: ○件
- 文章ルール問題: ○件
- 改善提案: ○件
- 総合評価: （A: 問題なし / B: 軽微な問題あり / C: 要修正 / D: 重大な問題あり）

コメント: （全体の印象・特記事項を2〜3文で）
"""

    # --- ストリーミングで返す ---
    def generate_stream():
        try:
            with client.messages.stream(
                model='claude-opus-4-6',
                max_tokens=16000,  # 整合性チェック結果が途中で切れないように大幅に増加
                messages=[{'role': 'user', 'content': prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'chunk': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate_stream()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/claude/fix_chapter_file', methods=['POST'])
def fix_chapter_file():
    """整合性チェック結果に基づいてchapter.txtを自動修正する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None
    chapter_file = data.get('chapter_file', '')  # 修正対象のファイル名（例: chapter01.txt）
    check_result = data.get('check_result', '')  # 整合性チェック結果のテキスト

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not chapter_file:
        return jsonify({'error': '修正対象のファイルが指定されていません'}), 400

    if not series:
        series = detect_series_from_project(project)

    project_dir = os.path.join(BASE_DIR, project)
    chapter_path = os.path.join(project_dir, chapter_file)

    # partディレクトリ内のファイルの可能性もチェック
    if not os.path.exists(chapter_path):
        # part01/, part02/ などの中を探す
        for dname in os.listdir(project_dir):
            dpath = os.path.join(project_dir, dname)
            if os.path.isdir(dpath) and dname.startswith('part'):
                test_path = os.path.join(dpath, chapter_file)
                if os.path.exists(test_path):
                    chapter_path = test_path
                    break

    if not os.path.exists(chapter_path):
        return jsonify({'error': f'{chapter_file}が見つかりません'}), 404

    # 現在の章ファイルを読み込む
    with open(chapter_path, 'r', encoding='utf-8') as f:
        current_chapter = f.read()

    # コンテキスト収集（シリーズ聖典・設定ファイル）
    context_parts = []

    if series:
        series_dir = get_series_dir(series)
        bible_path = os.path.join(series_dir, 'bible.md')
        if os.path.exists(bible_path):
            content = _read_and_trim(bible_path, 3000)
            context_parts.append(f'### [世界設定バイブル]\n{content}')

        chars_path = os.path.join(series_dir, 'characters_master.md')
        if os.path.exists(chars_path):
            content = _read_and_trim(chars_path, 3000)
            context_parts.append(f'### [キャラクターマスター]\n{content}')

    # この巻の設定ファイル
    for fname in ['character.md', 'plot.md']:
        fpath = os.path.join(project_dir, fname)
        content = _read_and_trim(fpath, 2000)
        if content:
            context_parts.append(f'### [{fname}]\n{content}')

    context_text = '\n\n'.join(context_parts) if context_parts else '（コンテキスト情報なし）'

    # 修正プロンプト
    prompt = f"""あなたはプロの小説編集者です。
以下の整合性チェック結果に基づいて、章ファイルの内容を修正してください。

## 整合性チェック結果
{check_result if check_result else '（特に問題点の指摘なし。一般的な文章品質向上のための修正を行ってください）'}

## 参考コンテキスト
{context_text}

## 現在の章ファイル（{chapter_file}）
{current_chapter}

---

## 修正指示

以下の優先順位で修正を行ってください：

1. **重大な矛盾・エラー**: 設定との矛盾を必ず修正
2. **Show, Don't Tell違反**: 感情の直接説明を具体的な描写に置き換え
   - 「彼は怒っていた」→ 行動・表情・声色で描写
   - 「悲しかった」→ 身体感覚・五感で表現
   - 説明台詞を自然な会話に修正
3. **視点の問題**: 視点の統一、視点人物以外の内面描写を削除
4. **描写の質**: 抽象的な表現を具体的に、五感のバランスを改善
5. **文章ルール**: マークダウン記法の削除、文末表現の多様化

【重要な制約】
- プロットや物語の展開は変更しないこと
- キャラクターの行動や会話の意図は保持すること
- 文章量は元の±20%程度に抑えること
- 通常の小説形式（マークダウン記法なし）で出力すること
- 修正後のファイル全文のみを出力すること（前置き・説明は不要）

【出力形式】
- 冒頭に説明や前置きを付けず、章の内容そのものを出力してください
- ```markdown などのコードブロックも不要です
- 章タイトルから本文まで、そのままファイルに保存できる形式で出力してください
"""

    # Claude APIで修正版を生成
    try:
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=20000,
            messages=[{'role': 'user', 'content': prompt}],
            timeout=1800.0
        )

        fixed_chapter = message.content[0].text.strip()

        # ファイルを上書き保存
        with open(chapter_path, 'w', encoding='utf-8') as f:
            f.write(fixed_chapter)

        return jsonify({
            'success': True,
            'message': f'{chapter_file}を修正しました',
            'file': chapter_file,
            'preview': fixed_chapter[:500] + '...' if len(fixed_chapter) > 500 else fixed_chapter
        })

    except Exception as e:
        return jsonify({'error': f'修正中にエラーが発生しました: {str(e)}'}), 500


@app.route('/api/claude/fix_notation_issues', methods=['POST'])
def fix_notation_issues():
    """表記揺れチェック結果に基づいて全chapter.txtを一括修正する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None
    notation_result = data.get('check_result', '')  # 表記揺れチェック結果

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not notation_result:
        return jsonify({'error': '表記揺れチェック結果がありません'}), 400

    if not series:
        series = detect_series_from_project(project)

    project_dir = os.path.join(BASE_DIR, project)

    # --- 全chapter*.txtファイルを収集 ---
    import re
    chapter_files = []
    chapter_pat = re.compile(r'chapter\d+\.txt$', re.IGNORECASE)

    # ルート直下
    for fname in sorted(os.listdir(project_dir)):
        if chapter_pat.match(fname):
            chapter_files.append((fname, os.path.join(project_dir, fname)))
        elif fname == 'epilogue.txt' or fname == 'chapter_end.txt':
            chapter_files.append((fname, os.path.join(project_dir, fname)))

    # part*/chapter*.txt
    for dname in sorted(os.listdir(project_dir)):
        dpath = os.path.join(project_dir, dname)
        if os.path.isdir(dpath) and dname.startswith('part'):
            for fname in sorted(os.listdir(dpath)):
                if chapter_pat.match(fname):
                    rel_path = os.path.join(dname, fname)
                    chapter_files.append((rel_path, os.path.join(dpath, fname)))

    if not chapter_files:
        return jsonify({'error': 'chapter*.txtが見つかりません'}), 404

    # --- 各ファイルを修正 ---
    fixed_files = []
    errors = []

    for file_name, file_path in chapter_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # 修正プロンプト
            prompt = f"""あなたはプロの校閲編集者です。
以下の表記揺れチェック結果に基づいて、この章ファイルの表記を統一してください。

## 表記揺れチェック結果
{notation_result}

## 修正対象ファイル: {file_name}
{original_content}

---

## 修正指示

表記揺れチェック結果で指摘された表記揺れを、推奨統一表記に従って修正してください。

【重要な制約】
1. **物語の内容は一切変更しないこと**（表記のみを修正）
2. 固有名詞の表記揺れを最優先で修正
3. 一般用語、数字、記号も統一
4. 指摘されていない箇所は変更しない
5. 通常の小説形式（マークダウン記法なし）を維持

【出力形式】
- 冒頭に説明や前置きを付けず、修正後の章の内容そのものを出力してください
- コードブロック（```）も不要です
- そのままファイルに保存できる形式で出力してください
"""

            # Claude APIで修正版を生成
            message = client.messages.create(
                model='claude-opus-4-6',
                max_tokens=20000,
                messages=[{'role': 'user', 'content': prompt}],
                timeout=1800.0
            )

            fixed_content = message.content[0].text.strip()

            # ファイルを上書き保存
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(fixed_content)

            fixed_files.append(file_name)

        except Exception as e:
            errors.append({'file': file_name, 'error': str(e)})

    if errors:
        return jsonify({
            'success': True,
            'message': f'{len(fixed_files)}ファイル修正完了（{len(errors)}ファイルでエラー）',
            'fixed_files': fixed_files,
            'errors': errors
        })
    else:
        return jsonify({
            'success': True,
            'message': f'{len(fixed_files)}ファイルを修正しました',
            'fixed_files': fixed_files
        })


@app.route('/api/claude/fix_plot_inconsistencies', methods=['POST'])
def fix_plot_inconsistencies():
    """plot.mdの矛盾箇所を自動修正する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None
    inconsistencies = data.get('inconsistencies', '')  # 整合性チェック結果のテキスト

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not series:
        series = detect_series_from_project(project)

    project_dir = os.path.join(BASE_DIR, project)
    plot_path = os.path.join(project_dir, 'plot.md')

    if not os.path.exists(plot_path):
        return jsonify({'error': 'plot.mdが見つかりません'}), 404

    # 現在のplot.mdを読み込む
    with open(plot_path, 'r', encoding='utf-8') as f:
        current_plot = f.read()

    # コンテキスト収集
    series_ctx_parts = []
    if series:
        series_dir = get_series_dir(series)

        bible_path = os.path.join(series_dir, 'bible.md')
        if os.path.exists(bible_path):
            content = _read_and_trim(bible_path, 5000)
            series_ctx_parts.append(f'### [世界設定バイブル]\n{content}')

        chars_path = os.path.join(series_dir, 'characters_master.md')
        if os.path.exists(chars_path):
            content = _read_and_trim(chars_path, 5000)
            series_ctx_parts.append(f'### [キャラクターマスター]\n{content}')

    # 他の設定ファイルを読み込む
    volume_ctx_parts = []
    for fname in ['character.md', 'worldbuilding.md', 'timeline.md']:
        fpath = os.path.join(project_dir, fname)
        content = _read_and_trim(fpath, 3000)
        if content:
            volume_ctx_parts.append(f'### [{fname}]\n{content}')

    series_section = ''
    if series_ctx_parts:
        series_section = '## シリーズ聖典\n\n' + '\n\n'.join(series_ctx_parts)

    volume_section = '## この巻の設定ファイル\n\n' + '\n\n'.join(volume_ctx_parts) if volume_ctx_parts else ''

    prompt = f"""あなたは長編小説シリーズの専任編集者です。
以下の整合性チェック結果に基づいて、plot.mdの矛盾箇所を修正してください。

## 整合性チェック結果
{inconsistencies}

{series_section}

{volume_section}

## 現在のplot.md
{current_plot}

---

## 修正指示

上記の整合性チェック結果で指摘された矛盾箇所を、シリーズ聖典や設定ファイルと整合するように修正してください。

**重要**:
- 修正後のplot.md全文を出力してください
- markdown形式を保持してください
- 矛盾が指摘されていない部分はそのまま維持してください
- 冒頭に説明や前置きを付けず、plot.mdの内容のみを出力してください
- ```markdown などのコードブロックも不要です。plot.mdの内容そのものを出力してください
"""

    try:
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=8000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        corrected_plot = message.content[0].text

        # コードブロックで囲まれている場合は除去
        import re
        corrected_plot = re.sub(r'^```(?:markdown)?\s*\n', '', corrected_plot)
        corrected_plot = re.sub(r'\n```\s*$', '', corrected_plot)

        # plot.mdを上書き
        with open(plot_path, 'w', encoding='utf-8') as f:
            f.write(corrected_plot)

        return jsonify({
            'success': True,
            'message': 'plot.mdを修正しました',
            'corrected_content': corrected_plot
        })

    except Exception as e:
        return jsonify({'error': f'修正中にエラーが発生しました: {str(e)}'}), 500


@app.route('/api/claude/generate_spoiler_free_synopsis', methods=['POST'])
def generate_spoiler_free_synopsis():
    """ネタバレ防止あらすじを生成する"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None
    synopsis_type = data.get('synopsis_type', 'short')  # short, medium, long

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    if not series:
        series = detect_series_from_project(project)

    project_dir = os.path.join(BASE_DIR, project)
    plot_path = os.path.join(project_dir, 'plot.md')

    if not os.path.exists(plot_path):
        return jsonify({'error': 'plot.mdが見つかりません'}), 404

    # plot.mdを読み込む
    with open(plot_path, 'r', encoding='utf-8') as f:
        plot_content = f.read()

    # 他の設定ファイルを読み込む
    character_content = ''
    worldbuilding_content = ''

    char_path = os.path.join(project_dir, 'character.md')
    if os.path.exists(char_path):
        character_content = _read_and_trim(char_path, 3000)

    world_path = os.path.join(project_dir, 'worldbuilding.md')
    if os.path.exists(world_path):
        worldbuilding_content = _read_and_trim(world_path, 3000)

    # 巻メタ情報
    vol_order = '?'
    vol_title = project
    if series:
        meta = get_series_meta(series)
        vol_info = next((v for v in meta.get('volumes', []) if v['project_name'] == project), None)
        if vol_info:
            vol_order = vol_info['order']
            vol_title = vol_info['title']

    # あらすじの長さ設定
    length_settings = {
        'short': {
            'chars': '200～300文字',
            'description': '書籍の帯や広告向けの簡潔なあらすじ',
            'focus': '主人公の状況設定と物語の発端のみ'
        },
        'medium': {
            'chars': '400～600文字',
            'description': '書籍の裏表紙やオンライン書店向けのあらすじ',
            'focus': '主人公の状況、物語の発端、序盤の展開（全体の1/3程度まで）'
        },
        'long': {
            'chars': '800～1200文字',
            'description': '出版社資料や詳細な紹介文向けのあらすじ',
            'focus': '序盤から中盤にかけての展開（全体の1/2程度まで）、主要な登場人物の紹介'
        }
    }

    settings = length_settings.get(synopsis_type, length_settings['medium'])

    prompt = f"""あなたは出版社の編集者です。
以下の小説のネタバレを避けた魅力的なあらすじを作成してください。

## 作品情報
- タイトル: 第{vol_order}巻「{vol_title}」{"（シリーズ: " + series + "）" if series else ""}

## plot.md
{plot_content}

## キャラクター設定
{character_content if character_content else '（なし）'}

## 世界観設定
{worldbuilding_content if worldbuilding_content else '（なし）'}

---

## あらすじ作成指示

**長さ**: {settings['chars']}
**用途**: {settings['description']}
**含める内容**: {settings['focus']}

**厳守事項**:
1. **ネタバレ禁止**:
   - 物語の結末には一切触れない
   - クライマックスの展開を明かさない
   - 重大な秘密や真相を暴露しない
   - キャラクターの生死や運命を明かさない
   - 予想外の展開（どんでん返し）には触れない

2. **読者の興味を引く要素**:
   - 主人公の魅力的な設定や状況
   - 物語の核となる謎や葛藤
   - 独特な世界観や設定
   - 「この先どうなるのか？」という期待感

3. **文体**:
   - 簡潔で読みやすい文章
   - 作品の雰囲気やトーンを反映
   - 魅力的で引き込まれる表現

**出力フォーマット**:
マークダウン形式で以下のように出力してください：

# ネタバレ防止あらすじ

## {synopsis_type.upper()}版（{settings['chars']}）

（あらすじ本文）

---

**対象読者層**: （想定される読者層を簡潔に）
**ジャンル・雰囲気**: （作品のジャンルや雰囲気を簡潔に）
"""

    try:
        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=3000,
            messages=[{'role': 'user', 'content': prompt}],
        )
        synopsis = message.content[0].text

        return jsonify({
            'success': True,
            'synopsis': synopsis
        })

    except Exception as e:
        return jsonify({'error': f'あらすじ生成中にエラーが発生しました: {str(e)}'}), 500


@app.route('/api/claude/generate', methods=['POST'])
def generate():
    data = request.json
    action = data.get('action')
    project = data.get('project', '')
    series = data.get('series', '') or None   # ★ フロントから明示的に渡されたシリーズ名
    current_content = data.get('current_content', '')
    extra_context = data.get('context', '')

    # ★ 階層コンテキストを構築
    if project:
        ctx_text, _ = build_context_text(project, series=series, include_plot=True)
    else:
        ctx_text = ''

    # キャラクター役割を取得
    character_role = data.get('character_role', 'メインキャラクター')

    prompts = {
        'generate_character': f"""以下のプロジェクト設定を参考に、詳細なキャラクタープロファイルを提案してください。

{ctx_text}

キャラクターの役割: {character_role}

追加の要望: {extra_context}

以下のフォーマットに厳密に従って、詳細なキャラクタープロファイルを作成してください：

# キャラクター設定

## 基本情報
- 名前:
- 役割: {character_role}
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

上記のフォーマットの各項目を埋めてください。マークダウン形式で出力し、説明文や前置きは不要です。""",

        'plot_draft': f"""以下のプロジェクト設定を参考に、詳細なプロット展開案を提案してください。

{ctx_text}

現在の内容:
{current_content}

目標執筆量: {data.get('length', '中編')}
- 短編: 5000文字前後（章数: 3-5章、部構造なし）
- 中編: 5万文字前後（章数: 10-15章、2-3部構成）
- 長編: 10万文字前後（章数: 20-30章、3-4部構成）

追加の要望: {extra_context}

## 出力形式

以下の形式に厳密に従って、詳細なプロット展開案を作成してください：

# プロット展開案
## 『タイトル（仮題）』

---

## 全体構造の概観

**総文字数目標：[目標文字数]　全[章数]章構成**

| ブロック | 章 | 機能 | 文字数目安 |
|---|---|---|---|
| 第一部「[部タイトル]」 | 第1〜[章数]章 | [機能説明] | 約[文字数] |
| 第二部「[部タイトル]」 | 第[章数]〜[章数]章 | [機能説明] | 約[文字数] |
（目標執筆量に応じて部数を調整）

---

## 物語の核心について

展開の中心となる主題やテーマ、物語が提示する主要な問いについて説明してください。
複数の展開案がある場合は、それぞれの強みとテーマへの寄与度を記載してください。

---

## 登場人物の追加設定（必要な場合）

プロット上必要な未設定キャラクターがいる場合、ここに記載してください。

---

## 第一部「[部タイトル]」　第1〜[章数]章　約[文字数]

### 第1章「[章タイトル]」　約[文字数]

**主な展開：**
この章で起こる出来事を具体的に記述してください。
場面、登場人物の行動、会話の要点、感情の動きなどを含めてください。

**ポイント：**
- この章の物語上の役割
- 伏線の配置
- キャラクターの成長や変化

---

（以下、各章について同様の形式で記述）

---

## 伏線一覧と回収タイミング

| 伏線 | 設置章 | 回収章 | 内容 |
|---|---|---|---|
| [伏線の内容] | 第[章数]章 | 第[章数]章 | [詳細] |

---

## 読者を引きつけるポイント

**①[ポイント1のタイトル]**
説明

**②[ポイント2のタイトル]**
説明

（3〜5つ程度）

---

## 章ごとの文字数配分まとめ

| 章 | タイトル（仮） | 目安文字数 |
|---|---|---|
| 第1章 | [タイトル] | [文字数] |
| 第2章 | [タイトル] | [文字数] |
（全章を記載）
| **合計** | | **約[総文字数]** |

---

## 指示事項

1. 目標執筆量に応じて部数と章数を適切に設定してください
   - 短編: 部構造なし、3-5章
   - 中編: 2-3部構成、10-15章
   - 長編: 3-4部構成、20-30章

2. 各章の展開は具体的かつ詳細に記述してください

3. 伏線の設置と回収を明確にしてください

4. キャラクター設定と世界観設定の内容を反映してください

5. マークダウン形式で出力し、上記のフォーマットを厳守してください""",

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
        model='claude-opus-4-6',
        max_tokens=30000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0  # 10分のタイムアウト
    )

    return jsonify({'result': message.content[0].text})


@app.route('/api/claude/context_debug', methods=['POST'])
def context_debug():
    """現在のコンテキスト構成をデバッグ表示するエンドポイント（開発用）"""
    data = request.json
    project = data.get('project', '')
    series = data.get('series', '') or None

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    ctx_text, summary = build_context_text(project, series=series, include_plot=True)

    detected_series = detect_series_from_project(project)
    used_series = series or detected_series

    return jsonify({
        'summary': summary,
        'detected_series': detected_series,
        'used_series': used_series,
        'context_length': len(ctx_text),
        'context_preview': ctx_text[:500] + ('...' if len(ctx_text) > 500 else ''),
        'sections': [line.lstrip('# ') for line in ctx_text.split('\n') if line.startswith('## ')]
    })


# --- 巻サマリー自動生成API ---

@app.route('/api/claude/generate_volume_summary', methods=['POST'])
def generate_volume_summary():
    """巻内の全 chapter*.txt を読み込み、次巻執筆用の圧縮サマリーを生成して
    series_summary.md に追記する。
    ストリーミングレスポンスで進捗を返す。
    """
    import re
    from flask import stream_with_context, Response

    data = request.json
    project = data.get('project', '')
    series  = data.get('series', '') or None

    if not project:
        return jsonify({'error': 'プロジェクトが指定されていません'}), 400

    # シリーズを自動検出
    if not series:
        series = detect_series_from_project(project)
    if not series:
        return jsonify({'error': 'このプロジェクトはシリーズに属していません'}), 400

    project_dir = os.path.join(BASE_DIR, project)
    series_dir  = get_series_dir(series)

    # --- 巻番号・タイトルをメタから取得 ---
    meta = get_series_meta(series)
    vol_info = next((v for v in meta.get('volumes', []) if v['project_name'] == project), None)
    vol_order = vol_info['order'] if vol_info else '?'
    vol_title = vol_info['title'] if vol_info else project

    # --- chapter*.txt を収集（part ディレクトリ含む） ---
    chapter_files = []
    chapter_pat = re.compile(r'chapter\d+\.txt$', re.IGNORECASE)

    # ルート直下
    for fname in sorted(os.listdir(project_dir)):
        if chapter_pat.match(fname):
            chapter_files.append(os.path.join(project_dir, fname))
        elif fname == 'epilogue.txt' or fname == 'chapter_end.txt':
            chapter_files.append(os.path.join(project_dir, fname))

    # part*/chapter*.txt
    for dname in sorted(os.listdir(project_dir)):
        dpath = os.path.join(project_dir, dname)
        if os.path.isdir(dpath) and dname.startswith('part'):
            for fname in sorted(os.listdir(dpath)):
                if chapter_pat.match(fname):
                    chapter_files.append(os.path.join(dpath, fname))

    if not chapter_files:
        return jsonify({'error': 'chapter*.txt が見つかりません。先に章を生成してください'}), 400

    # --- 章本文を結合（長すぎる場合は冒頭+末尾のみ） ---
    CHAPTER_CHAR_LIMIT = 2000   # 1章あたりの文字数上限
    chapters_text_parts = []
    for fpath in chapter_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        label = os.path.relpath(fpath, project_dir)
        if len(content) > CHAPTER_CHAR_LIMIT:
            half = CHAPTER_CHAR_LIMIT // 2
            content = content[:half] + f'\n\n... （中略） ...\n\n' + content[-half:]
        chapters_text_parts.append(f'### {label}\n{content}')

    chapters_combined = '\n\n---\n\n'.join(chapters_text_parts)
    total_chapters = len(chapter_files)

    # --- 既存の series_summary.md を読み込む ---
    summary_path = os.path.join(series_dir, 'series_summary.md')
    existing_summary = ''
    if os.path.exists(summary_path):
        with open(summary_path, 'r', encoding='utf-8') as f:
            existing_summary = f.read()

    # --- 伏線情報（この巻に関連するもの） ---
    foreshadowing_data = load_foreshadowing(series)
    vol_foreshadowing = [
        f"- [{v['id']}] {v['summary']} （状態: {v['status']}）"
        for v in foreshadowing_data.values()
        if str(v.get('introduced_volume', '')) == str(vol_order)
        or str(v.get('resolved_volume', '')) == str(vol_order)
    ]
    foreshadowing_note = '\n'.join(vol_foreshadowing) if vol_foreshadowing else '（この巻では伏線の登録なし）'

    # --- シリーズ聖典のキャラ情報（圧縮） ---
    chars_master_path = os.path.join(series_dir, 'characters_master.md')
    chars_master = ''
    if os.path.exists(chars_master_path):
        with open(chars_master_path, 'r', encoding='utf-8') as f:
            chars_master = f.read()[:3000]

    # --- プロンプト構築 ---
    prompt = f"""あなたは長編小説シリーズのシリーズ構成担当編集者です。
以下の「第{vol_order}巻「{vol_title}」」の全章テキストを読み込み、
次巻以降の執筆時にコンテキストとして使う「巻別サマリー」を生成してください。

## 制約
- 全体で **1000〜1500字以内** に収めること（次巻執筆時のトークン節約が目的）
- 本文の文章を引用せず、**変化・状態・結果** だけを記録すること
- 伏線の回収/追加は明示的に記録すること
- 各キャラクターの「巻末時点の状態」を必ず記録すること

## 既存サマリー（参考・重複しないこと）
{existing_summary[-1000:] if existing_summary else '（まだ他の巻のサマリーはありません）'}

## キャラクターマスター（参照用）
{chars_master if chars_master else '（未設定）'}

## この巻の伏線情報
{foreshadowing_note}

## 全章テキスト（第{vol_order}巻 全{total_chapters}章）
{chapters_combined}

## 出力フォーマット（必ずこの形式を守ること）

---

## 第{vol_order}巻「{vol_title}」

**あらすじ（300字以内）**:
（この巻で何が起きたかを簡潔に）

**この巻で起きた主要な変化**:
- キャラクターの変化: （誰がどう変わったか）
- 世界情勢の変化: （世界・組織・状況の変化）
- 解決した伏線: （回収された謎・伏線）
- 新たに張った伏線: （新しく登場した謎・布石）

**各キャラの巻末状態**:
- （キャラ名）: （心理状態・立場・関係性の現在）
（主要キャラ全員分を記載）

**次巻への引き）**:
（次巻の執筆者が把握すべき未解決事項・予告）

---
"""

    # --- Claude API 呼び出し（ストリーミング） ---
    def generate_stream():
        generated_text = ''
        try:
            with client.messages.stream(
                model='claude-opus-4-6',
                max_tokens=3000,
                messages=[{'role': 'user', 'content': prompt}],
            ) as stream:
                for text in stream.text_stream:
                    generated_text += text
                    # SSE 形式で進捗を送出
                    yield f"data: {json.dumps({'chunk': text})}\n\n"

            # --- series_summary.md に追記 ---
            # 既存に同じ巻のセクションがあれば置換、なければ末尾に追記
            section_header = f'## 第{vol_order}巻'
            new_section = generated_text.strip()

            if section_header in existing_summary:
                # 既存セクションを置換
                pattern = re.compile(
                    rf'(---\s*\n\s*{re.escape(section_header)}[^\n]*\n[\s\S]+?)(?=\n---\s*\n## 第|\Z)',
                    re.MULTILINE
                )
                if pattern.search(existing_summary):
                    updated = pattern.sub(new_section + '\n', existing_summary)
                else:
                    updated = existing_summary + '\n\n' + new_section
            else:
                # 末尾に追記
                updated = existing_summary.rstrip() + '\n\n' + new_section + '\n'

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(updated)

            yield f"data: {json.dumps({'done': True, 'saved': True, 'vol_order': vol_order, 'vol_title': vol_title})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate_stream()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


if __name__ == '__main__':
    app.run(debug=True, port=5000)
