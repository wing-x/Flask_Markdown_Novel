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
  const files = await res.json();
  const list = document.getElementById('file-list');
  list.innerHTML = '';
  files.forEach(f => {
    const li = document.createElement('li');
    li.textContent = f;
    li.onclick = () => openFile(f);
    li.dataset.name = f;
    list.appendChild(li);
  });
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
  document.querySelectorAll('#file-list li').forEach(li => {
    li.classList.toggle('active', li.dataset.name === filename);
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

// ---- Claude連携 ----
function claudeAction(action) {
  selectedAction = action;
  document.querySelectorAll('.claude-btn').forEach(btn => btn.classList.remove('selected'));
  event.target.classList.add('selected');
  document.getElementById('claude-run-btn').disabled = !currentProject;
}

async function runClaudeAction() {
  if (!selectedAction || !currentProject) return;

  const btn = document.getElementById('claude-run-btn');
  btn.disabled = true;
  btn.textContent = '生成中…';

  const context = document.getElementById('claude-context').value;
  const currentContent = editor.getValue();

  const res = await fetch('/api/claude/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      action: selectedAction,
      project: currentProject,
      current_content: currentContent,
      context
    })
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
