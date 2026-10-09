"""Offline test: never executes candidate or changes real tmux/Android."""
from pathlib import Path
import os, subprocess, tempfile, unittest, stat
SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/phone/prepare-asf-only-adapter.sh'


def boot(variant='valid'):
    lines=['# unused']*85
    lines[22]='if ! tmux has-session -t asf; then'
    lines[24]='echo ignored'
    lines[25]='tmux new-session -d -s asf "while true; do'
    lines[26]='  echo redacted # PRIVATE_PASSWORD_123'
    lines[27]='  proot-distro login debian -- /bin/bash -lc true'
    lines[28]='  cd /opt/asf'
    lines[29]='  ./ArchiSteamFarm'
    lines[30]='  sleep 3'
    lines[31]='done"'
    lines[34]='echo aux skip'
    lines[35]='fi'
    if variant == 'unsafe': lines[26]='  echo asf-proxy; echo SECRET_TOKEN'
    if variant == 'other_session': lines[25]=lines[25].replace('-s asf ', '-s asf-proxy ')
    if variant == 'invalid_shell': lines[31]="done\" '"
    if variant == 'missing_proot': lines[27]=' echo incorrect'
    return '\n'.join(lines)+'\n'

class Tests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='asfc-adapter-test-')
        self.addCleanup(temp.cleanup)
        self.p=Path(temp.name)
        self.file=self.p/'boot.sh'
        self.out=self.p/'private'/'candidate.sh'
        self.marker=self.p/'EXECUTED'
        self.file.write_text(boot())
        self.env=dict(os.environ,ASFC_BOOT_FILE=str(self.file),ASFC_CANDIDATE_PATH=str(self.out))
    def run_it(self,mode='--audit'):
        return subprocess.run(['bash',str(SCRIPT),mode],env=self.env,text=True,capture_output=True,timeout=10)
    def test_audit_static_no_write(self):
        p=self.run_it()
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertIn('ADAPTER_NOT_EXECUTED=PASS',p.stdout)
        self.assertIn('CANDIDATE_FILE=NOT_WRITTEN',p.stdout)
        self.assertFalse(self.out.exists())
    def test_prepare_candidate_private_no_execution(self):
        self.file.write_text(boot().replace('echo redacted',f'touch {self.marker}; echo redacted'))
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertTrue(self.out.exists())
        self.assertFalse(self.marker.exists())
        self.assertEqual(stat.S_IMODE(self.out.stat().st_mode),0o600)
        self.assertIn('proot-distro',self.out.read_text())
        self.assertNotIn('echo aux skip',self.out.read_text())
    def test_fail_closed_auxiliary_reference(self):
        self.file.write_text(boot('unsafe'))
        p=self.run_it('--prepare')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('ASF_FRAGMENT=UNSAFE_TOKEN',p.stdout)
        self.assertFalse(self.out.exists())
    def test_dotdot_alias_cannot_write_active_adapter(self):
        home = self.p/'home'
        active = home/'.config/asf/asf-only-session.sh'
        active.parent.mkdir(parents=True)
        self.env['HOME'] = str(home)
        self.env['ASFC_CANDIDATE_PATH'] = str(active.parent/'..'/'asf'/'asf-only-session.sh')
        p = self.run_it('--prepare')
        self.assertEqual(p.returncode, 13, p.stdout+p.stderr)
        self.assertIn('CANDIDATE_PATH=EXECUTABLE_PATH_REFUSED', p.stdout)
        self.assertFalse(active.exists())

    def test_symlinked_parent_cannot_write_active_adapter(self):
        home = self.p/'home'
        active = home/'.config/asf/asf-only-session.sh'
        active.parent.mkdir(parents=True)
        alias = self.p/'candidate-alias'
        alias.symlink_to(active.parent, target_is_directory=True)
        self.env['HOME'] = str(home)
        self.env['ASFC_CANDIDATE_PATH'] = str(alias/'asf-only-session.sh')
        p = self.run_it('--prepare')
        self.assertEqual(p.returncode, 13, p.stdout+p.stderr)
        self.assertFalse(active.exists())

    def test_no_secret_in_output(self):
        p=self.run_it('--audit')
        self.assertNotIn('PRIVATE_PASSWORD_123',p.stdout+p.stderr)
        self.assertNotIn(str(self.p),p.stdout+p.stderr)
    def test_wrong_session_refused(self):
        self.file.write_text(boot('other_session'))
        p=self.run_it('--prepare')
        self.assertNotEqual(p.returncode,0)
        self.assertFalse(self.out.exists())
    def test_truncated_shell_refused(self):
        self.file.write_text(boot('invalid_shell'))
        p=self.run_it('--prepare')
        self.assertNotEqual(p.returncode,0)
        self.assertFalse(self.out.exists())
    def test_missing_prerequisite_refused(self):
        self.file.write_text(boot('missing_proot'))
        p=self.run_it('--prepare')
        self.assertNotEqual(p.returncode,0)
        self.assertFalse(self.out.exists())
    def test_candidate_not_overwritten(self):
        self.out.parent.mkdir(parents=True)
        self.out.write_text('KEEP_ORIGINAL')
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,14)
        self.assertEqual(self.out.read_text(),'KEEP_ORIGINAL')
    def test_competing_candidate_commit_is_not_false_success(self):
        # Simulate destination appearing between preflight and atomic link.
        fakebin = self.p/'fakebin'
        fakebin.mkdir()
        fake_link = fakebin/'ln'
        fake_link.write_text('#!/bin/sh\nprintf RACE_WINNER > "$ASFC_CANDIDATE_PATH"\nexit 1\n')
        fake_link.chmod(0o700)
        self.env['PATH'] = str(fakebin) + ':' + os.environ['PATH']
        p = self.run_it('--prepare')
        self.assertEqual(p.returncode, 18, p.stdout + p.stderr)
        self.assertIn('CANDIDATE_COMMIT_REFUSED', p.stdout)
        self.assertNotIn('CANDIDATE_FILE=PRIVATE_REVIEW_ONLY', p.stdout)
        self.assertEqual(self.out.read_text(), 'RACE_WINNER')
        self.assertEqual(list(self.out.parent.glob('.asfc-candidate.*')), [])

    def test_symlink_output_refused(self):
        target=self.p/'target'
        target.write_text('KEEP')
        self.out.parent.mkdir(parents=True)
        self.out.symlink_to(target)
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,14)
        self.assertEqual(target.read_text(),'KEEP')
    def test_syntax_only_never_calls_tmux(self):
        fake=self.p/'tmux'
        fake.write_text(f'#!/bin/sh\ntouch "{self.marker}"\n')
        fake.chmod(0o700)
        self.env['PATH']=str(self.p)+':'+os.environ['PATH']
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        self.assertFalse(self.marker.exists())
    def test_stanza_line_number_change_refused(self):
        self.file.write_text(boot().replace('tmux new-session', 'tmux next-session'))
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,6)
        self.assertFalse(self.out.exists())
    def test_launch_command_substitution_rejected_without_execution(self):
        body=boot().replace('echo redacted',f'echo $(touch {self.marker}) redacted')
        self.file.write_text(body)
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,9,p.stdout+p.stderr)
        self.assertIn('ASF_FRAGMENT=UNSAFE_TOKEN',p.stdout)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.out.exists())
        self.assertNotIn(str(self.marker),p.stdout+p.stderr)
    def test_backtick_command_substitution_rejected(self):
        body=boot().replace('echo redacted',f'echo `touch {self.marker}` redacted')
        self.file.write_text(body)
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,9,p.stdout+p.stderr)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.out.exists())
    def test_two_tmux_operations_on_same_line_rejected(self):
        body=boot().replace('echo redacted', 'tmux new-session -d -s asf; tmux new-session -d -s asf; echo redacted')
        self.file.write_text(body)
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,10,p.stdout+p.stderr)
        self.assertFalse(self.out.exists())
    def test_duplicate_tmux_new_session_refused(self):
        body=boot().replace('echo redacted', 'tmux new-session -d -s asf; echo redacted')
        self.file.write_text(body)
        p=self.run_it('--prepare')
        self.assertEqual(p.returncode,10)
        self.assertFalse(self.out.exists())
if __name__=='__main__': unittest.main(verbosity=2)
