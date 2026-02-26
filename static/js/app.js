let editor = null;
let currentProject = '';
let currentFile = '';
let selectedAction = '';
let claudeResult = '';

// ---- 初期化 ----
window.addEventListener('DOMContentLoaded', () => {
  editor = CodeMirror.fromTextArea(document.getElementById('editor'), {
    mode: 'markdown',
    theme: 'default',
    lineNumbers: true,
    lineWrapping: true,
    autofocus: false,
  });

  // DOMが確定してから高さを再計算させる
  setTimeout(() => editor.refresh(), 0);

  // ウィンドウリサイズ時にも再計算
  window.addEventListener('resize', () => editor.refresh());

  editor.on('change', () => {
    updatePreview();
  });

  loadProjects();
});

function updatePreview() {
  const md = editor.getValue();
  document.getElementById('preview').innerHTML = marked.parse(md);
}

// ---- トースト通知 ----
function showToast(msg, color = '#1a5aa0') {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.style.background = color;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// ---- プロジェクト ----
async function loadProjects() {
  const res = await fetch('/api/projects');
  const projects = await res.json();
  const sel = document.getElementById('project-select');
  sel.innerHTML = '<option value="">-- プロジェクトを選択 --</option>';
  projects.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p;
    opt.textContent = p;
    sel.appendChild(opt);
  });
}

async function createProject() {
  const name = document.getElementById('new-project-name').value.trim();
  if (!name) { showToast('プロジェクト名を入力してください', '#a03020'); return; }
  const res = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });
  if (res.ok) {
    document.getElementById('new-project-name').value = '';
    await loadProjects();
    document.getElementById('project-select').value = name;
    await loadProject(name);
    showToast(`プロジェクト「${name}」を作成しました`);
  }
}

async function loadProject(name) {
  if (!name) return;
  currentProject = name;
  currentFile = '';
  document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
  document.getElementById('save-btn').disabled = true;
  editor.setValue('');
  updatePreview();
  await loadFiles();
}

// ---- ファイル一覧 ----
async function loadFiles() {
  if (!currentProject) return;
  const res = await fetch(`/api/projects/${currentProject}/files`);
  const structure = await res.json();
  const list = document.getElementById('file-list');
  list.innerHTML = '';
  renderFileTree(structure, list, 0);
}

function renderFileTree(items, parentElement, depth) {
  items.forEach(item => {
    if (item.type === 'directory') {
      // ディレクトリ
      const dirLi = document.createElement('li');
      dirLi.className = 'directory-item';
      dirLi.style.paddingLeft = `${depth * 15}px`;

      const dirHeader = document.createElement('div');
      dirHeader.className = 'directory-header';
      dirHeader.innerHTML = `<span class="dir-icon">📁</span> ${item.name}`;
      dirHeader.onclick = () => toggleDirectory(dirLi);

      dirLi.appendChild(dirHeader);

      const childrenUl = document.createElement('ul');
      childrenUl.className = 'directory-children';
      childrenUl.style.display = 'none';
      renderFileTree(item.children, childrenUl, depth + 1);

      dirLi.appendChild(childrenUl);
      parentElement.appendChild(dirLi);
    } else {
      // ファイル
      const fileLi = document.createElement('li');
      fileLi.className = 'file-item';
      fileLi.style.paddingLeft = `${depth * 15}px`;
      fileLi.innerHTML = `<span class="file-icon">📄</span> ${item.name}`;
      fileLi.onclick = () => openFile(item.path);
      fileLi.dataset.path = item.path;
      parentElement.appendChild(fileLi);
    }
  });
}

function toggleDirectory(dirElement) {
  const childrenUl = dirElement.querySelector('.directory-children');
  const icon = dirElement.querySelector('.dir-icon');
  if (childrenUl.style.display === 'none') {
    childrenUl.style.display = 'block';
    icon.textContent = '📂';
  } else {
    childrenUl.style.display = 'none';
    icon.textContent = '📁';
  }
}

// ---- ★ クイック作成ボタン（timeline.md / worldbuilding.md など） ----
async function quickCreateFile(filename) {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }
  const res = await fetch(`/api/projects/${currentProject}/files/${filename}`, {
    method: 'POST',
  });
  if (res.ok) {
    const data = await res.json();
    if (data.created) {
      showToast(`${filename} を作成しました ✅`, '#1a7a40');
    } else {
      showToast(`${filename} を開きました`);
    }
    await loadFiles();
    await openFile(filename);
  }
}

// ---- カスタムファイル作成 ----
async function createCustomFile() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }
  let name = document.getElementById('new-file-name').value.trim();
  if (!name) { showToast('ファイル名を入力してください', '#a03020'); return; }
  if (!name.endsWith('.md')) name += '.md';

  const res = await fetch(`/api/projects/${currentProject}/files/${name}`, {
    method: 'POST',
  });
  if (res.ok) {
    document.getElementById('new-file-name').value = '';
    await loadFiles();
    await openFile(name);
    showToast(`${name} を作成しました`);
  }
}

