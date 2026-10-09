"""Offline integration rehearsal: only synthetic Boot text and fake tmux/IPC.
Never run the private device candidate, ADB, PRoot, or real ASF.
"""
import hashlib
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARER = ROOT / 'scripts/phone/prepare-asf-only-adapter.sh'
BOOT_FIXTURE = runpy.run_path(str(ROOT/'tests/prepare_asf_only_adapter.test.py'))['boot']
def launcher_fixture():
    return runpy.run_path(str(ROOT/'tests/asf_only_launcher.test.py'))['AsfOnlyLauncherTests']


class SyntheticIntegration(unittest.TestCase):
    def setUp(self):
        self.stub = launcher_fixture()('test_pinned_adapter_only_starts_asf')
        self.stub.setUp()
        self.addCleanup(self.stub.doCleanups)
        self.boot = self.stub.root / 'synthetic-boot.sh'
        self.boot.write_text(BOOT_FIXTURE())
        self.candidate = self.stub.home / '.cache/asf-control-suite/candidates/asf-only-session.candidate.sh'
        self.marker = self.stub.root / 'FORBIDDEN_EXECUTION'
        for name in ('proot-distro', 'adb', 'ArchiSteamFarm'):
            self.stub.write(self.stub.bin/name,
                            '#!/bin/sh\nprintf forbidden > "$SYNTHETIC_MARKER"\nexit 99\n')
        self.stub.env['SYNTHETIC_MARKER'] = str(self.marker)

    def prepare(self):
        env = dict(self.stub.env, ASFC_BOOT_FILE=str(self.boot),
                   ASFC_CANDIDATE_PATH=str(self.candidate))
        p = subprocess.run(['bash', str(PREPARER), '--prepare'], env=env,
                           text=True, capture_output=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn('ADAPTER_NOT_EXECUTED=PASS', p.stdout)
        self.assertEqual(stat.S_IMODE(self.candidate.stat().st_mode), 0o600)
        self.assertEqual(self.stub.get_state(), self.stub.initial)
        self.assertFalse(self.marker.exists())

    def stage_synthetic_only(self):
        self.prepare()
        self.stub.adapter.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.candidate, self.stub.adapter)
        self.stub.env['ASFC_ONLY_ADAPTER_SHA256'] = hashlib.sha256(
            self.stub.adapter.read_bytes()).hexdigest()

    def test_preparation_never_launches(self):
        self.prepare()
        self.assertFalse(self.stub.adapter.exists())

    def test_fake_end_to_end_preserves_auxiliary_sessions(self):
        self.stage_synthetic_only()
        p = self.stub.run_launcher()
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertIn('ASF_ONLY_LAUNCH=PASS', p.stdout)
        s = self.stub.get_state()
        self.assertIn('asf', s)
        for name in ('asf-proxy', 'tailscale-watch'):
            self.assertEqual(s[name], self.stub.initial[name])
        self.assertEqual(s['_id'], self.stub.initial['_id'] + 1)
        self.assertFalse(self.marker.exists())

    def test_missing_confirmation_refuses(self):
        self.stage_synthetic_only()
        p = self.stub.run_launcher(extra={'ASFC_ONLY_START_CONFIRMATION': ''})
        self.assertEqual(p.returncode, 2)
        self.assertEqual(self.stub.get_state(), self.stub.initial)

    def test_invalid_hash_refuses(self):
        self.stage_synthetic_only()
        p = self.stub.run_launcher(extra={'ASFC_ONLY_ADAPTER_SHA256': 'f'*64})
        self.assertEqual(p.returncode, 10)
        self.assertEqual(self.stub.get_state(), self.stub.initial)

    def test_orphan_ipc_refuses(self):
        self.stage_synthetic_only()
        p = self.stub.run_launcher(extra={'MOCK_ORPHAN': '1'})
        self.assertEqual(p.returncode, 14)
        self.assertEqual(self.stub.get_state(), self.stub.initial)

    def test_existing_asf_refuses_duplicate(self):
        self.stage_synthetic_only()
        initial = dict(self.stub.initial, asf='$88')
        self.stub.put_state(initial)
        p = self.stub.run_launcher()
        self.assertEqual(p.returncode, 11)
        self.assertEqual(self.stub.get_state(), initial)


if __name__ == '__main__':
    unittest.main(verbosity=2)
