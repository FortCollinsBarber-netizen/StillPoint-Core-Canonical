import datetime as dt
import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "generate_common_calendar_v2.py"
)
SPEC = importlib.util.spec_from_file_location(
    "common_calendar_v2",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
v2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v2)


class CommonCalendarV2Tests(unittest.TestCase):
    def test_default_projection_is_fifty_exact_364_day_years(self):
        doc = v2.generate(
            first_year_label=1,
            first_opening=dt.date(2026, 1, 1),
            authority_id="TEST",
        )
        self.assertEqual(len(doc["years"]), 50)
        self.assertEqual(
            doc["projectionSemantics"]["openingCivilDate"]["role"],
            "external-translation-only",
        )
        self.assertFalse(
            doc["projectionSemantics"]["openingCivilDate"]["gridAuthority"]
        )
        self.assertEqual(doc["years"][0]["openingCivilDate"], "2026-01-01")
        for first, second in zip(doc["years"], doc["years"][1:]):
            a = dt.date.fromisoformat(first["openingCivilDate"])
            b = dt.date.fromisoformat(second["openingCivilDate"])
            self.assertEqual((b - a).days, 364)
            self.assertEqual(second["year"], first["year"] + 1)

    def test_projection_emits_only_fixed_surface_year_fields(self):
        doc = v2.generate(
            first_year_label=1,
            first_opening=dt.date(2026, 1, 1),
            count=2,
            authority_id="TEST",
        )
        self.assertEqual(
            set(doc["years"][0]),
            {"year", "openingCivilDate"},
        )
        self.assertEqual(
            set(doc["years"][1]),
            {"year", "openingCivilDate"},
        )

    def test_projection_digest_detects_tampering(self):
        doc = v2.generate(
            first_year_label=1,
            first_opening=dt.date(2026, 1, 1),
            count=2,
            authority_id="TEST",
        )
        doc["years"][1]["openingCivilDate"] = "2027-01-01"
        with self.assertRaises(v2.PublicationValidationError):
            v2.validate_publication_document(doc)


if __name__ == "__main__":
    unittest.main()
