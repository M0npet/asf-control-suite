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
import json, os, pathlib, sys
state_file = pathlib.Path(os.environ['MOCK_TMUX_STATE'])
s = json.loads(state_file.read_text())
a = sys.argv[1:]

# Initial state simulates the actual Termux supervisor. No device contacted.
if a[0] == 'has-session':
    target = a[a.index('-t')+1]
    sys.exit(0 if s.get(target, {}).get('exists') else 1)
if a[0] == 'display-message':
    field = a[-1]
    q = s['asf']
    fields = {
      '#{pane_start_command}': '/bin/sh -c ' + repr(q['start']) if q['type']=='guard' else q['start'],
      '#{pane_current_path}': os.environ['MOCK_HOME'],
      '#{pane_current_command}': 'unexpected' if os.environ.get('MOCK_BAD_PANE') else ('sleep' if q['type']=='guard' else 'bash'),
      '#{pane_dead}': '0' if q['exists'] else '1',
    }
    print(fields.get(field, 'unknown'))
    sys.exit(0)
if a[0] == 'list-panes':
    print('%1')
    sys.exit(0)
if a[0] == 'kill-session':
    assert a[-1] == 'asf'
    s['asf'] = {'exists':False,'type':'none','start':'','guard':''}
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
    s['asf']['guard'] = a[-1]
elif a[0] == 'show-options':
    print('corrupt' if os.environ.get('MOCK_BAD_GUARD') else s['asf'].get('guard',''))
    sys.exit(0)
else:
    raise Exception('unsupported tmux invocation: '+ repr(a))
state_file.write_text(json.dumps(s))
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
        self._write(self.home/'core.sh', '#!/bin/bash\nexit 0\n')
        self.sha = hashlib.sha256((self.home/'core.sh').read_bytes()).hexdigest()
        self.env = dict(os.environ,
            HOME=str(self.home), MOCK_HOME=str(self.home), MOCK_TMUX_STATE=str(self.s_file),
            MOCK_PD_COUNT=str(self.home/'pd_count'),
            PREFIX=str(self.prefix), ASFC_BACKUP=self.backup, ASFC_REMOTE_CORE=str(self.home/'core.sh'),
            ASFC_CORE_SHA=self.sha,
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
    def test_precheck_does_not_modify_sessions(self):
        p=self.run_phone('--precheck')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('GUARDED_ROLLBACK_PREFLIGHT=PASS',p.stdout)
        self.assertEqual(self.state()['kills'],0)
        self.assertEqual(self.state()['creates'],0)
    def test_success_restores_via_boot_not_replayed_string(self):
        p=self.run_phone('--run')
        self.assertEqual(p.returncode,0,p.stdout+'\n'+p.stderr)
        self.assertIn('SUPERVISOR_HELD=PASS',p.stdout)
        self.assertIn('RESTORED_FILES_EXACT=PASS',p.stdout)
        self.assertIn('SUPERVISOR_RESTORED_VIA_BOOT=PASS',p.stdout)
        self.assertIn('GUARDED_ROLLBACK=PASS',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'normal')
        self.assertNotIn('pane_start_command',self.state()['asf']['start'])
        self.assertFalse((self.home/'.cache'/'asf-control-suite'/('rollback-phase-'+self.backup)).exists())
    def test_premutation_invalid_pane_recovers_boot(self):
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
    def test_restoration_failure_preserves_hold(self):
        p=self.run_phone('--run',{'MOCK_FAIL_RESTORE':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('FILES_MAY_BE_CHANGED=YES',p.stdout)
        self.assertEqual(self.state()['asf']['type'],'guard')
        self.assertEqual(self.state()['creates'],1)
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

    def test_hold_creation_failure_recovers_through_boot(self):
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

    def test_empty_pane_after_boot_is_not_false_success(self):
        p=self.run_phone('--run',{'MOCK_BOOT_NO_SESSION':'1'})
        self.assertNotEqual(p.returncode,0)
        self.assertIn('BOOT_RESTART=FAIL',p.stdout)
        self.assertNotIn('GUARDED_ROLLBACK=PASS',p.stdout)
        marker=self.home/'.cache'/'asf-control-suite'/('rollback-phase-'+self.backup)
        self.assertTrue(marker.exists())

    def test_run_requires_explicit_live_confirmation_before_adb(self):
        source=SOURCE
        env=dict(os.environ, ASFC_LIVE_CONFIRMATION='', PATH=self.env['PATH'])
        p=subprocess.run(['bash',str(source),'--run'],env=env,text=True,capture_output=True,timeout=2)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('LIVE_CONFIRMATION_REQUIRED',p.stdout)
        self.assertNotIn('VERIFIED_SOURCE_AND_CANDIDATE',p.stdout)

if __name__=='__main__':
    unittest.main(verbosity=2)
