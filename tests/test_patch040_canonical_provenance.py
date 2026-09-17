from __future__ import annotations
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Patch040Tests(unittest.TestCase):
    def test_release_identity_is_patch040_and_binds_patch039_merge(self):
        cp=json.loads((ROOT/'CHECKPOINT.json').read_text())
        mf=json.loads((ROOT/'RELEASE_MANIFEST.json').read_text())
        self.assertEqual(cp['last_completed_milestone'],'patch-040-canonical-provenance-closure')
        self.assertEqual(cp['release_candidate']['closure_patch'],'040')
        self.assertEqual(mf['patch'],'040-canonical-provenance-closure')
        expected='b8391f9cf4fec0ecdf7329b82b11994d014688b5'
        self.assertEqual(cp['git']['patch039_merge_commit'],expected)
        self.assertEqual(mf['provenance']['canonical_patch039_merge'],expected)

    def test_host_installer_requires_current_patch040_identity(self):
        text=(ROOT/'deploy/macos/install_signal_host.sh').read_text()
        self.assertIn('test "$PATCH_ID" = "040-canonical-provenance-closure"',text)
        self.assertNotIn('test "$PATCH_ID" = "038-production-host-closure"',text)

    def test_release_audit_guards_latest_numbered_patch_against_metadata_drift(self):
        text=(ROOT/'tools/audit_release_metadata.py').read_text()
        self.assertIn('latest_documented_patch=max(patch_docs)',text)
        docs=[]
        for path in ROOT.glob('README_PATCH_*.md'):
            m=re.fullmatch(r'README_PATCH_(\d{3})\.md',path.name)
            if m: docs.append(int(m.group(1)))
        self.assertEqual(max(docs),40)

if __name__=='__main__':
    unittest.main()
