const { app, BrowserWindow, ipcMain, shell, dialog, nativeTheme, safeStorage, Menu } = require('electron');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const { spawn } = require('node:child_process');

let Store;
let store;
let mainWindow;
let activeProcess = null;

async function loadStore() {
  if (!Store) {
    const mod = await import('electron-store');
    Store = mod.default;
  }
  if (!store) {
    store = new Store({
      name: 'jarvis-live-command-hud',
      defaults: {
        appUrl: process.env.JARVIS_APP_URL || '',
        preferredModel: process.env.JARVIS_MODEL || 'auto',
        commandMode: 'ask',
        healthPort: Number(process.env.JARVIS_HEALTH_PORT || 41418),
        telemetryPreview: true,
      },
    });
  }
  return store;
}

function getProjectRoot() {
  if (!app.isPackaged) return path.resolve(__dirname, '..', '..');
  return path.join(process.resourcesPath, 'jarvis-src');
}

function getCacheDir() {
  if (process.platform === 'darwin') return path.join(os.homedir(), 'Library', 'Caches');
  return path.join(os.homedir(), '.jarvis', 'cache');
}

function getHudPath() {
  return path.join(getCacheDir(), 'jarvis-hud.json');
}

function getVoicePath() {
  return path.join(getCacheDir(), 'jarvis-voice.json');
}

function getPythonCandidates() {
  const configured = process.env.JARVIS_PYTHON;
  const py = process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3.12', 'python3.11', 'python3', 'python'];
  return configured ? [configured, ...py] : py;
}

function readJsonSafe(file, fallback = null) {
  try {
    if (!fs.existsSync(file)) return fallback;
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeJsonSafe(file, payload) {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(payload, null, 2));
    return true;
  } catch {
    return false;
  }
}

function setHudState(state, message = '') {
  writeJsonSafe(getHudPath(), { state, message: String(message || '').slice(0, 160), detail: String(message || '').slice(0, 160), ts: Date.now() / 1000 });
}

function spawnWithFallback(args, options = {}) {
  return new Promise((resolve, reject) => {
    const candidates = getPythonCandidates();
    let index = 0;
    const errors = [];
    const tryNext = () => {
      if (index >= candidates.length) {
        reject(new Error(`Python 실행 파일을 찾을 수 없습니다. 시도: ${candidates.join(', ')} / ${errors.join(' | ')}`));
        return;
      }
      const command = candidates[index++];
      const child = spawn(command, args, { ...options, stdio: ['ignore', 'pipe', 'pipe'] });
      let stdout = '';
      let stderr = '';
      let settled = false;
      child.stdout.on('data', (d) => { stdout += d.toString(); });
      child.stderr.on('data', (d) => { stderr += d.toString(); });
      child.on('error', (err) => {
        if (settled) return;
        settled = true;
        errors.push(`${command}: ${err.message}`);
        tryNext();
      });
      child.on('close', (code) => {
        if (settled) return;
        settled = true;
        resolve({ command, code, stdout, stderr });
      });
    };
    tryNext();
  });
}

function encryptSecret(value) {
  if (!value) return '';
  try {
    if (safeStorage.isEncryptionAvailable()) {
      return `safe:${safeStorage.encryptString(value).toString('base64')}`;
    }
  } catch {}
  return `plain:${Buffer.from(value, 'utf8').toString('base64')}`;
}

function decryptSecret(value) {
  if (!value || typeof value !== 'string') return '';
  try {
    if (value.startsWith('safe:') && safeStorage.isEncryptionAvailable()) {
      return safeStorage.decryptString(Buffer.from(value.slice(5), 'base64'));
    }
    if (value.startsWith('plain:')) return Buffer.from(value.slice(6), 'base64').toString('utf8');
  } catch {}
  return '';
}

