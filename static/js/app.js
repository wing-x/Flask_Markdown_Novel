let editor = null;
let currentProject = '';
let currentFile = '';
let selectedAction = '';
let claudeResult = '';
let contextMenuTarget = null;

// ★ シリーズ管理用の状態
let currentSeries = '';           // 選択中のシリーズ名
let currentVolume = null;         // 選択中の巻情報 {order, title, project_name}
let currentFileContext = 'project'; // 'project' or 'series' (聖典ファイル編集中かどうか)

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
  loadSeriesList();

  // 初期状態：ファイルセクションは非表示（プロジェクト or 巻選択後に表示）
  document.getElementById('file-section').style.display = 'none';

  // コンテキストメニューを閉じる
  document.addEventListener('click', () => {
    document.getElementById('file-context-menu').style.display = 'none';
  });
});

function updatePreview() {
  const content = editor.getValue();
  const previewEl = document.getElementById('preview');

  // .txtファイルの場合はプレーンテキストとして表示（改行を保持）
  if (currentFile && currentFile.endsWith('.txt')) {
    previewEl.innerHTML = '<pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit; margin: 0;">' +
                          escapeHtml(content) +
                          '</pre>';
  } else {
    // .mdファイルの場合はMarkdownレンダリング
    previewEl.innerHTML = marked.parse(content);
  }
}

// HTMLエスケープ用ヘルパー関数
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
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

// ---- シリーズ管理 ----

async function loadSeriesList() {
  const res = await fetch('/api/series');
  const seriesList = await res.json();
  const sel = document.getElementById('series-select');
  sel.innerHTML = '<option value="">-- シリーズを選択 --</option>';
  seriesList.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = `📚 ${s}`;
    sel.appendChild(opt);
  });
}