// ---- ファイルを開く ----
async function openFile(filename) {
  if (!currentProject) return;
  const res = await fetch(`/api/projects/${currentProject}/files/${filename}`);
  if (!res.ok) { showToast('ファイルを開けませんでした', '#a03020'); return; }
  const data = await res.json();
  currentFile = filename;
  editor.setValue(data.content);
  updatePreview();
  document.getElementById('current-file-label').textContent = `✏️ ${filename}`;
  document.getElementById('save-btn').disabled = false;

  // アクティブ表示
  document.querySelectorAll('#file-list .file-item').forEach(li => {
    li.classList.toggle('active', li.dataset.path === filename);
  });
}

// ---- ファイル保存 ----
async function saveFile() {
  if (!currentProject || !currentFile) return;
  const content = editor.getValue();
  const res = await fetch(`/api/projects/${currentProject}/files/${currentFile}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content })
  });
  if (res.ok) {
    showToast('💾 保存しました');
  }
}

// Ctrl+S で保存
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    saveFile();
  }
});

// ---- ★ plot.md → chapter ファイル生成 ----
async function generateChapters() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('plot-to-chapters-btn');
  const progressWrap = document.getElementById('chapter-progress');
  const progressBar = document.getElementById('chapter-progress-bar');
  const progressLabel = document.getElementById('chapter-progress-label');

  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';
  progressWrap.style.display = 'block';
  progressBar.style.width = '10%';
  progressLabel.textContent = 'plot.md を解析中…';

  try {
    const res = await fetch('/api/claude/generate_chapters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject })
    });

    progressBar.style.width = '90%';
    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    progressBar.style.width = '100%';
    const count = data.count;
    const names = data.created.map(c => c.filename).join('、');
    progressLabel.textContent = `${count} ファイル生成完了`;

    // ファイルリストを更新して最初の chapter を開く
    await loadFiles();
    if (data.created.length > 0) {
      await openFile(data.created[0].filename);
    }

    showToast(`📝 ${names} を生成しました ✅`, '#1a7a40');

    // 3秒後にプログレスを非表示
    setTimeout(() => {
      progressWrap.style.display = 'none';
      progressBar.style.width = '0%';
    }, 3000);

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '📝 plot.md → chapters';
  }
}

// ---- ★ draft → plot.md 生成 ----
async function generatePlotFromDraft() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('draft-to-plot-btn');
  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';

  try {
    const res = await fetch('/api/claude/draft_to_plot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    // ファイルリストを更新して plot.md を開く
    await loadFiles();
    await openFile('plot.md');
    showToast('plot.md を生成・保存しました ✅', '#1a7a40');

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '✍️ draft → plot.md';
  }
}

// ---- Claudeパネル 折りたたみ ----
function toggleClaudePanel() {
  const body = document.getElementById('claude-panel-body');
  const btn  = document.getElementById('claude-toggle-btn');
  const collapsed = body.classList.toggle('collapsed');
  btn.classList.toggle('collapsed', collapsed);
  btn.textContent = '▼';
  localStorage.setItem('claudePanelCollapsed', collapsed ? '1' : '0');
  // パネル開閉後にエディタの高さを再計算
  setTimeout(() => editor && editor.refresh(), 260);
}

// 初回ロード時：前回の状態を復元（デフォルトは展開）
window.addEventListener('DOMContentLoaded', () => {
  const wasCollapsed = localStorage.getItem('claudePanelCollapsed') === '1';
  if (wasCollapsed) {
    document.getElementById('claude-panel-body').classList.add('collapsed');
    document.getElementById('claude-toggle-btn').classList.add('collapsed');
  }
});

// ---- Claude連携 ----
function claudeAction(action) {
  selectedAction = action;
  document.querySelectorAll('.claude-btn').forEach(btn => btn.classList.remove('selected'));
  event.target.classList.add('selected');
  document.getElementById('claude-run-btn').disabled = !currentProject;

  // プロット展開案の場合のみ執筆量選択UIを表示
  const lengthSelector = document.getElementById('plot-length-selector');
  if (action === 'plot_development') {
    lengthSelector.style.display = 'block';
  } else {
    lengthSelector.style.display = 'none';
  }
}

async function runClaudeAction() {
  if (!selectedAction || !currentProject) return;

  const btn = document.getElementById('claude-run-btn');
  btn.disabled = true;
  btn.textContent = '生成中…';

  const context = document.getElementById('claude-context').value;
  const currentContent = editor.getValue();

  // プロット展開案の場合は執筆量を取得
  const requestBody = {
    action: selectedAction,
    project: currentProject,
    current_content: currentContent,
    context
  };

  if (selectedAction === 'plot_development') {
    requestBody.length = document.getElementById('plot-length-select').value;
  }

  const res = await fetch('/api/claude/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody)
  });

  btn.disabled = false;
  btn.textContent = '実行';

  if (res.ok) {
    const data = await res.json();
    claudeResult = data.result;
    const resultEl = document.getElementById('claude-result');
    resultEl.style.display = 'block';
    resultEl.textContent = claudeResult;
    document.getElementById('insert-result-btn').style.display = 'inline-block';
  } else {
    showToast('Claude APIエラーが発生しました', '#a03020');
  }
}

function insertResult() {
  if (!claudeResult) return;
  const current = editor.getValue();
  editor.setValue(current + '\n\n' + claudeResult);
  updatePreview();
  showToast('エディタに挿入しました ✅', '#1a7a40');
}
