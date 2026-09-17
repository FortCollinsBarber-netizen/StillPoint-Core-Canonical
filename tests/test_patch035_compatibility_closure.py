from __future__ import annotations
import hashlib, importlib.util, json, sys, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class Patch035CompatibilityClosureTests(unittest.TestCase):
    def test_real_contract_module_survives_patch021_import(self):
        import stillpoint.contracts.models as before
        self.assertTrue(hasattr(before,'ActionEvidence'))
        self.assertTrue(hasattr(before.ActionRequest,'permitted'))
        p=ROOT/'tests'/'test_patch021_signal_safety.py'
        spec=importlib.util.spec_from_file_location('_patch021_probe',p)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        import stillpoint.contracts.models as after
        self.assertIs(before,after)
        self.assertTrue(hasattr(after,'ActionEvidence'))

    def test_governance_fixture_is_nonsecret_and_exact_mailbox(self):
        p=ROOT/'tests'/'fixtures'/'signal_icloud_personal_business.draft.json'
        raw=json.loads(p.read_text())
        self.assertEqual(raw['mailbox'],{'provider':'icloud','account':'fortcollinsbarber@icloud.com','jurisdiction':'personal_business'})
        text=p.read_text().lower()
        self.assertNotIn('students.ccu.edu',text)
        self.assertNotIn('gmail',text)
        def walk(v):
            if isinstance(v,dict):
                for k,val in v.items():
                    self.assertNotIn(k.lower(),{'password','app_password','access_token','api_key','secret'})
                    walk(val)
            elif isinstance(v,list):
                for item in v: walk(item)
        walk(raw)

    def test_lease_events_use_causal_tie_breaker(self):
        src=(ROOT/'stillpoint'/'workers.py').read_text()
        self.assertIn('ORDER BY occurred_at,rowid',src)

    def test_legacy_signal_event_can_inherit_configured_account_only_when_omitted(self):
        src=(ROOT/'stillpoint'/'signal_email.py').read_text()
        self.assertIn("m.get('account') or self.account",src)
        self.assertIn("mailbox jurisdiction mismatch",src)

if __name__=='__main__':unittest.main()
