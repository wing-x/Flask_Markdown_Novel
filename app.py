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
            elif name.endswith('.md'):
                # .mdファイルの場合
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
    # 部構造（## ■ 第一部... など）
    part_pattern = re.compile(r'^##\s+■\s+第([一二三四五六七八九十\d]+)部', re.MULTILINE)
    # 章構造（### 第1章... など）
    chapter_pattern = re.compile(r'^###\s+第(\d+|[一二三四五六七八九十]+)章', re.MULTILINE)
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
            part_num = int(part_num_str) if part_num_str.isdigit() else KANJI_TO_NUM.get(part_num_str, i + 1)

            # この部の範囲を取得
            part_start = part_match.start()
            part_end = parts[i + 1].start() if i + 1 < len(parts) else len(draft_content)
            part_content = draft_content[part_start:part_end]

            # この部内の章を検出
            part_chapters = chapter_pattern.findall(part_content)

            template += f"\n## 第{num_to_kanji(part_num)}部\n\n"

            for ch_num_str in part_chapters:
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

                template += f"\n### 第{num_to_kanji(ch_num)}章\n\n"

    else:
        # 部構造がない場合は通常の章のみ
        KANJI_TO_NUM = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
        }

        chapter_count = 0
        for ch_num_str in chapter_pattern.findall(draft_content):
            if ch_num_str.isdigit():
                chapter_count = max(chapter_count, int(ch_num_str))
            else:
                if '十' in ch_num_str:
                    parts_split = ch_num_str.split('十')
                    tens = KANJI_TO_NUM.get(parts_split[0], 1) if parts_split[0] else 1
                    ones = KANJI_TO_NUM.get(parts_split[1], 0) if len(parts_split) > 1 and parts_split[1] else 0
                    num = tens * 10 + ones
                else:
                    num = KANJI_TO_NUM.get(ch_num_str, 0)
                chapter_count = max(chapter_count, num)

        if chapter_count == 0:
            chapter_count = 5

        for i in range(1, chapter_count + 1):
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
- 草稿の内容を適切に各セクションへ振り分けてください
- 草稿に記載のない項目は、文脈から自然に補完してください
- 出力はテンプレートのマークダウンのみとし、説明文や前置きは一切不要です"""

    message = client.messages.create(
        model='claude-sonnet-4-6',
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
    """plot.md の各章を解析し、chapter01.md, chapter02.md ... として本文を生成・保存する"""
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

    # character.md / worldbuilding.md もコンテキストとして読み込む
    extra_ctx = {}
    for fname in ['character.md', 'worldbuilding.md']:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                extra_ctx[fname] = f.read()

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

                    filepath = os.path.join(part_dir, f'chapter{chapter_num:02d}.md')
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
            chapters.append(('epilogue.md', '## エピローグ', body, False, True, None))

        ending_match = ending_pattern.search(plot_content)
        if ending_match:
            body = plot_content[ending_match.end():].strip()
            chapters.append(('chapter_end.md', '## 結末', body, True, False, None))

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

                filepath = f'chapter{chapter_num:02d}.md'
                chapters.append((filepath, heading, body, False, False, None))
                continue

            if epilogue_pattern.match(heading):
                chapters.append(('epilogue.md', heading, body, False, True, None))
                continue

            if ending_pattern.match(heading):
                chapters.append(('chapter_end.md', heading, body, True, False, None))

    if not chapters:
        return jsonify({'error': 'plot.md に章が見つかりません'}), 400

    # あらすじを取得（コンテキスト補強用）
    synopsis_match = re.search(r'## あらすじ\n+([\s\S]+?)(?=\n##|$)', plot_content)
    synopsis = synopsis_match.group(1).strip() if synopsis_match else ''

    # キャラクター情報
    char_ctx = extra_ctx.get('character.md', '')
    world_ctx = extra_ctx.get('worldbuilding.md', '')

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

        prompt = f"""あなたは小説の執筆者です。以下のプロット情報をもとに、指定された{section_label}の本文を日本語で執筆してください。

## 物語のあらすじ
{synopsis}

## キャラクター設定
{char_ctx if char_ctx else '（未設定）'}

## 世界観設定
{world_ctx if world_ctx else '（未設定）'}

## 今回執筆する{section_label}
{title}

## この{section_label}のプロット（箇条書きのあらまし）
{body}

## 執筆の指示
- 上記プロットの箇条書きを忠実に本文へ展開してください
- 情景・心理描写を豊かに盛り込んだ読み応えのある小説文体で書いてください
- 会話文・地の文を自然に組み合わせてください
- 分量の目安は1章辺り3000〜5000字程度です
- {writing_note}
- 出力はマークダウン形式で、最初に「# {title.lstrip('# ').strip()}」の見出しを付けてください
- 前置きや説明文は不要です。本文のみ出力してください"""

        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=30000,
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

以下のフォーマットに厳密に従って、詳細なキャラクタープロファイルを作成してください：

# キャラクター設定

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

上記のフォーマットの各項目を埋めてください。マークダウン形式で出力し、説明文や前置きは不要です。""",

        'plot_development': f"""以下のプロジェクト設定を参考に、プロット展開案を提案してください。

{ctx_text}

現在の内容:
{current_content}

目標執筆量: {data.get('length', '中編')}
- 短編: 5000文字前後（章数: 3-5章）
- 中編: 5万文字前後（章数: 10-15章）
- 長編: 10万文字前後（章数: 20-30章）

追加の要望: {extra_context}

指定された目標執筆量に適した章数と展開ペースで、以下を含むプロット展開を提案してください：
- 次の展開案（複数）
- 伏線の提案
- クライマックスへの道筋
- 読者を引きつけるポイント
- 各章のおおよその文字数配分""",

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
        model='claude-sonnet-4-6',
        max_tokens=30000,
        messages=[{'role': 'user', 'content': prompt}],
        timeout=600.0  # 10分のタイムアウト
    )

    return jsonify({'result': message.content[0].text})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