async function createSeries() {
  const name = document.getElementById('new-series-name').value.trim();
  if (!name) { showToast('シリーズ名を入力してください', '#a03020'); return; }

  const res = await fetch('/api/series', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name })
  });

  if (res.ok) {
    document.getElementById('new-series-name').value = '';
    await loadSeriesList();
    document.getElementById('series-select').value = name;
    await onSeriesChange(name);
    showToast(`📚 シリーズ「${name}」を作成しました`);
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

async function onSeriesChange(seriesName) {
  currentSeries = seriesName;
  currentVolume = null;
  currentProject = '';
  currentFile = '';
  currentFileContext = 'project';

  // エディタをリセット
  editor.setValue('');
  updatePreview();
  document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
  document.getElementById('save-btn').disabled = true;

  if (!seriesName) {
    document.getElementById('series-bible-section').style.display = 'none';
    document.getElementById('volume-section').style.display = 'none';
    document.getElementById('file-section').style.display = 'none';
    return;
  }

  // 聖典ボタン・巻セクションを表示
  document.getElementById('series-bible-section').style.display = 'block';
  document.getElementById('volume-section').style.display = 'block';
  document.getElementById('file-section').style.display = 'none';
  document.getElementById('volume-badge').style.display = 'none';

  await loadVolumeList(seriesName);
}

async function loadVolumeList(seriesName) {
  const res = await fetch(`/api/series/${encodeURIComponent(seriesName)}/volumes`);
  const volumes = await res.json();

  const sel = document.getElementById('volume-select');
  sel.innerHTML = '<option value="">-- 巻を選択 --</option>';
  volumes.forEach(v => {
    const opt = document.createElement('option');
    opt.value = v.project_name;
    opt.dataset.order = v.order;
    opt.dataset.title = v.title;
    opt.textContent = `第${v.order}巻「${v.title}」`;
    sel.appendChild(opt);
  });
}

async function createVolume() {
  if (!currentSeries) {
    showToast('先にシリーズを選択してください', '#a06020');
    return;
  }
  const title = document.getElementById('new-volume-title').value.trim();
  if (!title) { showToast('巻のタイトルを入力してください', '#a03020'); return; }

  const res = await fetch(`/api/series/${encodeURIComponent(currentSeries)}/volumes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title })
  });

  if (res.ok) {
    const data = await res.json();
    document.getElementById('new-volume-title').value = '';
    await loadVolumeList(currentSeries);
    document.getElementById('volume-select').value = data.project_name;
    await onVolumeChange(data.project_name);
    showToast(`📕 第${data.order}巻「${data.title}」を作成しました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

async function onVolumeChange(projectName) {
  if (!projectName) {
    currentVolume = null;
    currentProject = '';
    currentFile = '';
    currentFileContext = 'project';
    editor.setValue('');
    updatePreview();
    document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
    document.getElementById('save-btn').disabled = true;
    document.getElementById('file-section').style.display = 'none';
    document.getElementById('volume-badge').style.display = 'none';
    document.getElementById('volume-summary-section').style.display = 'none';
    return;
  }

  // 選択された巻のオプション情報を取得
  const sel = document.getElementById('volume-select');
  const selectedOpt = sel.querySelector(`option[value="${projectName}"]`);
  if (selectedOpt) {
    currentVolume = {
      order: selectedOpt.dataset.order,
      title: selectedOpt.dataset.title,
      project_name: projectName
    };
  }

  currentProject = projectName;
  currentFile = '';
  currentFileContext = 'project';

  editor.setValue('');
  updatePreview();
  document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
  document.getElementById('save-btn').disabled = true;

  // バッジ表示
  const badge = document.getElementById('volume-badge');
  badge.textContent = `📚 ${currentSeries}  ›  第${currentVolume.order}巻「${currentVolume.title}」`;
  badge.style.display = 'block';

  // 巻サマリー生成ボタンを表示
  document.getElementById('volume-summary-section').style.display = 'flex';

  // ファイルセクションを表示
  document.getElementById('file-section').style.display = 'block';
  await loadFiles();

  // 単体プロジェクトのセレクトをリセット
  document.getElementById('project-select').value = '';
}

// シリーズ聖典ファイルを開く
async function openSeriesBibleFile(filename) {
  if (!currentSeries) return;

  const res = await fetch(`/api/series/${encodeURIComponent(currentSeries)}/files/${filename}`);
  if (!res.ok) { showToast('ファイルを開けませんでした', '#a03020'); return; }

  const data = await res.json();
  currentFile = filename;
  currentFileContext = 'series';
  currentProject = ''; // プロジェクトは非選択状態に

  editor.setValue(data.content);
  updatePreview();

  const badgeHtml = `<span id="series-context-badge">聖典</span>`;
  document.getElementById('current-file-label').innerHTML = `${badgeHtml}✏️ ${filename}`;
  document.getElementById('save-btn').disabled = false;

  // 巻のファイルセクションは非表示
  document.getElementById('file-section').style.display = 'none';

  showToast(`📖 聖典「${filename}」を開きました`);
}

// 単体プロジェクト選択時（シリーズをリセット）
async function onProjectSelectChange(name) {
  if (!name) return;
  // シリーズ選択をリセット
  currentSeries = '';
  currentVolume = null;
  document.getElementById('series-select').value = '';
  document.getElementById('series-bible-section').style.display = 'none';
  document.getElementById('volume-section').style.display = 'none';
  document.getElementById('volume-badge').style.display = 'none';
  document.getElementById('file-section').style.display = 'block';

  await loadProject(name);
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
  currentFileContext = 'project';
  document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
  document.getElementById('save-btn').disabled = true;
  editor.setValue('');
  updatePreview();
  document.getElementById('file-section').style.display = 'block';
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
      dirHeader.oncontextmenu = (e) => {
        e.preventDefault();
        showContextMenu(e, item.path);
      };
      dirHeader.dataset.dirPath = item.path;

      // ディレクトリをドロップゾーンにする
      dirHeader.addEventListener('dragover', (e) => {
        e.preventDefault();
        dirHeader.classList.add('drag-over');
      });

      dirHeader.addEventListener('dragleave', (e) => {
        dirHeader.classList.remove('drag-over');
      });

      dirHeader.addEventListener('drop', (e) => {
        e.preventDefault();
        e.stopPropagation();
        dirHeader.classList.remove('drag-over');
        const sourcePath = e.dataTransfer.getData('text/plain');
        const destDir = item.path;
        if (sourcePath && destDir) {
          moveFileDragDrop(sourcePath, destDir);
        }
      });

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
      fileLi.draggable = true;
      fileLi.dataset.path = item.path; // アクティブ表示用にパスを保存
      fileLi.onclick = (e) => {
        if (e.button === 0) { // 左クリック
          openFile(item.path);
        }
      };
      fileLi.oncontextmenu = (e) => {
        e.preventDefault();
        showContextMenu(e, item.path);
      };

      // ドラッグ開始
      fileLi.addEventListener('dragstart', (e) => {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', item.path);
        fileLi.classList.add('dragging');
      });

      // ドラッグ終了
      fileLi.addEventListener('dragend', (e) => {
        fileLi.classList.remove('dragging');
        // すべてのdrag-overクラスを削除
        document.querySelectorAll('.drag-over').forEach(el => {
          el.classList.remove('drag-over');
        });
      });

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

  // .txtファイルの場合はプレーンテキストモード、.mdファイルの場合はMarkdownモード
  if (filename.endsWith('.txt')) {
    editor.setOption('mode', 'text/plain');
  } else if (filename.endsWith('.md')) {
    editor.setOption('mode', 'markdown');
  }

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
  if (!currentFile) return;
  const content = editor.getValue();

  let url;
  if (currentFileContext === 'series' && currentSeries) {
    // シリーズ聖典ファイルの保存
    url = `/api/series/${encodeURIComponent(currentSeries)}/files/${currentFile}`;
  } else if (currentProject) {
    // 通常プロジェクトファイルの保存
    url = `/api/projects/${currentProject}/files/${currentFile}`;
  } else {
    return;
  }

  const res = await fetch(url, {
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
      body: JSON.stringify({ project: currentProject, series: currentSeries })
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

// ---- ★ plot_draft → timeline.md 生成 ----
async function generateTimelineFromDraft() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('plot-draft-to-timeline-btn');
  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';

  try {
    const res = await fetch('/api/claude/plot_draft_to_timeline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject, series: currentSeries })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    // ファイルリストを更新して timeline.md を開く
    await loadFiles();
    await openFile('timeline.md');
    showToast('📅 timeline.md を生成・保存しました ✅', '#1a7a40');

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '📅 timeline.md 作成';
  }
}

// ---- ★ plot_draft → worldbuilding.md 生成 ----
async function generateWorldbuildingFromDraft() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('plot-draft-to-worldbuilding-btn');
  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';

  try {
    const res = await fetch('/api/claude/plot_draft_to_worldbuilding', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject, series: currentSeries })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    // ファイルリストを更新して worldbuilding.md を開く
    await loadFiles();
    await openFile('worldbuilding.md');
    showToast('🌍 worldbuilding.md を生成・保存しました ✅', '#1a7a40');

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '🌍 worldbuilding.md 作成';
  }
}

// ---- ★ plot.md → キャッチコピー生成 ----
async function generateCatchcopy() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('plot-to-catchcopy-btn');
  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';

  try {
    const res = await fetch('/api/claude/generate_catchcopy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject, series: currentSeries })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    // ファイルリストを更新して catchcopy.md を開く
    await loadFiles();
    await openFile('catchcopy.md');
    showToast('💡 catchcopy.md を生成・保存しました ✅', '#1a7a40');

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '💡 キャッチコピー作成';
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
      body: JSON.stringify({ project: currentProject, series: currentSeries })
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
  if (action === 'plot_draft') {
    lengthSelector.style.display = 'block';
  } else {
    lengthSelector.style.display = 'none';
  }

  // キャラクター生成の場合のみ生成オプションUIを表示
  const characterOptions = document.getElementById('character-generation-options');
  if (action === 'generate_character') {
    characterOptions.style.display = 'block';
  } else {
    characterOptions.style.display = 'none';
  }
}

function toggleCharacterMode() {
  const mode = document.getElementById('character-mode-select').value;
  const newMode = document.getElementById('character-new-mode');
  const draftMode = document.getElementById('character-draft-mode');

  if (mode === 'new') {
    newMode.style.display = 'block';
    draftMode.style.display = 'none';
  } else {
    newMode.style.display = 'none';
    draftMode.style.display = 'block';
  }
}

async function loadDraftCharacters() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  const btn = document.getElementById('load-draft-characters-btn');
  btn.disabled = true;
  btn.textContent = '読み込み中...';

  try {
    const res = await fetch('/api/claude/plot_draft_to_characters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject, series: currentSeries })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    const select = document.getElementById('draft-character-select');
    select.innerHTML = '<option value="">-- キャラクターを選択 --</option>';

    if (data.characters && data.characters.length > 0) {
      data.characters.forEach(char => {
        const option = document.createElement('option');
        option.value = char;
        option.textContent = char;
        select.appendChild(option);
      });
      showToast(`${data.characters.length}人のキャラクターを読み込みました`, '#1a7a40');
    } else {
      showToast('plot_draftにキャラクターが見つかりませんでした', '#a06020');
    }

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = 'キャラクターリストを読み込む';
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
    series: currentSeries || undefined,   // ★ シリーズ情報を付加
    current_content: currentContent,
    context
  };

  if (selectedAction === 'plot_draft') {
    requestBody.length = document.getElementById('plot-length-select').value;
  }

  // キャラクター生成の場合は生成モードに応じて処理
  if (selectedAction === 'generate_character') {
    const mode = document.getElementById('character-mode-select').value;
    const useChatMode = document.getElementById('character-chat-mode-checkbox').checked;

    if (mode === 'new') {
      // 新規作成モード
      const characterRole = document.getElementById('character-role-select').value;

      // チャットモードの場合
      if (useChatMode) {
        console.log('Starting new character chat with role:', characterRole);
        await startCharacterChat(null, mode, characterRole);
        btn.disabled = false;
        btn.textContent = '実行';
        return;
      }

      requestBody.character_role = characterRole;
    } else {
      // plot_draftから生成モード
      const characterName = document.getElementById('draft-character-select').value;
      if (!characterName) {
        showToast('キャラクターを選択してください', '#a03020');
        btn.disabled = false;
        btn.textContent = '実行';
        return;
      }

      // チャットモードの場合
      if (useChatMode) {
        console.log('Starting character chat for:', characterName);
        await startCharacterChat(characterName, mode);
        btn.disabled = false;
        btn.textContent = '実行';
        return;
      }

      // 通常モード: 別のAPIエンドポイントを使用
      const charRes = await fetch('/api/claude/generate_character_from_draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: currentProject,
          series: currentSeries || undefined,   // ★ シリーズ情報を付加
          character_name: characterName
        })
      });

      btn.disabled = false;
      btn.textContent = '実行';

      if (charRes.ok) {
        const charData = await charRes.json();
        claudeResult = charData.result;
        const resultEl = document.getElementById('claude-result');
        resultEl.style.display = 'block';
        resultEl.textContent = claudeResult;
        document.getElementById('insert-result-btn').style.display = 'inline-block';
      } else {
        showToast('Claude APIエラーが発生しました', '#a03020');
      }
      return;
    }
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

// ---- ファイル管理機能 ----

function showContextMenu(event, filePath) {
  event.stopPropagation();
  event.preventDefault(); // コンテキストメニュー表示時も念のため
  contextMenuTarget = filePath;

  const menu = document.getElementById('file-context-menu');
  menu.style.display = 'block';

  // ウィンドウサイズとメニューサイズを取得して、見切れを防ぐ
  const menuWidth = menu.offsetWidth;
  const menuHeight = menu.offsetHeight;
  const windowWidth = window.innerWidth;
  const windowHeight = window.innerHeight;

  let x = event.clientX;
  let y = event.clientY;

  // 右側の端を越える場合
  if (x + menuWidth > windowWidth) {
    x = windowWidth - menuWidth - 5;
  }
  // 下側の端を越える場合
  if (y + menuHeight > windowHeight) {
    y = windowHeight - menuHeight - 5;
  }

  menu.style.left = x + 'px';
  menu.style.top = y + 'px';
}

async function createDirectory() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }
  const name = document.getElementById('new-dir-name').value.trim();
  if (!name) {
    showToast('ディレクトリ名を入力してください', '#a03020');
    return;
  }

  const res = await fetch(`/api/projects/${currentProject}/directories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path: name })
  });

  if (res.ok) {
    document.getElementById('new-dir-name').value = '';
    await loadFiles();
    showToast(`📁 ${name} を作成しました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

function renameFileDialog() {
  if (!contextMenuTarget) return;
  const fileName = contextMenuTarget.split('/').pop();
  document.getElementById('rename-input').value = fileName;
  document.getElementById('rename-dialog').style.display = 'flex';
}

async function confirmRename() {
  if (!currentProject || !contextMenuTarget) return;
  const newName = document.getElementById('rename-input').value.trim();
  if (!newName) {
    showToast('ファイル名を入力してください', '#a03020');
    return;
  }

  // ディレクトリ構造を保持
  const pathParts = contextMenuTarget.split('/');
  pathParts[pathParts.length - 1] = newName;
  const newPath = pathParts.join('/');

  const res = await fetch(`/api/projects/${currentProject}/rename`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ old_path: contextMenuTarget, new_path: newPath })
  });

  if (res.ok) {
    // 現在開いているファイルがリネームされた場合
    if (currentFile === contextMenuTarget) {
      currentFile = newPath;
      document.getElementById('current-file-label').textContent = `✏️ ${newPath}`;
    }
    await loadFiles();
    closeModal('rename-dialog');
    showToast(`✏️ ${newName} にリネームしました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

function moveFileDialog() {
  if (!contextMenuTarget) return;
  document.getElementById('move-input').value = '';
  document.getElementById('move-dialog').style.display = 'flex';
}

async function confirmMove() {
  if (!currentProject || !contextMenuTarget) return;
  const destDir = document.getElementById('move-input').value.trim();
  if (!destDir) {
    showToast('移動先を入力してください', '#a03020');
    return;
  }

  const fileName = contextMenuTarget.split('/').pop();
  const destPath = destDir.endsWith('/') ? destDir + fileName : destDir + '/' + fileName;

  const res = await fetch(`/api/projects/${currentProject}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: contextMenuTarget, destination: destPath })
  });

  if (res.ok) {
    // 現在開いているファイルが移動された場合
    if (currentFile === contextMenuTarget) {
      currentFile = destPath;
      document.getElementById('current-file-label').textContent = `✏️ ${destPath}`;
    }
    await loadFiles();
    closeModal('move-dialog');
    showToast(`📦 ${destPath} に移動しました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

function deleteFileDialog() {
  if (!contextMenuTarget) return;
  document.getElementById('delete-confirm-text').textContent =
    `「${contextMenuTarget}」を削除してもよろしいですか？`;
  document.getElementById('delete-dialog').style.display = 'flex';
}

async function confirmDelete() {
  if (!currentProject || !contextMenuTarget) return;

  const res = await fetch(`/api/projects/${currentProject}/files/${contextMenuTarget}`, {
    method: 'DELETE'
  });

  if (res.ok) {
    // 現在開いているファイルが削除された場合
    if (currentFile === contextMenuTarget) {
      currentFile = '';
      editor.setValue('');
      document.getElementById('current-file-label').textContent = 'ファイルを選択してください';
      document.getElementById('save-btn').disabled = true;
    }
    await loadFiles();
    closeModal('delete-dialog');
    showToast(`🗑️ ${contextMenuTarget} を削除しました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

function closeModal(modalId) {
  document.getElementById(modalId).style.display = 'none';
}

async function moveFileDragDrop(sourcePath, destDir) {
  if (!currentProject || !sourcePath || !destDir) return;

  const fileName = sourcePath.split('/').pop();
  const destPath = destDir.endsWith('/') ? destDir + fileName : destDir + '/' + fileName;

  // 同じ場所への移動は無視
  const sourceDir = sourcePath.substring(0, sourcePath.lastIndexOf('/'));
  if (sourceDir === destDir) {
    return;
  }

  const res = await fetch(`/api/projects/${currentProject}/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source: sourcePath, destination: destPath })
  });

  if (res.ok) {
    // 現在開いているファイルが移動された場合
    if (currentFile === sourcePath) {
      currentFile = destPath;
      document.getElementById('current-file-label').textContent = `✏️ ${destPath}`;
    }
    await loadFiles();
    showToast(`📦 ${destPath} に移動しました`, '#1a7a40');
  } else {
    const data = await res.json();
    showToast(data.error || 'エラーが発生しました', '#c0392b');
  }
}

// ============================================================
// 伏線管理パネル
// ============================================================

let foreshadowingItems = [];     // 全データキャッシュ
let fsStatusFilter = 'all';      // 現在のステータスフィルター
let fsEditingId = null;          // 編集中のID（null=新規）

// ---- パネル開閉 ----

async function openForeshadowingPanel() {
  if (!currentSeries) {
    showToast('先にシリーズを選択してください', '#a06020');
    return;
  }
  document.getElementById('fs-series-label').textContent =
    `伏線管理 — 📚 ${currentSeries}`;
  document.getElementById('foreshadowing-panel').style.display = 'flex';
  await refreshForeshadowing();
}

function closeForeshadowingPanel() {
  document.getElementById('foreshadowing-panel').style.display = 'none';
}

// ESC でパネルを閉じる
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    if (document.getElementById('foreshadowing-form-modal').style.display !== 'none') {
      closeModal('foreshadowing-form-modal');
    } else if (document.getElementById('foreshadowing-panel').style.display !== 'none') {
      closeForeshadowingPanel();
    }
  }
});

// ---- データ取得 ----

async function refreshForeshadowing() {
  if (!currentSeries) return;
  const res = await fetch(`/api/series/${encodeURIComponent(currentSeries)}/foreshadowing`);
  if (!res.ok) { showToast('伏線データの取得に失敗しました', '#c0392b'); return; }
  foreshadowingItems = await res.json();
  populateVolumeFilter();
  renderForeshadowingList();
}

// ---- ボリュームフィルター生成 ----

function populateVolumeFilter() {
  const sel = document.getElementById('fs-volume-filter');
  const current = sel.value;
  const vols = [...new Set(foreshadowingItems.map(i => i.introduced_volume))].sort((a,b)=>a-b);
  sel.innerHTML = '<option value="">すべての巻</option>';
  vols.forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = `第${v}巻`;
    sel.appendChild(o);
  });
  sel.value = current;
}

// ---- フィルタータブ ----

function setFsStatusFilter(status) {
  fsStatusFilter = status;
  document.querySelectorAll('.fs-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.status === status);
  });
  renderForeshadowingList();
}

// ---- リスト描画 ----

function renderForeshadowingList() {
  const keyword = (document.getElementById('fs-keyword-filter')?.value || '').trim().toLowerCase();
  const volFilter = document.getElementById('fs-volume-filter')?.value || '';

  let items = foreshadowingItems.filter(item => {
    if (fsStatusFilter !== 'all' && item.status !== fsStatusFilter) return false;
    if (volFilter && String(item.introduced_volume) !== String(volFilter)) return false;
    if (keyword) {
      const haystack = [
        item.summary, item.notes, item.resolve_target,
        ...(item.related_characters || [])
      ].join(' ').toLowerCase();
      if (!haystack.includes(keyword)) return false;
    }
    return true;
  });

  const grid = document.getElementById('fs-cards');
  const empty = document.getElementById('fs-empty');

  // 統計
  const total = foreshadowingItems.length;
  const openCount = foreshadowingItems.filter(i => i.status === 'open').length;
  const resolvedCount = foreshadowingItems.filter(i => i.status === 'resolved').length;
  document.getElementById('fs-stats').textContent =
    `全 ${total} 件 ／ 未回収 ${openCount} 件 ／ 回収済み ${resolvedCount} 件`;

  if (items.length === 0) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }
  empty.style.display = 'none';

  grid.innerHTML = items.map(item => renderForeshadowingCard(item)).join('');
}

function renderForeshadowingCard(item) {
  const statusLabel = { open: '未回収', resolved: '回収済み', abandoned: '意図的放置' }[item.status] || item.status;
  const badgeClass = `fs-badge fs-badge-status-${item.status}`;

  const chars = (item.related_characters || []).length > 0
    ? `<div class="fs-card-characters">👤 ${item.related_characters.join('、')}</div>`
    : '';

  const notes = item.notes
    ? `<div class="fs-card-notes">📝 ${escapeHtml(item.notes)}</div>`
    : '';

  const resolveInfo = item.status === 'resolved' && (item.resolved_volume || item.resolved_chapter)
    ? `<span class="fs-badge fs-badge-ch">✅ ${item.resolved_volume ? '第' + item.resolved_volume + '巻' : ''}${item.resolved_chapter ? ' ' + item.resolved_chapter : ''}</span>`
    : item.resolve_target
    ? `<span class="fs-badge fs-badge-target">🎯 ${escapeHtml(item.resolve_target)}</span>`
    : '';

  return `
    <div class="fs-card status-${item.status}" data-id="${item.id}">
      <div class="fs-card-header">
        <span class="fs-card-id">${item.id}</span>
        <div class="fs-card-actions">
          <button class="edit-btn" title="編集" onclick="openForeshadowingForm('${item.id}')">✏️</button>
          <button class="del-btn"  title="削除" onclick="deleteForeshadowingItem('${item.id}')">🗑️</button>
        </div>
      </div>
      <div class="fs-card-summary">${escapeHtml(item.summary)}</div>
      <div class="fs-card-meta">
        <span class="${badgeClass}">${statusLabel}</span>
        <span class="fs-badge fs-badge-vol">第${item.introduced_volume}巻</span>
        ${item.introduced_chapter ? `<span class="fs-badge fs-badge-ch">${escapeHtml(item.introduced_chapter)}</span>` : ''}
        ${resolveInfo}
      </div>
      ${chars}
      ${notes}
    </div>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---- フォーム開閉 ----

function openForeshadowingForm(editId = null) {
  fsEditingId = editId;
  const isEdit = editId !== null;
  document.getElementById('fs-form-title').textContent = isEdit ? '🔖 伏線を編集' : '🔖 伏線を追加';

  // フォームをリセット
  document.getElementById('fs-f-summary').value = '';
  document.getElementById('fs-f-introduced-volume').value = 1;
  document.getElementById('fs-f-introduced-chapter').value = '';
  document.getElementById('fs-f-status').value = 'open';
  document.getElementById('fs-f-resolve-target').value = '';
  document.getElementById('fs-f-resolved-volume').value = '';
  document.getElementById('fs-f-resolved-chapter').value = '';
  document.getElementById('fs-f-related-characters').value = '';
  document.getElementById('fs-f-notes').value = '';
  toggleResolveFields();

  if (isEdit) {
    const item = foreshadowingItems.find(i => i.id === editId);
    if (item) {
      document.getElementById('fs-f-summary').value = item.summary || '';
      document.getElementById('fs-f-introduced-volume').value = item.introduced_volume || 1;
      document.getElementById('fs-f-introduced-chapter').value = item.introduced_chapter || '';
      document.getElementById('fs-f-status').value = item.status || 'open';
      document.getElementById('fs-f-resolve-target').value = item.resolve_target || '';
      document.getElementById('fs-f-resolved-volume').value = item.resolved_volume || '';
      document.getElementById('fs-f-resolved-chapter').value = item.resolved_chapter || '';
      document.getElementById('fs-f-related-characters').value = (item.related_characters || []).join(', ');
      document.getElementById('fs-f-notes').value = item.notes || '';
      toggleResolveFields();
    }
  }

  document.getElementById('foreshadowing-form-modal').style.display = 'flex';
}

function toggleResolveFields() {
  const status = document.getElementById('fs-f-status').value;
  const show = status === 'resolved';
  document.getElementById('fs-resolved-vol-group').style.display = show ? 'flex' : 'none';
  document.getElementById('fs-resolved-ch-group').style.display = show ? 'flex' : 'none';
}

// ---- 保存 ----

async function saveForeshadowingItem() {
  const summary = document.getElementById('fs-f-summary').value.trim();
  if (!summary) { showToast('伏線の内容を入力してください', '#a03020'); return; }

  const charsRaw = document.getElementById('fs-f-related-characters').value;
  const characters = charsRaw
    ? charsRaw.split(',').map(s => s.trim()).filter(Boolean)
    : [];

  const payload = {
    summary,
    introduced_volume: parseInt(document.getElementById('fs-f-introduced-volume').value) || 1,
    introduced_chapter: document.getElementById('fs-f-introduced-chapter').value.trim(),
    status: document.getElementById('fs-f-status').value,
    resolve_target: document.getElementById('fs-f-resolve-target').value.trim(),
    resolved_volume: document.getElementById('fs-f-resolved-volume').value.trim(),
    resolved_chapter: document.getElementById('fs-f-resolved-chapter').value.trim(),
    related_characters: characters,
    notes: document.getElementById('fs-f-notes').value.trim(),
  };

  const btn = document.getElementById('fs-form-save-btn');
  btn.disabled = true;
  btn.textContent = '保存中…';

  try {
    let res;
    if (fsEditingId) {
      res = await fetch(
        `/api/series/${encodeURIComponent(currentSeries)}/foreshadowing/${fsEditingId}`,
        { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
      );
    } else {
      res = await fetch(
        `/api/series/${encodeURIComponent(currentSeries)}/foreshadowing`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }
      );
    }

    if (!res.ok) {
      const err = await res.json();
      showToast(err.error || '保存に失敗しました', '#c0392b');
      return;
    }

    closeModal('foreshadowing-form-modal');
    await refreshForeshadowing();
    showToast(fsEditingId ? '✏️ 伏線を更新しました' : '🔖 伏線を追加しました', '#1a7a40');
  } finally {
    btn.disabled = false;
    btn.textContent = '保存';
  }
}

// ---- 削除 ----

async function deleteForeshadowingItem(id) {
  const item = foreshadowingItems.find(i => i.id === id);
  if (!item) return;
  if (!confirm(`「${item.summary}」を削除しますか？`)) return;

  const res = await fetch(
    `/api/series/${encodeURIComponent(currentSeries)}/foreshadowing/${id}`,
    { method: 'DELETE' }
  );
  if (res.ok) {
    await refreshForeshadowing();
    showToast(`🗑️ ${id} を削除しました`);
  } else {
    showToast('削除に失敗しました', '#c0392b');
  }
}

// ============================================================
// 巻サマリー自動生成
// ============================================================

async function generateVolumeSummary() {
  if (!currentProject || !currentSeries) {
    showToast('先にシリーズと巻を選択してください', '#a06020');
    return;
  }

  const btn      = document.getElementById('generate-volume-summary-btn');
  const progress = document.getElementById('volume-summary-progress');
  const bar      = document.getElementById('volume-summary-progress-bar');
  const label    = document.getElementById('volume-summary-progress-label');

  const volLabel = currentVolume
    ? `第${currentVolume.order}巻「${currentVolume.title}」`
    : currentProject;

  if (!confirm(
    volLabel + ' のサマリーを生成して series_summary.md に追記します。\n\n' +
    '・全章ファイル（chapter*.md）を読み込みます\n' +
    '・生成には1〜2分かかります\n\n' +
    '実行しますか？'
  )) return;

  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';
  progress.style.display = 'block';
  bar.style.width = '5%';
  label.textContent = 'Claude が全章を読み込んでいます…';

  let accumulated = '';
  let barWidth = 5;

  try {
    const res = await fetch('/api/claude/generate_volume_summary', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project: currentProject, series: currentSeries })
    });

    if (!res.ok) {
      const errData = await res.json();
      showToast(errData.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const result = await reader.read();
      if (result.done) break;

      buffer += decoder.decode(result.value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const payload = JSON.parse(line.slice(6));

          if (payload.error) {
            showToast('生成エラー: ' + payload.error, '#c0392b');
            return;
          }

          if (payload.chunk) {
            accumulated += payload.chunk;
            barWidth = Math.min(90, barWidth + 0.8);
            bar.style.width = barWidth + '%';
            label.textContent = '生成中… ' + accumulated.length + ' 字';
          }

          if (payload.done) {
            bar.style.width = '100%';
            label.textContent = '✅ 完了 — ' + accumulated.length + ' 字のサマリーを保存しました';
            showToast(
              '📋 第' + payload.vol_order + '巻「' + payload.vol_title + '」のサマリーを series_summary.md に追記しました',
              '#1a7a40'
            );
            await openSeriesBibleFile('series_summary.md');
          }
        } catch (parseErr) { /* ignore */ }
      }
    }

  } catch (e) {
    showToast('通信エラー: ' + e.message, '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '📋 巻サマリーを生成';
    setTimeout(function() {
      progress.style.display = 'none';
      bar.style.width = '0%';
    }, 3000);
  }
}

// ============================================================
// 整合性チェック パネル
// ============================================================

let ccScope = 'volume';   // 'volume' or 'series'

// ---- パネル開閉 ----

async function openConsistencyPanel() {
  if (!currentProject) {
    showToast('先にプロジェクトまたは巻を選択してください', '#a06020');
    return;
  }

  // タイトル更新
  const volLabel = currentVolume
    ? '第' + currentVolume.order + '巻「' + currentVolume.title + '」'
    : currentProject;
  const seriesLabel = currentSeries ? '  ／  📚 ' + currentSeries : '';
  document.getElementById('cc-panel-title').textContent =
    '整合性チェック — ' + volLabel + seriesLabel;

  // シリーズがない場合はシリーズスコープを無効化
  if (!currentSeries) {
    document.getElementById('cc-scope-series').disabled = true;
    document.getElementById('cc-scope-series').title = 'シリーズ選択時のみ使用可能';
    setCcScope('volume');
  } else {
    document.getElementById('cc-scope-series').disabled = false;
    document.getElementById('cc-scope-series').title = '';
  }

  // プレースホルダー説明更新
  updateCcPlaceholder();

  // 対象ファイルセレクトを現在のプロジェクトのファイルで埋める
  await populateCcTargetFiles();

  // 結果をリセット
  resetCcResults();

  document.getElementById('consistency-panel').style.display = 'flex';
}

function closeConsistencyPanel() {
  document.getElementById('consistency-panel').style.display = 'none';
}

function setCcScope(scope) {
  ccScope = scope;
  document.querySelectorAll('#consistency-panel .fs-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.scope === scope);
  });
  updateCcPlaceholder();
}

function updateCcPlaceholder() {
  const el = document.getElementById('cc-placeholder-scope');
  if (!el) return;
  if (ccScope === 'notation') {
    el.textContent = '範囲：この巻の全chapter*.txtファイル（固有名詞・用語の表記揺れを検出）';
  } else if (ccScope === 'series' && currentSeries) {
    el.textContent = '範囲：シリーズ聖典 ＋ 過去巻サマリー ＋ 伏線マスター ＋ この巻の設定';
  } else {
    el.textContent = '範囲：シリーズ聖典（ある場合）＋ この巻の設定ファイル ＋ 章サンプル';
  }
}

async function populateCcTargetFiles() {
  const sel = document.getElementById('cc-target-file');
  sel.innerHTML = '<option value="">設定ファイル全体</option>';
  if (!currentProject) return;

  try {
    const res = await fetch('/api/projects/' + currentProject + '/files');
    if (!res.ok) return;
    const structure = await res.json();

    // フラットリストに変換
    function flatten(items, prefix) {
      prefix = prefix || '';
      items.forEach(function(item) {
        if (item.type === 'file') {
          const opt = document.createElement('option');
          opt.value = item.path;
          opt.textContent = item.path;
          sel.appendChild(opt);
        } else if (item.type === 'directory' && item.children) {
          flatten(item.children, item.path + '/');
        }
      });
    }
    flatten(structure);
  } catch(e) { /* ignore */ }
}

function resetCcResults() {
  document.getElementById('cc-placeholder').style.display = 'block';
  document.getElementById('cc-summary-card').style.display = 'none';
  document.getElementById('cc-result-body').style.display = 'none';
  document.getElementById('cc-progress').style.display = 'none';
  document.getElementById('cc-progress-bar').style.width = '0%';
  document.getElementById('cc-result-body').innerHTML = '';
  document.getElementById('cc-grade').textContent = '';
  document.getElementById('cc-grade').className = 'cc-grade';
}

// ---- チェック実行 ----

async function runConsistencyCheck() {
  if (!currentProject) {
    showToast('先にプロジェクトまたは巻を選択してください', '#a06020');
    return;
  }

  const btn        = document.getElementById('cc-run-btn');
  const progress   = document.getElementById('cc-progress');
  const bar        = document.getElementById('cc-progress-bar');
  const barLabel   = document.getElementById('cc-progress-label');
  const placeholder = document.getElementById('cc-placeholder');
  const summaryCard = document.getElementById('cc-summary-card');
  const resultBody  = document.getElementById('cc-result-body');
  const targetFile  = document.getElementById('cc-target-file').value;

  // 対象ファイルをグローバル変数に保存（修正ボタンで使用）
  ccTargetFile = targetFile;

  btn.disabled = true;
  btn.textContent = '⏳ チェック中…';
  placeholder.style.display = 'none';
  summaryCard.style.display = 'none';
  resultBody.style.display = 'none';
  resultBody.innerHTML = '';
  progress.style.display = 'block';
  bar.style.width = '5%';
  barLabel.textContent = 'Claude が設定を読み込んでいます…';

  let accumulated = '';
  let barWidth = 5;

  try {
    const res = await fetch('/api/claude/consistency_check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: currentProject,
        series: currentSeries || undefined,
        scope: ccScope,
        target_file: targetFile
      })
    });

    if (!res.ok) {
      const errData = await res.json();
      showToast(errData.error || 'チェックに失敗しました', '#c0392b');
      return;
    }

    // SSE ストリーミング受信
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const result = await reader.read();
      if (result.done) break;

      buffer += decoder.decode(result.value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        try {
          const payload = JSON.parse(line.slice(6));

          if (payload.error) {
            showToast('チェックエラー: ' + payload.error, '#c0392b');
            return;
          }

          if (payload.chunk) {
            accumulated += payload.chunk;
            barWidth = Math.min(90, barWidth + 0.6);
            bar.style.width = barWidth + '%';
            barLabel.textContent = '分析中… ' + accumulated.length + ' 字';

            // リアルタイムでMarkdownレンダリング
            resultBody.innerHTML = marked.parse(accumulated);
            resultBody.style.display = 'block';
          }

          if (payload.done) {
            bar.style.width = '100%';
            barLabel.textContent = '✅ チェック完了';

            // 結果を解析してサマリーカードを更新
            parseCcSummary(accumulated);

            setTimeout(function() {
              progress.style.display = 'none';
            }, 2000);
          }
        } catch (parseErr) { /* ignore */ }
      }
    }

  } catch(e) {
    showToast('通信エラー: ' + e.message, '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔍 チェック実行';
  }
}