function createRuntimeEnv(storeRef) {
  const projectRoot = getProjectRoot();
  const key = decryptSecret(storeRef.get('anthropicApiKey')) || process.env.ANTHROPIC_API_KEY || '';
  const model = storeRef.get('preferredModel') || process.env.JARVIS_MODEL || 'auto';
  const env = {
    ...process.env,
    PYTHONPATH: path.join(projectRoot, 'src') + path.delimiter + (process.env.PYTHONPATH || ''),
    JARVIS_MODEL: model,
    JARVIS_HEALTH_PORT: String(storeRef.get('healthPort') || 41418),
  };
  if (key) env.ANTHROPIC_API_KEY = key;
  return { env, projectRoot, key, model };
}

function readHudState() {
  const candidates = [
    getHudPath(),
    path.join(os.homedir(), 'Library', 'Caches', 'jarvis-hud.json'),
    path.join(os.homedir(), '.jarvis', 'cache', 'jarvis-hud.json'),
    path.join(os.homedir(), '.cache', 'jarvis-hud.json'),
    path.join(os.tmpdir(), 'jarvis-hud.json'),
  ];
  for (const file of candidates) {
    const payload = readJsonSafe(file);
    if (payload) return { ...payload, source: file };
  }
  return { state: 'idle', message: 'standby', detail: 'standby', ts: null, source: getHudPath() };
}

function readVoiceState() {
  const candidates = [
    getVoicePath(),
    path.join(os.homedir(), 'Library', 'Caches', 'jarvis-voice.json'),
    path.join(os.homedir(), '.jarvis', 'cache', 'jarvis-voice.json'),
    path.join(os.tmpdir(), 'jarvis-voice.json'),
  ];
  for (const file of candidates) {
    const payload = readJsonSafe(file);
    if (payload) return { ...payload, source: file };
  }
  return { rms: 0, peak: 0, history: [], ts: null, source: getVoicePath() };
}

async function getPythonVersion(projectRoot) {
  let py = { ok: false, version: '', command: '', error: '' };
  try {
    const result = await spawnWithFallback(['--version'], { cwd: projectRoot });
    py = { ok: result.code === 0, version: (result.stdout || result.stderr).trim(), command: result.command, error: result.stderr.trim() };
  } catch (err) {
    py.error = err.message;
  }
  return py;
}

function parseDaemonStatus(text) {
  const merged = String(text || '');
  const hasPid = /pid\s*[:=]?\s*\d+|PID\s+\d+|\brunning\b|실행/i.test(merged);
  const stopped = /not\s+loaded|stopped|unloaded|중지|없음|not found/i.test(merged);
  return { running: hasPid && !stopped, text: merged.trim() };
}

async function getDaemonStatus(storeRef) {
  try {
    const { env, projectRoot } = createRuntimeEnv(storeRef);
    const result = await spawnWithFallback(['-m', 'jarvis', 'daemon', 'status'], { cwd: projectRoot, env });
    const parsed = parseDaemonStatus(`${result.stdout}\n${result.stderr}`);
    return { ...parsed, command: `${result.command} -m jarvis daemon status`, code: result.code };
  } catch (err) {
    return { running: false, text: err.message, error: err.message };
  }
}

function getRunArgs(mode, prompt) {
  if (mode === 'do') return ['-m', 'jarvis', 'do', prompt, '--max-turns', '12'];
  return ['-m', 'jarvis', 'ask', prompt];
}

function readJsonLines(file, limit = 20) {
  try {
    if (!fs.existsSync(file)) return [];
    const lines = fs.readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).slice(-limit);
    return lines.map((line) => {
      try { return JSON.parse(line); } catch { return { raw: line }; }
    });
  } catch {
    return [];
  }
}

function getUsageSummary() {
  const usagePath = path.join(os.homedir(), '.jarvis', 'usage', 'anthropic-usage.jsonl');
  const rows = readJsonLines(usagePath, 120);
  const summary = rows.reduce((acc, row) => {
    const usage = row.usage || {};
    acc.calls += 1;
    acc.ok += row.ok === false ? 0 : 1;
    acc.inputTokens += Number(usage.input_tokens || 0);
    acc.outputTokens += Number(usage.output_tokens || 0);
    acc.cacheRead += Number(usage.cache_read_input_tokens || 0);
    acc.cacheCreate += Number(usage.cache_creation_input_tokens || 0);
    acc.latencyTotal += Number(row.latency_ms || 0);
    if (row.model) acc.models[row.model] = (acc.models[row.model] || 0) + 1;
    return acc;
  }, { calls: 0, ok: 0, inputTokens: 0, outputTokens: 0, cacheRead: 0, cacheCreate: 0, latencyTotal: 0, models: {} });
  return {
    ...summary,
    avgLatencyMs: summary.calls ? Math.round(summary.latencyTotal / summary.calls) : 0,
    latest: rows.slice(-8).reverse(),
    source: usagePath,
  };
}

