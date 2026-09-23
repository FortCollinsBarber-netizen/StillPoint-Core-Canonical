import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "generate_common_calendar_v33.py"
)
SPEC = importlib.util.spec_from_file_location(
    "historical_common_calendar_v33",
    MODULE_PATH,
)
assert SPEC and SPEC.loader
v33 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v33)


class HistoricalCommonCalendarV33Tests(unittest.TestCase):
    def test_v33_generator_is_fail_closed_and_non_operational(self):
        with self.assertRaises(v33.SupersededCalendarModelError):
            v33.generate()


if __name__ == "__main__":
    unittest.main()