// ---- 結果パース・サマリーカード更新 ----

let ccResultText = ''; // 整合性チェック結果を保存
let ccTargetFile = '';  // 整合性チェックの対象ファイル

function parseCcSummary(text) {
  ccResultText = text; // 結果を保存

  // 重大な問題の件数
  const criticalMatch = text.match(/重大な問題[：:]\s*(\d+)/);
  const warningMatch  = text.match(/要確認事項[：:]\s*(\d+)/);
  const suggestMatch  = text.match(/改善提案[：:]\s*(\d+)/);
  const gradeMatch    = text.match(/総合評価[：:]\s*([ABCD])/);

  const criticalCount = criticalMatch ? parseInt(criticalMatch[1]) : 0;
  const warningCount  = warningMatch  ? parseInt(warningMatch[1])  : 0;
  const suggestCount  = suggestMatch  ? parseInt(suggestMatch[1])  : 0;
  const grade = gradeMatch ? gradeMatch[1] : '';

  // 文章ルール問題の件数も取得
  const textRuleMatch = text.match(/文章ルール問題[：:]\s*(\d+)/);
  const textRuleCount = textRuleMatch ? parseInt(textRuleMatch[1]) : 0;

  document.getElementById('cc-count-critical').textContent = criticalCount + ' 件';
  document.getElementById('cc-count-warning').textContent  = warningCount  + ' 件';
  document.getElementById('cc-count-textrule').textContent = textRuleCount + ' 件';
  document.getElementById('cc-count-suggest').textContent  = suggestCount  + ' 件';

  const gradeEl = document.getElementById('cc-grade');
  if (grade) {
    const gradeLabels = { A: 'A 問題なし', B: 'B 軽微な問題', C: 'C 要修正', D: 'D 重大な問題' };
    gradeEl.textContent = gradeLabels[grade] || grade;
    gradeEl.className = 'cc-grade cc-grade-' + grade;
  }

  document.getElementById('cc-summary-card').style.display = 'flex';

  // plot.md修正ボタンを表示（重大な問題または要確認事項がある場合のみ）
  const fixBtnContainer = document.getElementById('cc-fix-btn-container');
  if (criticalCount > 0 || warningCount > 0) {
    fixBtnContainer.style.display = 'block';
  } else {
    fixBtnContainer.style.display = 'none';
  }

  // chapter.txt修正ボタンを表示（対象ファイルが指定されており、問題や提案がある場合）
  const fixChapterContainer = document.getElementById('cc-fix-chapter-btn-container');
  const fixTargetFileName = document.getElementById('cc-fix-target-file-name');

  // 対象ファイルが指定されており、かつ何らかの問題や提案がある場合
  if (ccTargetFile && ccScope !== 'notation' && (textRuleCount > 0 || criticalCount > 0 || warningCount > 0 || suggestCount > 0)) {
    fixChapterContainer.style.display = 'block';
    fixTargetFileName.textContent = ccTargetFile;
  } else {
    fixChapterContainer.style.display = 'none';
  }

  // 表記揺れ一括修正ボタンを表示（表記揺れチェックで問題が見つかった場合）
  const fixNotationContainer = document.getElementById('cc-fix-notation-btn-container');

  // 表記揺れチェックスコープで、表記揺れが検出された場合
  if (ccScope === 'notation') {
    // 表記揺れのカウントを取得（表記ゆれの出力形式に幅があるため、複数パターンを許容）
    function extractCount(patterns) {
      for (const p of patterns) {
        const m = text.match(p);
        if (m) return parseInt(m[1], 10) || 0;
      }
      return 0;
    }

    // 重大な表記揺れ（固有名詞）
    const notationCriticalCount = extractCount([
      /重大な表記揺れ[（(]\s*固有名詞\s*[)）]\s*[：:|｜]\s*(\d+)/,                 // 見出しや箇条書き 「…： 5」
      /\|\s*重大な表記揺れ[（(]\s*固有名詞\s*[)）]\s*\|\s*(\d+)\s*件?\s*\|?/,   // Markdown表形式 「| … | 5件 |」
      /重大な表記揺れ[（(]\s*固有名詞\s*[)）][^\d\n\r]*?(\d+)\s*件/                 // その他 「… 5件」
    ]);

    // 一般用語の表記揺れ
    const notationGeneralCount = extractCount([
      /一般用語の表記揺れ\s*[：:|｜]\s*(\d+)/,
      /\|\s*一般用語の表記揺れ\s*\|\s*(\d+)\s*件?\s*\|?/,
      /一般用語の表記揺れ[^\d\n\r]*?(\d+)\s*件/
    ]);

    // 数字・記号の表記揺れ（中点の種類や空白差異を許容）
    const notationNumberCount = extractCount([
      /数字[・･・]\s*記号の表記揺れ\s*[：:|｜]\s*(\d+)/,
      /\|\s*数字[・･・]\s*記号の表記揺れ\s*\|\s*(\d+)\s*件?\s*\|?/,
      /数字[・･・]\s*記号の表記揺れ[^\d\n\r]*?(\d+)\s*件/
    ]);

    if (notationCriticalCount > 0 || notationGeneralCount > 0 || notationNumberCount > 0) {
      fixNotationContainer.style.display = 'block';
    } else {
      // 直接件数が抽出できなくても、該当セクションの存在でボタンを出すフォールバック
      const hasNotationSection = /重大な表記揺れ|一般用語の表記揺れ|数字[・･・]記号の表記揺れ/.test(text);
      fixNotationContainer.style.display = hasNotationSection ? 'block' : 'none';
    }
  } else {
    fixNotationContainer.style.display = 'none';
  }
}

