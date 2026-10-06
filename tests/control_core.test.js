'use strict';
const assert = require('node:assert/strict');
const core = require('../ControlWeb/www/core.js');
assert.equal(core.parseTargetHours(''), null);
assert.equal(core.parseTargetHours('  '), null);
assert.equal(core.parseTargetHours('1.5'), 1.5);
assert.throws(() => core.parseTargetHours('0'));
assert.throws(() => core.parseTargetHours('-1'));
assert.throws(() => core.parseTargetHours('wat'));
assert.throws(() => core.parseTargetHours(String(core.MAX_TARGET_HOURS + 1)));
assert.equal(core.normalizeBatchSize(1), 1);
assert.equal(core.normalizeBatchSize('32'), 32);
assert.throws(() => core.normalizeBatchSize(0));
assert.throws(() => core.normalizeBatchSize(33));
assert.throws(() => core.normalizeBatchSize(1.2));
assert.deepEqual(core.normalizeGoals([
  { appId: 730, selected: true, targetHours: '100' },
  { appId: 381210, selected: true, targetHours: '' },
  { appId: 10, selected: false, targetHours: '5' },
]), { '730': 100, '381210': null });
const original = { Enabled: true, OnlineStatus: 1, GamesPlayedWhileIdle: [10], CustomGamePlayedWhileIdle: 'legacy', OtherPluginSetting: { KeepMe: true } };
const enabled = core.applyPlaytimeConfig(original, { enabled: true, batchSize: 5, parentalWritesEnabled: true, entries: [{ appId: 730, selected: true, targetHours: '20' }, { appId: 381210, selected: true, targetHours: '' }] });
assert.deepEqual(enabled.GamesPlayedWhileIdle, []);
assert.equal(enabled.CustomGamePlayedWhileIdle, null);
assert.equal(enabled.PlaytimeGoalsEnabled, true);
assert.equal(enabled.PlaytimeGoalsBatchSize, 5);
assert.equal(enabled.PlaytimeGoalsParentalWritesEnabled, true);
assert.deepEqual(enabled.PlaytimeGoals, { '730': 20, '381210': null });
assert.deepEqual(enabled.OtherPluginSetting, { KeepMe: true });
assert.deepEqual(original.GamesPlayedWhileIdle, [10]);
const disabled = core.applyPlaytimeConfig(original, { enabled: false, batchSize: 3, parentalWritesEnabled: false, entries: [] });
assert.deepEqual(disabled.GamesPlayedWhileIdle, [10]);
assert.equal(disabled.CustomGamePlayedWhileIdle, 'legacy');
assert.equal(core.canToggleGame({ CanSelect: false }, false), false);
assert.equal(core.canToggleGame({ CanSelect: false }, true), true);
assert.equal(core.canToggleGame({ CanSelect: true }, false), true);
assert.equal(core.sourceLabel({ Source: 'free' }), 'FREE');
assert.equal(core.normalizeLockMinutes('15'), 15);
assert.equal(core.normalizeLockMinutes('999'), 15);
assert.equal(core.normalizeLockMinutes('0'), 0);
console.log('CONTROL CORE TESTS: PASS');
