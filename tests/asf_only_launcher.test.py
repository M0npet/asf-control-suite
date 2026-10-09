"""Offline isolated ASF-only launcher tests. No Android, ADB or network use."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

LAUNCHER = Path(__file__).resolve().parents[1] / "scripts/phone/asf-only-launcher.sh"

TMUX = r'''#!/usr/bin/env bash
set -Eeuo pipefail
state="$MOCK_SESSIONS"
cmd="${1:?}"; shift
target=''; name=''
args=("$@")
for (( j=0; j<${#args[@]}; j++ )); do
  if [[ "${args[j]}" == '-t' || "${args[j]}" == '-s' ]]; then
    target="${args[j+1]}"; break
  fi
done
case "$cmd" in
  has-session|display-message|kill-session)
    [[ "$target" == =* ]] || exit 55
    name="${target#=}" ;;
  new-session)
    name="$target" ;;
  list-sessions)
    [[ "${args[0]}" == '-F' && "${args[1]}" == '#{session_name}|#{session_id}' ]] || exit 58 ;;
  *) exit 56 ;;
esac
case "$cmd" in
  list-sessions)
    for f in "$state"/*; do
      [[ -f "$f" ]] || continue
      printf '%s|%s\n' "${f##*/}" "$(cat "$f")"
    done ;;
  has-session)
    [[ -f "$state/$name" ]] ;;
  display-message)
    [[ -f "$state/$name" ]] || exit 1
    [[ "${args[-1]}" == '#{session_id}' ]] || exit 1
    cat "$state/$name" ;;
  kill-session)
    [[ -f "$state/$name" ]] || exit 1
    rm "$state/$name" ;;
  new-session)
    [[ ! -e "$state/$name" ]] || exit 1
    num="$(cat "$state/.seq")"
    num=$((num+1))
    printf '%s\n' "$num" > "$state/.seq"
    printf '$%s\n' "$num" > "$state/$name" ;;
esac
'''

CURL = r'''#!/usr/bin/env bash
set -Eeuo pipefail
url="${*: -1}"
if [[ -n "${MOCK_ORPHAN_CODE:-}" ]]; then
  printf '%s' "$MOCK_ORPHAN_CODE"
  exit 0
fi
if [[ "${MOCK_RESTART_PROXY_DURING_HEALTH:-0}" == 1 && -f "$MOCK_SESSIONS/asf" &&
      "$url" == */Api/ASF ]]; then
  printf '$999\n' > "$MOCK_SESSIONS/asf-proxy"
fi
if [[ "${MOCK_ORPHAN:-}" == 1 ]] || {
    [[ -f "$MOCK_SESSIONS/asf" && "${MOCK_UNHEALTHY:-}" != 1 ]];
}; then
  if [[ "$url" == *'/Api/ASF' ]]; then printf 401; else printf 200; fi
else
  printf 000
fi
'''

class AsfOnlyLauncherTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory(prefix='asfc-only-')
        self.addCleanup(td.cleanup)
        self.root = Path(td.name)
        self.home = self.root/'home'
        self.home.mkdir()
        self.bin = self.root/'bin'
        self.bin.mkdir()
        self.state_dir = self.root/'sessions'
        self.state_dir.mkdir()
        self.initial = {'asf-proxy': '$3', 'tailscale-watch': '$4', '_id': 10}
        self.put_state(self.initial)
        for name, body in [('tmux', TMUX), ('curl', CURL)]:
            self.write(self.bin/name, body)
        self.adapter = self.home/'.config/asf/asf-only-session.sh'
        self.env = dict(os.environ, HOME=str(self.home), MOCK_SESSIONS=str(self.state_dir),
                        PATH=str(self.bin) + ':' + os.environ['PATH'],
                        ASFC_ONLY_START_CONFIRMATION='I_APPROVE_ASF_ONLY_START',
                        ASFC_ONLY_HEALTH_RETRIES='2')
    @staticmethod
    def write(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o700)
    def install_adapter(self, body=None):
        if body is None:
            body = "#!/usr/bin/env bash\ntmux new-session -d -s asf -c \"$HOME\" 'safe-test-stub'\n"
        self.write(self.adapter, body)
        self.env['ASFC_ONLY_ADAPTER_SHA256'] = hashlib.sha256(self.adapter.read_bytes()).hexdigest()
    def run_launcher(self, mode='--start', extra=None):
        env = dict(self.env)
        if extra: env.update(extra)
        return subprocess.run(['bash', str(LAUNCHER), mode], env=env,
                              text=True, capture_output=True, timeout=30)
    def put_state(self, state):
        for p in self.state_dir.iterdir():
            p.unlink()
        (self.state_dir/'.seq').write_text(str(state.get('_id', 10)))
        for name, sid in state.items():
            if name != '_id':
                (self.state_dir/name).write_text(sid)
    def get_state(self):
        state = {'_id': int((self.state_dir/'.seq').read_text())}
        for p in self.state_dir.iterdir():
            if p.name != '.seq':
                state[p.name] = p.read_text().strip()
        return state
    def test_audit_no_adapter_is_read_only(self):
        p = self.run_launcher('--audit')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn('ASF_ONLY_ADAPTER=NOT_READY', p.stdout)
        self.assertIn('ASF_ONLY_AUDIT_READ_ONLY=PASS', p.stdout)
        self.assertEqual(self.get_state(), self.initial)
    def test_missing_confirmation_rejects_before_modification(self):
        self.install_adapter()
        p = self.run_launcher(extra={'ASFC_ONLY_START_CONFIRMATION': ''})
        self.assertEqual(p.returncode, 2)
        self.assertEqual(self.get_state(), self.initial)
    def test_invalid_health_retries_cannot_create_session(self):
        self.install_adapter()
        for invalid in ('0', '-1', '121', 'abc', '9999'):
            with self.subTest(retries=invalid):
                p = self.run_launcher(extra={'ASFC_ONLY_HEALTH_RETRIES': invalid})
                self.assertEqual(p.returncode, 20, p.stdout + p.stderr)
                self.assertIn('INVALID_HEALTH_RETRIES', p.stderr)
                self.assertEqual(self.get_state(), self.initial)

    def test_missing_adapter_fails_closed(self):
        p = self.run_launcher()
        self.assertEqual(p.returncode, 10)
        self.assertEqual(self.get_state(), self.initial)
    def test_bad_adapter_hash_fails_closed(self):
        self.install_adapter()
        p = self.run_launcher(extra={'ASFC_ONLY_ADAPTER_SHA256': '0'*64})
        self.assertEqual(p.returncode, 10)
        self.assertEqual(self.get_state(), self.initial)
    def test_asf_present_will_not_start_another(self):
        self.install_adapter()
        state = self.get_state(); state['asf'] = '$6'
        self.put_state(state)
        p = self.run_launcher()
        self.assertEqual(p.returncode, 11)
        self.assertEqual(self.get_state(), state)
    def test_missing_proxy_refuses_to_start(self):
        self.install_adapter()
        state = self.get_state(); del state['asf-proxy']
        self.put_state(state)
        p = self.run_launcher()
        self.assertEqual(p.returncode, 12)
        self.assertEqual(self.get_state(), state)
    def test_orphan_asf_http_refuses_duplicate(self):
        self.install_adapter()
        p = self.run_launcher(extra={'MOCK_ORPHAN': '1'})
        self.assertEqual(p.returncode, 14)
        self.assertEqual(self.get_state(), self.initial)
    def test_any_orphan_http_listener_refuses_duplicate(self):
        self.install_adapter()
        for code in ('200', '401', '404', '503'):
            with self.subTest(http_code=code):
                p = self.run_launcher(extra={'MOCK_ORPHAN_CODE': code})
                self.assertEqual(p.returncode, 14, p.stdout+p.stderr)
                self.assertIn('ORPHAN_ASF_HTTP_LISTENER', p.stderr)
                self.assertEqual(self.get_state(), self.initial)

    def test_malformed_session_id_fails_closed(self):
        self.install_adapter()
        corrupt = dict(self.initial, **{'asf-proxy': 'not-a-tmux-id'})
        self.put_state(corrupt)
        p = self.run_launcher()
        self.assertEqual(p.returncode, 13, p.stdout+p.stderr)
        self.assertEqual(self.get_state(), corrupt)

    def test_pinned_adapter_only_starts_asf(self):
        self.install_adapter()
        p = self.run_launcher()
        self.assertEqual(p.returncode, 0, p.stdout+'\n'+p.stderr)
        self.assertIn('ASF_ONLY_LAUNCH=PASS', p.stdout)
        state=self.get_state()
        self.assertIn('asf', state)
        for k in ('asf-proxy', 'tailscale-watch'):
            self.assertEqual(state[k], self.initial[k])
    def test_adapter_output_suppressed_and_snapshot_cleaned(self):
        self.install_adapter("#!/usr/bin/env bash\necho 'SECRET_IN_TEST'\n" +
                             "tmux new-session -d -s asf -c \"$HOME\" 'safe'\n")
        p = self.run_launcher()
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotIn('SECRET_IN_TEST', p.stdout + p.stderr)
        snapshots = list((self.home/'.cache/asf-control-suite').glob('asf-only-pinned.*'))
        self.assertEqual(snapshots, [])

    def test_failed_adapter_still_cleans_private_snapshot(self):
        self.install_adapter("#!/usr/bin/env bash\nexit 4\n")
        p = self.run_launcher()
        self.assertEqual(p.returncode, 17)
        snapshots = list((self.home/'.cache/asf-control-suite').glob('asf-only-pinned.*'))
        self.assertEqual(snapshots, [])
        self.assertEqual(self.get_state(), self.initial)

    def test_proxy_restart_detected_not_pass(self):
        self.install_adapter("#!/usr/bin/env bash\ntmux kill-session -t '=asf-proxy'\n"
                             "tmux new-session -d -s asf-proxy -c \"$HOME\" 'bad'\n"
                             "tmux new-session -d -s asf -c \"$HOME\" 'fake'\n")
        p = self.run_launcher()
        self.assertEqual(p.returncode, 19, p.stdout + p.stderr)
        self.assertIn('AUXILIARY_SESSION_CHANGED', p.stderr)
    def test_proxy_restart_between_http_checks_refuses_success(self):
        self.install_adapter()
        p = self.run_launcher(extra={'MOCK_RESTART_PROXY_DURING_HEALTH': '1'})
        self.assertEqual(p.returncode, 19, p.stdout+p.stderr)
        self.assertIn('AUXILIARY_SESSION_CHANGED', p.stderr)
        self.assertNotIn('ASF_ONLY_LAUNCH=PASS', p.stdout)

    def test_no_health_never_reports_success(self):
        self.install_adapter()
        p = self.run_launcher(extra={'MOCK_UNHEALTHY': '1'})
        self.assertEqual(p.returncode, 22, p.stdout+p.stderr)
        self.assertNotIn('ASF_ONLY_LAUNCH=PASS', p.stdout)
    def test_adapter_syntax_failure_rejected(self):
        self.install_adapter('#!/usr/bin/env bash\nif true; then\n')
        p = self.run_launcher()
        self.assertEqual(p.returncode, 10)
        self.assertEqual(self.get_state(), self.initial)
    def test_stale_lock_refuses(self):
        self.install_adapter()
        (self.home/'.cache/asf-control-suite/asf-only-start.lock').mkdir(parents=True)
        p = self.run_launcher()
        self.assertEqual(p.returncode, 15)
        self.assertEqual(self.get_state(), self.initial)
    def test_exact_targets_not_prefix_match(self):
        source = LAUNCHER.read_text()
        self.assertIn('tmux has-session -t "=$1"', source)
        self.assertIn("tmux list-sessions -F '#{session_name}|#{session_id}'", source)
        self.assertNotIn('tmux display-message -p -t "=$1"', source)
        self.assertNotIn('start-asf.sh', source)
        self.assertNotIn('pane_start_command', source.replace('# No eval and no pane_start_command round-trip are involved.', ''))

if __name__ == '__main__':
    unittest.main(verbosity=2)
