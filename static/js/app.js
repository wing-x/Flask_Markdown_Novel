// グローバル変数
let currentProject = null;
let currentFile = null;
let currentFilePath = null;
let autoSaveTimeout = null;
let claudeResponse = '';

// DOM要素
const projectSelect = document.getElementById('projectSelect');
const fileList = document.getElementById('fileList');
const editor = document.getElementById('editor');
const preview = document.getElementById('preview');
const saveBtn = document.getElementById('saveBtn');
const currentFileName = document.getElementById('currentFileName');
const newProjectBtn = document.getElementById('newProjectBtn');
const newProjectModal = document.getElementById('newProjectModal');
const projectNameInput = document.getElementById('projectNameInput');
const createProjectBtn = document.getElementById('createProjectBtn');
const cancelProjectBtn = document.getElementById('cancelProjectBtn');
const claudeContext = document.getElementById('claudeContext');
const claudeResponseDiv = document.getElementById('claudeResponse');
const responseContent = document.getElementById('responseContent');
const insertBtn = document.getElementById('insertBtn');

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    loadProjects();
    setupEventListeners();
});

// イベントリスナー設定
function setupEventListeners() {
    // プロジェクト選択
    projectSelect.addEventListener('change', (e) => {
        currentProject = e.target.value;
        if (currentProject) {
            loadFiles(currentProject);
        } else {
            fileList.innerHTML = '';
            clearEditor();
        }
    });
    
    // エディタ入力時
    editor.addEventListener('input', () => {
        updatePreview();
        enableSaveButton();
        scheduleAutoSave();
    });
    
    // 保存ボタン
    saveBtn.addEventListener('click', saveCurrentFile);
    
    // 新規プロジェクトボタン
    newProjectBtn.addEventListener('click', () => {
        newProjectModal.classList.add('show');
        projectNameInput.focus();
    });
    
    // プロジェクト作成ボタン
    createProjectBtn.addEventListener('click', createProject);
    
    // キャンセルボタン
    cancelProjectBtn.addEventListener('click', () => {
        newProjectModal.classList.remove('show');
        projectNameInput.value = '';
    });
    
    // Enterキーでプロジェクト作成
    projectNameInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            createProject();
        }
    });
    
    // Claudeボタン
    document.querySelectorAll('.btn-claude').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const type = e.target.dataset.type;
            callClaude(type);
        });
    });
    
    // 挿入ボタン
    insertBtn.addEventListener('click', () => {
        insertClaudeResponse();
    });
}

// プロジェクト一覧を読み込む
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const projects = await response.json();
        
        projectSelect.innerHTML = '<option value="">プロジェクトを選択...</option>';
        
        projects.forEach(project => {
            const option = document.createElement('option');
            option.value = project.name;
            option.textContent = project.name;
            projectSelect.appendChild(option);
        });
    } catch (error) {
        console.error('プロジェクトの読み込みエラー:', error);
        alert('プロジェクトの読み込みに失敗しました');
    }
}

// ファイル一覧を読み込む
async function loadFiles(projectName) {
    try {
        const response = await fetch(`/api/projects/${projectName}/files`);
        const files = await response.json();
        
        fileList.innerHTML = '';
        
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.textContent = file.name;
            fileItem.dataset.path = file.path;
            
            fileItem.addEventListener('click', () => {
                loadFile(file.path);
                
                // アクティブ状態を更新
                document.querySelectorAll('.file-item').forEach(item => {
                    item.classList.remove('active');
                });
                fileItem.classList.add('active');
            });
            
            fileList.appendChild(fileItem);
        });
    } catch (error) {
        console.error('ファイル一覧の読み込みエラー:', error);
        alert('ファイル一覧の読み込みに失敗しました');
    }
}

// ファイルを読み込む
async function loadFile(filePath) {
    try {
        const response = await fetch(`/api/files/${filePath}`);
        const data = await response.json();
        
        currentFilePath = data.path;
        currentFile = data.content;
        editor.value = data.content;
        currentFileName.textContent = filePath.split('/').pop();
        
        updatePreview();
        saveBtn.disabled = true;
    } catch (error) {
        console.error('ファイルの読み込みエラー:', error);
        alert('ファイルの読み込みに失敗しました');
    }
}