// ---- 表記揺れ一括修正 ----

async function fixNotationIssues() {
  if (!currentProject) {
    showToast('プロジェクトが選択されていません', '#a06020');
    return;
  }

  if (!ccResultText) {
    showToast('表記揺れチェック結果がありません', '#a06020');
    return;
  }

  if (!confirm('全chapter.txtファイルの表記揺れを一括修正します。\n各ファイルが順次上書き保存されますが、よろしいですか？\n\n※ファイル数が多い場合、処理に時間がかかります。')) {
    return;
  }

  const btn = document.getElementById('cc-fix-notation-btn');
  const progressContainer = document.getElementById('cc-fix-notation-progress');
  const progressBar = document.getElementById('cc-fix-notation-progress-bar');
  const progressLabel = document.getElementById('cc-fix-notation-progress-label');
  const originalText = btn.textContent;

  btn.disabled = true;
  btn.textContent = '⏳ 修正中…';
  progressContainer.style.display = 'block';
  progressBar.style.width = '0%';
  progressLabel.textContent = '処理を開始しています...';

  try {
    const res = await fetch('/api/claude/fix_notation_issues', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: currentProject,
        series: currentSeries || undefined,
        check_result: ccResultText
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || '修正に失敗しました', '#c0392b');
      progressContainer.style.display = 'none';
      return;
    }

    // 成功メッセージの表示
    const fixedCount = data.fixed_files ? data.fixed_files.length : 0;
    const errorCount = data.errors ? data.errors.length : 0;

    progressBar.style.width = '100%';
    progressLabel.textContent = `完了: ${fixedCount}ファイル修正`;

    let message = `✅ 表記揺れ修正完了\n修正されたファイル: ${fixedCount}件`;

    if (data.fixed_files && data.fixed_files.length > 0) {
      message += '\n\n修正ファイル:\n' + data.fixed_files.join('\n');
    }

    if (errorCount > 0) {
      message += `\n\n⚠️ エラー: ${errorCount}件\n` + data.errors.join('\n');
    }

    showToast(message, fixedCount > 0 ? '#27ae60' : '#e67e22');

    // ファイルリストを更新
    if (fixedCount > 0) {
      loadFiles();

      // 現在開いているファイルが修正された場合、リロード
      if (currentFile && data.fixed_files && data.fixed_files.includes(currentFile)) {
        openFile(currentFile);
      }
    }

    // プログレスバーを少し表示してから非表示
    setTimeout(() => {
      progressContainer.style.display = 'none';
    }, 2000);

  } catch (err) {
    console.error('表記揺れ修正エラー:', err);
    showToast('修正中にエラーが発生しました: ' + err.message, '#c0392b');
    progressContainer.style.display = 'none';
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// ---- plot.md自動修正 ----

async function fixPlotInconsistencies() {
  if (!currentProject) {
    showToast('プロジェクトが選択されていません', '#a06020');
    return;
  }

  if (!ccResultText) {
    showToast('整合性チェック結果がありません', '#a06020');
    return;
  }

  if (!confirm('plot.mdの内容を自動修正します。上書き保存されますが、よろしいですか？')) {
    return;
  }

  const btn = document.getElementById('cc-fix-plot-btn');
  const originalText = btn.textContent;

  btn.disabled = true;
  btn.textContent = '⏳ 修正中…';

  try {
    const res = await fetch('/api/claude/fix_plot_inconsistencies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: currentProject,
        series: currentSeries || undefined,
        inconsistencies: ccResultText
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || '修正に失敗しました', '#c0392b');
      return;
    }

    showToast('✅ plot.mdを修正しました', '#27ae60');

    // ファイルリストを更新
    loadFiles();

    // 修正後のplot.mdをエディタに開く（オプション）
    if (confirm('修正後のplot.mdをエディタで開きますか？')) {
      openFile('plot.md');
    }

  } catch (e) {
    showToast('通信エラー: ' + e.message, '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// ---- 章ファイル自動修正 ----

async function fixChapterFile() {
  if (!currentProject) {
    showToast('プロジェクトが選択されていません', '#a06020');
    return;
  }

  // 整合性チェックで指定された対象ファイルを使用
  const chapterFile = ccTargetFile;
  if (!chapterFile) {
    showToast('修正対象ファイルが指定されていません', '#a06020');
    return;
  }

  if (!ccResultText) {
    showToast('整合性チェック結果がありません', '#a06020');
    return;
  }

  if (!confirm(`${chapterFile}の内容を自動修正します。上書き保存されますが、よろしいですか？`)) {
    return;
  }

  const btn = document.getElementById('cc-fix-chapter-btn');
  const originalText = btn.textContent;

  btn.disabled = true;
  btn.textContent = '⏳ 修正中…（最大30分）';

  try {
    const res = await fetch('/api/claude/fix_chapter_file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: currentProject,
        series: currentSeries || undefined,
        chapter_file: chapterFile,
        check_result: ccResultText
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || '修正に失敗しました', '#c0392b');
      return;
    }

    showToast(`✅ ${chapterFile}を修正しました`, '#27ae60');

    // ファイルリストを更新
    loadFiles();

    // 修正後のファイルをエディタで開く（オプション）
    if (confirm(`修正後の${chapterFile}をエディタで開きますか？`)) {
      openFile(chapterFile);
    }

  } catch (e) {
    showToast('通信エラー: ' + e.message, '#c0392b');
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

// ---- ネタバレ防止あらすじ生成 ----

let synopsisResultText = ''; // 生成されたあらすじを保存

function openSpoilerFreeSynopsisModal() {
  if (!currentProject) {
    showToast('先にプロジェクトを選択してください', '#a06020');
    return;
  }

  // 結果エリアをリセット
  document.getElementById('synopsis-result-area').style.display = 'none';
  document.getElementById('synopsis-result').innerHTML = '';
  synopsisResultText = '';

  // モーダルを表示
  document.getElementById('synopsis-modal').style.display = 'flex';
}

async function generateSpoilerFreeSynopsis() {
  if (!currentProject) {
    showToast('プロジェクトが選択されていません', '#a06020');
    return;
  }

  const btn = document.getElementById('synopsis-generate-btn');
  const resultArea = document.getElementById('synopsis-result-area');
  const resultDiv = document.getElementById('synopsis-result');
  const synopsisType = document.getElementById('synopsis-type-select').value;

  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = '⏳ 生成中…';

  resultDiv.innerHTML = '<p style="color: #999;">あらすじを生成しています...</p>';
  resultArea.style.display = 'block';

  try {
    const res = await fetch('/api/claude/generate_spoiler_free_synopsis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project: currentProject,
        series: currentSeries || undefined,
        synopsis_type: synopsisType
      })
    });

    const data = await res.json();

    if (!res.ok) {
      showToast(data.error || 'あらすじ生成に失敗しました', '#c0392b');
      resultArea.style.display = 'none';
      return;
    }

    synopsisResultText = data.synopsis;

    // Markdownレンダリング
    resultDiv.innerHTML = marked.parse(synopsisResultText);
    resultArea.style.display = 'block';

    showToast('✅ あらすじを生成しました', '#27ae60');

  } catch (e) {
    showToast('通信エラー: ' + e.message, '#c0392b');
    resultArea.style.display = 'none';
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

function insertSynopsisToEditor() {
  if (!synopsisResultText) {
    showToast('挿入するあらすじがありません', '#a06020');
    return;
  }

  if (editor) {
    const doc = editor.getDoc();
    const cursor = doc.getCursor();
    doc.replaceRange('\n\n' + synopsisResultText + '\n\n', cursor);
    showToast('✅ エディタに挿入しました', '#27ae60');
    closeModal('synopsis-modal');
  } else {
    showToast('エディタが開いていません', '#a06020');
  }
}

// ========================================
// キャラクターチャット機能
// ========================================

let currentChatSessionId = null;

async function startCharacterChat(characterName, mode = 'from_draft', characterRole = '') {
  console.log('startCharacterChat called with:', characterName, mode, characterRole);
  console.log('currentProject:', currentProject);
  console.log('currentSeries:', currentSeries);

  try {
    const requestBody = {
      project: currentProject,
      series: currentSeries || undefined,
      character_name: characterName,
      mode: mode
    };

    // 新規作成モードの場合はロールを追加
    if (mode === 'new') {
      requestBody.character_role = characterRole;
    }

    const res = await fetch('/api/claude/character_chat_start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    console.log('Response status:', res.status);

    if (!res.ok) {
      const data = await res.json();
      console.error('Error response:', data);
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    const data = await res.json();
    console.log('Success response:', data);
    currentChatSessionId = data.session_id;

    // モーダルを開く
    document.getElementById('chat-character-name').textContent = characterName || '新規キャラクター';
    const messagesArea = document.getElementById('character-chat-messages');
    messagesArea.innerHTML = '';

    // 初回のアシスタントメッセージを追加
    addChatMessage('assistant', data.response);

    // モーダルを表示
    const modal = document.getElementById('character-chat-modal');
    console.log('Opening modal:', modal);
    modal.style.display = 'block';
    document.getElementById('character-chat-input').value = '';
    document.getElementById('character-chat-input').focus();

    showToast('チャットセッションを開始しました', '#1a7a40');

  } catch (e) {
    showToast('通信エラーが発生しました: ' + e.message, '#c0392b');
    console.error('Exception in startCharacterChat:', e);
  }
}

async function sendCharacterChatMessage() {
  const input = document.getElementById('character-chat-input');
  const message = input.value.trim();

  if (!message) {
    showToast('メッセージを入力してください', '#a06020');
    return;
  }

  if (!currentChatSessionId) {
    showToast('セッションが無効です', '#c0392b');
    return;
  }

  // ユーザーメッセージを表示
  addChatMessage('user', message);
  input.value = '';

  // 送信ボタンを無効化
  const sendBtn = document.getElementById('character-chat-send-btn');
  const originalText = sendBtn.textContent;
  sendBtn.disabled = true;
  sendBtn.textContent = '送信中...';

  try {
    const res = await fetch('/api/claude/character_chat_continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: currentChatSessionId,
        message: message
      })
    });

    if (!res.ok) {
      const data = await res.json();
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    const data = await res.json();

    // アシスタントメッセージを表示
    addChatMessage('assistant', data.response);

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
    console.error(e);
  } finally {
    sendBtn.disabled = false;
    sendBtn.textContent = originalText;
  }
}

function addChatMessage(role, content) {
  const messagesArea = document.getElementById('character-chat-messages');
  const messageDiv = document.createElement('div');
  messageDiv.style.marginBottom = '15px';

  if (role === 'user') {
    messageDiv.innerHTML = `
      <div style="text-align: right;">
        <div style="display: inline-block; max-width: 70%; background: #5a67d8; color: white; padding: 10px 15px; border-radius: 12px; text-align: left; word-wrap: break-word;">
          ${escapeHtml(content)}
        </div>
      </div>
    `;
  } else {
    messageDiv.innerHTML = `
      <div style="text-align: left;">
        <div style="font-size: 11px; color: #999; margin-bottom: 4px;">🤖 アシスタント</div>
        <div style="display: inline-block; max-width: 85%; background: white; border: 1px solid #ddd; padding: 10px 15px; border-radius: 12px; text-align: left; word-wrap: break-word; white-space: pre-wrap;">
          ${escapeHtml(content)}
        </div>
      </div>
    `;
  }

  messagesArea.appendChild(messageDiv);
  messagesArea.scrollTop = messagesArea.scrollHeight;
}

async function finalizeCharacterChat() {
  if (!currentChatSessionId) {
    showToast('セッションが無効です', '#c0392b');
    return;
  }

  try {
    const res = await fetch('/api/claude/character_chat_finalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: currentChatSessionId
      })
    });

    if (!res.ok) {
      const data = await res.json();
      showToast(data.error || 'エラーが発生しました', '#c0392b');
      return;
    }

    const data = await res.json();

    // 結果を Claude パネルに表示
    claudeResult = data.result;
    const resultEl = document.getElementById('claude-result');
    resultEl.style.display = 'block';
    resultEl.textContent = claudeResult;
    document.getElementById('insert-result-btn').style.display = 'inline-block';

    showToast('キャラクター情報を確定しました', '#1a7a40');
    closeCharacterChatModal();

  } catch (e) {
    showToast('通信エラーが発生しました', '#c0392b');
    console.error(e);
  }
}

async function closeCharacterChatModal() {
  // セッションをキャンセル
  if (currentChatSessionId) {
    try {
      await fetch('/api/claude/character_chat_cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentChatSessionId
        })
      });
    } catch (e) {
      console.error('Failed to cancel session:', e);
    }
    currentChatSessionId = null;
  }

  document.getElementById('character-chat-modal').style.display = 'none';
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Enterキーで送信
document.addEventListener('DOMContentLoaded', () => {
  const chatInput = document.getElementById('character-chat-input');
  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendCharacterChatMessage();
      }
    });
  }
});
