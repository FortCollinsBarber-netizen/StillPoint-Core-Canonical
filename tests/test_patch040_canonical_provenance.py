from __future__ import annotations
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Patch040Tests(unittest.TestCase):
    def test_patch040_provenance_remains_bound_after_later_patches(self):
        cp=json.loads((ROOT/'CHECKPOINT.json').read_text())
        mf=json.loads((ROOT/'RELEASE_MANIFEST.json').read_text())
        expected='b8391f9cf4fec0ecdf7329b82b11994d014688b5'
        self.assertEqual(cp['git']['patch039_merge_commit'],expected)
        self.assertEqual(mf['provenance']['canonical_patch039_merge'],expected)

    def test_host_installer_requires_current_canonical_commit_and_green_ci(self):
        text=(ROOT/'deploy/macos/install_signal_host.sh').read_text()
        self.assertIn('COMMIT="$(gh api "repos/$REPO/commits/main"',text)
        self.assertIn('gh run list --repo "$REPO" --commit "$COMMIT"',text)
        self.assertIn('canonical CI is not green',text)
        self.assertNotIn('PATCH_ID=',text)
        self.assertNotIn('canonical main is not Patch',text)

    def test_release_audit_guards_latest_numbered_patch_against_metadata_drift(self):
        text=(ROOT/'tools/audit_release_metadata.py').read_text()
        self.assertIn('latest_documented_patch=max(patch_docs)',text)
        docs=[]
        for path in ROOT.glob('README_PATCH_*.md'):
            m=re.fullmatch(r'README_PATCH_(\d{3})\.md',path.name)
            if m: docs.append(int(m.group(1)))
        latest=max(docs)
        mf=json.loads((ROOT/'RELEASE_MANIFEST.json').read_text())
        cp=json.loads((ROOT/'CHECKPOINT.json').read_text())

        # The newest numbered patch remains the immutable earned baseline.
        self.assertTrue(mf['patch'].startswith(f'{latest:03d}-'))

        if mf.get('program') == '0.4-autonomous-company-os':
            # Once the numbered patch train transitions into the 0.4 program,
            # current milestone identity is allowed to advance. The safety
            # invariant becomes provenance continuity: 0.4 must remain pinned
            # to the exact latest numbered baseline rather than pretending the
            # current milestone is still Patch 041.
            self.assertEqual(mf['baseline_patch'],mf['patch'])
            self.assertEqual(cp['program'],mf['program'])
            self.assertTrue(cp['last_completed_milestone'].startswith('v0.4-'))
            self.assertEqual(
                cp['git']['v04_program_base_commit'],
                mf['provenance']['canonical_patch041_merge'],
            )
            self.assertIn('0.4 baseline trails latest earned numbered patch',text)
        else:
            self.assertTrue(cp['last_completed_milestone'].startswith(f'patch-{latest:03d}-'))

if __name__=='__main__':
    unittest.main()
