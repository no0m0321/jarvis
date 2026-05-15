const api = window.jarvisDesktop;
const $ = (id) => document.getElementById(id);

let selectedModel = 'auto';
let selectedMode = 'ask';
let currentState = 'booting';
let eventCount = 0;
let lastStatus = null;

const STATE_COPY = {
  booting: ['Booting', '자비스 런타임과 실행 창을 연결하는 중입니다.'],
  idle: ['Standby', '자비스가 다음 명령을 기다리고 있습니다.'],
  listening: ['Listening', '마이크 또는 명령 입력을 수신 중입니다. 필요한 정보를 또렷하게 말하거나 입력하세요.'],
  analyzing: ['Analyzing', '입력 내용을 전사하고 의도를 분석하는 중입니다.'],
  executing: ['Executing', 'Claude 추론과 로컬 도구 실행을 진행 중입니다.'],
  speaking: ['Speaking', '자비스가 응답을 출력하거나 음성으로 말하는 중입니다.'],
  complete: ['Complete', '작업이 완료되었습니다. 다음 명령을 바로 실행할 수 있습니다.'],
  error: ['Attention', '오류가 감지되었습니다. 로그와 설정을 확인하세요.'],
};

function nowTime() {
  return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove('show'), 3200);
}

function addEvent(type, text) {
  const stream = $('eventStream');
  const empty = stream.querySelector('.empty-event');
  if (empty) empty.remove();
  const item = document.createElement('article');
  item.className = `event event-${type || 'info'}`;
  item.innerHTML = `<time>${nowTime()}</time><p></p>`;
  item.querySelector('p').textContent = text;
  stream.appendChild(item);
  eventCount += 1;
  while (stream.children.length > 80) stream.removeChild(stream.firstElementChild);
  stream.scrollTop = stream.scrollHeight;
}

function setOutput(text, append = false) {
  const el = $('output');
  el.textContent = append ? (el.textContent + text) : text;
  el.scrollTop = el.scrollHeight;
}

function setDaemonLog(text, append = false) {
  const el = $('daemonLog');
  el.textContent = append ? (el.textContent + text) : text;
  el.scrollTop = el.scrollHeight;
}

function setUtilityOutput(text, append = false) {
  const el = $('utilityOutput');
  if (!el) return;
  el.textContent = append ? (el.textContent + text) : text;
  el.scrollTop = el.scrollHeight;
}

