import hashlib
import json
import unittest

from stillpoint.calendar_core.artifact_manifest import (
    ARTIFACT_MANIFEST_VERSION,
    build_calendar_core_artifact_manifest,
    canonical_export_bytes,
)
from stillpoint.calendar_core.projection_vectors import (
    build_calendar_projection_vectors,
)
from stillpoint.calendar_core.spec import (
    build_calendar_core_spec,
)


class CalendarArtifactCustodyTests(unittest.TestCase):
    def test_manifest_separates_law_from_proof(self):
        manifest = build_calendar_core_artifact_manifest()
        self.assertEqual(
            manifest["version"],
            ARTIFACT_MANIFEST_VERSION,
        )
        self.assertEqual(
            manifest["authorityStatus"],
            "custody-only",
        )

        by_role = {
            row["role"]: row
            for row in manifest["artifacts"]
        }

        self.assertIn("calendar-law", by_role)
        self.assertIn(
            "conformance-proof-only",
            by_role,
        )
        self.assertEqual(
            manifest["compatibilityBridge"][
                "authorityStatus"
            ],
            "historical-compatibility-only",
        )

    def test_manifest_hashes_exact_export_bytes(self):
        manifest = build_calendar_core_artifact_manifest()
        by_role = {
            row["role"]: row
            for row in manifest["artifacts"]
        }

        spec_bytes = canonical_export_bytes(
            build_calendar_core_spec()
        )
        vector_bytes = canonical_export_bytes(
            build_calendar_projection_vectors()
        )

        self.assertEqual(
            by_role["calendar-law"]["sha256"],
            hashlib.sha256(
                spec_bytes
            ).hexdigest(),
        )
        self.assertEqual(
            by_role["calendar-law"]["bytes"],
            len(spec_bytes),
        )
        self.assertEqual(
            by_role[
                "conformance-proof-only"
            ]["sha256"],
            hashlib.sha256(
                vector_bytes
            ).hexdigest(),
        )
        self.assertEqual(
            by_role[
                "conformance-proof-only"
            ]["bytes"],
            len(vector_bytes),
        )

    def test_manifest_is_deterministic(self):
        first = canonical_export_bytes(
            build_calendar_core_artifact_manifest()
        )
        second = canonical_export_bytes(
            build_calendar_core_artifact_manifest()
        )
        self.assertEqual(first, second)

    def test_manifest_contains_no_pilot_enactment_authority(self):
        serialized = json.dumps(
            build_calendar_core_artifact_manifest()
        )
        self.assertNotIn(
            '"status": "enacted"',
            serialized,
        )
        self.assertNotIn(
            '"publicationDigest"',
            serialized,
        )


if __name__ == "__main__":
    unittest.main()
