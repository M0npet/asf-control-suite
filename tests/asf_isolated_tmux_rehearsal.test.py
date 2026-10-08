"""Offline mock of on-device tmux socket isolation. No Android/ASF/PRoot calls."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/phone/asf-isolated-tmux-rehearsal.sh'
TMUX = r'''#!/usr/bin/env bash
set -euo pipefail
SOCKET=''
while (($#)); do
  case "$1" in
    -S) SOCKET="$2"; shift 2 ;;
    -f) shift 2 ;;
    *) break ;;
  esac
done
COMMAND="$1"; shift
if [[ -z "$SOCKET" ]]; then
  if [[ "$COMMAND" == list-sessions ]]; then
    [[ "$1" == '-F' && "$2" ==   TARGET=''
  while (($#)); do
    if [[ "$1" == '-t' ]]; then TARGET="$2"; break; fi
    shift
  done
  case "$TARGET" in '=asf'|'=asf-proxy'|'=tailscale-watch') ;; *) exit 52;; esac
  [[ "${MOCK_LIVE_MISSING:-}" != "${TARGET#=}" ]] || exit 53

  exit 0
fi
[[ -d "$(dirname "$SOCKET")" ]] || exit 54
case "$COMMAND" in
  has-session)
    [[ -e "$SOCKET" ]] ;;
  new-session)
    [[ "${MOCK_FAIL_CREATE:-}" != 1 ]] || exit 55
    SESSION=''
    commandline="${*: -1}"
    while (($#)); do
      if [[ "$1" == '-s' ]]; then SESSION="$2"; break; fi
      shift
    done
    [[ "$SESSION" == 'asfc-isolated' ]] || exit 56
    [[ "$commandline" == exec\ * && "$commandline" == *worker.sh* ]] || exit 57
    [[ "$commandline" != *ArchiSteamFarm* && "$commandline" != *proot-distro* ]] || exit 58
    touch -- "$SOCKET"
    printf 'OK\n' > "$(dirname "$SOCKET")/started"
    if [[ "${MOCK_CHANGE_PROXY:-}" == 1 ]]; then touch "$MOCK_TMUX_STATE/changed"; fi ;;
  kill-server)
    rm -f -- "$SOCKET" ;;
  *) exit 59 ;;
esac
'''

class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='asfc-synthetic-tmux-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.home=self.root/'home'
        self.home.mkdir()
        self.tmp=self.root/'tmp'
        self.tmp.mkdir()
        self.bin=self.root/'bin'
        self.bin.mkdir()
        self.state=self.root/'state'
        self.state.mkdir()
        self.tmux=self.bin/'tmux'
        self.tmux.write_text(TMUX)
        self.tmux.chmod(0o700)
        self.candidate=self.home/'.cache/asf-control-suite/candidates/asf-only-session.candidate.sh'
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text('#!/usr/bin/env bash\ntmux new-session -d -s asf "echo forbidden"\n')
        self.candidate.chmod(0o600)
        self.active=self.home/'.config/asf/asf-only-session.sh'
        self.env=dict(os.environ, HOME=str(self.home), TMPDIR=str(self.tmp), PREFIX=str(self.root), MOCK_TMUX_STATE=str(self.state), PATH=str(self.bin)+':'+os.environ['PATH'])
    def run_it(self, *args, overrides=None):
        env=dict(self.env)
        env.update(overrides or {})
        return subprocess.run(['bash',str(SCRIPT),*args],env=env,text=True,capture_output=True,timeout=20)
    def assert_temp_clean(self):
        self.assertEqual(list(self.tmp.iterdir()),[])
    def test_success_isolated_socket_unchanged_sessions(self):
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        for marker in ('ISOLATED_TMUX_CREATE=PASS','ISOLATED_WORKER=PASS',
                       'LIVE_SESSIONS=UNCHANGED','PROOT_EXECUTION=NOT_ATTEMPTED',
                       'CANDIDATE_EXECUTION=NOT_ATTEMPTED','ISOLATED_TMUX_CLEANUP=PASS',
                       'SYNTHETIC_REHEARSAL=PASS'):
            self.assertIn(marker,p.stdout)
        self.assert_temp_clean()
    def test_default_mode_does_not_run(self):
        p=self.run_it()
        self.assertEqual(p.returncode,2)
        self.assert_temp_clean()
    def test_missing_private_candidate_fails_closed(self):
        self.candidate.unlink()
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,10)
        self.assert_temp_clean()
    def test_existing_active_adapter_fails_closed(self):
        self.active.parent.mkdir(parents=True)
        self.active.write_text('do not modify\n')
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,14)
        self.assertEqual(self.active.read_text(),'do not modify\n')
        self.assert_temp_clean()
    def test_missing_live_session_fails_closed(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_LIVE_MISSING':'asf-proxy'})
        self.assertEqual(p.returncode,18)
        self.assert_temp_clean()
    def test_change_live_session_refuses_success(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_CHANGE_PROXY':'1'})
        self.assertEqual(p.returncode,25,p.stdout+p.stderr)
        self.assertIn('LIVE_SESSIONS=CHANGED',p.stdout)
        self.assertNotIn('SYNTHETIC_REHEARSAL=PASS',p.stdout)
        self.assert_temp_clean()
    def test_isolated_launch_failure_cleans_files(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_FAIL_CREATE':'1'})
        self.assertEqual(p.returncode,22,p.stdout+p.stderr)
        self.assert_temp_clean()
    def test_non_executed_candidate_proof(self):
        marker=self.root/'NEVER_EXECUTED'
        self.candidate.write_text('#!/usr/bin/env bash\ntouch '+str(marker)+'\n')
        self.candidate.chmod(0o600)
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertFalse(marker.exists())
        self.assert_temp_clean()
    def test_invalid_candidate_syntax_fails(self):
        self.candidate.write_text('#!/usr/bin/env bash\nif true; then\n')
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,13)
        self.assert_temp_clean()
    def test_no_sensitive_paths_in_output(self):
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0)
        self.assertNotIn(str(self.root),p.stdout+p.stderr)
        self.assertNotIn(str(self.candidate),p.stdout+p.stderr)
    def test_only_isolated_tmux_mutation(self):
        s=SCRIPT.read_text()
        self.assertIn('tmux -S "$SOCKET" -f /dev/null new-session',s)
        self.assertIn('tmux -S "$SOCKET" kill-server',s)
        self.assertNotIn('proot-distro login',s)
        self.assertNotIn('bash "$C"',s)
        self.assertNotIn('start-asf.sh',s)

    def test_session_native_api_regression(self):
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        s=SCRIPT.read_text()
        self.assertIn('tmux list-sessions -F',s)
        self.assertNotIn('tmux display-message -p',s)
        self.assert_temp_clean()
    def test_malformed_session_id_refuses(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_LIST_INVALID':'1'})
        self.assertEqual(p.returncode,19,p.stdout+p.stderr)
        self.assertIn('LIVE_ID=UNAVAILABLE',p.stdout)
        self.assert_temp_clean()

if __name__ == '__main__':
    unittest.main(verbosity=2)
#{session_name}\t#{session_id}' ]] || exit 60
    proxy_id='$2'
    [[ -f "$MOCK_TMUX_STATE/changed" ]] && proxy_id='$8'
    if [[ "${MOCK_LIST_INVALID:-}" == 1 ]]; then
      printf 'asf\tinvalid\nasf-proxy\t%s\ntailscale-watch\t$3\n' "$proxy_id"
    else
      printf 'asf\t$1\nasf-proxy\t%s\ntailscale-watch\t$3\n' "$proxy_id"
    fi
    exit 0
  fi
  [[ "$COMMAND" == has-session ]] || exit 51
  TARGET=''
  while (($#)); do
    if [[ "$1" == '-t' ]]; then TARGET="$2"; break; fi
    shift
  done
  case "$TARGET" in '=asf'|'=asf-proxy'|'=tailscale-watch') ;; *) exit 52;; esac
  [[ "${MOCK_LIVE_MISSING:-}" != "${TARGET#=}" ]] || exit 53
  if [[ "$COMMAND" == display-message ]]; then
    suffix=initial
    if [[ "$TARGET" == '=asf-proxy' && -f "$MOCK_TMUX_STATE/changed" ]]; then suffix=changed; fi
    printf '%s:%s\n' "$TARGET" "$suffix"
  fi
  exit 0
fi
[[ -d "$(dirname "$SOCKET")" ]] || exit 54
case "$COMMAND" in
  has-session)
    [[ -e "$SOCKET" ]] ;;
  new-session)
    [[ "${MOCK_FAIL_CREATE:-}" != 1 ]] || exit 55
    SESSION=''
    commandline="${*: -1}"
    while (($#)); do
      if [[ "$1" == '-s' ]]; then SESSION="$2"; break; fi
      shift
    done
    [[ "$SESSION" == 'asfc-isolated' ]] || exit 56
    [[ "$commandline" == exec\ * && "$commandline" == *worker.sh* ]] || exit 57
    [[ "$commandline" != *ArchiSteamFarm* && "$commandline" != *proot-distro* ]] || exit 58
    touch -- "$SOCKET"
    printf 'OK\n' > "$(dirname "$SOCKET")/started"
    if [[ "${MOCK_CHANGE_PROXY:-}" == 1 ]]; then touch "$MOCK_TMUX_STATE/changed"; fi ;;
  kill-server)
    rm -f -- "$SOCKET" ;;
  *) exit 59 ;;
esac
'''

class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='asfc-synthetic-tmux-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.home=self.root/'home'
        self.home.mkdir()
        self.tmp=self.root/'tmp'
        self.tmp.mkdir()
        self.bin=self.root/'bin'
        self.bin.mkdir()
        self.state=self.root/'state'
        self.state.mkdir()
        self.tmux=self.bin/'tmux'
        self.tmux.write_text(TMUX)
        self.tmux.chmod(0o700)
        self.candidate=self.home/'.cache/asf-control-suite/candidates/asf-only-session.candidate.sh'
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text('#!/usr/bin/env bash\ntmux new-session -d -s asf "echo forbidden"\n')
        self.candidate.chmod(0o600)
        self.active=self.home/'.config/asf/asf-only-session.sh'
        self.env=dict(os.environ, HOME=str(self.home), TMPDIR=str(self.tmp), PREFIX=str(self.root), MOCK_TMUX_STATE=str(self.state), PATH=str(self.bin)+':'+os.environ['PATH'])
    def run_it(self, *args, overrides=None):
        env=dict(self.env)
        env.update(overrides or {})
        return subprocess.run(['bash',str(SCRIPT),*args],env=env,text=True,capture_output=True,timeout=20)
    def assert_temp_clean(self):
        self.assertEqual(list(self.tmp.iterdir()),[])
    def test_success_isolated_socket_unchanged_sessions(self):
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        for marker in ('ISOLATED_TMUX_CREATE=PASS','ISOLATED_WORKER=PASS',
                       'LIVE_SESSIONS=UNCHANGED','PROOT_EXECUTION=NOT_ATTEMPTED',
                       'CANDIDATE_EXECUTION=NOT_ATTEMPTED','ISOLATED_TMUX_CLEANUP=PASS',
                       'SYNTHETIC_REHEARSAL=PASS'):
            self.assertIn(marker,p.stdout)
        self.assert_temp_clean()
    def test_default_mode_does_not_run(self):
        p=self.run_it()
        self.assertEqual(p.returncode,2)
        self.assert_temp_clean()
    def test_missing_private_candidate_fails_closed(self):
        self.candidate.unlink()
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,10)
        self.assert_temp_clean()
    def test_existing_active_adapter_fails_closed(self):
        self.active.parent.mkdir(parents=True)
        self.active.write_text('do not modify\n')
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,14)
        self.assertEqual(self.active.read_text(),'do not modify\n')
        self.assert_temp_clean()
    def test_missing_live_session_fails_closed(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_LIVE_MISSING':'asf-proxy'})
        self.assertEqual(p.returncode,18)
        self.assert_temp_clean()
    def test_change_live_session_refuses_success(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_CHANGE_PROXY':'1'})
        self.assertEqual(p.returncode,25,p.stdout+p.stderr)
        self.assertIn('LIVE_SESSIONS=CHANGED',p.stdout)
        self.assertNotIn('SYNTHETIC_REHEARSAL=PASS',p.stdout)
        self.assert_temp_clean()
    def test_isolated_launch_failure_cleans_files(self):
        p=self.run_it('--run-synthetic',overrides={'MOCK_FAIL_CREATE':'1'})
        self.assertEqual(p.returncode,22,p.stdout+p.stderr)
        self.assert_temp_clean()
    def test_non_executed_candidate_proof(self):
        marker=self.root/'NEVER_EXECUTED'
        self.candidate.write_text('#!/usr/bin/env bash\ntouch '+str(marker)+'\n')
        self.candidate.chmod(0o600)
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertFalse(marker.exists())
        self.assert_temp_clean()
    def test_invalid_candidate_syntax_fails(self):
        self.candidate.write_text('#!/usr/bin/env bash\nif true; then\n')
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,13)
        self.assert_temp_clean()
    def test_no_sensitive_paths_in_output(self):
        p=self.run_it('--run-synthetic')
        self.assertEqual(p.returncode,0)
        self.assertNotIn(str(self.root),p.stdout+p.stderr)
        self.assertNotIn(str(self.candidate),p.stdout+p.stderr)
    def test_only_isolated_tmux_mutation(self):
        s=SCRIPT.read_text()
        self.assertIn('tmux -S "$SOCKET" -f /dev/null new-session',s)
        self.assertIn('tmux -S "$SOCKET" kill-server',s)
        self.assertNotIn('proot-distro login',s)
        self.assertNotIn('bash "$C"',s)
        self.assertNotIn('start-asf.sh',s)

if __name__ == '__main__':
    unittest.main(verbosity=2)
