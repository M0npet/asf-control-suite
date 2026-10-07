(() => {
  'use strict';

  const CACHE = new Map();
  const SECRET = new Set(['SteamPassword','SteamParentalCode','IPCPassword','WebProxyPassword','LicenseID']);
  const PRIMITIVE = new Map([
    ['System.Boolean','boolean'], ['System.String','string'], ['System.Guid','string'],
    ['System.Byte','number'], ['System.UInt16','number'], ['System.UInt32','number'], ['System.UInt64','string'],
    ['System.Int16','number'], ['System.Int32','number'], ['System.Int64','string'],
    ['System.Single','number'], ['System.Double','number'], ['System.Decimal','number'],
  ]);

  const SUBTYPE_REGEX = /\[[^\]]+]/g;
  function subtypes(type) {
    const matches = String(type || '').match(SUBTYPE_REGEX);
    return matches ? matches.map((value) => value.slice(1, -1)) : [];
  }

  async function cached(key, fn) {
    if (!CACHE.has(key)) CACHE.set(key, fn());
    return CACHE.get(key);
  }

  async function typeInfo(api, type) {
    return cached(`type:${type}`, () => api(`/Api/Type/${encodeURIComponent(type)}`));
  }

  async function structure(api, type) {
    return cached(`structure:${type}`, () => api(`/Api/Structure/${encodeURIComponent(type)}`));
  }

  async function describe(api, type) {
    if (PRIMITIVE.has(type)) return { kind:PRIMITIVE.get(type), type };
    const base = String(type || '').split('`')[0];
    const subs = subtypes(type);
    if (base === 'System.Nullable' && subs[0]) return { ...(await describe(api, subs[0])), nullable:true };
    if (['System.Collections.Generic.HashSet','System.Collections.Immutable.ImmutableHashSet','System.Collections.Immutable.ImmutableList','System.Collections.Generic.List','System.Collections.Generic.Dictionary','System.Collections.Immutable.ImmutableDictionary'].includes(base)) return { kind:'json', type };
    const info = await typeInfo(api, type);
    const props = info?.Properties || {};
    if (props.BaseType === 'System.Enum') {
      const values = Object.entries(info?.Body || {}).map(([name,value]) => [name, Number(value)]);
      return { kind:(props.CustomAttributes || []).includes('System.FlagsAttribute') ? 'flags' : 'enum', type, values };
    }
    return { kind:'json', type };
  }

  async function schema(api, type) {
    return cached(`schema:${type}`, async () => {
      const [info, defaults] = await Promise.all([typeInfo(api, type), structure(api, type)]);
      const fields = [];
      for (const [name, fieldType] of Object.entries(info?.Body || {})) {
        const paramName = fieldType === 'System.UInt64' ? `s_${name}` : name;
        fields.push({ name, paramName, fieldType, defaultValue:defaults?.[name], ...(await describe(api, fieldType)) });
      }
      return fields.sort((a,b) => a.name.localeCompare(b.name));
    });
  }

  function displayValue(field, value) {
    if (SECRET.has(field.name)) return '';
    if (value === undefined) value = field.defaultValue;
    if (field.kind === 'json') return JSON.stringify(value ?? null, null, 2);
    return value ?? '';
  }

  function fieldMarkup(field, value, prefix, escapeHtml) {
    const id = `${prefix}-${field.name}`;
    const initial = JSON.stringify(value === undefined ? field.defaultValue : value);
    const common = `data-native-field="${escapeHtml(field.paramName)}" data-native-source-field="${escapeHtml(field.name)}" data-native-kind="${escapeHtml(field.kind)}" data-native-initial="${escapeHtml(initial)}"`;
    const label = `<label for="${escapeHtml(id)}">${escapeHtml(field.name)}</label>`;
    const help = `<small class="field-help">${escapeHtml(field.fieldType)}${SECRET.has(field.name) ? ' · blank keeps the existing secret' : ''}</small>`;
    let control = '';
    if (field.kind === 'boolean') {
      control = `<label class="switch-row"><input id="${escapeHtml(id)}" type="checkbox" ${value ?? field.defaultValue ? 'checked' : ''} ${common}><span>Enabled</span></label>`;
    } else if (field.kind === 'enum') {
      const selected = Number(value ?? field.defaultValue ?? 0);
      control = `<select id="${escapeHtml(id)}" ${common}>${field.values.map(([name,v]) => `<option value="${v}" ${v === selected ? 'selected' : ''}>${escapeHtml(name)} (${v})</option>`).join('')}</select>`;
    } else if (field.kind === 'flags') {
      const selected = Number(value ?? field.defaultValue ?? 0);
      control = `<div id="${escapeHtml(id)}" class="native-flags" ${common} data-native-flags="1">${field.values.filter(([,v]) => v !== 0).map(([name,v]) => `<label><input type="checkbox" data-native-flag-value="${v}" ${(selected & v) === v ? 'checked' : ''}><span>${escapeHtml(name)}</span></label>`).join('')}<small>numeric value: <span data-native-flag-total>${selected}</span></div>`;
    } else if (field.kind === 'number') {
      const step = ['System.Single','System.Double','System.Decimal'].includes(field.fieldType) ? 'any' : '1';
      control = `<input id="${escapeHtml(id)}" type="number" step="${step}" value="${escapeHtml(displayValue(field,value))}" ${common}>`;
    } else if (field.kind === 'json') {
      control = `<textarea id="${escapeHtml(id)}" class="native-json" rows="4" spellcheck="false" ${common}>${escapeHtml(displayValue(field,value))}</textarea>`;
    } else {
      const secret = SECRET.has(field.name);
      control = `<input id="${escapeHtml(id)}" type="${secret ? 'password' : 'text'}" value="${escapeHtml(displayValue(field,value))}" placeholder="${secret ? 'Keep unchanged' : ''}" autocomplete="off" ${common}>`;
    }
    return `<div class="native-field">${label}${control}${help}</div>`;
  }

  function readControl(node) {
    const kind = node.dataset.nativeKind;
    if (kind === 'boolean') return Boolean(node.checked);
    if (kind === 'number') {
      if (String(node.value).trim() === '') return null;
      const n = Number(node.value);
      if (!Number.isFinite(n)) throw new Error(`${node.dataset.nativeField}: invalid number`);
      return n;
    }
    if (kind === 'enum') return Number(node.value);
    if (kind === 'flags') return [...node.querySelectorAll('[data-native-flag-value]:checked')].reduce((sum, box) => sum | Number(box.dataset.nativeFlagValue || 0), 0);
    if (kind === 'json') {
      try { return JSON.parse(node.value); } catch (_) { throw new Error(`${node.dataset.nativeField}: invalid JSON`); }
    }
    return node.value;
  }

  function collect(container, fields) {
    const changes = {};
    const byName = new Map(fields.map((f) => [f.paramName, f]));
    container.querySelectorAll('[data-native-field]').forEach((node) => {
      const name = node.dataset.nativeField;
      const field = byName.get(name);
      if (!field) return;
      const value = readControl(node);
      if (SECRET.has(field.name) && value === '') return;
      let initial;
      try { initial = JSON.parse(node.dataset.nativeInitial); } catch (_) { initial = undefined; }
      if (JSON.stringify(value) !== JSON.stringify(initial)) changes[name] = value;
    });
    return changes;
  }

  function wireFlags(root=document) {
    root.querySelectorAll('[data-native-flags]').forEach((group) => group.addEventListener('change', () => {
      const total = [...group.querySelectorAll('[data-native-flag-value]:checked')].reduce((sum, box) => sum + Number(box.dataset.nativeFlagValue || 0), 0);
      const node = group.querySelector('[data-native-flag-total]');
      if (node) node.textContent = String(total);
    }));
  }

  window.NativeASF = { schema, fieldMarkup, collect, wireFlags };
})();