function compact(text, max = 260) {
  const value = String(text || '').replace(/\s+/g, ' ').trim();
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function normalizeState(raw, detail = '') {
  const state = String(raw || '').toLowerCase();
  const d = String(detail || '').toLowerCase();
  if (state.includes('listen')) return 'listening';
  if (state.includes('analy') || d.includes('transcribe') || d.includes('think')) return 'analyzing';
  if (state.includes('speak')) return 'speaking';
  if (state.includes('run') || state.includes('exec')) return 'executing';
  if (state.includes('error') || state.includes('fail')) return 'error';
  if (state.includes('complete') || state.includes('done')) return 'complete';
  return state || 'idle';
}

function setState(state, detail = '') {
  const normalized = normalizeState(state, detail);
  if (currentState !== normalized) {
    addEvent('state', `상태 전환: ${currentState.toUpperCase()} → ${normalized.toUpperCase()}${detail ? ` · ${detail}` : ''}`);
  }
  currentState = normalized;
  document.body.dataset.state = normalized;

  const [title, subtitle] = STATE_COPY[normalized] || STATE_COPY.idle;
  $('coreTitle').textContent = title;
  $('coreSubtitle').textContent = detail || subtitle;
  $('sideState').textContent = title;
  $('sideDetail').textContent = detail || subtitle;
  $('hudStatus').textContent = `${normalized.toUpperCase()}${detail ? ` · ${detail}` : ''}`;
  $('liveBadge').textContent = normalized.toUpperCase();

  const activeStep = normalized === 'complete' ? 'speaking' : normalized === 'error' ? 'executing' : normalized;
  document.querySelectorAll('#stateTimeline li').forEach((item) => {
    const step = item.dataset.step;
    const order = ['idle', 'listening', 'analyzing', 'executing', 'speaking'];
    const activeIndex = order.indexOf(activeStep);
    const stepIndex = order.indexOf(step);
    item.classList.toggle('active', stepIndex <= activeIndex && activeIndex >= 0);
  });
}

function updateVoice(level) {
  const safe = Math.max(0, Math.min(100, Number(level) || 0));
  $('voiceLevelText').textContent = `${Math.round(safe)}%`;
  document.querySelectorAll('.spectrum i').forEach((bar, idx) => {
    const jitter = ((idx * 17) % 31) - 12;
    bar.style.setProperty('--level', Math.max(8, safe + jitter));
  });
}

function setCheck(id, ok, label) {
  const el = $(id);
  el.textContent = label;
  el.classList.toggle('ok', Boolean(ok));
}

function calculateReadiness(status) {
  let score = 0;
  if (status?.python?.ok) score += 28;
  if (status?.hasAnthropicKey) score += 28;
  if ((status?.hud?.state || '').length) score += 16;
  if (status?.daemon?.running) score += 16;
  if (status?.model) score += 12;
  return Math.min(100, score);
}

function renderStatus(status) {
  lastStatus = status;
  const pythonOk = Boolean(status.python?.ok);
  const daemonRunning = Boolean(status.daemon?.running);
  const hudState = status.hud || {};
  const voice = status.voice || {};
  const state = normalizeState(hudState.state || (daemonRunning ? 'idle' : 'idle'), hudState.detail || hudState.message || '');
  const detail = hudState.detail || hudState.message || (daemonRunning ? 'wake daemon 연결됨' : '명령 대기');

  $('pythonStatus').textContent = pythonOk ? `${String(status.python.version || '').replace(/^Python\s*/i, 'Python ')} · ${status.python.command}` : '미감지';
  $('pythonDetail').textContent = pythonOk ? `런타임 준비 · ${status.platform}/${status.arch}` : (status.python?.error || 'Python 설치 또는 PATH 확인 필요');
  $('keyStatus').textContent = status.hasAnthropicKey ? 'SECURED' : 'NEEDED';
  $('modelStatus').textContent = status.model || selectedModel;
  $('packageStatus').textContent = status.packaged ? `${status.platform}/${status.arch}` : `DEV · ${status.platform}/${status.arch}`;
  $('lastUpdated').textContent = `마지막 갱신: ${nowTime()}`;
  $('appUrlInput').value = status.appUrl || '';
  $('modelInput').value = status.model || selectedModel;
  $('healthPortInput').value = status.healthPort || '41418';

  selectedModel = status.model || selectedModel;
  document.querySelectorAll('.model-card').forEach((card) => card.classList.toggle('selected', card.dataset.model === selectedModel));

  const readiness = calculateReadiness(status);
  $('readinessScore').textContent = String(readiness);
  document.querySelector('.score-ring').style.setProperty('--score', readiness);
  setCheck('checkPython', pythonOk, pythonOk ? 'Python OK' : 'Python 필요');
  setCheck('checkClaude', status.hasAnthropicKey, status.hasAnthropicKey ? 'Claude OK' : 'Key 필요');
  setCheck('checkHud', Boolean(hudState.state), hudState.state ? 'HUD OK' : 'HUD 대기');
  setCheck('checkDaemon', daemonRunning, daemonRunning ? 'Daemon ON' : 'Daemon OFF');

  updateVoice((voice.rms || voice.peak || 0) * (voice.rms <= 1 ? 100 : 1));
  setState(state, detail);
}

async function refreshStatus({ silent = false } = {}) {
  try {
    const status = await api.getStatus();
    renderStatus(status);
    if (!silent && eventCount === 0) addEvent('system', 'JARVIS Live Command HUD 준비 완료. 명령을 입력하거나 wake daemon을 시작하세요.');
    if ($('output').textContent === '시스템 준비 중…') setOutput('JARVIS Live Command HUD 준비 완료. Command Console에서 첫 명령을 실행하세요.');
  } catch (err) {
    setState('error', `상태 확인 실패: ${err.message || err}`);
    setOutput(`상태 확인 실패:\n${err.message || err}`);
  }
}

function renderIntelligence(data) {
  const usage = data?.usage || {};
  $('usageCalls').textContent = String(usage.calls || 0);
  $('usageLatency').textContent = `${usage.avgLatencyMs || 0}ms`;
  $('usageTokens').textContent = `${usage.inputTokens || 0} / ${usage.outputTokens || 0}`;
  $('usageCache').textContent = String(usage.cacheRead || 0);

  const history = data?.history?.items || [];
  const list = $('historyList');
  if (!history.length) {
    list.textContent = '아직 저장된 대화 기록이 없습니다. 첫 명령을 실행하면 최근 메모리가 표시됩니다.';
  } else {
    list.innerHTML = history.slice(0, 8).map((item) => {
      const role = item.role || item.event || 'memory';
      const content = compact(item.content || item.text || item.raw || JSON.stringify(item), 220);
      return `<article class="history-item"><strong>${role}</strong><p>${content}</p></article>`;
    }).join('');
  }

  const stats = data?.stats?.stdout || data?.stats?.stderr || '';
  if (stats && $('utilityOutput').textContent === '운영 도구 결과가 여기에 표시됩니다.') {
    setUtilityOutput(stats.trim());
  }
}

async function refreshIntelligence() {
  if (!api.getIntelligence) return;
  try {
    const data = await api.getIntelligence();
    renderIntelligence(data);
  } catch (err) {
    setUtilityOutput(`지능형 운영 지표 로드 실패:\n${err.message || err}`);
  }
}

function bindNavigation() {
  document.querySelectorAll('.rail-nav a').forEach((link) => {
    link.addEventListener('click', () => {
      document.querySelectorAll('.rail-nav a').forEach((a) => a.classList.remove('active'));
      link.classList.add('active');
    });
  });
}

function bindModelCards() {
  document.querySelectorAll('.model-card').forEach((card) => {
    card.addEventListener('click', () => {
      selectedModel = card.dataset.model;
      $('modelInput').value = selectedModel;
      document.querySelectorAll('.model-card').forEach((c) => c.classList.toggle('selected', c === card));
      toast(`${selectedModel} 선택됨`);
    });
  });
}

function bindModes() {
  document.querySelectorAll('.mode').forEach((btn) => {
    btn.addEventListener('click', () => {
      selectedMode = btn.dataset.mode;
      document.querySelectorAll('.mode').forEach((b) => b.classList.toggle('active', b === btn));
      if (selectedMode === 'wake') {
        $('promptInput').placeholder = 'Wake Daemon 모드에서는 아래 Daemon 시작 버튼으로 음성 대기 상태를 실행합니다.';
      } else if (selectedMode === 'do') {
        $('promptInput').placeholder = '예: 이 프로젝트의 문제점을 찾아 수정 계획을 세우고 가능한 작업을 실행해줘.';
      } else {
        $('promptInput').placeholder = '예: 내 오늘 업무를 우선순위대로 정리하고, 바로 실행할 수 있는 3단계 계획을 만들어줘.';
      }
      toast(`${btn.textContent} 모드 선택됨`);
    });
  });
}

function bindQuickMissions() {
  document.querySelectorAll('.quick-missions button').forEach((btn) => {
    btn.addEventListener('click', () => {
      $('promptInput').value = btn.dataset.prompt || btn.textContent;
      $('promptInput').focus();
      addEvent('user', `프리셋 선택: ${btn.textContent}`);
    });
  });
}

async function saveSettings() {
  const payload = {
    appUrl: $('appUrlInput').value,
    anthropicApiKey: $('apiKeyInput').value,
    preferredModel: $('modelInput').value || selectedModel,
    healthPort: $('healthPortInput').value,
  };
  const result = await api.saveSettings(payload);
  if (result.ok) {
    $('apiKeyInput').value = '';
    toast('설정이 안전하게 저장되었습니다.');
    addEvent('system', '보안 설정 저장 완료');
    await refreshStatus({ silent: true });
  } else toast(result.error || '저장 실패');
}

async function runPrompt() {
  const prompt = $('promptInput').value.trim();
  if (selectedMode === 'wake') return daemonAction('start');
  if (!prompt) return toast('실행할 명령을 입력하세요.');

  setState('executing', selectedMode === 'do' ? 'Agent Do 실행 중' : 'Quick Ask 실행 중');
  addEvent('user', prompt);
  setOutput(`JARVIS ${selectedMode.toUpperCase()} 실행 중…\n\n`);
  $('runBtn').disabled = true;
  $('stopBtn').disabled = false;

  try {
    const result = await api.runPrompt({ prompt, mode: selectedMode, model: selectedModel });
    $('runBtn').disabled = false;
    if (!result.ok) {
      setState('error', result.error || result.stderr || '실행 실패');
      addEvent('error', result.error || result.stderr || '실행 실패');
      setOutput(`실행 실패:\n${result.error || result.stderr || '알 수 없는 오류'}`);
      return;
    }
    if (result.stdout) addEvent('assistant', result.stdout.trim());
    if (!result.stdout && result.stderr) setOutput(`완료되었지만 stderr 출력이 있습니다:\n${result.stderr}`);
    else if (!result.stdout) setOutput('작업이 완료되었습니다. 출력이 없습니다.');
    setState('complete', '작업 완료');
    toast('자비스 작업 완료');
    await refreshStatus({ silent: true });
  } catch (err) {
    $('runBtn').disabled = false;
    setState('error', err.message || String(err));
    addEvent('error', err.message || String(err));
  }
}

async function runUtility(action) {
  if (!api.runUtility) return toast('운영 도구 IPC가 연결되지 않았습니다.');
  try {
    const note = action === 'note' ? $('noteInput').value.trim() : '';
    setUtilityOutput(`JARVIS ${action} 실행 중…\n`);
    const result = await api.runUtility({ action, note });
    const text = result.stdout || result.stderr || result.error || '출력 없음';
    setUtilityOutput(text.trim());
    addEvent(result.ok ? 'system' : 'error', `${action}: ${compact(text, 180)}`);
    if (action === 'note' && result.ok) $('noteInput').value = '';
    toast(result.ok ? `${action} 완료` : `${action} 실패`);
    await refreshIntelligence();
    await refreshStatus({ silent: true });
  } catch (err) {
    setUtilityOutput(`운영 도구 실행 실패:\n${err.message || err}`);
    toast(err.message || String(err));
  }
}

async function exportSession() {
  if (!api.exportSession) return toast('세션 리포트 IPC가 연결되지 않았습니다.');
  try {
    const result = await api.exportSession({ events: eventCount, lastStatus, currentState, selectedModel, selectedMode });
    if (result.canceled) return;
    toast('세션 리포트 저장 완료');
    addEvent('system', `세션 리포트 저장: ${result.filePath}`);
  } catch (err) {
    toast(err.message || String(err));
  }
}

async function daemonAction(action) {
  try {
    setState(action === 'stop' ? 'idle' : 'executing', `daemon ${action}`);
    const result = api.daemonControl ? await api.daemonControl({ action }) : { ok: false, error: 'daemon 제어 IPC가 아직 연결되지 않았습니다.' };
    if (!result.ok) {
      addEvent('error', result.error || `daemon ${action} 실패`);
      toast(result.error || `daemon ${action} 실패`);
      return;
    }
    const text = result.stdout || result.stderr || result.message || `daemon ${action} 완료`;
    addEvent('daemon', text.trim());
    setDaemonLog(text.trim() || '로그 없음');
    toast(`daemon ${action} 완료`);
    await refreshStatus({ silent: true });
    await refreshIntelligence();
  } catch (err) {
    addEvent('error', err.message || String(err));
    toast(err.message || String(err));
  }
}

function bindActions() {
  $('refreshBtn').addEventListener('click', () => refreshStatus());
  $('focusCommandBtn').addEventListener('click', () => $('promptInput').focus());
  $('openProjectBtn').addEventListener('click', () => api.openProject());
  $('doctorBtn').addEventListener('click', () => runUtility('doctor'));
  $('exportBtn').addEventListener('click', exportSession);
  $('saveNoteBtn').addEventListener('click', () => runUtility('note'));
  document.querySelectorAll('[data-utility]').forEach((btn) => btn.addEventListener('click', () => runUtility(btn.dataset.utility)));
  $('openWebBtn').addEventListener('click', async () => {
    const appUrl = $('appUrlInput').value.trim();
    if (!appUrl) return toast('먼저 JARVIS_APP_URL을 입력하세요.');
    await api.openExternal(`${appUrl.replace(/\/$/, '')}/dashboard.html`);
  });
  $('saveBtn').addEventListener('click', saveSettings);
  $('runBtn').addEventListener('click', runPrompt);
  $('stopBtn').addEventListener('click', async () => {
    const result = await api.stop();
    setState('idle', result.stopped ? '실행 중인 작업을 중지했습니다.' : '중지할 작업이 없습니다.');
    addEvent('system', result.stopped ? '실행 중인 작업 중지' : '중지할 작업 없음');
    toast(result.stopped ? '실행 중인 작업을 중지했습니다.' : '중지할 작업이 없습니다.');
    $('runBtn').disabled = false;
  });
  $('daemonStartBtn').addEventListener('click', () => daemonAction('start'));
  $('daemonRestartBtn').addEventListener('click', () => daemonAction('restart'));
  $('daemonStopBtn').addEventListener('click', () => daemonAction('stop'));
  $('daemonLogsBtn').addEventListener('click', () => daemonAction('logs'));

  api.onProcessOutput(({ stream, text }) => {
    if (!text) return;
    const prefix = stream === 'stderr' ? '\n[stderr] ' : '';
    setOutput(prefix + text, true);
    addEvent(stream === 'stderr' ? 'error' : 'runtime', `${stream}: ${text.trim()}`);
    if (/transcrib|analyz|분석|전사/i.test(text)) setState('analyzing', text.trim().slice(0, 120));
    else if (/speaking|자비스:|answer|응답/i.test(text)) setState('speaking', text.trim().slice(0, 120));
    else setState('executing', '런타임 출력 수신 중');
  });
}

window.addEventListener('DOMContentLoaded', async () => {
  $('eventStream').innerHTML = '<article class="event empty-event"><time>--:--:--</time><p>자비스 이벤트 스트림을 준비하는 중입니다.</p></article>';
  bindNavigation();
  bindModelCards();
  bindModes();
  bindQuickMissions();
  bindActions();
  setState('booting', '자비스 연결 준비 중');
  updateVoice(0);
  await refreshStatus();
  await refreshIntelligence();
  setInterval(() => refreshStatus({ silent: true }), 5000);
  setInterval(() => refreshIntelligence(), 15000);
});
