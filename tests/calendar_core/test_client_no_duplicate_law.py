import unittest
from pathlib import Path


class ClientNoDuplicateLawTests(unittest.TestCase):
    def test_apple_projection_does_not_hardcode_calendar_law(self):
        root = Path(__file__).resolve().parents[2]
        production_files = [
            root / "clients/apple-watch/CivicClock/Shared/CivicCalendarEngine.swift",
            root / "clients/apple-watch/CivicClock/Shared/SolarBoundaryCalculator.swift",
        ]
        forbidden = [
            "90.8333",
            "[30, 30, 31",
            "baseYearDays = 364",
            "quarterDays = 91",
        ]

        for path in production_files:
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(
                    token,
                    text,
                    f"{path} duplicates constitutional law token {token!r}",
                )


if __name__ == "__main__":
    unittest.main()
