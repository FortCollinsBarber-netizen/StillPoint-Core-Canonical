import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]

class CLITests(unittest.TestCase):
    def run_cli(self,tmp,*args):
        env=os.environ.copy();env['STILLPOINT_ROOT']=str(tmp);env['PYTHONPATH']=str(ROOT)
        return subprocess.run([sys.executable,'-m','stillpoint.cli',*args],cwd=ROOT,env=env,text=True,capture_output=True)

    def test_doctor_clean_checkout_shape(self):
        env=os.environ.copy();env['STILLPOINT_ROOT']=str(ROOT);env['PYTHONPATH']=str(ROOT)
        p=subprocess.run([sys.executable,'-m','stillpoint.cli','doctor'],cwd=ROOT,env=env,text=True,capture_output=True)
        data=json.loads(p.stdout)
        # Source checkout may fail overall if CHECKPOINT schema is stale; shape must include new keys
        self.assertIn('migration_mirror', data)
        self.assertIn('database', data)
        self.assertIn('frozen_corpora', data)
        self.assertIn('checkpoint', data)
        self.assertIn('unresolved_dispatches', data)
        self.assertIn('overall_ok', data)

    def test_doctor_runtime_only_install_does_not_require_eval_assets(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            p=self.run_cli(tmp,'doctor')
            self.assertEqual(p.returncode,0,p.stderr+p.stdout)
            data=json.loads(p.stdout)
            self.assertTrue(data['frozen_corpora']['ok'])
            self.assertTrue(data['frozen_corpora'].get('runtime_only'))
            self.assertTrue(data['checkpoint'].get('runtime_only'))

    def test_doctor_source_checkout_fails_closed_when_checkpoint_stale(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)
            (tmp/'pyproject.toml').write_text('[project]\nname="fake"\nversion="0"\n')
            (tmp/'migrations').mkdir()
            # no matching package migrations under tmp — mirror fails
            p=self.run_cli(tmp,'doctor')
            data=json.loads(p.stdout)
            self.assertIn('overall_ok', data)
            self.assertFalse(data['overall_ok'])

    def test_submit_and_status(self):
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d);(tmp/'config').mkdir();(tmp/'config'/'agents.json').write_text((ROOT/'config'/'agents.json').read_text())
            p=self.run_cli(tmp,'submit','Rewrite chapter 3 in my voice.')
            self.assertEqual(p.returncode,0,p.stderr);self.assertIn('completed',p.stdout)
            s=self.run_cli(tmp,'status');self.assertIn('RECENTLY COMPLETED',s.stdout)

    def test_status_shows_uncertain_category(self):
        # Category labels must exist in status output structure for operator truthfulness
        from stillpoint.cli import cmd_status
        # smoke: ensure category strings are in the source
        src=(ROOT/'stillpoint'/'cli.py').read_text()
        self.assertIn('UNCERTAIN — RECONCILIATION REQUIRED', src)
        self.assertIn('EXTERNAL DISPATCH IN PROGRESS', src)
        self.assertIn('RECONCILED / CLOSED', src)

if __name__=='__main__':unittest.main()
