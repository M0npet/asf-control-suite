(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.ControlCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const MIN_BATCH = 1;
  const MAX_BATCH = 32;
  const MAX_TARGET_HOURS = 0xFFFFFFFF / 60;
  const LOCK_MINUTES = Object.freeze([0, 5, 15, 30, 60]);

  function normalizeLockMinutes(value, fallback = 15) {
    const minutes = Number(value);
    return LOCK_MINUTES.includes(minutes) ? minutes : fallback;
  }

  function parseTargetHours(value) {
    const text = String(value ?? '').trim();
    if (text === '') return null;
    const hours = Number(text);
    if (!Number.isFinite(hours) || hours <= 0) throw new Error('Target hours must be a positive number or blank for unlimited');
    if (hours > MAX_TARGET_HOURS) throw new Error('Target hours exceed the PlaytimeGoals maximum');
    return hours;
  }

  function normalizeBatchSize(value) {
    const batch = Number(value);
    if (!Number.isInteger(batch) || batch < MIN_BATCH || batch > MAX_BATCH) throw new Error(`Batch size must be an integer from ${MIN_BATCH} to ${MAX_BATCH}`);
    return batch;
  }

  function normalizeGoals(entries) {
    const goals = {};
    for (const entry of entries || []) {
      if (!entry || !entry.selected) continue;
      const appId = Number(entry.appId);
      if (!Number.isInteger(appId) || appId <= 0 || appId > 0xFFFFFFFF) throw new Error(`Invalid AppID: ${entry?.appId}`);
      goals[String(appId)] = parseTargetHours(entry.targetHours);
    }
    return goals;
  }

  function applyPlaytimeConfig(botConfig, settings) {
    if (!botConfig || typeof botConfig !== 'object' || Array.isArray(botConfig)) throw new Error('BotConfig is unavailable');
    const next = JSON.parse(JSON.stringify(botConfig));
    const enabled = Boolean(settings?.enabled);
    next.PlaytimeGoalsEnabled = enabled;
    next.PlaytimeGoalsBatchSize = normalizeBatchSize(settings?.batchSize);
    next.PlaytimeGoalsParentalWritesEnabled = Boolean(settings?.parentalWritesEnabled);
    next.PlaytimeGoals = normalizeGoals(settings?.entries);
    if (enabled) {
      next.GamesPlayedWhileIdle = [];
      next.CustomGamePlayedWhileIdle = null;
    }
    return next;
  }

  function canToggleGame(game, managed) { return Boolean(managed || game?.CanSelect); }
  function sourceLabel(game) {
    const source = String(game?.Source || 'unknown').toLowerCase();
    if (source === 'own') return 'OWN';
    if (source === 'family') return 'FAMILY';
    if (source === 'free') return 'FREE';
    if (source === 'excluded') return 'EXCLUDED';
    return source.toUpperCase();
  }

  return { MIN_BATCH, MAX_BATCH, MAX_TARGET_HOURS, LOCK_MINUTES, normalizeLockMinutes, parseTargetHours, normalizeBatchSize, normalizeGoals, applyPlaytimeConfig, canToggleGame, sourceLabel };
});
