"""Mock-only regression for session snapshots + private tmux socket cleanup.
No ADB, PRoot, real tmux, ASF, or phone candidate is ever executed.
"""
from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/phone/asf-isolated-tmux-rehearsal.sh'

MOCK_TMUX = r'''#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$MOCK_EVENTS"
if [[ "${1:-}" == '-S' ]]; then
  socket="$2"; shift 2
  if [[ "${1:-}" == '-f' ]]; then shift 2; fi
  cmd="${1:-}"
  case "$cmd" in
    has-session) [[ -e "$socket" ]] ;;
    new-session)
      [[ "${MOCK_PRIVATE_FAIL:-0}" == 0 ]] || exit 62
      : > "$socket"
      printf 'OK\n' > "$(dirname "$socket")/started" ;;
    kill-server) rm -f -- "$socket" ;;
    *) exit 60 ;;
  esac
  exit 0
fi
case "${1:-}" in
  has-session)
    [[ "$2" == '-t' ]] || exit 61
    case "$3" in
      '=asf'|'=asf-proxy'|'=tailscale-watch')
        [[ "${MOCK_MISSING:-}" != "$3" ]] ;;
      *) exit 61 ;;
    esac ;;
  display-message) exit 66 ;; # Previous implementation falsely failed here.
  list-sessions)
    [[ "${2:-}" == '-F' ]] || exit 61
    [[ "${3:-}" == '#{session_name}|#{session_id}' ]] || exit 65
    calls=0
    [[ -e "$MOCK_CALLS" ]] && read -r calls < "$MOCK_CALLS"
    calls=$((calls+1))
    printf '%s\n' "$calls" > "$MOCK_CALLS"
    [[ "${MOCK_LIST_FAIL:-0}" == 0 ]] || exit 63
    if [[ "${MOCK_MALFORMED:-0}" == 1 ]]; then
      printf 'asf|bad\nasf-proxy|$2\ntailscale-watch|$3\n'
    elif [[ "${MOCK_DUPLICATE:-0}" == 1 ]]; then
      printf 'asf|$1\nasf|$8\nasf-proxy|$2\ntailscale-watch|$3\n'
    elif [[ "${MOCK_CHANGED:-0}" == 1 && "$calls" -ge 2 ]]; then
      printf 'asf|$1\nasf-proxy|$99\ntailscale-watch|$3\n'
    else
      printf 'unrelated|$9\nasf-proxy|$2\ntailscale-watch|$3\nasf|$1\n'
    fi ;;
  *) exit 64 ;;
esac
'''

class RehearsalTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix='asfc-private-socket-')
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        self.home = self.root/'home'
        self.home.mkdir()
        self.temp = self.root/'tmp'
        self.temp.mkdir()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        fake = self.bin/'tmux'
        fake.write_text(MOCK_TMUX)
        fake.chmod(0o700)
        self.candidate = self.home/'.cache/asf-control-suite/candidates/asf-only-session.candidate.sh'
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text('#!/bin/bash\ntrue\n')
        self.candidate.chmod(0o600)
        self.events = self.root/'events'
        self.calls = self.root/'calls'
        self.env = dict(os.environ, HOME=str(self.home), PREFIX=str(self.root/'prefix'),
                        TMPDIR=str(self.temp), PATH=str(self.bin)+':'+os.environ['PATH'],
                        MOCK_EVENTS=str(self.events), MOCK_CALLS=str(self.calls))

    def run_it(self, vars=None):
        e = dict(self.env, **(vars or {}))
        return subprocess.run(['bash',str(SCRIPT),'--run-synthetic'],env=e,
                              text=True,capture_output=True,timeout=12)

    def assert_no_workspace(self):
        self.assertEqual(list(self.temp.glob('asfc-isolated.*')), [])

    def test_regression_list_sessions_succeeds_when_display_message_fails(self):
        p = self.run_it()
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn('SYNTHETIC_REHEARSAL=PASS', p.stdout)
        self.assertIn('LIVE_SESSIONS=UNCHANGED', p.stdout)
        self.assertIn('ISOLATED_TMUX_CLEANUP=PASS', p.stdout)
        events=self.events.read_text()
        self.assertIn('list-sessions',events)
        self.assertNotIn('display-message',events)
        self.assertTrue(all(not line.startswith('kill-server') for line in events.splitlines()))
        self.assert_no_workspace()

    def test_pipe_format_is_required_not_tab(self):
        p=self.run_it()
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        events=self.events.read_text()
        self.assertIn('#{session_name}|#{session_id}',events)
        self.assertNotIn('\t#{session_id}',events)
        self.assert_no_workspace()

    def test_list_sessions_unavailable_refuses_before_create(self):
        p=self.run_it({'MOCK_LIST_FAIL':'1'})
        self.assertEqual(p.returncode,19)
        self.assertIn('LIVE_ID=UNAVAILABLE',p.stdout)
        self.assertNotIn('new-session',self.events.read_text())
        self.assert_no_workspace()

    def test_malformed_session_id_refused(self):
        p=self.run_it({'MOCK_MALFORMED':'1'})
        self.assertEqual(p.returncode,19)
        self.assert_no_workspace()

    def test_duplicate_named_sessions_refused(self):
        p=self.run_it({'MOCK_DUPLICATE':'1'})
        self.assertEqual(p.returncode,19)
        self.assert_no_workspace()

    def test_aux_session_changed_after_creation_detected_and_cleaned(self):
        p=self.run_it({'MOCK_CHANGED':'1'})
        self.assertEqual(p.returncode,25)
        self.assertIn('LIVE_SESSIONS=CHANGED',p.stdout)
        self.assert_no_workspace()

    def test_missing_live_session_refused_before_create(self):
        p=self.run_it({'MOCK_MISSING':'=asf-proxy'})
        self.assertEqual(p.returncode,18)
        self.assert_no_workspace()

    def test_private_tmux_creation_failure_cleaned(self):
        p=self.run_it({'MOCK_PRIVATE_FAIL':'1'})
        self.assertEqual(p.returncode,22)
        self.assert_no_workspace()

    def test_active_adapter_refused(self):
        active=self.home/'.config/asf/asf-only-session.sh'
        active.parent.mkdir(parents=True)
        active.write_text('true\n')
        p=self.run_it()
        self.assertEqual(p.returncode,14)
        self.assert_no_workspace()

    def test_candidate_permissions_refused(self):
        self.candidate.chmod(0o644)
        p=self.run_it()
        self.assertEqual(p.returncode,11)
        self.assert_no_workspace()

    def test_candidate_execution_not_attempted(self):
        marker=self.root/'ran'
        self.candidate.write_text(f'#!/bin/bash\ntouch {marker}\n')
        self.candidate.chmod(0o600)
        p=self.run_it()
        self.assertEqual(p.returncode,0)
        self.assertFalse(marker.exists())
        self.assertIn('CANDIDATE_EXECUTION=NOT_ATTEMPTED',p.stdout)
        self.assert_no_workspace()

if __name__ == '__main__':
    unittest.main(verbosity=2)