// ファイルを保存
async function saveCurrentFile() {
    if (!currentFilePath) return;
    
    try {
        const response = await fetch(`/api/files/${currentFilePath}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                content: editor.value
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            saveBtn.disabled = true;
            showNotification('保存しました');
        } else {
            alert('保存に失敗しました: ' + data.error);
        }
    } catch (error) {
        console.error('保存エラー:', error);
        alert('保存に失敗しました');
    }
}

// プレビューを更新
function updatePreview() {
    const markdown = editor.value;
    preview.innerHTML = marked.parse(markdown);
}

// 保存ボタンを有効化
function enableSaveButton() {
    if (currentFilePath) {
        saveBtn.disabled = false;
    }
}

// 自動保存をスケジュール
function scheduleAutoSave() {
    if (autoSaveTimeout) {
        clearTimeout(autoSaveTimeout);
    }
    
    autoSaveTimeout = setTimeout(() => {
        if (!saveBtn.disabled && currentFilePath) {
            saveCurrentFile();
        }
    }, 3000); // 3秒後に自動保存
}

// エディタをクリア
function clearEditor() {
    editor.value = '';
    preview.innerHTML = '';
    currentFileName.textContent = 'ファイルを選択してください';
    currentFilePath = null;
    saveBtn.disabled = true;
}

// 新規プロジェクトを作成
async function createProject() {
    const name = projectNameInput.value.trim();
    
    if (!name) {
        alert('プロジェクト名を入力してください');
        return;
    }
    
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            newProjectModal.classList.remove('show');
            projectNameInput.value = '';
            
            // プロジェクト一覧を再読み込み
            await loadProjects();
            
            // 作成したプロジェクトを選択
            projectSelect.value = name;
            currentProject = name;
            loadFiles(name);
            
            showNotification('プロジェクトを作成しました');
        } else {
            alert('作成に失敗しました: ' + data.error);
        }
    } catch (error) {
        console.error('プロジェクト作成エラー:', error);
        alert('プロジェクトの作成に失敗しました');
    }
}

// Claudeを呼び出す
async function callClaude(type) {
    const context = claudeContext.value.trim();
    
    if (!currentProject) {
        alert('プロジェクトを選択してください');
        return;
    }
    
    // ボタンを無効化
    const buttons = document.querySelectorAll('.btn-claude');
    buttons.forEach(btn => {
        btn.disabled = true;
        btn.textContent = '処理中...';
    });
    
    try {
        const response = await fetch('/api/claude/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                type: type,
                context: context || editor.value,
                project: currentProject
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            claudeResponse = data.response;
            responseContent.textContent = data.response;
            claudeResponseDiv.style.display = 'block';
            
            // スクロール
            claudeResponseDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alert('エラー: ' + data.error);
        }
    } catch (error) {
        console.error('Claude API呼び出しエラー:', error);
        alert('Claudeの呼び出しに失敗しました');
    } finally {
        // ボタンを再有効化
        buttons.forEach(btn => {
            btn.disabled = false;
            // 元のテキストに戻す
            const type = btn.dataset.type;
            const labels = {
                'character': 'キャラクター生成',
                'plot': 'プロット展開案',
                'improve': '文章推敲',
                'consistency': '整合性チェック',
                'dialogue': '対話シミュレーション'
            };
            btn.textContent = labels[type];
        });
    }
}

// Claudeの回答をエディタに挿入
function insertClaudeResponse() {
    if (!claudeResponse) return;
    
    const cursorPos = editor.selectionStart;
    const textBefore = editor.value.substring(0, cursorPos);
    const textAfter = editor.value.substring(editor.selectionEnd);
    
    editor.value = textBefore + '\n\n' + claudeResponse + '\n\n' + textAfter;
    
    updatePreview();
    enableSaveButton();
    
    // カーソル位置を調整
    const newCursorPos = cursorPos + claudeResponse.length + 4;
    editor.setSelectionRange(newCursorPos, newCursorPos);
    editor.focus();
    
    showNotification('挿入しました');
}

// 通知を表示（簡易版）
function showNotification(message) {
    // 簡易的な通知実装
    const originalText = saveBtn.textContent;
    saveBtn.textContent = '✓ ' + message;
    
    setTimeout(() => {
        saveBtn.textContent = originalText;
    }, 2000);
}