function getHistory(limit = 12) {
  const file = process.env.JARVIS_HISTORY_PATH || path.join(os.homedir(), '.jarvis', 'history.jsonl');
  return { source: file, items: readJsonLines(file, Math.max(1, Math.min(Number(limit) || 12, 80))).reverse() };
}

async function runJarvisUtility(storeRef, args) {
  const { env, projectRoot } = createRuntimeEnv(storeRef);
  const result = await spawnWithFallback(['-m', 'jarvis', ...args], { cwd: projectRoot, env });
  return { ok: result.code === 0, code: result.code, command: `${result.command} -m jarvis ${args.join(' ')}`, stdout: result.stdout, stderr: result.stderr };
}

function getExportPayload(payload = {}) {
  return {
    exportedAt: new Date().toISOString(),
    title: 'JARVIS Live Command HUD Session Export',
    hud: readHudState(),
    voice: readVoiceState(),
    usage: getUsageSummary(),
    history: getHistory(20),
    session: payload,
  };
}

function createMenu() {
  const template = [
    {
      label: 'JARVIS',
      submenu: [
        { label: 'Live HUD 새로고침', accelerator: 'CmdOrCtrl+R', click: () => mainWindow?.reload() },
        { label: '개발자 도구', accelerator: 'Alt+CmdOrCtrl+I', click: () => mainWindow?.webContents.openDevTools({ mode: 'detach' }) },
        { type: 'separator' },
        { label: '종료', role: 'quit' },
      ],
    },
    {
      label: '작업',
      submenu: [
        { label: '프로젝트 폴더 열기', click: () => shell.openPath(getProjectRoot()) },
        { label: '웹 계정 대시보드 열기', click: async () => {
          const s = await loadStore();
          const appUrl = s.get('appUrl');
          if (appUrl) shell.openExternal(`${appUrl.replace(/\/$/, '')}/dashboard.html`);
          else dialog.showMessageBox({ type: 'info', message: 'Secure Setup에서 JARVIS_APP_URL을 먼저 입력하세요.' });
        }},
      ],
    },
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

async function createWindow() {
  await loadStore();
  nativeTheme.themeSource = 'dark';
  mainWindow = new BrowserWindow({
    width: 1520,
    height: 980,
    minWidth: 1120,
    minHeight: 760,
    title: 'JARVIS Live Command HUD',
    backgroundColor: '#030610',
    show: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: true,
    },
  });
  setHudState('idle', 'JARVIS Live Command HUD ready');
  mainWindow.once('ready-to-show', () => mainWindow.show());
  await mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
}

ipcMain.handle('jarvis:get-status', async () => {
  const s = await loadStore();
  const projectRoot = getProjectRoot();
  const { key, model } = createRuntimeEnv(s);
  const py = await getPythonVersion(projectRoot);
  const daemon = await getDaemonStatus(s);
  return {
    appVersion: app.getVersion(),
    platform: process.platform,
    arch: process.arch,
    projectRoot,
    cacheDir: getCacheDir(),
    python: py,
    hasAnthropicKey: Boolean(key),
    model,
    appUrl: s.get('appUrl'),
    healthPort: s.get('healthPort') || 41418,
    hud: readHudState(),
    voice: readVoiceState(),
    daemon,
    packaged: app.isPackaged,
  };
});

ipcMain.handle('jarvis:save-settings', async (_event, payload) => {
  const s = await loadStore();
  if (typeof payload.appUrl === 'string') s.set('appUrl', payload.appUrl.trim());
  if (typeof payload.preferredModel === 'string') s.set('preferredModel', payload.preferredModel.trim() || 'auto');
  if (typeof payload.healthPort === 'string' || typeof payload.healthPort === 'number') {
    const port = Number(payload.healthPort);
    if (Number.isInteger(port) && port > 0 && port < 65536) s.set('healthPort', port);
  }
  if (typeof payload.anthropicApiKey === 'string' && payload.anthropicApiKey.trim()) {
    s.set('anthropicApiKey', encryptSecret(payload.anthropicApiKey.trim()));
  }
  setHudState('idle', 'settings saved');
  return { ok: true };
});

ipcMain.handle('jarvis:run-prompt', async (_event, payload) => {
  const prompt = String(payload?.prompt || '').trim();
  const mode = ['ask', 'do'].includes(payload?.mode) ? payload.mode : 'ask';
  const requestedModel = String(payload?.model || '').trim();
  if (!prompt) return { ok: false, error: '프롬프트가 비어 있습니다.' };
  if (activeProcess) return { ok: false, error: '이미 실행 중인 작업이 있습니다.' };

  const s = await loadStore();
  if (requestedModel) s.set('preferredModel', requestedModel);
  const { env, projectRoot, model } = createRuntimeEnv(s);
  setHudState('executing', `${mode.toUpperCase()} · ${model}`);

  try {
    const candidates = getPythonCandidates();
    return await new Promise((resolve) => {
      let index = 0;
      const tryNext = () => {
        const command = candidates[index++];
        if (!command) {
          setHudState('error', 'Python 실행 파일을 찾을 수 없습니다.');
          return resolve({ ok: false, error: `Python 실행 파일을 찾을 수 없습니다: ${candidates.join(', ')}` });
        }
        const child = spawn(command, getRunArgs(mode, prompt), { cwd: projectRoot, env, stdio: ['ignore', 'pipe', 'pipe'] });
        activeProcess = child;
        let stdout = '';
        let stderr = '';
        let started = false;
        child.stdout.on('data', (d) => {
          started = true;
          const text = d.toString();
          stdout += text;
          mainWindow?.webContents.send('jarvis:process-output', { stream: 'stdout', text });
        });
        child.stderr.on('data', (d) => {
          const text = d.toString();
          stderr += text;
          mainWindow?.webContents.send('jarvis:process-output', { stream: 'stderr', text });
        });
        child.on('error', (err) => {
          activeProcess = null;
          if (/ENOENT/.test(err.message || '')) return tryNext();
          setHudState('error', err.message);
          resolve({ ok: false, error: err.message, command });
        });
        child.on('close', (code) => {
          activeProcess = null;
          if (!started && code !== 0 && /not found|ENOENT/i.test(stderr)) return tryNext();
          setHudState(code === 0 ? 'speaking' : 'error', code === 0 ? 'response ready' : (stderr || `exit ${code}`));
          resolve({ ok: code === 0, code, command, stdout, stderr, mode, model });
        });
      };
      tryNext();
    });
  } catch (err) {
    activeProcess = null;
    setHudState('error', err.message);
    return { ok: false, error: err.message };
  }
});

ipcMain.handle('jarvis:daemon-control', async (_event, payload) => {
  const action = String(payload?.action || 'status');
  const s = await loadStore();
  const { env, projectRoot } = createRuntimeEnv(s);
  const argsByAction = {
    status: ['-m', 'jarvis', 'daemon', 'status'],
    start: ['-m', 'jarvis', 'daemon', 'install', '--no-chime'],
    restart: ['-m', 'jarvis', 'daemon', 'restart'],
    stop: ['-m', 'jarvis', 'daemon', 'uninstall'],
    logs: ['-m', 'jarvis', 'daemon', 'logs', '-n', '80'],
  };
  const args = argsByAction[action];
  if (!args) return { ok: false, error: `지원하지 않는 daemon action: ${action}` };
  setHudState(action === 'stop' ? 'idle' : 'executing', `daemon ${action}`);
  try {
    const result = await spawnWithFallback(args, { cwd: projectRoot, env });
    const merged = `${result.stdout || ''}${result.stderr ? `\n${result.stderr}` : ''}`.trim();
    if (action !== 'logs') setHudState(action === 'stop' ? 'idle' : 'listening', merged.slice(0, 140) || `daemon ${action} done`);
    return { ok: result.code === 0, action, command: result.command, code: result.code, stdout: result.stdout, stderr: result.stderr, message: merged };
  } catch (err) {
    setHudState('error', err.message);
    return { ok: false, error: err.message, action };
  }
});

ipcMain.handle('jarvis:get-intelligence', async () => {
  const s = await loadStore();
  let stats = { ok: false, stdout: '', stderr: '' };
  let tools = { ok: false, stdout: '', stderr: '' };
  try { stats = await runJarvisUtility(s, ['stats']); } catch (err) { stats = { ok: false, stdout: '', stderr: err.message }; }
  try { tools = await runJarvisUtility(s, ['tools-list']); } catch (err) { tools = { ok: false, stdout: '', stderr: err.message }; }
  return {
    ok: true,
    usage: getUsageSummary(),
    history: getHistory(12),
    stats,
    tools,
  };
});

ipcMain.handle('jarvis:run-utility', async (_event, payload) => {
  const action = String(payload?.action || 'doctor');
  const note = String(payload?.note || '').trim();
  const s = await loadStore();
  const allowed = {
    doctor: ['doctor'],
    stats: ['stats'],
    tools: ['tools-list', '--detail'],
    init: ['init'],
    history: ['hud', 'history', '--n', '20'],
    note: note ? ['note', note] : null,
  };
  const args = allowed[action];
  if (!args) return { ok: false, error: action === 'note' ? '저장할 메모가 비어 있습니다.' : `지원하지 않는 utility action: ${action}` };
  setHudState('executing', `utility ${action}`);
  try {
    const result = await runJarvisUtility(s, args);
    setHudState(result.ok ? 'complete' : 'error', `utility ${action} ${result.ok ? 'complete' : 'failed'}`);
    return { ...result, action };
  } catch (err) {
    setHudState('error', err.message);
    return { ok: false, action, error: err.message };
  }
});

ipcMain.handle('jarvis:export-session', async (_event, payload) => {
  const data = getExportPayload(payload || {});
  const defaultPath = path.join(os.homedir(), 'Desktop', `jarvis-session-${new Date().toISOString().replace(/[:.]/g, '-')}.json`);
  const result = await dialog.showSaveDialog(mainWindow, {
    title: 'JARVIS 세션 리포트 저장',
    defaultPath,
    filters: [{ name: 'JSON', extensions: ['json'] }],
  });
  if (result.canceled || !result.filePath) return { ok: false, canceled: true };
  fs.writeFileSync(result.filePath, JSON.stringify(data, null, 2), 'utf8');
  return { ok: true, filePath: result.filePath };
});

ipcMain.handle('jarvis:stop', async () => {
  if (!activeProcess) return { ok: true, stopped: false };
  activeProcess.kill('SIGTERM');
  activeProcess = null;
  setHudState('idle', '사용자가 실행을 중지했습니다.');
  return { ok: true, stopped: true };
});

ipcMain.handle('jarvis:open-external', async (_event, url) => {
  if (typeof url !== 'string') return { ok: false };
  if (!/^https?:\/\//i.test(url)) return { ok: false, error: '허용되지 않은 URL입니다.' };
  await shell.openExternal(url);
  return { ok: true };
});

ipcMain.handle('jarvis:open-project', async () => {
  await shell.openPath(getProjectRoot());
  return { ok: true };
});

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();
else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
  app.whenReady().then(async () => {
    createMenu();
    await createWindow();
    app.on('activate', async () => {
      if (BrowserWindow.getAllWindows().length === 0) await createWindow();
    });
  });
}

app.on('before-quit', () => {
  if (activeProcess) {
    activeProcess.kill('SIGTERM');
    activeProcess = null;
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
