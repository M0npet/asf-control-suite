"""Offline mocked contract tests. Never contacts a device or modifies ASF."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'scripts' / 'phone' / 'phone-guarded-rollback-v3.sh'

FAKE_TMUX = r'''#!/usr/bin/env -S python3 -S
import json, os, pathlib, sys, signal
state_file = pathlib.Path(os.environ['MOCK_TMUX_STATE'])
s = json.loads(state_file.read_text())
a = sys.argv[1:]

def resolve_session():
    if '-t' not in a:
        return None
    target = a[a.index('-t')+1]
    # Actual tmux accepts a unique prefix, unless the target starts with '='.
    if target.startswith('='):
        name = target[1:]
        return name if s.get(name, {}).get('exists') else None
    if s.get(target, {}).get('exists'):
        return target
    matches = [name for name, value in s.items()
               if name.startswith(target) and value.get('exists')]
    return matches[0] if len(matches) == 1 else None

# Initial state simulates the actual Termux supervisor. No device contacted.
if a[0] == 'has-session':
    sys.exit(0 if resolve_session() else 1)
if a[0] == 'display-message':
    field = a[-1]
    q = s[resolve_session()]
    fields = {
      '#{pane_start_command}': '/bin/sh -c ' + repr(q['start']) if q['type']=='guard' else q['start'],
      '#{pane_current_path}': os.environ['MOCK_HOME'],
      '#{pane_current_command}': 'unexpected' if os.environ.get('MOCK_BAD_PANE') else ('sleep' if q['type']=='guard' else 'bash'),
      '#{pane_dead}': '0' if q['exists'] else '1',
    }
    print(fields.get(field, 'unknown'))
    sys.exit(0)
if a[0] == 'list-panes':
    assert resolve_session()
    print('%1')
    sys.exit(0)
if a[0] == 'kill-session':
    key = resolve_session()
    assert key
    s[key] = {'exists':False,'type':'none','start':'','guard':''}
    s['kills'] = s.get('kills', 0) + 1
elif a[0] == 'new-session':
    assert a[a.index('-s')+1] == 'asf'
    if os.environ.get('MOCK_TMUX_HOLD_CREATE_FAIL') and 'sleep 3600' in a[-1]:
        sys.exit(68)
    c = a[-1]
    if os.environ.get('MOCK_BOOT_NO_SESSION') and 'sleep 3600' not in c:
        sys.exit(0)
    s['asf'] = {'exists':True,'type':'guard' if 'sleep 3600' in c else 'normal', 'start':c, 'guard':''}
    s['creates'] = s.get('creates', 0) + 1
elif a[0] == 'set-option':
    assert a[-2] == '@asfc_guard'
    s[resolve_session()]['guard'] = a[-1]
elif a[0] == 'show-options':
    print('corrupt' if os.environ.get('MOCK_BAD_GUARD') else s[resolve_session()].get('guard',''))
    sys.exit(0)
else:
    raise Exception('unsupported tmux invocation: '+ repr(a))
state_file.write_text(json.dumps(s))
if a[0] == 'kill-session' and os.environ.get('MOCK_SIGNAL_AFTER_FIRST_KILL') and s['kills'] == 1:
    os.kill(os.getppid(), signal.SIGTERM)
'''

FAKE_PD = r'''#!/usr/bin/env bash
set -euo pipefail
f="${MOCK_PD_COUNT}"
n=0
[[ ! -f "$f" ]] || n=$(cat "$f")
n=$((n+1)); printf '%s\n' "$n" > "$f"
case "$n" in
  1) if [[ "${MOCK_FAIL_PRECHECK:-0}" == 1 ]]; then echo 'BACKUP_INTEGRITY=FAIL'; exit 71; fi; echo 'BACKUP_INTEGRITY=PASS' ;;
  2)
    if [[ "${MOCK_SIGNAL_DURING_RESTORE:-0}" == 1 ]]; then
      kill -TERM "$PPID"
      exit 74
    fi
    if [[ "${MOCK_FAIL_RESTORE:-0}" == 1 ]]; then echo 'TEST_RESTORE=FAIL'; exit 73; fi
    mkdir -p "$HOME/.cache/asf-control-suite"
    echo MUTATION_ATTEMPTED > "$HOME/.cache/asf-control-suite/rollback-phase-${ASFC_BACKUP}"
    echo 'ASF_QUIESCENT=PASS'
    echo 'RESTORED_FILES_EXACT=PASS'
    ;;
  3) : ;;
  4) echo 'OLD_RUNTIME_HEALTH=PASS' ;;
  *) echo 'UNEXPECTED_PD_CALL'; exit 88 ;;
esac
'''

class GuardedRollback(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory(prefix='asfc-test-')
        self.addCleanup(self.td.cleanup)
        self.home = pathlib.Path(self.td.name)
        self.fakebin = self.home/'fakebin'
        self.fakebin.mkdir()
        self.prefix = self.home/'prefix'
        (self.prefix/'bin').mkdir(parents=True)
        self.backup = '20261008T135623Z-6531'
        self.base_start = 'while :; do proot-distro login debian -- ArchiSteamFarm; sleep 2; done'
        self.s_file = self.home/'state.json'
        self.s_file.write_text(json.dumps({
            'asf': {'exists':True, 'type':'normal', 'start':self.base_start, 'guard':''},
            'asf-proxy': {'exists':True}, 'tailscale-watch': {'exists':True},
            'kills':0, 'creates':0
        }))
        body=SOURCE.read_text().split("<<'PHONE'\n",1)[1].rsplit('\nPHONE\n',1)[0]
        self.body=self.home/'phone-body-under-test.sh'
        self._write(self.body,'#!/usr/bin/env bash\n'+body+'\n')
        self._write(self.fakebin/'tmux',FAKE_TMUX)
        self._write(self.prefix/'bin'/'proot-distro',FAKE_PD)
        self._write(self.fakebin/'sleep','#!/bin/sh\nexit 0\n')
        self._write(self.fakebin/'seq','#!/bin/bash\nif [[ "$*" == "1 90" || "$*" == "1 100" ]]; then /usr/bin/seq 1 2; else /usr/bin/seq "$@"; fi\n')
        self._write(self.home/'.termux'/'boot'/'start-asf.sh', '''#!/bin/bash
# tmux proot-distro ArchiSteamFarm
# mimic normal Termux:Boot startup without service side effects
tmux new-session -d -s asf -c "$HOME" 'while :; do proot-distro login debian -- ArchiSteamFarm; sleep 2; done'
''')
        # Future-only recovery path: inject a harmless, fixed local launcher.
        # The production --run entrypoint remains unconditionally blocked.
        self.launcher=self.home/'.config'/'asf'/'asf-only-launcher.sh'
        self._write(self.launcher, '''#!/usr/bin/env bash
tmux new-session -d -s asf -c "$HOME" 'while :; do proot-distro login debian -- ArchiSteamFarm; sleep 2; done'
''')
        self.launcher_sha=hashlib.sha256(self.launcher.read_bytes()).hexdigest()
        self.adapter=self.home/'.config'/'asf'/'asf-only-session.sh'
        self._write(self.adapter,'#!/usr/bin/env bash\nexit 0\n')
        self.adapter_sha=hashlib.sha256(self.adapter.read_bytes()).hexdigest()
        self._write(self.home/'core.sh', '#!/bin/bash\nexit 0\n')
        self.sha = hashlib.sha256((self.home/'core.sh').read_bytes()).hexdigest()
        self.env = dict(os.environ,
            HOME=str(self.home), MOCK_HOME=str(self.home), MOCK_TMUX_STATE=str(self.s_file),
            MOCK_PD_COUNT=str(self.home/'pd_count'),
            PREFIX=str(self.prefix), ASFC_BACKUP=self.backup, ASFC_REMOTE_CORE=str(self.home/'core.sh'),
            ASFC_CORE_SHA=self.sha,
            ASFC_ONLY_LAUNCHER_SHA256=self.launcher_sha,
            ASFC_ONLY_ADAPTER_SHA256=self.adapter_sha,
            PATH=str(self.fakebin)+':'+os.environ['PATH'])
    @staticmethod
    def _write(path, txt):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(txt)
        path.chmod(0o700)
    def run_phone(self, mode, extra=None):
        env = dict(self.env, ASFC_MODE=mode)
        if extra: env.update(extra)
        return subprocess.run(['bash',str(self.body)], env=env,text=True,capture_output=True,timeout=12)
    def state(self):
        return json.loads(self.s_file.read_text())
    def test_term_during_guard_transition_recovers_via_asf_only(self):
        p = self.run_phone('--run', {'MOCK_SIGNAL_AFTER_FIRST_KILL': '1'})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('PREMUTATION_SUPERVISOR_RECOVERED=YES', p.stdout)
        self.assertEqual(self.state()['asf']['type'], 'normal')
        self.assertTrue(self.state()['asf-proxy']['exists'])
        self.assertEqual(self.state()['kills'], 1)

    def test_missing_asf_must_not_resolve_asf_proxy(self):
        state = self.state()
        state['asf']['exists'] = False
        self.s_file.write_text(json.dumps(state))
        p = self.run_phone('--precheck')
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('MISSING_TMUX_SESSION', p.stdout)
        self.assertEqual(self.state()['kills'], 0)
        self.assertTrue(self.state()['asf-proxy']['exists'])

    def test_invalid_backup_id_rejected_before_contacting_adb(self):
        # These override values must not cross the local/remote shell boundary.
        adb_marker = self.home / 'adb-was-called'
        self._write(self.fakebin / 'adb',
                    '#!/bin/sh\nprintf called >> "$MOCK_ADB_MARKER"\nexit 99\n')
        values = [
            '../backup',
            '20261008T135623Z-1/../2',
            '20261008T135623Z-1;touch /tmp/unsafe',
            '20261008T135623Z-1$(true)',
            "20261008T135623Z-1'quoted'",
            '20261008T0000Z-23',
            '20261008T135623Z-' + '9' * 65,
        ]
        for bad in values:
            with self.subTest(value=repr(bad)):
                adb_marker.unlink(missing_ok=True)
                env = dict(self.env, ASFC_BACKUP_ID=bad,
                           MOCK_ADB_MARKER=str(adb_marker))
                p = subprocess.run(['bash', str(SOURCE), '--precheck'],
                                   env=env, text=True, capture_output=True, timeout=5)
                self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
                self.assertIn('INVALID_BACKUP_ID', p.stderr)
                self.assertFalse(adb_marker.exists())

    def test_valid_backup_id_passes_input_validation(self):
        self._write(self.fakebin / 'adb', '#!/bin/sh\nexit 99\n')
        env = dict(self.env, ASFC_BACKUP_ID='20261008T135623Z-6531')
        p = subprocess.run(['bash', str(SOURCE), '--precheck'],
                           env=env, text=True, capture_output=True, timeout=5)
        self.assertNotIn('INVALID_BACKUP_ID', p.stderr)
        # Deliberately missing artifact prevents ADB access in this isolated test.
        self.assertIn('MISSING_CANDIDATE_OR_CORE', p.stdout)

    def test_precheck_does_not_modify_sessions(self):
        p=self.run_phone('--precheck')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('GUARDED_ROLLBACK_PREFLIGHT=PASS',p.stdout)
        self.assertEqual(self.state()['kills'],0)
        self.assertEqual(self.state()['creates'],0)
    def test_success_restores_via_isolated_launcher_not_replayed_string(self):
        p=self.run_phone('--run')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('SUPERVISOR_HELD=PASS',p.stdout)
        self.assertIn('RESTORED_FILES_EXACT=PASS',p.stdout)
        self.assertIn('SUPERVISOR_RESTORED_VIA_ASF_ONLY=PASS',p.stdout)
        self.assertIn('GUARDED_ROLLBACK=PASS',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'normal')
        self.assertNotIn('pane_start_command',self.state()['asf']['start'])
        self.assertFalse((self.home/'.cache'/'asf-control-suite'/('rollback-phase-'+self.backup)).exists())
    def test_premutation_invalid_pane_recovers_asf_only(self):
        p=self.run_phone('--run',{'MOCK_BAD_PANE':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('HOLD_PANE_UNEXPECTED',p.stdout)
        self.assertIn('PREMUTATION_SUPERVISOR_RECOVERED=YES',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'normal')
        self.assertEqual((self.home/'pd_count').read_text().strip(),'1')
    def test_unidentified_guard_refuses_to_kill(self):
        p=self.run_phone('--run',{'MOCK_BAD_GUARD':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('PREMUTATION_UNVERIFIED_SESSION=YES',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'guard')
        self.assertEqual((self.home/'pd_count').read_text().strip(),'1')
    def test_unpinned_asf_only_launcher_fails_before_supervisor_stop(self):
        p=self.run_phone('--run', {'ASFC_ONLY_LAUNCHER_SHA256':'0'*64})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_ONLY_RECOVERY_PIN_MISMATCH',p.stdout)
        self.assertNotIn('GUARDED_ROLLBACK=PASS',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_missing_private_adapter_fails_before_supervisor_stop(self):
        self.adapter.unlink()
        p=self.run_phone('--run')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_ONLY_RECOVERY_NOT_PROVISIONED',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_missing_pinned_launcher_fails_before_supervisor_stop(self):
        self.launcher.unlink()
        p=self.run_phone('--run')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_ONLY_RECOVERY_NOT_PROVISIONED',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_bad_adapter_pin_fails_before_supervisor_stop(self):
        p=self.run_phone('--run', {'ASFC_ONLY_ADAPTER_SHA256':'0'*64})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_ONLY_RECOVERY_PIN_MISMATCH',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_multi_service_boot_not_executed_during_mocked_recovery(self):
        marker=self.home/'WRONG_BOOT_REPLAY'
        with (self.home/'.termux/boot/start-asf.sh').open('a') as fp:
            fp.write('touch "$HOME/WRONG_BOOT_REPLAY"\n')
        p=self.run_phone('--run')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertFalse(marker.exists())
        self.assertIn('SUPERVISOR_RESTORED_VIA_ASF_ONLY=PASS',p.stdout)

    def test_restoration_failure_preserves_hold(self):
        p=self.run_phone('--run',{'MOCK_FAIL_RESTORE':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('FILES_MAY_BE_CHANGED=YES',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'guard')
        self.assertEqual(self.state()['creates'],1)
    def test_signal_during_restore_preserves_guard_and_stops(self):
        p = self.run_phone('--run', {'MOCK_SIGNAL_DURING_RESTORE': '1'})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn('FILES_MAY_BE_CHANGED=YES', p.stdout)
        self.assertEqual(self.state()['asf']['type'], 'guard')
        self.assertTrue(self.state()['asf-proxy']['exists'])

    def test_missing_boot_refuses_before_stop(self):
        (self.home/'.termux'/'boot'/'start-asf.sh').unlink()
        p=self.run_phone('--run')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('BOOT_SCRIPT_MISSING',p.stdout)
        self.assertEqual(self.state()['kills'],0)
    def test_missing_backup_refuses_before_stop(self):
        p=self.run_phone('--run',{'MOCK_FAIL_PRECHECK':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('BACKUP_INTEGRITY=FAIL',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_hold_creation_failure_recovers_through_asf_only(self):
        p=self.run_phone('--run',{'MOCK_TMUX_HOLD_CREATE_FAIL':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('PREMUTATION_SUPERVISOR_RECOVERED=YES',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'normal')
        self.assertEqual(self.state()['kills'],1)

    def test_transfer_corruption_cannot_stop_supervisor(self):
        p=self.run_phone('--run',{'ASFC_CORE_SHA':'a'*64})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ROLLBACK_CORE_TRANSFER=FAIL',p.stdout)
        self.assertEqual(self.state()['kills'],0)

    def test_guard_must_exist_for_complete_roll_back(self):
        p=self.run_phone('--run',{'MOCK_BAD_GUARD':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertNotIn('GUARDED_ROLLBACK=PASS',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'guard')

    def test_success_preserves_proxy_and_tailscale_sessions(self):
        p=self.run_phone('--run')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        state=self.state()
        self.assertTrue(state['asf-proxy']['exists'])
        self.assertTrue(state['tailscale-watch']['exists'])

    def test_source_requires_pinned_asf_only_recovery_without_boot_replay(self):
        source=SOURCE.read_text()
        body=source.split("<<'PHONE'\n",1)[1].rsplit('\nPHONE\n',1)[0]
        self.assertNotIn('bash "$BOOT"',body)
        self.assertNotIn('boot_start_and_wait()',body)
        self.assertIn('asf_only_start_and_wait()',body)
        self.assertIn('ASF_ONLY_RECOVERY_PIN_MISMATCH',body)
        self.assertIn('ASF_ONLY_RECOVERY_NOT_PROVISIONED',body)
        self.assertIn("tmux has-session -t '=asf' >/dev/null 2>&1 || return 1",body)
        self.assertLess(body.index('ASF_ONLY_RECOVERY_PREFLIGHT=PASS'),
                        body.index("STATE=1\ntmux kill-session -t '=asf'"))
        self.assertIn('ASF_ONLY_RECOVERY_REQUIRED; LIVE_RUN_DISABLED',source)

    def test_source_and_harness_match_exactly(self):
        source=SOURCE.read_text()
        body=source.split("<<'PHONE'\n",1)[1].rsplit('\nPHONE\n',1)[0]
        actual=self.body.read_text().split('\n',1)[1].strip()
        self.assertEqual(body.strip(),actual)

    def test_no_raw_command_persisted_in_recovery_record(self):
        p=self.run_phone('--run')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        rec=self.home/'.cache'/'asf-control-suite'/('rollback-command-fingerprint-v3-'+self.backup)
        self.assertTrue(rec.is_file())
        body=rec.read_text()
        self.assertIn('command_sha256=',body)
        self.assertNotIn('ArchiSteamFarm',body)
        self.assertNotIn('proot-distro',body)
        self.assertNotIn(self.base_start,body)

    def test_empty_pane_after_asf_only_is_not_false_success(self):
        p=self.run_phone('--run',{'MOCK_BOOT_NO_SESSION':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_ONLY_RESTART=FAIL',p.stdout)
        self.assertNotIn('GUARDED_ROLLBACK=PASS',p.stdout)
        marker=self.home/'.cache'/'asf-control-suite'/('rollback-phase-'+self.backup)
        self.assertTrue(marker.exists())

    def test_live_run_blocked_until_asf_only_recovery_is_verified(self):
        # Full Termux:Boot script restarts the HTTPS proxy: never allow real --run
        # until ASF-only recovery is implemented and separately accepted.
        env = dict(self.env, ASFC_LIVE_CONFIRMATION='I_ACCEPT_ASF_DOWNTIME')
        p = subprocess.run(['bash', str(SOURCE), '--run'], env=env,
                           text=True, capture_output=True, timeout=3)
        self.assertEqual(p.returncode, 40, p.stdout + p.stderr)
        self.assertIn('ASF_ONLY_RECOVERY_REQUIRED', p.stderr)
        self.assertNotIn('VERIFIED_SOURCE_AND_CANDIDATE', p.stdout)

    def test_run_requires_explicit_live_confirmation_before_adb(self):
        source=SOURCE
        env=dict(os.environ, ASFC_LIVE_CONFIRMATION='', PATH=self.env['PATH'])
        p=subprocess.run(['bash',str(source),'--run'],env=env,text=True,capture_output=True,timeout=2)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('LIVE_CONFIRMATION_REQUIRED',p.stdout)
        self.assertNotIn('VERIFIED_SOURCE_AND_CANDIDATE',p.stdout)

if __name__=='__main__':
    unittest.main(verbosity=2)
