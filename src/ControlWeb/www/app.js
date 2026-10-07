(() => {
  'use strict';

  const LEGACY_IPC_STORAGE_KEY = 'asf.control.ipcPassword';
  const LOCK_KEY = 'asf.control.lockMinutes';
  const VIEW_KEY = 'asf.control.view';
  const DEFAULT_LOCK_MINUTES = 15;
  const QR_INPUT_TYPE = 8;
  const QR_POLL_MS = 1200;
  const PERSONA_STATES = Object.freeze([
    [0, 'Offline'],
    [1, 'Online'],
    [2, 'Busy'],
    [3, 'Away'],
    [4, 'Snooze'],
    [5, 'Looking to trade'],
    [6, 'Looking to play'],
    [7, 'Invisible'],
  ]);
  const STEAM_AVATAR_ORIGIN = 'https://avatars.akamai.steamstatic.com';
  const Core = window.ControlCore;
  if (!Core) throw new Error('ControlCore failed to load');

  const VIEW_META = {
    dashboard: ['Dashboard', 'Live overview of ASF, accounts and runtime health.'],
    accounts: ['Accounts', 'Create, inspect and control ASF bot accounts.'],
    playtime: ['Playtime Goals', 'Manage finite and unlimited playtime goals safely.'],
    native: ['Native ASF', 'Use standard ASF configuration and tools without leaving Control Suite.'],
    security: ['Security', 'Session controls and the authentication boundary.'],
    system: ['System', 'Runtime health, modules and native ASF process actions.'],
    advanced: ['Advanced', 'Architecture, pinned targets and native API access.'],
  };

  // Remove credentials persisted by pre-RAM-only releases.
  sessionStorage.removeItem(LEGACY_IPC_STORAGE_KEY);

  const state = {
    password: '',
    view: VIEW_META[sessionStorage.getItem(VIEW_KEY)] ? sessionStorage.getItem(VIEW_KEY) : 'dashboard',
    accounts: [],
    selectedBot: '',
    defaults: {},
    lockMinutes: Core.normalizeLockMinutes(sessionStorage.getItem(LOCK_KEY) ?? DEFAULT_LOCK_MINUTES, DEFAULT_LOCK_MINUTES),
    lastActivityAt: Date.now(),
    rendering: false,
    createMode: 'qr',
    goalSort: 'managed-first',
    qrOnboardingBot: '',
    nativeFocus: '',
  };

  let lockTimer = null;
  let modalResolver = null;
  let qrPollTimer = null;
  const qrPromptReady = new Map();
  const $ = (id) => document.getElementById(id);
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const escapeHtml = (value) => String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
  const sourceClass = (label) => ['OWN','FAMILY','FREE','EXCLUDED'].includes(label) ? label.toLowerCase() : 'missing';
  const formatBytes = (value) => {
    const bytes = Number(value || 0);
    if (!Number.isFinite(bytes) || bytes <= 0) return 'unknown';
    const units = ['B','KiB','MiB','GiB','TiB'];
    let n = bytes, i = 0;
    while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1; }
    return `${n.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
  };
  const formatDuration = (seconds) => {
    const value = Math.max(0, Number(seconds || 0));
    if (value < 60) return `${Math.floor(value)}s`;
    if (value < 3600) return `${Math.floor(value / 60)}m`;
    if (value < 86400) return `${Math.floor(value / 3600)}h ${Math.floor((value % 3600) / 60)}m`;
    return `${Math.floor(value / 86400)}d ${Math.floor((value % 86400) / 3600)}h`;
  };
  const formatGoalDuration = (seconds) => {
    const total = Math.max(0, Math.ceil(Number(seconds || 0)));
    const hours = Math.floor(total / 3600);
    const minutes = Math.floor((total % 3600) / 60);
    const remainder = total % 60;
    if (hours) return `${hours}h ${minutes}m ${remainder}s`;
    if (minutes) return `${minutes}m ${remainder}s`;
    return `${remainder}s`;
  };
  const yesNo = (value) => value ? 'yes' : 'no';
  const legacyAsfHref = (path) => `${path}${path.includes('?') ? '&' : '?'}asfui=1`;
  const prettyJson = (value) => JSON.stringify(value ?? {}, null, 2);
  const SENSITIVE_BOT_CONFIG_KEYS = Object.freeze(['SteamLogin','SteamPassword','SteamParentalCode','WebProxyPassword','SteamTradeToken']);
  const cloneJson = (value) => JSON.parse(JSON.stringify(value ?? {}));
  const redactBotConfigForEditor = (value) => {
    const next = cloneJson(value);
    SENSITIVE_BOT_CONFIG_KEYS.forEach((key) => { delete next[key]; });
    return next;
  };
  const restoreSensitiveBotConfig = (edited, baseline) => {
    const next = cloneJson(edited);
    SENSITIVE_BOT_CONFIG_KEYS.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(baseline || {}, key)) next[key] = baseline[key];
    });
    return next;
  };
  const assertNoSensitiveBotPatch = (patch) => {
    const key = SENSITIVE_BOT_CONFIG_KEYS.find((name) => Object.prototype.hasOwnProperty.call(patch || {}, name));
    if (key) throw new Error(`Mass edit cannot modify security-controlled field ${key}.`);
  };
  const confirmationSummary = (item) => {
    const type = item?.Type ?? item?.ConfirmationType ?? 'unknown';
    const creator = item?.CreatorID ?? item?.s_CreatorID ?? item?.CreatorId ?? '';
    const id = item?.ID ?? item?.s_ID ?? item?.Id ?? '';
    return `type ${type}${creator ? ` · creator ${creator}` : ''}${id ? ` · id ${id}` : ''}`;
  };
  const mergePatch = (base, patch) => {
    if (patch === null || Array.isArray(patch) || typeof patch !== 'object') return patch;
    const next = { ...(base && typeof base === 'object' && !Array.isArray(base) ? base : {}) };
    Object.entries(patch).forEach(([key, value]) => {
      if (value === null) delete next[key];
      else if (Array.isArray(value) || typeof value !== 'object') next[key] = value;
      else next[key] = mergePatch(next[key], value);
    });
    return next;
  };

  function accountDisplayName(account) {
    const nickname = String(account?.Nickname || '').trim();
    return nickname || String(account?.BotName || 'unknown');
  }
  function accountAvatarUrl(account) {
    const hash = String(account?.AvatarHash || '').trim();
    return hash ? `${STEAM_AVATAR_ORIGIN}/${encodeURIComponent(hash)}_full.jpg` : '';
  }
  function accountOptionLabel(account) {
    const display = accountDisplayName(account);
    const botName = String(account?.BotName || 'unknown');
    return display === botName ? display : `${display} · ASF ${botName}`;
  }
  function nextBotName() {
    const used = new Set(state.accounts.map((account) => String(account.BotName || '').toLowerCase()));
    for (let number = 1; number < 10000; number += 1) {
      const candidate = `account-${number}`;
      if (!used.has(candidate.toLowerCase())) return candidate;
    }
    throw new Error('Could not allocate a free ASF bot ID');
  }
  function naturalNameCompare(left, right) {
    return String(left?.Name || '').localeCompare(String(right?.Name || ''), undefined, { numeric:true, sensitivity:'base' });
  }
  function goalTargetValue(game, managed) {
    const goal = managed.get(Number(game.AppId));
    if (!goal) return Number.NEGATIVE_INFINITY;
    return goal.TargetHours == null ? Number.POSITIVE_INFINITY : Number(goal.TargetHours || 0);
  }
  function sortGoalGames(games, managed, mode) {
    const rows = [...(games || [])];
    const byName = (a, b) => naturalNameCompare(a, b) || Number(a.AppId) - Number(b.AppId);
    const sourceRank = (game, familyFirst = false) => {
      const source = Core.sourceLabel(game);
      const order = familyFirst ? { FAMILY:0, OWN:1, FREE:2, EXCLUDED:3 } : { OWN:0, FAMILY:1, FREE:2, EXCLUDED:3 };
      return order[source] ?? 9;
    };
    const comparator = {
      'name-asc': byName,
      'name-desc': (a, b) => -byName(a, b),
      'hours-desc': (a, b) => Number(b.CurrentHours || 0) - Number(a.CurrentHours || 0) || byName(a, b),
      'hours-asc': (a, b) => Number(a.CurrentHours || 0) - Number(b.CurrentHours || 0) || byName(a, b),
      'target-desc': (a, b) => goalTargetValue(b, managed) - goalTargetValue(a, managed) || byName(a, b),
      'target-asc': (a, b) => goalTargetValue(a, managed) - goalTargetValue(b, managed) || byName(a, b),
      'appid-asc': (a, b) => Number(a.AppId) - Number(b.AppId),
      'appid-desc': (a, b) => Number(b.AppId) - Number(a.AppId),
      'own-first': (a, b) => sourceRank(a) - sourceRank(b) || byName(a, b),
      'family-first': (a, b) => sourceRank(a, true) - sourceRank(b, true) || byName(a, b),
      'managed-first': (a, b) => Number(managed.has(Number(b.AppId))) - Number(managed.has(Number(a.AppId))) || byName(a, b),
    }[mode] || byName;
    return rows.sort(comparator);
  }

  function markActivity() { state.lastActivityAt = Date.now(); }
  function startLockWatch() {
    if (lockTimer) clearInterval(lockTimer);
    markActivity();
    lockTimer = setInterval(() => {
      if (state.password && state.lockMinutes > 0 && Date.now() - state.lastActivityAt >= state.lockMinutes * 60000) {
        lockSession(`Locked after ${state.lockMinutes} minute(s) of inactivity.`);
      }
    }, 15000);
  }
  function lockSession(message = '') {
    state.password = '';
    if (lockTimer) { clearInterval(lockTimer); lockTimer = null; }
    if (qrPollTimer) { clearTimeout(qrPollTimer); qrPollTimer = null; }
    if ($('modal')?.open) closeModal(null);
    setConnection(false, 'locked');
    showAuth(message);
  }

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('Authentication', state.password);
    if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
    const response = await fetch(path, { cache: 'no-store', ...options, headers });
    let payload = null;
    try { payload = await response.json(); } catch (_) { /* non-json response */ }
    if (!response.ok || payload?.Success === false) {
      const error = new Error(payload?.Message || `${response.status} ${response.statusText}`);
      error.status = response.status;
      if ((response.status === 401 || response.status === 403) && state.password) lockSession('Authorization expired or was rejected.');
      throw error;
    }
    return payload?.Result ?? payload;
  }

  function setConnection(ok, label = ok ? 'connected' : 'offline') {
    const node = $('connection');
    if (!node) return;
    node.innerHTML = `<span class="status-dot ${ok ? 'good' : 'neutral'}"></span>${escapeHtml(label)}`;
    node.className = `pill ${ok ? 'good' : (label === 'locked' ? 'neutral' : 'bad')}`;
  }
  function updateSidebarSummary() {
    const connected = state.accounts.filter((a) => a.Connected).length;
    const waiting = state.accounts.filter((a) => Number(a.RequiredInput || 0) > 0).length;
    const node = $('sidebarBotSummary');
    if (node) node.textContent = `${connected}/${state.accounts.length} connected${waiting ? ` · ${waiting} waiting input` : ''}`;
  }
  function showApp() { $('authGate').classList.add('hidden'); $('app').classList.remove('hidden'); }
  function showAuth(message = '') {
    $('app').classList.add('hidden');
    $('authGate').classList.remove('hidden');
    $('authError').textContent = message;
    $('password').value = '';
    $('password').focus();
  }
  async function authenticate(password) {
    state.password = password;
    await api('/Api/ASF');
    showApp();
    setConnection(true);
    startLockWatch();
    await loadAccounts();
    await render();
  }

  function toast(title, message = '', tone = 'good', timeout = 4200) {
    const region = $('toastRegion');
    const item = document.createElement('div');
    item.className = `toast ${tone}`;
    item.innerHTML = `<span class="status-dot ${tone === 'good' ? 'good' : tone === 'warn' ? 'warn' : ''}"></span><div><div class="toast-title">${escapeHtml(title)}</div>${message ? `<div class="toast-message">${escapeHtml(message)}</div>` : ''}</div><button class="toast-close" type="button" aria-label="Dismiss">×</button>`;
    item.querySelector('.toast-close').addEventListener('click', () => item.remove());
    region.appendChild(item);
    if (timeout > 0) setTimeout(() => item.remove(), timeout);
  }

  function closeModal(result = null) {
    const modal = $('modal');
    if (modal.open) modal.close();
    document.body.classList.remove('modal-open');
    const resolve = modalResolver;
    modalResolver = null;
    if (resolve) resolve(result);
  }

  function openModal({ title, eyebrow = '', body = '', confirmLabel = 'Confirm', tone = 'default', fields = [], requireText = '' }) {
    if (modalResolver) closeModal(null);
    $('modalTitle').textContent = title;
    $('modalEyebrow').textContent = eyebrow;
    $('modalBody').innerHTML = `${body}${fields.map((field, index) => `<label for="modalField${index}">${escapeHtml(field.label)}</label><input id="modalField${index}" data-modal-field="${escapeHtml(field.name)}" type="${escapeHtml(field.type || 'text')}" value="${escapeHtml(field.value || '')}" ${field.placeholder ? `placeholder="${escapeHtml(field.placeholder)}"` : ''} ${field.autocomplete ? `autocomplete="${escapeHtml(field.autocomplete)}"` : 'autocomplete="off"'} ${field.required === false ? '' : 'required'}>${field.help ? `<span class="field-help">${escapeHtml(field.help)}</span>` : ''}`).join('')}${requireText ? `<label for="modalConfirmText">Type <strong>${escapeHtml(requireText)}</strong> to continue</label><input id="modalConfirmText" autocomplete="off" required>` : ''}`;
    $('modalConfirm').textContent = confirmLabel;
    $('modalError').textContent = '';
    $('modal').dataset.tone = tone;
    $('modal').dataset.requireText = requireText;
    $('modal').showModal();
    document.body.classList.add('modal-open');
    const focusTarget = $('modalBody').querySelector('input') || $('modalConfirm');
    requestAnimationFrame(() => focusTarget?.focus());
    return new Promise((resolve) => { modalResolver = resolve; });
  }

  function readModalFields() {
    const values = {};
    document.querySelectorAll('[data-modal-field]').forEach((field) => { values[field.dataset.modalField] = field.value; });
    return values;
  }

  function wireModal() {
    $('modalCancel').addEventListener('click', (event) => { event.preventDefault(); closeModal(null); });
    $('modalClose').addEventListener('click', (event) => { event.preventDefault(); closeModal(null); });
    $('modal').addEventListener('cancel', (event) => { event.preventDefault(); closeModal(null); });
    $('modalConfirm').addEventListener('click', (event) => {
      event.preventDefault();
      const required = $('modalConfirmText');
      const form = $('modalForm');
      if (!form.reportValidity()) return;
      if (required) {
        const expected = $('modal').dataset.requireText || '';
        if (expected && required.value !== expected) {
          $('modalError').textContent = `Confirmation text must match ${expected}.`;
          required.focus();
          return;
        }
      }
      closeModal(readModalFields());
    });
  }

  async function loadAccounts() {
    const result = await api('/Api/AccountManager');
    state.accounts = result?.Accounts || [];
    if (state.selectedBot && !state.accounts.some((a) => a.BotName === state.selectedBot)) state.selectedBot = '';
    if (!state.selectedBot && state.accounts.length) state.selectedBot = state.accounts[0].BotName;
    if (state.qrOnboardingBot && !state.accounts.some((a) => a.BotName === state.qrOnboardingBot)) state.qrOnboardingBot = '';
    if (!state.qrOnboardingBot) {
      const qrAccount = state.accounts.find((a) => !a.Connected && Number(a.RequiredInput || 0) === QR_INPUT_TYPE);
      if (qrAccount) state.qrOnboardingBot = qrAccount.BotName;
    }
    updateSidebarSummary();
  }
  async function loadDefaults() {
    const result = await api('/Api/AccountManager/Defaults');
    state.defaults = result?.Defaults || {};
    return result;
  }
  async function getBotRecord(botName) {
    const result = await api(`/Api/Bot/${encodeURIComponent(botName)}`);
    const record = result?.[botName] || Object.values(result || {})[0];
    if (!record?.BotConfig) throw new Error(`ASF did not return BotConfig for ${botName}`);
    return record;
  }
  async function writeBotConfig(botName, botConfig) {
    const next = cloneJson(botConfig);
    if (next.PlaytimeGoalsEnabled === true) {
      next.GamesPlayedWhileIdle = [];
      next.CustomGamePlayedWhileIdle = null;
    }
    await api(`/Api/Bot/${encodeURIComponent(botName)}`, { method:'POST', body:JSON.stringify({ BotConfig:next }) });
  }
  async function updateBotConfig(botName, mutate) {
    const record = await getBotRecord(botName);
    const next = JSON.parse(JSON.stringify(record.BotConfig));
    mutate(next, record);
    await writeBotConfig(botName, next);
    await sleep(300);
    await loadAccounts();
  }

  async function botAction(botName, action, body = null) {
    await api(`/Api/Bot/${encodeURIComponent(botName)}/${action}`, { method:'POST', body:body == null ? undefined : JSON.stringify(body) });
    await sleep(200);
    await loadAccounts();
    toast(`${action} requested`, botName, 'good');
    await render();
  }
  async function renameBot(botName) {
    const values = await openModal({ title:'Rename account', eyebrow:'Account action', body:`<p>Rename <strong>${escapeHtml(botName)}</strong>. ASF will rename the related bot files as well.</p>`, confirmLabel:'Rename', fields:[{name:'name',label:'New bot name',value:botName}] });
    const newName = String(values?.name || '').trim();
    if (!newName || newName === botName) return;
    await api(`/Api/Bot/${encodeURIComponent(botName)}/Rename`, { method:'POST', body:JSON.stringify({ NewName:newName }) });
    state.selectedBot = newName;
    await loadAccounts();
    toast('Account renamed', `${botName} → ${newName}`);
    await render();
  }
  async function deleteBot(botName) {
    const values = await openModal({ title:'Delete account', eyebrow:'Permanent action', body:`<p>This deletes <strong>${escapeHtml(botName)}</strong> and all related ASF files.</p><div class="notice bad">This cannot be undone from the Control UI.</div>`, confirmLabel:'Delete permanently', tone:'danger', requireText:botName });
    if (!values) return;
    await api(`/Api/Bot/${encodeURIComponent(botName)}`, { method:'DELETE' });
    state.selectedBot = '';
    await sleep(250);
    await loadAccounts();
    toast('Account deleted', botName, 'warn');
    await render();
  }

  async function acceptQrPrompt(botName) {
    await api(`/Api/Bot/${encodeURIComponent(botName)}/Input`, { method:'POST', body:JSON.stringify({ Type:QR_INPUT_TYPE, Value:'Y' }) });
    qrPromptReady.set(botName, false);
  }

  function qrAccount(botName = state.qrOnboardingBot) {
    return state.accounts.find((item) => item.BotName === botName) || null;
  }

  async function maybeAcceptQrPrompt(account) {
    if (!account || account.Connected || account.QrChallengeUrl) return false;
    const required = Number(account.RequiredInput || 0);
    if (required !== QR_INPUT_TYPE) {
      qrPromptReady.set(account.BotName, true);
      return false;
    }
    if (qrPromptReady.get(account.BotName) === false) return false;
    qrPromptReady.set(account.BotName, false);
    try {
      await acceptQrPrompt(account.BotName);
      return true;
    } catch (error) {
      qrPromptReady.set(account.BotName, true);
      throw error;
    }
  }

  async function waitForQrChallenge(botName, timeoutMs = 30000) {
    const deadline = Date.now() + timeoutMs;
    qrPromptReady.set(botName, true);
    while (Date.now() < deadline) {
      await loadAccounts();
      const account = qrAccount(botName);
      if (!account) { await sleep(250); continue; }
      if (account.Connected || account.QrChallengeUrl) return account;
      const required = Number(account.RequiredInput || 0);
      if (required > 0 && required !== QR_INPUT_TYPE) {
        throw new Error(`ASF requested input type ${required} instead of QR login. Open this account to continue.`);
      }
      await maybeAcceptQrPrompt(account);
      await sleep(350);
    }
    throw new Error('ASF did not provide a QR challenge. QR login is disabled in ASF Headless/Service mode or the login session did not start.');
  }

  async function createBotFromForm(form) {
    const data = new FormData(form);
    const mode = form.dataset.mode === 'password' ? 'password' : 'qr';
    const botName = String(data.get('botName') || '').trim() || nextBotName();
    if (state.accounts.some((account) => String(account.BotName).toLowerCase() === botName.toLowerCase())) throw new Error(`ASF bot ID ${botName} already exists`);
    await loadDefaults();
    let botConfig = { ...state.defaults, Enabled:true };
    if (mode === 'password') {
      const steamLogin = String(data.get('steamLogin') || '').trim();
      const steamPassword = String(data.get('steamPassword') || '');
      if (!steamLogin || !steamPassword) throw new Error('Steam login and Steam password are required');
      const encryptedPassword = await api('/Api/ASF/Encrypt', { method:'POST', body:JSON.stringify({ CryptoMethod:1, StringToEncrypt:steamPassword }) });
      if (!encryptedPassword) throw new Error('ASF did not return an encrypted Steam password');
      botConfig = { ...botConfig, SteamLogin:steamLogin, SteamPassword:encryptedPassword, PasswordFormat:1 };
    }
    await writeBotConfig(botName, botConfig);
    state.selectedBot = botName;
    if (mode === 'qr') {
      state.qrOnboardingBot = botName;
      qrPromptReady.set(botName, true);
    }
    await sleep(300);
    await loadAccounts();
    if (mode === 'qr') {
      toast('Account created', `${botName} is waiting for Steam Mobile QR login.`);
      updateQrOnboardingPanel();
      scheduleQrRefresh();
      try { await waitForQrChallenge(botName); } catch (error) {
        updateQrOnboardingPanel();
        throw error;
      }
    } else {
      toast('Account created', `${botName} was written with an ASF-encrypted Steam password.`);
    }
    if (mode !== 'qr') form.reset();
    await loadAccounts();
    await render();
  }

  async function sendRequiredInput(botName, requiredType, value) {
    if (!requiredType || !String(value || '').trim()) throw new Error('Input value is required');
    await api(`/Api/Bot/${encodeURIComponent(botName)}/Input`, { method:'POST', body:JSON.stringify({ Type:requiredType, Value:String(value).trim() }) });
    await sleep(300);
    await loadAccounts();
    toast('Input sent', `${botName} · type ${requiredType}`);
    await render();
  }
  async function setConfigEnabled(botName, enabled) {
    await updateBotConfig(botName, (config) => { config.Enabled = Boolean(enabled); });
    toast(enabled ? 'Config enabled' : 'Config disabled', botName, enabled ? 'good' : 'warn');
    await render();
  }

  function accountStatus(account) {
    if (Number(account.RequiredInput || 0) > 0) return ['Needs input', 'warn'];
    if (account.Connected) return ['Connected', 'good'];
    if (account.KeepRunning) return ['Connecting', 'neutral'];
    return ['Stopped', 'bad'];
  }
  function accountIdentityMarkup(account, { large = false } = {}) {
    const avatar = accountAvatarUrl(account);
    const display = accountDisplayName(account);
    const avatarMarkup = avatar
      ? `<img class="steam-avatar${large ? ' large' : ''}" src="${escapeHtml(avatar)}" alt="${escapeHtml(display)} Steam avatar" loading="lazy">`
      : `<div class="steam-avatar placeholder${large ? ' large' : ''}" aria-hidden="true">S</div>`;
    return `<div class="account-identity">${avatarMarkup}<div class="account-identity-text"><strong class="account-display-name">${escapeHtml(display)}</strong><small class="account-bot-id">ASF ID: ${escapeHtml(account.BotName || 'unknown')}</small></div></div>`;
  }

  function accountRows({ compact = false } = {}) {
    if (!state.accounts.length) return '<div class="empty-state"><strong>No ASF accounts yet</strong>Create one from the Accounts page.</div>';
    return `<div class="account-list">${state.accounts.map((account) => {
      const [label, tone] = accountStatus(account);
      return `<div class="account-row ${compact ? 'compact-account-row' : 'full-account-row'}"><div class="account-row-main">${accountIdentityMarkup(account)}<div class="account-meta"><span>Steam ${escapeHtml(account.SteamId || 'unknown')}</span><span>·</span><span>${account.Farming ? 'cards farming' : account.FarmerPaused ? 'farmer paused' : 'farmer idle'}</span><span>·</span><span>config ${account.Enabled ? 'enabled' : 'disabled'}</span><span class="pill ${tone}">${escapeHtml(label)}</span></div></div><div class="actions"><button data-act="workspace" data-bot="${escapeHtml(account.BotName)}" class="secondary">Open</button><button data-act="goals" data-bot="${escapeHtml(account.BotName)}" class="secondary">Goals</button>${compact ? '' : `<button data-act="${account.KeepRunning ? 'stop' : 'start'}" data-bot="${escapeHtml(account.BotName)}" class="secondary">${account.KeepRunning ? 'Stop' : 'Start'}</button><button data-act="pause" data-bot="${escapeHtml(account.BotName)}" class="secondary">Pause</button><button data-act="resume" data-bot="${escapeHtml(account.BotName)}" class="secondary">Resume</button><button data-act="rename" data-bot="${escapeHtml(account.BotName)}" class="secondary">Rename ASF ID</button><button data-act="delete" data-bot="${escapeHtml(account.BotName)}" class="danger">Delete</button>`}</div></div>`;
    }).join('')}</div>`;
  }

  function qrOnboardingMarkup() {
    const account = qrAccount();
    if (!account) {
      return `<div id="qrOnboardingPanel" class="qr-panel qr-placeholder" data-qr-signature="idle"><div><h4>QR login</h4><p id="qrOnboardingStatus">QR will appear here after account creation.</p></div><div class="qr-placeholder-box" aria-hidden="true">QR</div></div>`;
    }
    if (account.Connected) {
      return `<div id="qrOnboardingPanel" class="qr-panel qr-success" data-qr-signature="connected:${escapeHtml(account.BotName)}"><div><h4>Steam account connected</h4><p id="qrOnboardingStatus">${escapeHtml(accountDisplayName(account))} is connected. You can add another account when ready.</p></div><div class="qr-status-mark" aria-hidden="true">✓</div></div>`;
    }
    if (account.QrChallengeUrl) {
      return `<div id="qrOnboardingPanel" class="qr-panel" data-qr-signature="challenge:${escapeHtml(account.QrChallengeUrl)}"><div><h4>Scan with Steam Mobile</h4><p id="qrOnboardingStatus">Open the Steam app, scan this QR code and confirm the sign-in. The challenge is rendered locally in this browser and automatically refreshes when ASF rotates it.</p></div><div id="qrCode" data-qr-url="${escapeHtml(account.QrChallengeUrl)}"></div></div>`;
    }
    const required = Number(account.RequiredInput || 0);
    if (!account.KeepRunning || (required > 0 && required !== QR_INPUT_TYPE)) {
      const detail = required > 0 && required !== QR_INPUT_TYPE
        ? ` ASF is waiting for input type ${required}.`
        : ' The bot stopped before QR login completed.';
      return `<div id="qrOnboardingPanel" class="qr-panel qr-error" data-qr-signature="terminal:${account.KeepRunning ? 1 : 0}:${required}"><div><h4>QR login could not continue</h4><p id="qrOnboardingStatus">QR login could not continue.${detail}</p></div><div class="qr-status-mark" aria-hidden="true">!</div></div>`;
    }
    const status = required === QR_INPUT_TYPE
      ? 'Starting Steam QR session…'
      : 'Reconnecting to Steam…';
    return `<div id="qrOnboardingPanel" class="qr-panel qr-placeholder" data-qr-signature="waiting:${required}"><div><h4>QR login</h4><p id="qrOnboardingStatus">${status}</p></div><div class="qr-placeholder-box" aria-hidden="true">QR</div></div>`;
  }

  function updateQrOnboardingPanel() {
    const panel = $('qrOnboardingPanel');
    if (!panel) return;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = qrOnboardingMarkup();
    const next = wrapper.firstElementChild;
    if (!next) return;
    if (panel.dataset.qrSignature === next.dataset.qrSignature) return;
    panel.replaceWith(next);
    window.ControlI18n?.apply?.(next);
    renderQrCode();
  }

  async function setOnlineStatus(botName, value) {
    const status = Number(value);
    if (!Number.isInteger(status) || status < 0 || status > 7) throw new Error('Invalid Steam persona status');
    await updateBotConfig(botName, (next) => { next.OnlineStatus = status; });
    toast('Steam status saved', `${botName} · ${PERSONA_STATES.find(([id]) => id === status)?.[1] || status}`);
    await render();
  }

  async function renderAccountWorkspace() {
    if (!state.selectedBot) return '<div class="empty-state"><strong>No account selected</strong>Choose an account above.</div>';
    const summary = state.accounts.find((a) => a.BotName === state.selectedBot);
    if (!summary) return '<div class="empty-state"><strong>Account unavailable</strong>Refresh the account list.</div>';
    let botConfig = null;
    try {
      botConfig = (await getBotRecord(state.selectedBot))?.BotConfig || null;
    } catch (_) {
      botConfig = null;
    }
    const parsedOnlineStatus = Number(botConfig?.OnlineStatus);
    const onlineStatus = Number.isInteger(parsedOnlineStatus) && parsedOnlineStatus >= 0 && parsedOnlineStatus <= 7 ? parsedOnlineStatus : null;
    const personaOptions = PERSONA_STATES.map(([value, label]) => `<option value="${value}" ${value === onlineStatus ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
    const personaDisabled = onlineStatus == null ? 'disabled' : '';
    const encodedBot = encodeURIComponent(state.selectedBot);
    const requiredInput = Number(summary.RequiredInput || 0);
    const inputForm = requiredInput > 0 && requiredInput !== QR_INPUT_TYPE
      ? `<div class="notice warn section"><strong>Action required.</strong> ASF is waiting for interactive input type ${requiredInput}.</div><form id="requiredInputForm" class="section" data-input-type="${requiredInput}"><label for="requiredInputValue">Steam / ASF input</label><div class="inline-form"><input id="requiredInputValue" autocomplete="one-time-code" placeholder="Enter requested value" required><button type="submit">Send securely</button></div></form>`
      : requiredInput === QR_INPUT_TYPE ? '<div class="notice section">QR sign-in is active in the Add account card above.</div>' : '<div class="notice good section">No interactive input is required from this account.</div>';
    const [statusLabel, statusTone] = accountStatus(summary);
    return `<div class="card account-workspace section"><div class="card-head"><div>${accountIdentityMarkup(summary, { large:true })}<div class="workspace-title"><span class="pill ${statusTone}">${escapeHtml(statusLabel)}</span><span class="workspace-steamid">Steam ${escapeHtml(summary.SteamId || 'unknown')}</span></div></div><div class="actions"><button data-act="goals" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">Open goals</button><button data-act="${summary.KeepRunning ? 'stop' : 'start'}" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">${summary.KeepRunning ? 'Stop' : 'Start'}</button><button data-act="${summary.FarmerPaused ? 'resume' : 'pause'}" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">${summary.FarmerPaused ? 'Resume' : 'Pause'}</button><button data-act="rename" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">Rename ASF ID</button><button id="toggleConfigEnabled" class="secondary">${summary.Enabled ? 'Disable config' : 'Enable config'}</button></div></div><div class="grid compact-grid"><div class="metric"><span>Keep running</span><strong>${yesNo(summary.KeepRunning)}</strong></div><div class="metric"><span>Playing</span><strong>${summary.IsPlayingPossible ? 'possible' : 'blocked'}</strong></div><div class="metric"><span>CardsFarmer</span><strong>${summary.Farming ? 'active' : summary.FarmerPaused ? 'paused' : 'idle'}</strong></div><div class="metric"><span>Authenticator</span><strong>${yesNo(summary.HasMobileAuthenticator)}</strong></div></div><div class="card section native-settings"><div class="card-head"><div><h3>Steam / ASF settings</h3><p>Common native ASF settings here; the full stock editor remains one click away.</p></div><span class="pill neutral">native</span></div><div class="settings-grid"><label for="onlineStatus">Steam persona status<select id="onlineStatus" ${personaDisabled}>${personaOptions}</select></label><div><span class="field-help">${onlineStatus == null ? 'Native BotConfig is temporarily unavailable.' : 'Invisible keeps ASF connected while your Steam persona appears offline to friends.'}</span><button id="saveOnlineStatus" class="secondary" type="button" ${personaDisabled}>Save Steam status</button></div></div><div class="actions section"><button class="secondary" type="button" data-native-focus="bot-config">Full bot config</button><button class="secondary" type="button" data-native-focus="2fa">2FA</button><button class="secondary" type="button" data-native-focus="bgr">Background redeemer</button><button class="secondary" type="button" data-native-focus="commands">Commands</button><button class="secondary" type="button" data-native-focus="log">Log</button></div></div>${inputForm}</div>`;
  }

  async function renderDashboard() {
    const [asf, control] = await Promise.all([api('/Api/ASF'), api('/Api/ControlCenter/Status')]);
    const connected = state.accounts.filter((x) => x.Connected).length;
    const farming = state.accounts.filter((x) => x.Farming).length;
    const waiting = state.accounts.filter((x) => Number(x.RequiredInput || 0) > 0).length;
    const healthNotice = waiting
      ? `<div class="notice warn">${waiting} account${waiting === 1 ? '' : 's'} waiting for interactive input. Open Accounts to continue login.</div>`
      : '<div class="notice good">Control plane is healthy and no account is waiting for input.</div>';
    return `<div class="grid"><div class="card metric"><span>Accounts</span><strong>${state.accounts.length}</strong><small class="metric-detail">${connected} connected</small></div><div class="card metric"><span>Connected</span><strong>${connected}</strong><small class="metric-detail">${state.accounts.length ? Math.round(connected / state.accounts.length * 100) : 0}% of accounts</small></div><div class="card metric"><span>Cards farming</span><strong>${farming}</strong><small class="metric-detail">native CardsFarmer</small></div><div class="card metric"><span>Control uptime</span><strong>${formatDuration(control?.UptimeSeconds)}</strong><small class="metric-detail">ControlCenter 1.0</small></div></div><div class="section">${healthNotice}</div><div class="two-col section"><div class="card"><div class="card-head"><div><h3>Accounts</h3><p>Current ASF bots and the actions that need attention.</p></div><button data-view-jump="accounts" class="secondary">Manage</button></div>${accountRows({compact:true})}</div><div class="card"><div class="card-head"><div><h3>Runtime</h3><p>Read-only host and ASF health.</p></div><span class="pill good"><span class="status-dot good"></span>healthy</span></div><div class="row"><div class="row-main"><strong>ASF API</strong><small>${asf ? 'authenticated and responding' : 'unknown'}</small></div></div><div class="row"><div class="row-main"><strong>ASF version</strong><small>${escapeHtml(asf?.Version || 'unknown')}</small></div></div><div class="row"><div class="row-main"><strong>Build variant</strong><small>${escapeHtml(asf?.BuildVariant || 'unknown')}</small></div></div><div class="row"><div class="row-main"><strong>Managed memory</strong><small>${formatBytes((asf?.MemoryUsage || control?.ManagedMemoryKiB || 0) * 1024)}</small></div></div><div class="row"><div class="row-main"><strong>Disk free</strong><small>${control?.StorageAvailable ? formatBytes(control?.DiskFreeBytes) : 'unavailable'}</small></div></div></div></div>`;
  }

  async function renderAccounts() {
    const defaults = await loadDefaults();
    const workspace = await renderAccountWorkspace();
    const suggestedBotName = nextBotName();
    const switcher = state.accounts.length
      ? `<div class="account-switcher section" aria-label="Steam accounts">${state.accounts.map((account) => `<button type="button" data-switch-bot="${escapeHtml(account.BotName)}" class="account-chip ${account.BotName === state.selectedBot ? 'active' : ''}">${accountIdentityMarkup(account)}</button>`).join('')}<button type="button" id="focusAddAccount" class="account-chip add-account">+ Add account</button></div>`
      : '';
    return `${switcher}<div class="two-col"><div class="card"><div class="card-head"><div><h3>Registered accounts</h3><p>${state.accounts.length} Steam account${state.accounts.length === 1 ? '' : 's'} managed by ASF.</p></div></div>${accountRows()}</div><div class="card" id="addAccountCard"><div class="card-head"><div><h3>Add account</h3><p>Use Steam Mobile QR login or encrypted Steam credentials through native ASF APIs.</p></div></div><div class="auth-mode-switch" role="group" aria-label="Sign-in method"><button id="createModeQr" type="button" class="secondary ${state.createMode === 'qr' ? 'active' : ''}">QR code</button><button id="createModePassword" type="button" class="secondary ${state.createMode === 'password' ? 'active' : ''}">Login / password</button></div><form id="createBotForm" data-mode="${escapeHtml(state.createMode)}"><label for="createBotName">Internal ASF bot ID <span class="muted">(optional)</span></label><input id="createBotName" name="botName" autocomplete="off" placeholder="${escapeHtml(suggestedBotName)}"><span class="field-help">Technical identifier only. The UI shows the Steam persona name as the primary account name.</span><div id="createQrFields" class="auth-mode-panel ${state.createMode === 'qr' ? '' : 'hidden'}"><div class="notice good">No Steam password is sent or stored for QR login. ASF creates the native Steam QR challenge and this browser renders it locally.</div><div class="section">${qrOnboardingMarkup()}</div></div><div id="createPasswordFields" class="auth-mode-panel ${state.createMode === 'password' ? '' : 'hidden'}"><label for="createSteamLogin">Steam login</label><input id="createSteamLogin" name="steamLogin" autocomplete="username" ${state.createMode === 'password' ? 'required' : ''}><label for="createSteamPassword">Steam password</label><input id="createSteamPassword" name="steamPassword" type="password" autocomplete="new-password" ${state.createMode === 'password' ? 'required' : ''}><span class="field-help">The password is AES-encrypted by ASF before BotConfig is written.</span></div><div class="toolbar section"><button type="submit">Create account</button></div></form><div class="notice section">AccountManager never receives or persists the Steam password. QR onboarding does not require one.</div></div></div>${workspace}<details class="card section"><summary><strong>Defaults for new accounts</strong> <span class="pill neutral">advanced</span></summary><p><small>Credential-like keys are recursively stripped server-side. Maximum payload: ${Math.round(Number(defaults?.MaxPayloadChars || 65536) / 1024)} KiB.</small></p><textarea id="defaultsEditor" rows="12" aria-label="Defaults JSON">${escapeHtml(JSON.stringify(state.defaults, null, 2))}</textarea><div class="toolbar section"><button id="saveDefaults">Validate & save defaults</button></div><div class="defaults-note">Blocked keys: ${escapeHtml((defaults?.ForbiddenKeys || []).join(', ') || 'credentials and security fields')}</div></details>`;
  }

  function setCreateMode(mode) {
    state.createMode = mode === 'password' ? 'password' : 'qr';
    const form = $('createBotForm');
    if (!form) return;
    form.dataset.mode = state.createMode;
    $('createModeQr')?.classList.toggle('active', state.createMode === 'qr');
    $('createModePassword')?.classList.toggle('active', state.createMode === 'password');
    $('createQrFields')?.classList.toggle('hidden', state.createMode !== 'qr');
    $('createPasswordFields')?.classList.toggle('hidden', state.createMode !== 'password');
    const login = $('createSteamLogin'), password = $('createSteamPassword');
    if (login) login.required = state.createMode === 'password';
    if (password) password.required = state.createMode === 'password';
  }

  function mergeGoalGames(libraryGames, statusGames) {
    const map = new Map((libraryGames || []).map((game) => [Number(game.AppId), { ...game }]));
    for (const goal of statusGames || []) {
      const id = Number(goal.AppId);
      if (!map.has(id)) map.set(id, { AppId:id, Name:goal.Name || `App ${id}`, Source:'missing', CanSelect:false, Available:false, CurrentHours:goal.CurrentHours || 0 });
    }
    return [...map.values()];
  }
  function managedStatusRows(games) {
    if (!(games || []).length) return '<div class="empty-state"><strong>No managed games</strong>Select games above and save the configuration.</div>';
    return `<div class="managed-list">${games.map((game) => {
      const current = Number(game.EffectiveHours || 0);
      const target = game.TargetHours == null ? null : Number(game.TargetHours);
      const effectiveSeconds = Number(game.EffectiveSeconds ?? Math.round(current * 3600));
      const targetSeconds = game.TargetSeconds == null ? null : Number(game.TargetSeconds);
      const remainingSeconds = game.RemainingSeconds == null ? null : Number(game.RemainingSeconds);
      const pct = targetSeconds ? Math.max(0, Math.min(100, effectiveSeconds / targetSeconds * 100)) : 100;
      const remaining = target == null ? 'unlimited' : `${formatGoalDuration(remainingSeconds ?? Math.max(0, (target - current) * 3600))} left`;
      const exactProgress = target == null ? '∞ unlimited' : `${formatGoalDuration(effectiveSeconds)} / ${formatGoalDuration(targetSeconds ?? target * 3600)}`;
      return `<div class="managed-row"><div class="managed-row-head"><div><strong>${escapeHtml(game.Name || `App ${game.AppId}`)}</strong><small>AppID ${Number(game.AppId)} · ${escapeHtml(game.State || 'unknown')}${game.QueuePosition ? ` · queue #${Number(game.QueuePosition)}` : ''}</small></div><span class="pill ${String(game.State || '').includes('blocked') ? 'warn' : 'neutral'}">${exactProgress}</span></div><div class="progress ${target == null ? 'unlimited' : ''}" aria-label="${escapeHtml(remaining)}"><span style="width:${pct.toFixed(1)}%"></span></div><small>${escapeHtml(remaining)}</small></div>`;
    }).join('')}</div>`;
  }
  function parentalStatus(parental) {
    const apps = parental?.Apps || [];
    const allowed = apps.filter((app) => app.EffectiveAllowed).length;
    const denied = apps.length - allowed;
    const appRows = apps.length ? `<div class="parental-apps">${apps.map((app) => `<div class="row"><div class="row-main"><strong>App ${Number(app.AppId)}</strong><small>base ${app.BaseAllowed == null ? 'unset' : app.BaseAllowed ? 'allow' : 'deny'} · custom ${app.CustomAllowed == null ? 'unset' : app.CustomAllowed ? 'allow' : 'deny'}</small></div><span class="pill ${app.EffectiveAllowed ? 'good' : 'bad'}">${app.EffectiveAllowed ? 'allowed' : 'blocked'}</span></div>`).join('')}</div>` : '<div class="empty-state"><strong>No managed Family View entries</strong>Nothing to restore or override right now.</div>';
    return `<div class="family-summary"><div class="mini-stat"><span>Available</span><strong>${yesNo(parental?.Available)}</strong></div><div class="mini-stat"><span>Enabled</span><strong>${yesNo(parental?.Enabled)}</strong></div><div class="mini-stat"><span>Allowed</span><strong>${allowed}</strong></div><div class="mini-stat"><span>Blocked</span><strong>${denied}</strong></div></div>${parental?.Error ? `<div class="notice bad section">${escapeHtml(parental.Error)}</div>` : ''}${appRows}`;
  }

  async function renderPlaytime() {
    if (!state.selectedBot && state.accounts.length) state.selectedBot = state.accounts[0].BotName;
    const options = state.accounts.map((a) => `<option value="${escapeHtml(a.BotName)}" ${a.BotName === state.selectedBot ? 'selected' : ''}>${escapeHtml(accountOptionLabel(a))}</option>`).join('');
    if (!state.selectedBot) return '<div class="empty-state"><strong>No account available</strong>Add an ASF account first.</div>';
    let status, library, parental;
    try {
      [status, library, parental] = await Promise.all([
        api(`/Api/PlaytimeGoals/${encodeURIComponent(state.selectedBot)}`),
        api(`/Api/PlaytimeGoals/${encodeURIComponent(state.selectedBot)}/Library`),
        api(`/Api/PlaytimeGoals/${encodeURIComponent(state.selectedBot)}/Parental`),
      ]);
    } catch (error) {
      return `<div class="toolbar"><select id="botSelect">${options}</select></div><div class="notice bad section">PlaytimeGoals is unavailable: ${escapeHtml(error.message)}</div>`;
    }
    const managed = new Map((status?.Games || []).map((game) => [Number(game.AppId), game]));
    const games = sortGoalGames(mergeGoalGames(library?.Games || [], status?.Games || []), managed, state.goalSort);
    const sources = { OWN:0, FAMILY:0, FREE:0, EXCLUDED:0 };
    const rows = games.map((game) => {
      const appId = Number(game.AppId), goal = managed.get(appId), isManaged = Boolean(goal), canToggle = Core.canToggleGame(game, isManaged), source = Core.sourceLabel(game);
      if (Object.prototype.hasOwnProperty.call(sources, source)) sources[source] += 1;
      const target = goal?.TargetHours == null ? '' : goal.TargetHours;
      const search = `${game.Name || ''} ${appId} ${source}`.toLowerCase();
      const availability = game.Available === false ? 'unavailable' : game.FamilyAvailabilityKnown === false && source === 'FAMILY' ? 'availability unknown' : 'available';
      const stateText = goal?.State ? `${goal.State}${goal.QueuePosition ? ` · queue #${goal.QueuePosition}` : ''}` : availability;
      return `<div class="goal-row" data-goal-row data-appid="${appId}" data-name="${escapeHtml(game.Name || `App ${appId}`)}" data-hours="${Number(game.CurrentHours || 0)}" data-source="${escapeHtml(source)}" data-search="${escapeHtml(search)}"><label class="goal-select"><input type="checkbox" data-goal-select data-appid="${appId}" ${isManaged ? 'checked' : ''} ${canToggle ? '' : 'disabled'}><span><strong>${escapeHtml(game.Name || `App ${appId}`)}</strong><small>AppID ${appId} · <span class="source-badge source-${sourceClass(source)}">${source}</span> · ${escapeHtml(stateText)}</small></span></label><div class="goal-hours"><input type="number" min="0.000277778" step="any" data-goal-target data-appid="${appId}" value="${escapeHtml(target)}" placeholder="∞ unlimited" ${isManaged ? '' : 'disabled'} aria-label="Target hours for ${escapeHtml(game.Name || `App ${appId}`)}"><small>${goal ? `${formatGoalDuration(goal.EffectiveSeconds ?? Number(goal.EffectiveHours || 0) * 3600)} effective` : `${Number(game.CurrentHours || 0).toFixed(2)}h Steam`}</small></div></div>`;
    }).join('') || '<div class="empty-state"><strong>Library is empty</strong>Reconnect the account and refresh.</div>';
    return `<div class="toolbar"><select id="botSelect" aria-label="ASF account">${options}</select><span class="pill ${status?.Enabled ? 'good' : 'neutral'}">${status?.Enabled ? 'enabled' : 'disabled'}</span><span class="pill neutral">${managed.size} managed</span></div><div class="grid section"><div class="card metric"><span>Active batch</span><strong>${(status?.CurrentBatch || []).length}/${status?.BatchSize ?? 0}</strong><small class="metric-detail">queued by priority</small></div><div class="card metric"><span>Library</span><strong>${(library?.Games || []).length}</strong><small class="metric-detail">${sources.OWN} own · ${sources.FAMILY} family</small></div><div class="card metric"><span>Free / excluded</span><strong>${sources.FREE}/${sources.EXCLUDED}</strong><small class="metric-detail">free selectable · excluded blocked</small></div><div class="card metric"><span>Recovery</span><strong>${status?.RecoveryReady ? 'OK' : 'BLOCK'}</strong><small class="metric-detail">Family View journal</small></div></div><div class="card section"><div class="card-head"><div><h3>Configuration</h3><p>PlaytimeGoals remains the only owner of managed GamesPlayed state.</p></div></div><div class="settings-grid"><label class="checkline"><input id="ptgEnabled" type="checkbox" ${status?.Enabled ? 'checked' : ''}> PlaytimeGoals enabled</label><label for="ptgBatch">Batch size<input id="ptgBatch" type="number" min="1" max="32" step="1" value="${escapeHtml(status?.BatchSize ?? 5)}"></label><label class="checkline"><input id="ptgParental" type="checkbox" ${status?.ParentalWritesEnabled ? 'checked' : ''}> Family View writes</label></div><div class="notice section">Blank target means unlimited. Finite goals use second-precision local deadlines; Steam historical playtime remains minute-granularity. Enabling PlaytimeGoals clears native ASF idle-game fields to prevent competing GamesPlayed owners.</div><div class="goal-toolbar section"><input id="goalSearch" placeholder="Search by game name or AppID" aria-label="Search games"><select id="goalSource" aria-label="Filter by source"><option value="ALL">All sources</option><option>OWN</option><option>FAMILY</option><option>FREE</option><option>EXCLUDED</option></select><select id="goalSort" aria-label="Sort games"><option value="managed-first" ${state.goalSort === 'managed-first' ? 'selected' : ''}>Managed first</option><option value="name-asc" ${state.goalSort === 'name-asc' ? 'selected' : ''}>Name A → Z</option><option value="name-desc" ${state.goalSort === 'name-desc' ? 'selected' : ''}>Name Z → A</option><option value="hours-desc" ${state.goalSort === 'hours-desc' ? 'selected' : ''}>Steam hours high → low</option><option value="hours-asc" ${state.goalSort === 'hours-asc' ? 'selected' : ''}>Steam hours low → high</option><option value="target-desc" ${state.goalSort === 'target-desc' ? 'selected' : ''}>Target high → low</option><option value="target-asc" ${state.goalSort === 'target-asc' ? 'selected' : ''}>Target low → high</option><option value="appid-asc" ${state.goalSort === 'appid-asc' ? 'selected' : ''}>AppID ascending</option><option value="appid-desc" ${state.goalSort === 'appid-desc' ? 'selected' : ''}>AppID descending</option><option value="own-first" ${state.goalSort === 'own-first' ? 'selected' : ''}>Own first</option><option value="family-first" ${state.goalSort === 'family-first' ? 'selected' : ''}>Family first</option></select><button id="saveGoals">Save goals</button></div><div id="goalRows" class="goal-list section">${rows}</div></div><div class="two-col section"><div class="card"><div class="card-head"><div><h3>Managed status</h3><p>Effective credit, targets and queue state.</p></div></div>${managedStatusRows(status?.Games || [])}</div><div class="card"><div class="card-head"><div><h3>Family View</h3><p>Current parental state for managed applications.</p></div><span class="pill ${parental?.Available ? 'good' : 'warn'}">${parental?.Available ? 'available' : 'unavailable'}</span></div>${parentalStatus(parental)}</div></div>`;
  }

  async function savePlaytimeGoals() {
    const botName = state.selectedBot;
    if (!botName) throw new Error('No bot selected');
    const entries = [...document.querySelectorAll('[data-goal-select]')].map((box) => {
      const appId = Number(box.dataset.appid);
      const target = document.querySelector(`[data-goal-target][data-appid="${appId}"]`);
      return { appId, selected:box.checked, targetHours:target?.value ?? '' };
    });
    const settings = { enabled:$('ptgEnabled').checked, batchSize:$('ptgBatch').value, parentalWritesEnabled:$('ptgParental').checked, entries };
    const record = await getBotRecord(botName);
    const next = Core.applyPlaytimeConfig(record.BotConfig, settings);
    await writeBotConfig(botName, next);
    const expectedGoals = Core.normalizeGoals(entries);
    let reloaded = false;
    for (let attempt = 0; attempt < 10; attempt += 1) {
      await sleep(400);
      try {
        const latest = await api(`/Api/PlaytimeGoals/${encodeURIComponent(botName)}`);
        const actual = Object.fromEntries((latest?.Games || []).map((game) => [String(game.AppId), game.TargetHours ?? null]));
        const expectedKeys = Object.keys(expectedGoals).sort(), actualKeys = Object.keys(actual).sort();
        const keysMatch = JSON.stringify(actualKeys) === JSON.stringify(expectedKeys);
        const targetsMatch = keysMatch && expectedKeys.every((key) => {
          const expected = expectedGoals[key], observed = actual[key];
          if (expected == null || observed == null) return expected == null && observed == null;
          return Math.abs(Number(expected) - Number(observed)) < 1e-9;
        });
        if (latest?.Enabled === Boolean(settings.enabled) && Number(latest?.BatchSize) === Number(settings.batchSize) && latest?.ParentalWritesEnabled === Boolean(settings.parentalWritesEnabled) && targetsMatch) { reloaded = true; break; }
      } catch (_) { /* config reload still settling */ }
    }
    await loadAccounts();
    await render();
    if (reloaded) toast('PlaytimeGoals saved', `${botName} reloaded and verified.`);
    else toast('Configuration written', 'ASF reload is still settling. Refresh shortly.', 'warn', 6500);
  }

  async function renderSecurity() {
    const options = [0,5,15,30,60].map((minutes) => `<option value="${minutes}" ${Number(state.lockMinutes) === minutes ? 'selected' : ''}>${minutes === 0 ? 'Never in this tab' : `${minutes} min`}</option>`).join('');
    return `<div class="two-col"><div class="card"><div class="card-head"><div><h3>Authentication boundary</h3><p>Defense in depth around ASF IPC.</p></div><span class="pill good">active</span></div><div class="boundary"><span class="boundary-index">1</span><div><strong>HTTPS / Tailscale</strong><small>Transport and network reachability remain outside ASF.</small></div></div><div class="boundary"><span class="boundary-index">2</span><div><strong>ASF IPCPassword</strong><small>Every /Api request from this UI carries the native Authentication header.</small></div></div><div class="boundary"><span class="boundary-index">3</span><div><strong>Tab-scoped session</strong><small>The IPC password is kept only in page memory and is lost on refresh, lock, or tab close.</small></div></div></div><div class="card"><div class="card-head"><div><h3>Session lock</h3><p>Protect an unattended browser tab.</p></div></div><label for="lockMinutes">Auto-lock after inactivity</label><select id="lockMinutes">${options}</select><span class="field-help">Activity resets the timer. “Never” applies only to this tab.</span><div class="toolbar section"><button id="lockNow" class="secondary">Lock now</button></div></div></div><div class="card section"><div class="card-head"><div><h3>Security invariants</h3><p>What Control Suite 1.0 intentionally does not expose.</p></div></div><div class="grid three"><div class="notice good">No arbitrary shell or process execution endpoint.</div><div class="notice good">Steam credentials are never persisted by AccountManager.</div><div class="notice good">Destructive actions require an explicit confirmation dialog.</div></div></div>`;
  }

  async function renderSystem() {
    const [control, asf] = await Promise.all([api('/Api/ControlCenter/Status'), api('/Api/ASF')]);
    const modules = (control?.Modules || []).map((m) => `<div class="module-row"><div><strong>${escapeHtml(m.Name)}</strong><div class="module-version">loaded ${escapeHtml(m.Version || '—')} · expected ${escapeHtml(m.ExpectedVersion || '—')}</div></div><span class="pill ${m.Loaded && (!m.ExpectedVersion || m.Version === m.ExpectedVersion) ? 'good' : 'warn'}">${m.Loaded ? (m.Version === m.ExpectedVersion ? 'OK' : 'VERSION') : 'MISSING'}</span></div>`).join('');
    const storageAvailable = control?.StorageAvailable === true && Number(control?.DiskTotalBytes) > 0 && Number(control?.DiskFreeBytes) >= 0;
    const diskPct = storageAvailable ? Math.max(0, Math.min(100, Number(control.DiskFreeBytes) / Number(control.DiskTotalBytes) * 100)) : 0;
    const diskFree = storageAvailable ? formatBytes(control.DiskFreeBytes) : 'unavailable';
    const diskDetail = storageAvailable ? `${diskPct.toFixed(0)}% of ${formatBytes(control.DiskTotalBytes)}` : 'not exposed by runtime';
    const managedMemory = Number(asf?.MemoryUsage || control?.ManagedMemoryKiB || 0);
    return `<div class="grid"><div class="card metric"><span>Managed memory</span><strong>${formatBytes(managedMemory * 1024)}</strong><small class="metric-detail">reported by native ASF</small></div><div class="card metric"><span>Disk free</span><strong>${diskFree}</strong><small class="metric-detail">${diskDetail}</small></div><div class="card metric"><span>ASF variant</span><strong>${escapeHtml(asf?.BuildVariant || 'unknown')}</strong><small class="metric-detail">native build target</small></div><div class="card metric"><span>Waiting input</span><strong>${Number(control?.WaitingForInputBots || 0)}</strong><small class="metric-detail">interactive bot requests</small></div></div><div class="two-col section"><div class="card"><div class="card-head"><div><h3>Modules</h3><p>Loaded assemblies and expected release versions.</p></div></div>${modules || '<div class="empty-state">No module data.</div>'}</div><div class="card"><div class="card-head"><div><h3>Runtime</h3><p>Trim-safe runtime details sourced from native ASF where available.</p></div></div><div class="row"><div class="row-main"><strong>ASF version</strong><small>${escapeHtml(asf?.Version || 'unknown')}</small></div></div><div class="row"><div class="row-main"><strong>Build variant</strong><small>${escapeHtml(asf?.BuildVariant || 'unknown')}</small></div></div><div class="row"><div class="row-main"><strong>Plugin target</strong><small>net10.0 · ASF ${escapeHtml(control?.TargetAsfVersion || 'unknown')}</small></div></div><div class="row"><div class="row-main"><strong>Control uptime</strong><small>${formatDuration(control?.UptimeSeconds)}</small></div></div></div></div><div class="card danger-zone section"><div class="card-head"><div><h3>ASF process actions</h3><p>Native authenticated ASF endpoints only. No host shell is exposed.</p></div><span class="pill warn">confirmation required</span></div><div class="actions"><button id="restartAsf" class="warning">Restart ASF</button><button id="exitAsf" class="danger">Exit ASF</button></div></div>`;
  }


  async function renderNative() {
    const botName = state.selectedBot || state.accounts[0]?.BotName || '';
    const encodedBot = encodeURIComponent(botName);
    let botRecord = null;
    let asf = null;
    let plugins = [];
    let bans = [];
    let logTail = [];

    const tasks = [
      api('/Api/ASF').then((value) => { asf = value; }),
      api('/Api/Plugins').then((value) => { plugins = Array.isArray(value) ? value : []; }).catch(() => { plugins = []; }),
      api('/Api/IPC/Bans').then((value) => { bans = Array.isArray(value) ? value : []; }).catch(() => { bans = []; }),
      api('/Api/NLog/File?count=250').then((value) => { logTail = Array.isArray(value?.Content) ? value.Content : []; }).catch(() => { logTail = []; }),
    ];

    if (botName) tasks.push(getBotRecord(botName).then((value) => { botRecord = value; }));

    await Promise.all(tasks);

    const globalConfig = asf?.GlobalConfig || {};
    const botConfig = botRecord?.BotConfig || {};
    const visibleBotConfig = redactBotConfigForEditor(botConfig);
    const botOptions = state.accounts.map((account) => `<option value="${escapeHtml(account.BotName)}" ${account.BotName === botName ? 'selected' : ''}>${escapeHtml(accountOptionLabel(account))}</option>`).join('');
    const pluginRows = plugins.map((plugin) => `<div class="row"><div class="row-main"><strong>${escapeHtml(plugin.Name || plugin.GetType || 'Plugin')}</strong><small>${escapeHtml(plugin.Version || plugin.AssemblyName || 'loaded')}</small></div><span class="pill good">loaded</span></div>`).join('') || '<div class="empty-state"><strong>No plugins reported</strong>ASF returned an empty plugin list.</div>';
    const banRows = bans.map((ip) => `<div class="row"><div class="row-main"><strong>${escapeHtml(ip)}</strong><small>Blocked by ASF IPC authentication</small></div><button class="secondary" data-unban-ip="${escapeHtml(ip)}">Unban</button></div>`).join('') || '<div class="empty-state"><strong>No banned IPs</strong>ASF IPC currently has no blocked clients.</div>';
    const massBots = state.accounts.map((account) => `<label class="checkline"><input type="checkbox" data-mass-bot value="${escapeHtml(account.BotName)}"> ${escapeHtml(accountOptionLabel(account))}</label>`).join('');

    return `
      <div class="toolbar">
        <select id="nativeBotSelect" aria-label="ASF account">${botOptions}</select>
        <span class="pill neutral">native ASF APIs</span>
      </div>

      <div class="two-col section">
        <div class="card" id="native-bot-config">
          <div class="card-head"><div><h3>Bot configuration</h3><p>Complete BotConfig editor. ASF preserves omitted security-controlled values.</p></div><span class="pill good">native</span></div>
          ${botName ? `<textarea id="nativeBotConfig" class="code-editor" rows="22" spellcheck="false" aria-label="Complete BotConfig JSON">${escapeHtml(prettyJson(visibleBotConfig))}</textarea><span class="field-help">Security-controlled fields are hidden from the editor and preserved on save.</span><div class="actions section"><button id="saveNativeBotConfig">Save bot config</button></div>` : '<div class="empty-state"><strong>No account selected</strong>Add an ASF account first.</div>'}
        </div>

        <div class="card">
          <div class="card-head"><div><h3>Global ASF configuration</h3><p>Complete GlobalConfig editor through ASF's native validated endpoint.</p></div><span class="pill warn">global</span></div>
          <textarea id="nativeGlobalConfig" class="code-editor" rows="22" spellcheck="false" aria-label="Complete GlobalConfig JSON">${escapeHtml(prettyJson(globalConfig))}</textarea>
          <div class="actions section"><button id="saveNativeGlobalConfig">Save global config</button></div>
        </div>
      </div>

      <div class="two-col section">
        <div class="card" id="native-commands">
          <div class="card-head"><div><h3>Commands</h3><p>Run standard ASF commands through /Api/Command.</p></div></div>
          <form id="nativeCommandForm">
            <label for="nativeCommand">ASF command</label>
            <div class="inline-form"><input id="nativeCommand" autocomplete="off" placeholder="status"><button type="submit">Run</button></div>
          </form>
          <label for="nativeCommandOutput">Output</label>
          <textarea id="nativeCommandOutput" class="code-editor" rows="10" readonly placeholder="Command output appears here."></textarea>
        </div>

        <div class="card" id="native-bgr">
          <div class="card-head"><div><h3>Background redeemer</h3><p>Queue Steam keys without reading existing key/output contents into Control Suite.</p></div><span class="pill neutral">write-only</span></div>
          ${botName ? `<label for="nativeBgrKeys">Keys to queue</label><textarea id="nativeBgrKeys" class="code-editor" rows="10" placeholder="AAAAA-BBBBB-CCCCC | Optional name"></textarea><span class="field-help">One key per line. Existing stored/output keys are intentionally not fetched by Control Suite.</span><div class="actions section"><button id="queueNativeBgr">Queue keys</button></div>` : '<div class="empty-state"><strong>No account selected</strong>Select an ASF account first.</div>'}
        </div>
      </div>

      <div class="two-col section">
        <div class="card" id="native-2fa">
          <div class="card-head"><div><h3>2FA</h3><p>Steam Guard token, confirmations and authenticator management through native ASF.</p></div></div>
          ${botName ? `
            <div class="inline-form"><input id="native2faToken" readonly placeholder="Token hidden until requested"><button id="fetchNative2faToken" type="button">Generate token</button></div>
            <div class="actions section"><button id="loadNative2faConfirmations" class="secondary" type="button">Load confirmations</button><button id="acceptNative2faConfirmations" class="secondary" type="button">Accept all</button><button id="declineNative2faConfirmations" class="secondary" type="button">Decline all</button></div>
            <div id="native2faConfirmations" class="notice section">Confirmations are not loaded yet.</div>
            <label for="nativeAuthenticatorJson">Import authenticator JSON</label>
            <textarea id="nativeAuthenticatorJson" class="code-editor" rows="8" spellcheck="false" placeholder='{"shared_secret":"..."}'></textarea>
            <div class="actions section"><button id="importNativeAuthenticator" type="button">Import authenticator</button><button id="deleteNativeAuthenticator" class="danger" type="button">Delete authenticator</button></div>
          ` : '<div class="empty-state"><strong>No account selected</strong>Select an ASF account first.</div>'}
        </div>

        <div class="card">
          <div class="card-head"><div><h3>IPC bans</h3><p>Clients currently blocked by ASF authentication throttling.</p></div><button id="clearNativeBans" class="secondary" type="button" ${bans.length ? '' : 'disabled'}>Clear all</button></div>
          ${banRows}
        </div>
      </div>

      <div class="two-col section">
        <div class="card">
          <div class="card-head"><div><h3>Mass editor</h3><p>Apply a JSON merge patch to multiple BotConfig objects through native ASF validation.</p></div></div>
          <div class="mass-bot-grid">${massBots || '<span class="muted">No bots available.</span>'}</div>
          <label for="nativeMassPatch">BotConfig patch</label>
          <textarea id="nativeMassPatch" class="code-editor" rows="10" spellcheck="false" placeholder='{"OnlineStatus":7}'></textarea>
          <div class="actions section"><button id="applyNativeMassPatch" type="button">Apply to selected</button></div>
        </div>

        <div class="card">
          <div class="card-head"><div><h3>Plugins & release policy</h3><p>Loaded plugins are visible here. Runtime updates stay pinned to the Control Suite release pipeline.</p></div><span class="pill good">${plugins.length} loaded</span></div>
          ${pluginRows}
          <div class="notice warn section">Native ASF self-update and plugin-update actions are intentionally not exposed because this installation uses a pinned compatibility patch and reproducible Control Suite releases.</div>
        </div>
      </div>

      <div class="two-col section">
        <div class="card" id="native-copy">
          <div class="card-head"><div><h3>Copy bot configuration</h3><p>Create a new ASF bot from the selected BotConfig without copying hidden credentials.</p></div></div>
          ${botName ? `<label for="nativeCopyBotName">New ASF bot ID</label><div class="inline-form"><input id="nativeCopyBotName" autocomplete="off" placeholder="${escapeHtml(nextBotName())}"><button id="copyNativeBotConfig" type="button">Copy config</button></div><span class="field-help">Control Suite strips login/password/parental/proxy secrets and SteamTradeToken from the copy; the new bot will request login/QR as needed.</span>` : '<div class="empty-state"><strong>No account selected</strong>Select an ASF account first.</div>'}
        </div>

        <div class="card" id="native-crypto">
          <div class="card-head"><div><h3>Crypto tools</h3><p>Native ASF encryption and hashing helpers.</p></div></div>
          <label for="nativeCryptoInput">Input</label>
          <input id="nativeCryptoInput" type="password" autocomplete="off" placeholder="Value to encrypt or hash">
          <div class="settings-grid section">
            <label for="nativeCryptoMethod">Encryption<select id="nativeCryptoMethod"><option value="1">AES</option><option value="0">Plain text</option><option value="2">Protected data</option><option value="3">Environment variable</option><option value="4">File</option></select></label>
            <label for="nativeHashMethod">Hashing<select id="nativeHashMethod"><option value="1">SCrypt</option><option value="2">PBKDF2</option><option value="0">Plain text</option></select></label>
            <div class="actions"><button id="runNativeEncrypt" class="secondary" type="button">Encrypt</button><button id="runNativeHash" class="secondary" type="button">Hash</button></div>
          </div>
          <label for="nativeCryptoOutput">Result</label>
          <textarea id="nativeCryptoOutput" class="code-editor" rows="5" readonly placeholder="Result appears here."></textarea>
        </div>
      </div>

      <div class="card section" id="native-log">
        <div class="card-head"><div><h3>ASF log</h3><p>Authenticated read-only history through ASF's native NLog API.</p></div><span class="pill neutral">${logTail.length} lines</span></div>
        <textarea id="nativeLogTail" class="code-editor" rows="18" readonly aria-label="ASF log tail">${escapeHtml(logTail.join('\n'))}</textarea>
        <div class="actions section"><button id="refreshNativeLog" class="secondary" type="button">Refresh log</button></div>
      </div>

      <div class="card section">
        <div class="card-head"><div><h3>Legacy fallback</h3><p>Only for a native ASF function not yet migrated into Control Suite.</p></div><a href="${legacyAsfHref('/bots')}"><button class="secondary" type="button">Open stock ASF-ui</button></a></div>
        <div class="notice">The fallback remains hidden behind an explicit bypass. Normal administration should stay in Control Suite.</div>
      </div>
    `;
  }

  async function renderAdvanced() {
    const control = await api('/Api/ControlCenter/Status');

    const shortCommit = (value) => {
      const text = String(value || 'unknown');
      return /^[0-9a-f]{40}$/i.test(text) ? `${text.slice(0, 12)}…` : text;
    };

    const suiteVersion = String(control?.ControlSuiteVersion || 'unknown');
    const moduleVersion = String(control?.ControlModuleVersion || 'unknown');
    const asfVersion = String(control?.TargetAsfVersion || 'unknown');
    const asfCommit = shortCommit(control?.TargetAsfCommit);
    const asfPatch = shortCommit(control?.TargetAsfPatchSha256);
    const asfUiCommit = shortCommit(control?.TargetAsfUiCommit);
    const ptgVersion = String(control?.TargetPlaytimeGoalsVersion || 'unknown');
    const ptgCommit = shortCommit(control?.TargetPlaytimeGoalsCommit);

    return `<div class="two-col"><div class="card"><div class="card-head"><div><h3>Pinned compatibility</h3><p>Control Suite ${escapeHtml(suiteVersion)} is built against a fixed baseline.</p></div></div><div class="row"><div class="row-main"><strong>ASF</strong><small>${escapeHtml(asfVersion)} · ${escapeHtml(asfCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>ASF compatibility patch</strong><small>SHA-256 · ${escapeHtml(asfPatch)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>ASF-ui</strong><small>${escapeHtml(asfUiCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>PlaytimeGoals</strong><small>${escapeHtml(ptgVersion)} · ${escapeHtml(ptgCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>Control modules</strong><small>AccountManager · ControlCenter · ControlWeb</small></div><span class="pill good">${escapeHtml(moduleVersion)}</span></div></div><div class="card"><div class="card-head"><div><h3>Ownership boundaries</h3><p>Each module has one clear job.</p></div></div><div class="boundary"><span class="boundary-index">P</span><div><strong>PlaytimeGoals</strong><small>Managed GamesPlayed, Family availability and Family View journal.</small></div></div><div class="boundary"><span class="boundary-index">A</span><div><strong>AccountManager</strong><small>Credential-free defaults and account summary.</small></div></div><div class="boundary"><span class="boundary-index">C</span><div><strong>ControlCenter</strong><small>Read-only runtime and module health.</small></div></div><div class="boundary"><span class="boundary-index">W</span><div><strong>ControlWeb</strong><small>Presentation and orchestration through existing authenticated APIs.</small></div></div></div></div><div class="card section"><div class="card-head"><div><h3>Native API</h3><p>Use ASF Swagger when you need direct endpoint inspection.</p></div><div class="actions"><a href="/swagger" target="_blank" rel="noreferrer"><button class="secondary" type="button">Open API docs</button></a><a href="${legacyAsfHref('/bots')}"><button class="secondary" type="button">Open legacy Bots</button></a></div></div><div class="notice">The stock ASF-ui remains available for every native ASF function. Control Suite adds focused workflows without removing upstream functionality. Deployment, backups and rollback remain out-of-band through the ADB installer. The browser cannot execute arbitrary host commands.</div><div class="actions section"><button data-view-jump="native" type="button">Open Native ASF workspace</button><a href="${legacyAsfHref('/bots')}"><button class="secondary" type="button">Emergency legacy fallback</button></a></div></div>`;
  }

  const renderers = { dashboard:renderDashboard, accounts:renderAccounts, playtime:renderPlaytime, native:renderNative, security:renderSecurity, system:renderSystem, advanced:renderAdvanced };

  function renderQrCode() {
    const node = $('qrCode');
    if (!node) return;
    const url = String(node.dataset.qrUrl || '');
    if (!url) return;
    if (typeof window.QRCode !== 'function') {
      node.innerHTML = '<div class="notice bad">Local QR renderer failed to load.</div>';
      return;
    }
    node.replaceChildren();
    new window.QRCode(node, { text:url, width:224, height:224, colorDark:'#08111f', colorLight:'#ffffff', correctLevel:window.QRCode.CorrectLevel.M });
  }

  function scheduleQrRefresh() {
    if (qrPollTimer) { clearTimeout(qrPollTimer); qrPollTimer = null; }
    if (state.view !== 'accounts' || !state.qrOnboardingBot) return;
    const account = qrAccount();
    const required = Number(account?.RequiredInput || 0);
    if (!account || account.Connected || !account.KeepRunning || (required > 0 && required !== QR_INPUT_TYPE)) {
      updateQrOnboardingPanel();
      return;
    }
    qrPollTimer = setTimeout(async () => {
      qrPollTimer = null;
      try {
        await loadAccounts();
        const latest = qrAccount();
        const latestRequired = Number(latest?.RequiredInput || 0);
        const terminal = !latest || latest.Connected || !latest.KeepRunning || (latestRequired > 0 && latestRequired !== QR_INPUT_TYPE);
        if (latest && !terminal) await maybeAcceptQrPrompt(latest);
        updateQrOnboardingPanel();
        if (!terminal) scheduleQrRefresh();
      } catch (_) {
        updateQrOnboardingPanel();
        scheduleQrRefresh();
      }
    }, QR_POLL_MS);
  }

  function loadingMarkup() {
    return '<div class="grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div><div class="two-col section"><div class="skeleton"></div><div class="skeleton"></div></div>';
  }
  async function render() {
    if (state.rendering) return;
    state.rendering = true;
    const [title, subtitle] = VIEW_META[state.view] || VIEW_META.dashboard;
    $('title').textContent = title;
    $('subtitle').textContent = subtitle;
    $('content').innerHTML = loadingMarkup();
    try {
      $('content').innerHTML = await renderers[state.view]();
      setConnection(true);
      wireDynamicEvents();
      renderQrCode();
      scheduleQrRefresh();
      if (state.view === 'native' && state.nativeFocus) {
        requestAnimationFrame(() => document.getElementById(`native-${state.nativeFocus}`)?.scrollIntoView({ block:'start' }));
      }
    } catch (error) {
      if (!state.password) return;
      setConnection(false, 'error');
      $('content').innerHTML = `<div class="card error-state"><h3>Could not load ${escapeHtml(title)}</h3><p>${escapeHtml(error.message)}</p><button id="retryView" class="secondary">Try again</button></div>`;
      $('retryView')?.addEventListener('click', () => render());
    } finally {
      state.rendering = false;
    }
  }

  function filterGoalRows() {
    const search = String($('goalSearch')?.value || '').trim().toLowerCase();
    const source = String($('goalSource')?.value || 'ALL');
    document.querySelectorAll('[data-goal-row]').forEach((row) => {
      const matchesText = !search || String(row.dataset.search || '').includes(search);
      const matchesSource = source === 'ALL' || row.dataset.source === source;
      row.classList.toggle('hidden', !(matchesText && matchesSource));
    });
  }

  function sortGoalRowsInPlace() {
    const container = $('goalRows');
    const select = $('goalSort');
    if (!container || !select) return;
    const mode = String(select.value || 'managed-first');
    state.goalSort = mode;
    const rows = [...container.querySelectorAll('[data-goal-row]')];
    const byName = (a, b) => String(a.dataset.name || '').localeCompare(String(b.dataset.name || ''), undefined, { numeric:true, sensitivity:'base' }) || Number(a.dataset.appid || 0) - Number(b.dataset.appid || 0);
    const selected = (row) => Boolean(row.querySelector('[data-goal-select]')?.checked);
    const target = (row) => {
      if (!selected(row)) return Number.NEGATIVE_INFINITY;
      const value = String(row.querySelector('[data-goal-target]')?.value || '').trim();
      return value === '' ? Number.POSITIVE_INFINITY : Number(value || 0);
    };
    const sourceRank = (row, familyFirst = false) => {
      const order = familyFirst ? { FAMILY:0, OWN:1, FREE:2, EXCLUDED:3 } : { OWN:0, FAMILY:1, FREE:2, EXCLUDED:3 };
      return order[row.dataset.source] ?? 9;
    };
    const comparator = {
      'name-asc': byName,
      'name-desc': (a, b) => -byName(a, b),
      'hours-desc': (a, b) => Number(b.dataset.hours || 0) - Number(a.dataset.hours || 0) || byName(a, b),
      'hours-asc': (a, b) => Number(a.dataset.hours || 0) - Number(b.dataset.hours || 0) || byName(a, b),
      'target-desc': (a, b) => target(b) - target(a) || byName(a, b),
      'target-asc': (a, b) => target(a) - target(b) || byName(a, b),
      'appid-asc': (a, b) => Number(a.dataset.appid || 0) - Number(b.dataset.appid || 0),
      'appid-desc': (a, b) => Number(b.dataset.appid || 0) - Number(a.dataset.appid || 0),
      'own-first': (a, b) => sourceRank(a) - sourceRank(b) || byName(a, b),
      'family-first': (a, b) => sourceRank(a, true) - sourceRank(b, true) || byName(a, b),
      'managed-first': (a, b) => Number(selected(b)) - Number(selected(a)) || byName(a, b),
    }[mode] || byName;
    rows.sort(comparator).forEach((row) => container.appendChild(row));
    filterGoalRows();
  }

  async function nativeProcessAction(action, confirmation) {
    const values = await openModal({ title:`${action} ASF`, eyebrow:'Process action', body:`<p>${action === 'Restart' ? 'ASF will restart and the Control UI will temporarily disconnect.' : 'ASF will exit. An external supervisor is required to start it again.'}</p>`, confirmLabel:action, tone:action === 'Exit' ? 'danger' : 'warning', requireText:confirmation });
    if (!values) return;
    await api(`/Api/ASF/${action}`, { method:'POST' });
    if (action === 'Restart') {
      setConnection(false, 'restarting');
      toast('ASF restart requested', 'Reconnect after the process is back.', 'warn', 7000);
    } else {
      setConnection(false, 'stopped');
      lockSession('ASF exit requested.');
    }
  }

  function wireDynamicEvents() {
    document.querySelectorAll('[data-act]').forEach((button) => button.addEventListener('click', async () => {
      const bot = button.dataset.bot, action = button.dataset.act;
      button.disabled = true;
      try {
        if (action === 'workspace') { state.selectedBot = bot; state.view = 'accounts'; updateNav(); await render(); return; }
        if (action === 'goals') { state.selectedBot = bot; state.view = 'playtime'; updateNav(); await render(); return; }
        if (action === 'start') await botAction(bot, 'Start');
        if (action === 'stop') await botAction(bot, 'Stop');
        if (action === 'pause') await botAction(bot, 'Pause', { Permanent:true, ResumeInSeconds:0 });
        if (action === 'resume') await botAction(bot, 'Resume');
        if (action === 'rename') await renameBot(bot);
        if (action === 'delete') await deleteBot(bot);
      } catch (error) { toast('Action failed', error.message, 'bad', 7000); }
      finally { button.disabled = false; }
    }));
    document.querySelectorAll('[data-native-focus]').forEach((button) => button.addEventListener('click', async () => {
      state.nativeFocus = button.dataset.nativeFocus || '';
      state.view = 'native';
      updateNav();
      await render();
      document.getElementById(`native-${state.nativeFocus}`)?.scrollIntoView({ behavior:'smooth', block:'start' });
    }));
    document.querySelectorAll('[data-view-jump]').forEach((button) => button.addEventListener('click', async () => { state.view = button.dataset.viewJump; updateNav(); await render(); }));
    const form = $('createBotForm');
    if (form) form.addEventListener('submit', async (event) => { event.preventDefault(); const submit = form.querySelector('button[type="submit"]'); submit.disabled = true; try { await createBotFromForm(form); } catch (error) { toast('Could not create account', error.message, 'bad', 7000); } finally { submit.disabled = false; } });
    $('createModeQr')?.addEventListener('click', () => setCreateMode('qr'));
    $('createModePassword')?.addEventListener('click', () => setCreateMode('password'));
    document.querySelectorAll('[data-switch-bot]').forEach((button) => button.addEventListener('click', async () => { state.selectedBot = button.dataset.switchBot; await render(); }));
    $('focusAddAccount')?.addEventListener('click', () => { $('addAccountCard')?.scrollIntoView({ behavior:'smooth', block:'start' }); $('createBotName')?.focus(); });
    const requiredInputForm = $('requiredInputForm');
    if (requiredInputForm) requiredInputForm.addEventListener('submit', async (event) => { event.preventDefault(); const button = requiredInputForm.querySelector('button[type="submit"]'); button.disabled = true; try { await sendRequiredInput(state.selectedBot, Number(requiredInputForm.dataset.inputType), $('requiredInputValue').value); } catch (error) { toast('Input failed', error.message, 'bad'); } finally { button.disabled = false; } });
    const toggleEnabled = $('toggleConfigEnabled');
    if (toggleEnabled) toggleEnabled.addEventListener('click', async () => { const summary = state.accounts.find((a) => a.BotName === state.selectedBot); if (!summary) return; toggleEnabled.disabled = true; try { await setConfigEnabled(state.selectedBot, !summary.Enabled); } catch (error) { toast('Config update failed', error.message, 'bad'); } finally { toggleEnabled.disabled = false; } });
    const saveOnlineStatus = $('saveOnlineStatus');
    if (saveOnlineStatus) saveOnlineStatus.addEventListener('click', async () => { saveOnlineStatus.disabled = true; try { await setOnlineStatus(state.selectedBot, $('onlineStatus')?.value); } catch (error) { toast('Steam status not saved', error.message, 'bad', 7000); } finally { saveOnlineStatus.disabled = false; } });
    const saveDefaults = $('saveDefaults');
    if (saveDefaults) saveDefaults.addEventListener('click', async () => { saveDefaults.disabled = true; try { const parsed = JSON.parse($('defaultsEditor').value); await api('/Api/AccountManager/Defaults', { method:'POST', body:JSON.stringify(parsed) }); await loadDefaults(); toast('Defaults saved', 'Server-side secret filtering applied.'); } catch (error) { toast('Defaults not saved', error.message, 'bad', 7000); } finally { saveDefaults.disabled = false; } });
    const botSelect = $('botSelect');
    if (botSelect) botSelect.addEventListener('change', async () => { state.selectedBot = botSelect.value; await render(); });
    document.querySelectorAll('[data-goal-select]').forEach((box) => box.addEventListener('change', () => { const target = document.querySelector(`[data-goal-target][data-appid="${box.dataset.appid}"]`); if (target) target.disabled = !box.checked; }));
    $('goalSearch')?.addEventListener('input', filterGoalRows);
    $('goalSource')?.addEventListener('change', filterGoalRows);
    $('goalSort')?.addEventListener('change', sortGoalRowsInPlace);
    $('saveGoals')?.addEventListener('click', async () => { const button = $('saveGoals'); button.disabled = true; try { await savePlaytimeGoals(); } catch (error) { toast('PlaytimeGoals not saved', error.message, 'bad', 7000); } finally { button.disabled = false; } });
    const nativeBotSelect = $('nativeBotSelect');
    if (nativeBotSelect) nativeBotSelect.addEventListener('change', async () => { state.selectedBot = nativeBotSelect.value; await render(); });

    $('saveNativeBotConfig')?.addEventListener('click', async () => {
      const button = $('saveNativeBotConfig');
      button.disabled = true;
      try {
        const parsed = JSON.parse($('nativeBotConfig').value);
        const current = await getBotRecord(state.selectedBot);
        const next = restoreSensitiveBotConfig(parsed, current.BotConfig);
        await writeBotConfig(state.selectedBot, next);
        await loadAccounts();
        toast('BotConfig saved', state.selectedBot);
        await render();
      } catch (error) {
        toast('BotConfig not saved', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('saveNativeGlobalConfig')?.addEventListener('click', async () => {
      const button = $('saveNativeGlobalConfig');
      button.disabled = true;
      try {
        const parsed = JSON.parse($('nativeGlobalConfig').value);
        await api('/Api/ASF', { method:'POST', body:JSON.stringify({ GlobalConfig:parsed }) });
        toast('Global ASF config saved', 'ASF validated and wrote the configuration.');
        await render();
      } catch (error) {
        toast('Global config not saved', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('nativeCommandForm')?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const command = String($('nativeCommand').value || '').trim();
      if (!command) return;
      const submit = event.currentTarget.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        const result = await api('/Api/Command', { method:'POST', body:JSON.stringify({ Command:command }) });
        $('nativeCommandOutput').value = typeof result === 'string' ? result : prettyJson(result);
      } catch (error) {
        $('nativeCommandOutput').value = `ERROR: ${error.message}`;
      } finally {
        submit.disabled = false;
      }
    });

    $('queueNativeBgr')?.addEventListener('click', async () => {
      const button = $('queueNativeBgr');
      button.disabled = true;
      try {
        const entries = {};
        String($('nativeBgrKeys').value || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean).forEach((line) => {
          const [rawKey, ...rawName] = line.split('|');
          const key = String(rawKey || '').trim();
          const name = rawName.join('|').trim() || 'Control Suite';
          if (key) entries[key] = name;
        });
        if (!Object.keys(entries).length) throw new Error('Enter at least one key.');
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/GamesToRedeemInBackground`, { method:'POST', body:JSON.stringify({ GamesToRedeemInBackground:entries }) });
        $('nativeBgrKeys').value = '';
        toast('Keys queued', `${Object.keys(entries).length} key(s) sent to Background Redeemer.`);
        await render();
      } catch (error) {
        toast('Keys not queued', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('fetchNative2faToken')?.addEventListener('click', async () => {
      const button = $('fetchNative2faToken');
      button.disabled = true;
      try {
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Token`);
        const botResult = result?.[state.selectedBot];
        const token = typeof botResult === 'string' ? botResult : botResult?.Result ?? result?.Token ?? '';
        if (!token) throw new Error(botResult?.Message || 'No 2FA token returned.');
        $('native2faToken').value = String(token);
      } catch (error) {
        toast('2FA token unavailable', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('loadNative2faConfirmations')?.addEventListener('click', async () => {
      const button = $('loadNative2faConfirmations');
      button.disabled = true;
      try {
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Confirmations`);
        const botResult = result?.[state.selectedBot];
        const confirmations = Array.isArray(botResult?.Result) ? botResult.Result : [];
        $('native2faConfirmations').innerHTML = confirmations.length
          ? confirmations.map((item) => `<div class="row"><div class="row-main"><strong>${escapeHtml(confirmationSummary(item))}</strong><small>Steam mobile confirmation</small></div></div>`).join('')
          : '<strong>No pending confirmations</strong>';
      } catch (error) {
        toast('Could not load confirmations', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    const handleAll2fa = async (accept) => {
      const word = accept ? 'ACCEPT' : 'DECLINE';
      const values = await openModal({ title:`${accept ? 'Accept' : 'Decline'} all confirmations`, eyebrow:'Steam Guard 2FA', body:'<p>This applies to every currently pending confirmation for the selected account.</p>', confirmLabel:accept ? 'Accept all' : 'Decline all', tone:accept ? 'warning' : 'danger', requireText:word });
      if (!values) return;
      await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Confirmations`, { method:'POST', body:JSON.stringify({ Accept:accept, AcceptedCreatorIDs:[], WaitIfNeeded:false }) });
      toast('2FA confirmations handled', accept ? 'Accepted all pending confirmations.' : 'Declined all pending confirmations.');
      $('loadNative2faConfirmations')?.click();
    };
    $('acceptNative2faConfirmations')?.addEventListener('click', async () => { try { await handleAll2fa(true); } catch (error) { toast('2FA action failed', error.message, 'bad', 7000); } });
    $('declineNative2faConfirmations')?.addEventListener('click', async () => { try { await handleAll2fa(false); } catch (error) { toast('2FA action failed', error.message, 'bad', 7000); } });

    $('importNativeAuthenticator')?.addEventListener('click', async () => {
      const button = $('importNativeAuthenticator');
      button.disabled = true;
      try {
        const authenticator = JSON.parse($('nativeAuthenticatorJson').value);
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication`, { method:'POST', body:JSON.stringify(authenticator) });
        $('nativeAuthenticatorJson').value = '';
        toast('Authenticator imported', state.selectedBot);
        await loadAccounts();
      } catch (error) {
        toast('Authenticator import failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('deleteNativeAuthenticator')?.addEventListener('click', async () => {
      const values = await openModal({ title:'Delete mobile authenticator', eyebrow:'Steam Guard 2FA', body:'<p>Remove the authenticator data from ASF for this account?</p>', confirmLabel:'Delete authenticator', tone:'danger', requireText:'DELETE 2FA' });
      if (!values) return;
      try {
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication`, { method:'DELETE' });
        toast('Authenticator deleted', state.selectedBot, 'warn');
        await loadAccounts();
        await render();
      } catch (error) {
        toast('Authenticator delete failed', error.message, 'bad', 7000);
      }
    });

    document.querySelectorAll('[data-unban-ip]').forEach((button) => button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await api(`/Api/IPC/Bans/${encodeURIComponent(button.dataset.unbanIp)}`, { method:'DELETE' });
        toast('IP unbanned', button.dataset.unbanIp);
        await render();
      } catch (error) {
        toast('Could not unban IP', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    }));

    $('clearNativeBans')?.addEventListener('click', async () => {
      const values = await openModal({ title:'Clear all IPC bans', eyebrow:'Native ASF', body:'<p>Remove every IP currently blocked by ASF IPC authentication?</p>', confirmLabel:'Clear bans', tone:'warning', requireText:'CLEAR' });
      if (!values) return;
      try {
        await api('/Api/IPC/Bans', { method:'DELETE' });
        toast('IPC bans cleared');
        await render();
      } catch (error) {
        toast('Could not clear bans', error.message, 'bad', 7000);
      }
    });

    $('copyNativeBotConfig')?.addEventListener('click', async () => {
      const button = $('copyNativeBotConfig');
      button.disabled = true;
      try {
        const source = state.selectedBot;
        const target = String($('nativeCopyBotName').value || '').trim() || nextBotName();
        if (!source) throw new Error('No source bot selected.');
        if (state.accounts.some((account) => String(account.BotName).toLowerCase() === target.toLowerCase())) throw new Error(`ASF bot ID ${target} already exists.`);
        const record = await getBotRecord(source);
        const copy = { ...redactBotConfigForEditor(record.BotConfig), Enabled:false };
        await writeBotConfig(target, copy);
        await sleep(250);
        await loadAccounts();
        state.selectedBot = target;
        toast('Bot config copied', `${source} → ${target}. Credentials were not copied.`);
        await render();
      } catch (error) {
        toast('Bot config copy failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('runNativeEncrypt')?.addEventListener('click', async () => {
      const button = $('runNativeEncrypt');
      button.disabled = true;
      try {
        const value = String($('nativeCryptoInput').value || '');
        if (!value) throw new Error('Input is required.');
        const result = await api('/Api/ASF/Encrypt', { method:'POST', body:JSON.stringify({ CryptoMethod:Number($('nativeCryptoMethod').value), StringToEncrypt:value }) });
        $('nativeCryptoOutput').value = String(result ?? '');
      } catch (error) {
        toast('Encryption failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('runNativeHash')?.addEventListener('click', async () => {
      const button = $('runNativeHash');
      button.disabled = true;
      try {
        const value = String($('nativeCryptoInput').value || '');
        if (!value) throw new Error('Input is required.');
        const result = await api('/Api/ASF/Hash', { method:'POST', body:JSON.stringify({ HashingMethod:Number($('nativeHashMethod').value), StringToHash:value }) });
        $('nativeCryptoOutput').value = String(result ?? '');
      } catch (error) {
        toast('Hashing failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('refreshNativeLog')?.addEventListener('click', async () => {
      const button = $('refreshNativeLog');
      button.disabled = true;
      try {
        const result = await api('/Api/NLog/File?count=250');
        const lines = Array.isArray(result?.Content) ? result.Content : [];
        $('nativeLogTail').value = lines.join('\n');
        toast('Log refreshed', `${lines.length} of ${result?.TotalLines ?? lines.length} line(s)`);
      } catch (error) {
        toast('Log refresh failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('applyNativeMassPatch')?.addEventListener('click', async () => {
      const button = $('applyNativeMassPatch');
      button.disabled = true;
      try {
        const patch = JSON.parse($('nativeMassPatch').value);
        assertNoSensitiveBotPatch(patch);
        const bots = [...document.querySelectorAll('[data-mass-bot]:checked')].map((box) => box.value);
        if (!bots.length) throw new Error('Select at least one bot.');

        const originals = new Map();
        const updates = new Map();
        for (const bot of bots) {
          const record = await getBotRecord(bot);
          originals.set(bot, cloneJson(record.BotConfig));
          updates.set(bot, mergePatch(record.BotConfig, patch));
        }

        const applied = [];
        try {
          for (const bot of bots) {
            await writeBotConfig(bot, updates.get(bot));
            applied.push(bot);
          }
        } catch (writeError) {
          const rollbackFailures = [];
          for (const bot of [...applied].reverse()) {
            try { await writeBotConfig(bot, originals.get(bot)); }
            catch (_) { rollbackFailures.push(bot); }
          }
          const suffix = rollbackFailures.length ? ` Rollback also failed for: ${rollbackFailures.join(', ')}.` : ' Earlier writes were rolled back.';
          throw new Error(`${writeError.message}.${suffix}`);
        }

        await loadAccounts();
        toast('Mass edit complete', `${bots.length} bot(s) updated.`);
        await render();
      } catch (error) {
        toast('Mass edit failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    const lockMinutes = $('lockMinutes');
    if (lockMinutes) lockMinutes.addEventListener('change', () => { state.lockMinutes = Core.normalizeLockMinutes(lockMinutes.value, DEFAULT_LOCK_MINUTES); sessionStorage.setItem(LOCK_KEY, String(state.lockMinutes)); markActivity(); startLockWatch(); toast('Auto-lock updated', state.lockMinutes ? `${state.lockMinutes} minute(s)` : 'disabled for this tab'); });
    $('lockNow')?.addEventListener('click', () => lockSession());
    $('restartAsf')?.addEventListener('click', async () => { try { await nativeProcessAction('Restart', 'RESTART'); } catch (error) { toast('Restart failed', error.message, 'bad'); } });
    $('exitAsf')?.addEventListener('click', async () => { try { await nativeProcessAction('Exit', 'EXIT'); } catch (error) { toast('Exit failed', error.message, 'bad'); } });
  }

  function updateNav() {
    document.querySelectorAll('#nav button').forEach((button) => button.classList.toggle('active', button.dataset.view === state.view));
    sessionStorage.setItem(VIEW_KEY, state.view);
  }

  for (const eventName of ['pointerdown','keydown','touchstart']) window.addEventListener(eventName, markActivity, { passive:true });
  wireModal();
  $('togglePassword').addEventListener('click', () => { const input = $('password'); const show = input.type === 'password'; input.type = show ? 'text' : 'password'; $('togglePassword').textContent = show ? 'Hide' : 'Show'; $('togglePassword').setAttribute('aria-label', show ? 'Hide password' : 'Show password'); });
  $('authForm').addEventListener('submit', async (event) => { event.preventDefault(); $('authError').textContent = ''; const submit = $('authForm').querySelector('button[type="submit"]'); submit.disabled = true; try { await authenticate($('password').value); } catch (error) { state.password = ''; showAuth(error.message); } finally { submit.disabled = false; } });
  $('nav').addEventListener('click', async (event) => { const button = event.target.closest('[data-view]'); if (!button) return; state.view = button.dataset.view; updateNav(); await render(); });
  $('logout').addEventListener('click', () => lockSession());
  $('refreshView').addEventListener('click', async () => { const button = $('refreshView'); button.disabled = true; try { await loadAccounts(); await render(); toast('Refreshed', VIEW_META[state.view][0]); } catch (error) { toast('Refresh failed', error.message, 'bad'); } finally { button.disabled = false; } });

  updateNav();
  showAuth();
})();
