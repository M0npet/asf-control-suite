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
    security: ['Security', 'Session controls and the authentication boundary.'],
    system: ['System', 'Runtime health, modules and native ASF process actions.'],
    advanced: ['ASF', 'Native ASF configuration and tools without leaving Control Suite.'],
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
    advancedTab: sessionStorage.getItem('asf.control.advancedTab') || 'bot-config',
    commandLog: [],
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


  const NATIVE_SECRET_FIELDS = new Set([
    'SteamPassword',
    'SteamParentalCode',
    'WebProxyPassword',
    'IPCPassword',
    'LicenseID',
    'SteamTradeToken',
  ]);
  const BOT_CONFIG_CATEGORIES = Object.freeze([
    ['Basic', ['Name','SteamLogin','SteamPassword','Enabled','OnlineStatus','BotBehaviour']],
    ['Security', ['PasswordFormat','UseLoginKeys']],
    ['Access', ['SteamUserPermissions','SteamParentalCode']],
    ['Connection', ['WebProxy','WebProxyUsername','WebProxyPassword']],
    ['Trading', ['SteamTradeToken','AcceptGifts','TradeCheckPeriod','SendTradePeriod','CompleteTypesToSend','TradingPreferences','LootableTypes','TransferableTypes','MatchableTypes']],
    ['Farming', ['FarmingPreferences','FarmingOrders','HoursUntilCardDrops']],
    ['Customization', ['RemoteCommunication','SteamMasterClanID','UserInterfaceMode','GamingDeviceType','MachineName','OnlinePreferences','OnlineFlags','RedeemingPreferences','GamesPlayedWhileIdle','CustomGamePlayedWhileFarming','CustomGamePlayedWhileIdle']],
  ]);
  const ASF_CONFIG_CATEGORIES = Object.freeze([
    ['Basic', ['SteamOwnerID']],
    ['Trading', ['MaxTradeHoldDuration','FilterBadBots','LicenseID']],
    ['Customization', ['AutoRestart','Blacklist','CommandPrefix','CurrentCulture','SteamMessagePrefix']],
    ['Remote access', ['Headless','IPC','IPCPassword','IPCPasswordFormat']],
    ['Connection', ['ConnectionTimeout','SteamProtocols','WebProxy','WebProxyPassword','WebProxyUsername']],
    ['Farming', ['FarmingDelay','IdleFarmingPeriod','MaxFarmingTime','MinFarmingDelayAfterBlock','ShutdownIfPossible']],
    ['Performance', ['OptimizationMode','ConfirmationsLimiterDelay','GiftsLimiterDelay','InventoryLimiterDelay','LoginLimiterDelay','WebLimiterDelay']],
    ['Updates', ['UpdateChannel','UpdatePeriod']],
    ['Plugins', ['PluginsUpdateMode','PluginsUpdateList']],
    ['Advanced', ['Debug','DefaultBot']],
  ]);
  const typeDefinitionCache = new Map();
  const structureDefinitionCache = new Map();
  const nativeSchemaCache = new Map();
  const subtypeRegex = /\[[^\]]+]/g;

  function nativeSubtypes(type) {
    const matches = String(type || '').match(subtypeRegex);
    return matches ? matches.map((item) => item.slice(1, -1)) : [];
  }

  async function nativeTypeDefinition(type) {
    if (!typeDefinitionCache.has(type)) {
      typeDefinitionCache.set(type, api(`/Api/Type/${encodeURIComponent(type)}`));
    }
    return typeDefinitionCache.get(type);
  }

  async function nativeStructureDefinition(type) {
    if (!structureDefinitionCache.has(type)) {
      structureDefinitionCache.set(type, api(`/Api/Structure/${encodeURIComponent(type)}`));
    }
    return structureDefinitionCache.get(type);
  }

  function nativeEnumValues(values = {}) {
    return Object.fromEntries(Object.entries(values).map(([name, value]) => [name, Number(value)]));
  }

  async function resolveNativeType(targetType) {
    const subtypes = nativeSubtypes(targetType);
    switch (String(targetType).split('`')[0]) {
      case 'System.Boolean': return { type:'boolean' };
      case 'System.String':
      case 'System.Guid': return { type:'string' };
      case 'System.Byte': return { type:'byte' };
      case 'System.UInt16': return { type:'uint16' };
      case 'System.UInt32': return { type:'uint32' };
      case 'System.UInt64': return { type:'uint64' };
      case 'System.Collections.Generic.HashSet':
      case 'System.Collections.Immutable.ImmutableHashSet':
        return { type:'hashSet', values:await resolveNativeType(subtypes[0]) };
      case 'System.Collections.Immutable.ImmutableList':
      case 'System.Collections.Generic.List':
        return { type:'list', values:await resolveNativeType(subtypes[0]) };
      case 'System.Collections.Generic.Dictionary':
      case 'System.Collections.Immutable.ImmutableDictionary':
        return { type:'dictionary', key:await resolveNativeType(subtypes[0]), value:await resolveNativeType(subtypes[1]) };
      case 'System.Nullable': {
        const resolved = await resolveNativeType(subtypes[0]);
        return { ...resolved, nullable:true };
      }
      default: {
        const definition = await nativeTypeDefinition(targetType);
        const baseType = definition?.Properties?.BaseType;
        if (baseType === 'System.Enum') {
          const flags = (definition?.Properties?.CustomAttributes || []).includes('System.FlagsAttribute');
          return { type:flags ? 'flag' : 'enum', values:nativeEnumValues(definition?.Body || {}) };
        }
        if (baseType === 'System.Object') return { type:'object' };
        return { type:'unknown' };
      }
    }
  }

  async function loadNativeConfigSchema(typeName) {
    if (nativeSchemaCache.has(typeName)) return nativeSchemaCache.get(typeName);
    const promise = (async () => {
      const [definition, defaults] = await Promise.all([
        nativeTypeDefinition(typeName),
        nativeStructureDefinition(typeName),
      ]);
      const body = definition?.Body || {};
      return Promise.all(Object.keys(body).map(async (param) => {
        const rawType = body[param];
        const resolved = await resolveNativeType(rawType);
        return {
          param,
          paramName: rawType === 'System.UInt64' ? `s_${param}` : param,
          defaultValue: defaults?.[param],
          rawType,
          ...resolved,
        };
      }));
    })();
    nativeSchemaCache.set(typeName, promise);
    return promise;
  }

  function fieldValue(model, field) {
    if (Object.prototype.hasOwnProperty.call(model || {}, field.paramName)) return model[field.paramName];
    if (Object.prototype.hasOwnProperty.call(model || {}, field.param)) return model[field.param];
    return field.defaultValue;
  }

  function renderNativeField(field, model) {
    const value = fieldValue(model, field);
    const name = field.paramName;
    const secret = NATIVE_SECRET_FIELDS.has(field.param);
    const id = `native-${name.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
    const meta = `<small class="field-help">${escapeHtml(field.rawType || field.type)}</small>`;
    if (field.type === 'boolean') {
      return `<label class="native-field checkline"><input id="${id}" type="checkbox" data-native-field="${escapeHtml(name)}" data-native-type="boolean" ${value ? 'checked' : ''}> <span><strong>${escapeHtml(field.param)}</strong>${meta}</span></label>`;
    }
    if (field.type === 'enum') {
      const options = Object.entries(field.values || {}).sort((a,b) => a[1]-b[1]).map(([label, number]) => `<option value="${number}" ${Number(value) === Number(number) ? 'selected' : ''}>${escapeHtml(label)} · ${number}</option>`).join('');
      return `<label class="native-field" for="${id}"><strong>${escapeHtml(field.param)}</strong><select id="${id}" data-native-field="${escapeHtml(name)}" data-native-type="enum">${options}</select>${meta}</label>`;
    }
    if (field.type === 'flag') {
      const numeric = Number(value || 0);
      const flags = Object.entries(field.values || {}).filter(([,number]) => Number(number) > 0).sort((a,b) => a[1]-b[1]).map(([label, number]) => `<label class="flag-option"><input type="checkbox" data-native-flag-option="${escapeHtml(name)}" value="${number}" ${(numeric & Number(number)) === Number(number) ? 'checked' : ''}> ${escapeHtml(label)}</label>`).join('');
      return `<div class="native-field"><strong>${escapeHtml(field.param)}</strong><input id="${id}" type="number" step="1" data-native-field="${escapeHtml(name)}" data-native-type="flag" value="${numeric}" aria-label="${escapeHtml(field.param)} numeric flags">${meta}<div class="flag-grid">${flags}</div></div>`;
    }
    if (['byte','uint16','uint32'].includes(field.type)) {
      return `<label class="native-field" for="${id}"><strong>${escapeHtml(field.param)}</strong><input id="${id}" type="number" min="0" step="1" data-native-field="${escapeHtml(name)}" data-native-type="${field.type}" value="${escapeHtml(value ?? '')}">${meta}</label>`;
    }
    if (field.type === 'uint64') {
      return `<label class="native-field" for="${id}"><strong>${escapeHtml(field.param)}</strong><input id="${id}" type="text" inputmode="numeric" pattern="[0-9]*" data-native-field="${escapeHtml(name)}" data-native-type="uint64" value="${escapeHtml(value ?? '')}">${meta}</label>`;
    }
    if (['hashSet','list','dictionary','object','unknown'].includes(field.type)) {
      const fallback = field.type === 'dictionary' || field.type === 'object' ? {} : [];
      const json = JSON.stringify(value ?? fallback, null, 2);
      return `<label class="native-field native-field-wide" for="${id}"><strong>${escapeHtml(field.param)}</strong><textarea id="${id}" rows="4" spellcheck="false" data-native-field="${escapeHtml(name)}" data-native-type="${field.type}">${escapeHtml(json)}</textarea>${meta}</label>`;
    }
    return `<label class="native-field" for="${id}"><strong>${escapeHtml(field.param)}</strong><input id="${id}" type="${secret ? 'password' : 'text'}" data-native-field="${escapeHtml(name)}" data-native-param="${escapeHtml(field.param)}" data-native-type="string" data-native-secret="${secret ? '1' : '0'}" value="${secret ? '' : escapeHtml(value ?? '')}" placeholder="${secret ? 'Keep unchanged unless entered' : ''}" autocomplete="off">${meta}</label>`;
  }

  function categorizedNativeFields(schema, model, categories) {
    const byParam = new Map(schema.map((field) => [field.param, field]));
    const used = new Set();
    const sections = categories.map(([name, params]) => {
      const fields = params.map((param) => byParam.get(param)).filter(Boolean);
      fields.forEach((field) => used.add(field.param));
      return fields.length ? `<section class="native-config-section"><h4>${escapeHtml(name)}</h4><div class="native-config-grid">${fields.map((field) => renderNativeField(field, model)).join('')}</div></section>` : '';
    }).join('');
    const other = schema.filter((field) => !used.has(field.param)).sort((a,b) => a.param.localeCompare(b.param));
    return sections + (other.length ? `<section class="native-config-section"><h4>Other</h4><div class="native-config-grid">${other.map((field) => renderNativeField(field, model)).join('')}</div></section>` : '');
  }

  function readNativeConfigEditor(baseConfig) {
    const next = JSON.parse(JSON.stringify(baseConfig || {}));
    document.querySelectorAll('[data-native-field]').forEach((input) => {
      const name = input.dataset.nativeField;
      const type = input.dataset.nativeType;
      if (input.dataset.nativeSecret === '1' && String(input.value || '') === '') return;
      if (name.startsWith('s_')) delete next[name.slice(2)];
      let value;
      if (type === 'boolean') value = input.checked;
      else if (['byte','uint16','uint32','enum','flag'].includes(type)) {
        if (String(input.value).trim() === '') return;
        value = Number(input.value);
        if (!Number.isFinite(value)) throw new Error(`Invalid numeric value for ${name}`);
      } else if (type === 'uint64') {
        value = String(input.value || '').trim();
        if (value && !/^\d+$/.test(value)) throw new Error(`Invalid UInt64 value for ${name}`);
      } else if (['hashSet','list','dictionary','object','unknown'].includes(type)) {
        value = JSON.parse(input.value || (type === 'dictionary' || type === 'object' ? '{}' : '[]'));
      } else value = input.value;
      next[name] = value;
    });
    return next;
  }

  function parseBgrKeys(text) {
    const keyPattern = /[0-9A-Z]{4,7}(?:-[0-9A-Z]{4,7}){2,4}/;
    const result = {};
    for (const raw of String(text || '').split(/\r?\n/)) {
      const line = raw.trim();
      if (!line) continue;
      const match = line.match(keyPattern);
      if (!match) continue;
      const key = match[0];
      const label = line.replace(key, '').replace(/^\s*[:;|,\-]\s*/, '').replace(/\s*[:;|,\-]\s*$/, '').trim();
      result[key] = label || key;
    }
    return result;
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
    await api(`/Api/Bot/${encodeURIComponent(botName)}`, { method:'POST', body:JSON.stringify({ BotConfig:botConfig }) });
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
    await sleep(350);
    await loadAccounts();
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
    return `<div class="card account-workspace section"><div class="card-head"><div>${accountIdentityMarkup(summary, { large:true })}<div class="workspace-title"><span class="pill ${statusTone}">${escapeHtml(statusLabel)}</span><span class="workspace-steamid">Steam ${escapeHtml(summary.SteamId || 'unknown')}</span></div></div><div class="actions"><button data-act="goals" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">Open goals</button><button data-act="${summary.KeepRunning ? 'stop' : 'start'}" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">${summary.KeepRunning ? 'Stop' : 'Start'}</button><button data-act="${summary.FarmerPaused ? 'resume' : 'pause'}" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">${summary.FarmerPaused ? 'Resume' : 'Pause'}</button><button data-act="rename" data-bot="${escapeHtml(state.selectedBot)}" class="secondary">Rename ASF ID</button><button id="toggleConfigEnabled" class="secondary">${summary.Enabled ? 'Disable config' : 'Enable config'}</button></div></div><div class="grid compact-grid"><div class="metric"><span>Keep running</span><strong>${yesNo(summary.KeepRunning)}</strong></div><div class="metric"><span>Playing</span><strong>${summary.IsPlayingPossible ? 'possible' : 'blocked'}</strong></div><div class="metric"><span>CardsFarmer</span><strong>${summary.Farming ? 'active' : summary.FarmerPaused ? 'paused' : 'idle'}</strong></div><div class="metric"><span>Authenticator</span><strong>${yesNo(summary.HasMobileAuthenticator)}</strong></div></div><div class="card section native-settings"><div class="card-head"><div><h3>Steam / ASF settings</h3><p>Common native ASF settings here; the full native editor is built into Control Suite.</p></div><span class="pill neutral">native</span></div><div class="settings-grid"><label for="onlineStatus">Steam persona status<select id="onlineStatus" ${personaDisabled}>${personaOptions}</select></label><div><span class="field-help">${onlineStatus == null ? 'Native BotConfig is temporarily unavailable.' : 'Invisible keeps ASF connected while your Steam persona appears offline to friends.'}</span><button id="saveOnlineStatus" class="secondary" type="button" ${personaDisabled}>Save Steam status</button></div></div><div class="actions section"><button class="secondary" type="button" data-native-jump="bot-config">Full bot config</button><button class="secondary" type="button" data-native-jump="2fa">2FA</button><button class="secondary" type="button" data-native-jump="bgr">Background redeemer</button><button class="secondary" type="button" data-native-jump="commands">Commands</button><button class="secondary" type="button" data-native-jump="log">Log</button></div></div>${inputForm}</div>`;
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


  function nativeBotOptions() {
    return state.accounts.map((account) => `<option value="${escapeHtml(account.BotName)}" ${account.BotName === state.selectedBot ? 'selected' : ''}>${escapeHtml(accountOptionLabel(account))}</option>`).join('');
  }

  function nativeTabsMarkup() {
    const tabs = [
      ['bot-config','Bot config'],
      ['2fa','2FA'],
      ['bgr','BGR'],
      ['commands','Commands'],
      ['log','Log'],
      ['asf-config','ASF config'],
      ['bans','Bans'],
      ['mass-editor','Mass editor'],
      ['plugins','Plugins'],
      ['releases','Releases'],
      ['diagnostics','Diagnostics'],
    ];
    return `<div class="native-tabs" role="tablist" aria-label="Native ASF tools">${tabs.map(([id,label]) => `<button type="button" data-advanced-tab="${id}" class="${state.advancedTab === id ? 'active' : ''}" role="tab" aria-selected="${state.advancedTab === id ? 'true' : 'false'}">${label}</button>`).join('')}</div>`;
  }

  function botEnvelope(result, botName) {
    const entry = result?.[botName] || Object.values(result || {})[0];
    if (!entry) return null;
    if (entry.Success === false) throw new Error(entry.Message || `ASF action failed for ${botName}`);
    return Object.prototype.hasOwnProperty.call(entry, 'Result') ? entry.Result : entry;
  }

  async function renderNativeBotConfigTab() {
    if (!state.selectedBot && state.accounts.length) state.selectedBot = state.accounts[0].BotName;
    if (!state.selectedBot) return '<div class="empty-state"><strong>No account available</strong>Add an ASF account first.</div>';
    const [record, schema] = await Promise.all([
      getBotRecord(state.selectedBot),
      loadNativeConfigSchema('ArchiSteamFarm.Steam.Storage.BotConfig'),
    ]);
    return `<div class="toolbar"><select id="nativeBotSelect" aria-label="ASF account">${nativeBotOptions()}</select><span class="pill good">native BotConfig</span></div><div class="card section"><div class="card-head"><div><h3>Full bot configuration</h3><p>Every native BotConfig field is editable here. Secret fields are write-only and remain unchanged when left blank.</p></div><button id="saveNativeBotConfig">Save bot config</button></div><div id="nativeConfigEditor" class="native-config-editor">${categorizedNativeFields(schema, record.BotConfig, BOT_CONFIG_CATEGORIES)}</div></div>`;
  }

  async function renderNativeTwoFactorTab() {
    if (!state.selectedBot && state.accounts.length) state.selectedBot = state.accounts[0].BotName;
    if (!state.selectedBot) return '<div class="empty-state"><strong>No account available</strong>Add an ASF account first.</div>';
    const account = state.accounts.find((item) => item.BotName === state.selectedBot);
    let token = '-----';
    let tokenError = '';
    if (account?.HasMobileAuthenticator) {
      try {
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Token`);
        token = String(botEnvelope(result, state.selectedBot) || '-----');
      } catch (error) {
        tokenError = error.message;
      }
    }
    return `<div class="toolbar"><select id="nativeBotSelect" aria-label="ASF account">${nativeBotOptions()}</select><span class="pill ${account?.HasMobileAuthenticator ? 'good' : 'neutral'}">${account?.HasMobileAuthenticator ? 'authenticator active' : 'no authenticator'}</span></div><div class="two-col section"><div class="card"><div class="card-head"><div><h3>Steam Guard 2FA</h3><p>Generate a token and handle mobile confirmations through native ASF.</p></div></div>${tokenError ? `<div class="notice bad">${escapeHtml(tokenError)}</div>` : ''}<div class="token-display">${escapeHtml(token)}</div><div class="actions section"><button id="refresh2fa" class="secondary">Refresh token</button><button id="accept2fa">Accept confirmations</button><button id="reject2fa" class="secondary">Reject confirmations</button></div>${account?.HasMobileAuthenticator ? '<button id="delete2fa" class="danger">Delete authenticator</button>' : ''}</div><div class="card"><div class="card-head"><div><h3>Import authenticator</h3><p>Import a Steam .maFile into the selected ASF bot.</p></div></div><label for="import2faFile">Authenticator file<input id="import2faFile" type="file" accept=".maFile,application/json"></label><button id="import2fa" class="section">Import authenticator</button></div></div>`;
  }

  async function renderNativeBgrTab() {
    if (!state.selectedBot && state.accounts.length) state.selectedBot = state.accounts[0].BotName;
    if (!state.selectedBot) return '<div class="empty-state"><strong>No account available</strong>Add an ASF account first.</div>';
    let data = { UnusedKeys:{}, UsedKeys:{} };
    try {
      const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/GamesToRedeemInBackground`);
      data = result?.[state.selectedBot] || Object.values(result || {})[0] || data;
    } catch (_) { /* render empty state and allow adding */ }
    const used = Object.entries(data.UsedKeys || {});
    const unused = Object.entries(data.UnusedKeys || {});
    const rows = (items, empty) => items.length ? items.map(([key,name]) => `<div class="row"><div class="row-main"><strong>${escapeHtml(name || key)}</strong><small>${escapeHtml(key)}</small></div></div>`).join('') : `<div class="empty-state">${empty}</div>`;
    return `<div class="toolbar"><select id="nativeBotSelect" aria-label="ASF account">${nativeBotOptions()}</select><span class="pill neutral">${used.length + unused.length} queued/history</span></div><div class="card section"><div class="card-head"><div><h3>Background game redeemer</h3><p>Add Steam keys to ASF's persistent background redemption queue.</p></div><button id="resetBgr" class="secondary">Reset BGR</button></div><label for="bgrKeys">Keys<textarea id="bgrKeys" rows="8" spellcheck="false" placeholder="AAAAA-BBBBB-CCCCC Game name"></textarea></label><button id="addBgr" class="section">Add keys</button></div><div class="two-col section"><div class="card"><div class="card-head"><h3>Unused keys</h3></div>${rows(unused,'No unused keys.')}</div><div class="card"><div class="card-head"><h3>Used keys</h3></div>${rows(used,'No used keys.')}</div></div>`;
  }

  async function renderNativeCommandsTab() {
    const rows = state.commandLog.length ? state.commandLog.map((entry) => `<div class="command-line ${entry.type}"><span>${entry.type === 'out' ? '>' : '<'}</span><pre>${escapeHtml(entry.text)}</pre></div>`).join('') : '<div class="empty-state">Run any native ASF command here.</div>';
    return `<div class="card"><div class="card-head"><div><h3>ASF command console</h3><p>Commands are sent to the native authenticated /Api/Command endpoint.</p></div><button id="clearCommands" class="secondary">Clear</button></div><div id="commandTerminal" class="native-terminal">${rows}</div><form id="nativeCommandForm" class="inline-form section"><label class="sr-only" for="nativeCommand">ASF command</label><input id="nativeCommand" autocomplete="off" spellcheck="false" placeholder="status ASF" required><button type="submit">Run command</button></form></div>`;
  }

  async function renderNativeLogTab() {
    const result = await api('/Api/NLog/File?count=200');
    const lines = result?.Content || [];
    return `<div class="card"><div class="card-head"><div><h3>ASF log</h3><p>Latest ${lines.length} lines loaded through the authenticated native log API.</p></div><div class="actions"><button id="refreshNativeLog" class="secondary">Refresh</button><button id="downloadNativeLog" class="secondary">Download full log</button></div></div><pre id="nativeLog" class="native-log">${escapeHtml(lines.join('\n'))}</pre></div>`;
  }

  async function renderNativeAsfConfigTab() {
    const [asf, schema] = await Promise.all([
      api('/Api/ASF'),
      loadNativeConfigSchema('ArchiSteamFarm.Storage.GlobalConfig'),
    ]);
    return `<div class="notice warn">Saving global ASF config can restart ASF. IPCPassword and other sensitive values are never prefilled by Control Suite.</div><div class="card section"><div class="card-head"><div><h3>Global ASF configuration</h3><p>Schema-driven editor for the complete native GlobalConfig.</p></div><button id="saveNativeAsfConfig">Save ASF config</button></div><div id="nativeConfigEditor" class="native-config-editor">${categorizedNativeFields(schema, asf?.GlobalConfig || {}, ASF_CONFIG_CATEGORIES)}</div></div>`;
  }

  async function renderNativeBansTab() {
    const bans = await api('/Api/IPC/Bans') || [];
    return `<div class="card"><div class="card-head"><div><h3>IPC bans</h3><p>Addresses blocked by ASF after repeated authentication failures.</p></div><button id="clearAllBans" class="secondary" ${bans.length ? '' : 'disabled'}>Remove all bans</button></div><div class="ban-grid section">${bans.length ? bans.map((ip) => `<div class="ban-card"><code>${escapeHtml(ip)}</code><button class="secondary" data-remove-ban="${escapeHtml(ip)}">Remove</button></div>`).join('') : '<div class="empty-state">No banned IP addresses.</div>'}</div></div>`;
  }

  async function renderNativeMassEditorTab() {
    const schema = await loadNativeConfigSchema('ArchiSteamFarm.Steam.Storage.BotConfig');
    const names = schema.map((field) => field.paramName).sort();
    return `<div class="card"><div class="card-head"><div><h3>Mass editor</h3><p>Merge a JSON patch into the selected bots. Any native BotConfig field is supported.</p></div></div><div class="mass-bots section">${state.accounts.map((account) => `<label class="checkline"><input type="checkbox" data-mass-bot="${escapeHtml(account.BotName)}"> ${escapeHtml(accountOptionLabel(account))}</label>`).join('') || '<div class="empty-state">No bots available.</div>'}</div><label for="massPatch">BotConfig patch<textarea id="massPatch" rows="10" spellcheck="false" placeholder='{"OnlineStatus":7}'></textarea></label><details class="section"><summary>Available native fields</summary><div class="tag-cloud">${names.map((name) => `<code>${escapeHtml(name)}</code>`).join('')}</div></details><button id="applyMassPatch" class="section">Apply to selected bots</button></div>`;
  }

  async function renderNativePluginsTab() {
    const [official, custom] = await Promise.all([
      api('/Api/Plugins?official=true&custom=false'),
      api('/Api/Plugins?official=false&custom=true'),
    ]);
    const rows = [
      ...(official || []).map((plugin) => ({...plugin, kind:'official'})),
      ...(custom || []).map((plugin) => ({...plugin, kind:'custom'})),
    ].sort((a,b) => String(a.Name || '').localeCompare(String(b.Name || '')));
    return `<div class="card"><div class="card-head"><div><h3>Loaded plugins</h3><p>Native ASF plugin inventory.</p></div><span class="pill neutral">${rows.length}</span></div>${rows.length ? rows.map((plugin) => `<div class="row"><div class="row-main"><strong>${escapeHtml(plugin.Name || 'Unknown plugin')}</strong><small>${escapeHtml(plugin.Version || 'unknown version')}</small></div><span class="pill ${plugin.kind === 'official' ? 'good' : 'neutral'}">${plugin.kind}</span></div>`).join('') : '<div class="empty-state">No plugins reported by ASF.</div>'}</div>`;
  }

  async function renderNativeReleasesTab() {
    const asf = await api('/Api/ASF');
    const requests = await Promise.allSettled([
      api('/Api/WWW/GitHub/Release/'),
      api('/Api/WWW/GitHub/Release/latest'),
      api(`/Api/WWW/GitHub/Release/${encodeURIComponent(asf?.Version || '')}`),
    ]);
    const releases = [];
    for (const request of requests) {
      if (request.status !== 'fulfilled' || !request.value?.Version) continue;
      if (!releases.some((item) => item.Version === request.value.Version)) releases.push(request.value);
    }
    const rows = releases.map((release) => `<div class="row release-row"><div class="row-main"><strong>ASF ${escapeHtml(release.Version)}</strong><small>${release.Stable ? 'stable' : 'pre-release'} · ${escapeHtml(release.ReleasedAt || '')}</small></div><span class="pill ${release.Stable ? 'good' : 'warn'}">${release.Stable ? 'stable' : 'pre'}</span></div>`).join('');
    return `<div class="notice warn">Control Suite is pinned to ASF ${escapeHtml(asf?.Version || 'unknown')}. Native self-update can break compatibility with the Control Suite patch and plugins.</div><div class="card section"><div class="card-head"><div><h3>ASF releases</h3><p>Release information from ASF's native GitHub proxy.</p></div>${asf?.CanUpdate ? '<button id="nativeAsfUpdate" class="warning">Native ASF update</button>' : ''}</div>${rows || '<div class="empty-state">Release data unavailable.</div>'}</div>`;
  }

  async function renderNativeDiagnosticsTab() {
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
    return `<div class="two-col"><div class="card"><div class="card-head"><div><h3>Pinned compatibility</h3><p>Control Suite ${escapeHtml(suiteVersion)} is built against a fixed baseline.</p></div></div><div class="row"><div class="row-main"><strong>ASF</strong><small>${escapeHtml(asfVersion)} · ${escapeHtml(asfCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>ASF compatibility patch</strong><small>SHA-256 · ${escapeHtml(asfPatch)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>ASF-ui</strong><small>${escapeHtml(asfUiCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>PlaytimeGoals</strong><small>${escapeHtml(ptgVersion)} · ${escapeHtml(ptgCommit)}</small></div><span class="pill good">pinned</span></div><div class="row"><div class="row-main"><strong>Control modules</strong><small>AccountManager · ControlCenter · ControlWeb</small></div><span class="pill good">${escapeHtml(moduleVersion)}</span></div></div><div class="card"><div class="card-head"><div><h3>Compatibility fallback</h3><p>The old ASF-ui is kept only as an emergency escape hatch while parity is field-tested.</p></div></div><div class="actions"><a href="/swagger" target="_blank" rel="noreferrer"><button class="secondary" type="button">Open API docs</button></a><a href="${legacyAsfHref('/bots')}"><button class="secondary" type="button">Emergency legacy ASF-ui</button></a></div></div></div>`;
  }

  async function renderAdvanced() {
    let body;
    switch (state.advancedTab) {
      case '2fa': body = await renderNativeTwoFactorTab(); break;
      case 'bgr': body = await renderNativeBgrTab(); break;
      case 'commands': body = await renderNativeCommandsTab(); break;
      case 'log': body = await renderNativeLogTab(); break;
      case 'asf-config': body = await renderNativeAsfConfigTab(); break;
      case 'bans': body = await renderNativeBansTab(); break;
      case 'mass-editor': body = await renderNativeMassEditorTab(); break;
      case 'plugins': body = await renderNativePluginsTab(); break;
      case 'releases': body = await renderNativeReleasesTab(); break;
      case 'diagnostics': body = await renderNativeDiagnosticsTab(); break;
      case 'bot-config':
      default:
        state.advancedTab = 'bot-config';
        body = await renderNativeBotConfigTab();
        break;
    }
    return `${nativeTabsMarkup()}<div class="native-tab-content section">${body}</div>`;
  }

  const renderers = { dashboard:renderDashboard, accounts:renderAccounts, playtime:renderPlaytime, security:renderSecurity, system:renderSystem, advanced:renderAdvanced };

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
    document.querySelectorAll('[data-view-jump]').forEach((button) => button.addEventListener('click', async () => { state.view = button.dataset.viewJump; updateNav(); await render(); }));
    document.querySelectorAll('[data-native-jump]').forEach((button) => button.addEventListener('click', async () => {
      state.view = 'advanced';
      state.advancedTab = button.dataset.nativeJump || 'bot-config';
      sessionStorage.setItem('asf.control.advancedTab', state.advancedTab);
      updateNav();
      await render();
    }));
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

    document.querySelectorAll('[data-advanced-tab]').forEach((button) => button.addEventListener('click', async () => {
      state.advancedTab = button.dataset.advancedTab || 'bot-config';
      sessionStorage.setItem('asf.control.advancedTab', state.advancedTab);
      await render();
    }));

    const nativeBotSelect = $('nativeBotSelect');
    if (nativeBotSelect) nativeBotSelect.addEventListener('change', async () => {
      state.selectedBot = nativeBotSelect.value;
      await render();
    });

    document.querySelectorAll('[data-native-flag-option]').forEach((box) => box.addEventListener('change', () => {
      const name = box.dataset.nativeFlagOption;
      const raw = document.querySelector(`[data-native-field="${CSS.escape(name)}"][data-native-type="flag"]`);
      if (!raw) return;
      let total = 0;
      document.querySelectorAll(`[data-native-flag-option="${CSS.escape(name)}"]`).forEach((option) => {
        if (option.checked) total |= Number(option.value || 0);
      });
      raw.value = String(total);
    }));

    document.querySelectorAll('[data-native-field][data-native-type="flag"]').forEach((raw) => raw.addEventListener('input', () => {
      const value = Number(raw.value || 0);
      const name = raw.dataset.nativeField;
      document.querySelectorAll(`[data-native-flag-option="${CSS.escape(name)}"]`).forEach((option) => {
        const bit = Number(option.value || 0);
        option.checked = bit > 0 && (value & bit) === bit;
      });
    }));

    $('saveNativeBotConfig')?.addEventListener('click', async () => {
      const button = $('saveNativeBotConfig');
      button.disabled = true;
      try {
        const record = await getBotRecord(state.selectedBot);
        const next = readNativeConfigEditor(record.BotConfig);
        await writeBotConfig(state.selectedBot, next);
        await sleep(500);
        await loadAccounts();
        toast('Bot config saved', state.selectedBot);
        await render();
      } catch (error) {
        toast('Bot config not saved', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('saveNativeAsfConfig')?.addEventListener('click', async () => {
      const button = $('saveNativeAsfConfig');
      button.disabled = true;
      try {
        const current = await api('/Api/ASF');
        const next = readNativeConfigEditor(current?.GlobalConfig || {});
        await api('/Api/ASF', { method:'POST', body:JSON.stringify({ GlobalConfig:next }) });
        toast('ASF config saved', 'ASF may restart to apply global changes.', 'warn', 7000);
        setConnection(false, 'restarting');
      } catch (error) {
        toast('ASF config not saved', error.message, 'bad', 7000);
        button.disabled = false;
      }
    });

    const commandForm = $('nativeCommandForm');
    if (commandForm) commandForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const input = $('nativeCommand');
      const command = String(input?.value || '').trim();
      if (!command) return;
      const submit = commandForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      state.commandLog.push({ type:'out', text:command });
      input.value = '';
      try {
        const result = await api('/Api/Command', { method:'POST', body:JSON.stringify({ Command:command }) });
        state.commandLog.push({ type:'in', text:String(result ?? '') });
      } catch (error) {
        state.commandLog.push({ type:'in', text:`Error: ${error.message}` });
      } finally {
        submit.disabled = false;
        await render();
        $('nativeCommand')?.focus();
      }
    });
    $('clearCommands')?.addEventListener('click', async () => {
      state.commandLog = [];
      await render();
    });

    $('refreshNativeLog')?.addEventListener('click', async () => render());
    $('downloadNativeLog')?.addEventListener('click', async () => {
      const button = $('downloadNativeLog');
      button.disabled = true;
      try {
        const result = await api('/Api/NLog/File?count=2147483647');
        const content = (result?.Content || []).join('\n') + '\n';
        const blob = new Blob([content], { type:'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'ArchiSteamFarm.log.txt';
        link.click();
        URL.revokeObjectURL(url);
      } catch (error) {
        toast('Log download failed', error.message, 'bad');
      } finally {
        button.disabled = false;
      }
    });

    document.querySelectorAll('[data-remove-ban]').forEach((button) => button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await api(`/Api/IPC/Bans/${encodeURIComponent(button.dataset.removeBan)}`, { method:'DELETE' });
        toast('Ban removed', button.dataset.removeBan);
        await render();
      } catch (error) {
        toast('Ban not removed', error.message, 'bad');
        button.disabled = false;
      }
    }));
    $('clearAllBans')?.addEventListener('click', async () => {
      const button = $('clearAllBans');
      button.disabled = true;
      try {
        await api('/Api/IPC/Bans', { method:'DELETE' });
        toast('All IPC bans removed');
        await render();
      } catch (error) {
        toast('Bans not removed', error.message, 'bad');
        button.disabled = false;
      }
    });

    $('applyMassPatch')?.addEventListener('click', async () => {
      const button = $('applyMassPatch');
      const bots = [...document.querySelectorAll('[data-mass-bot]:checked')].map((box) => box.dataset.massBot);
      if (!bots.length) {
        toast('Mass editor', 'Select at least one bot.', 'warn');
        return;
      }
      button.disabled = true;
      try {
        const patch = JSON.parse($('massPatch').value || '{}');
        if (!patch || Array.isArray(patch) || typeof patch !== 'object') throw new Error('BotConfig patch must be a JSON object');
        for (const bot of bots) {
          const record = await getBotRecord(bot);
          await writeBotConfig(bot, { ...record.BotConfig, ...patch });
        }
        await sleep(500);
        await loadAccounts();
        toast('Mass edit saved', `${bots.length} bot(s) updated.`);
      } catch (error) {
        toast('Mass edit failed', error.message, 'bad', 7000);
      } finally {
        button.disabled = false;
      }
    });

    $('refresh2fa')?.addEventListener('click', async () => render());
    $('accept2fa')?.addEventListener('click', async () => {
      const button = $('accept2fa'); button.disabled = true;
      try {
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Confirmations`, { method:'POST', body:JSON.stringify({ Accept:true }) });
        const handled = botEnvelope(result, state.selectedBot);
        toast('Confirmations accepted', Array.isArray(handled) ? `${handled.length} handled` : 'Native ASF completed the request.');
      } catch (error) { toast('2FA action failed', error.message, 'bad'); }
      finally { button.disabled = false; }
    });
    $('reject2fa')?.addEventListener('click', async () => {
      const button = $('reject2fa'); button.disabled = true;
      try {
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication/Confirmations`, { method:'POST', body:JSON.stringify({ Accept:false }) });
        const handled = botEnvelope(result, state.selectedBot);
        toast('Confirmations rejected', Array.isArray(handled) ? `${handled.length} handled` : 'Native ASF completed the request.');
      } catch (error) { toast('2FA action failed', error.message, 'bad'); }
      finally { button.disabled = false; }
    });
    $('delete2fa')?.addEventListener('click', async () => {
      const values = await openModal({ title:'Delete authenticator', eyebrow:'Permanent action', body:`<p>Remove the ASF mobile authenticator from <strong>${escapeHtml(state.selectedBot)}</strong>.</p>`, confirmLabel:'Delete authenticator', tone:'danger', requireText:'DELETE 2FA' });
      if (!values) return;
      try {
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication`, { method:'DELETE' });
        await sleep(350); await loadAccounts(); toast('Authenticator deleted', state.selectedBot, 'warn'); await render();
      } catch (error) { toast('Authenticator not deleted', error.message, 'bad'); }
    });
    $('import2fa')?.addEventListener('click', async () => {
      const file = $('import2faFile')?.files?.[0];
      if (!file) { toast('Import authenticator', 'Choose a .maFile first.', 'warn'); return; }
      const button = $('import2fa'); button.disabled = true;
      try {
        const parsed = JSON.parse(await file.text());
        const result = await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/TwoFactorAuthentication`, { method:'POST', body:JSON.stringify(parsed) });
        botEnvelope(result, state.selectedBot);
        await sleep(350); await loadAccounts(); toast('Authenticator imported', state.selectedBot); await render();
      } catch (error) { toast('Authenticator import failed', error.message, 'bad', 7000); }
      finally { button.disabled = false; }
    });

    $('addBgr')?.addEventListener('click', async () => {
      const button = $('addBgr'); button.disabled = true;
      try {
        const keys = parseBgrKeys($('bgrKeys')?.value || '');
        if (!Object.keys(keys).length) throw new Error('No valid Steam keys found');
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/GamesToRedeemInBackground`, { method:'POST', body:JSON.stringify({ GamesToRedeemInBackground:keys }) });
        toast('Keys added to BGR', `${Object.keys(keys).length} key(s)`);
        await render();
      } catch (error) { toast('BGR update failed', error.message, 'bad', 7000); }
      finally { button.disabled = false; }
    });
    $('resetBgr')?.addEventListener('click', async () => {
      const values = await openModal({ title:'Reset background redeemer', eyebrow:'Destructive action', body:'<p>Clear used and unused background-redeemer keys for this bot.</p>', confirmLabel:'Reset BGR', tone:'danger', requireText:'RESET BGR' });
      if (!values) return;
      try {
        await api(`/Api/Bot/${encodeURIComponent(state.selectedBot)}/GamesToRedeemInBackground`, { method:'DELETE' });
        toast('BGR reset', state.selectedBot, 'warn');
        await render();
      } catch (error) { toast('BGR reset failed', error.message, 'bad'); }
    });

    $('nativeAsfUpdate')?.addEventListener('click', async () => {
      const values = await openModal({ title:'Native ASF update', eyebrow:'Compatibility warning', body:'<div class="notice bad">Control Suite is built against a pinned ASF commit. Native self-update can invalidate the compatibility patch and plugins. Prefer a new Control Suite release.</div>', confirmLabel:'Update ASF anyway', tone:'danger', requireText:'UPDATE ASF' });
      if (!values) return;
      try {
        await api('/Api/ASF/Update', { method:'POST', body:'{}' });
        setConnection(false, 'restarting');
        toast('Native ASF update requested', 'Compatibility must be re-verified after restart.', 'warn', 9000);
      } catch (error) { toast('ASF update failed', error.message, 'bad'); }
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
