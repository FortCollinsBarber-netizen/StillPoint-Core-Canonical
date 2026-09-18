from __future__ import annotations

import hashlib
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from stillpoint.db import CompanyDB

ROOT = Path(__file__).resolve().parents[1]


def copy_migrations(destination: Path, *, through: int | None = None) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted((ROOT / "migrations").glob("[0-9][0-9][0-9]_*.sql")):
        version = int(source.name[:3])
        if through is not None and version > through:
            continue
        shutil.copy2(source, destination / source.name)


class Stage3MigrationAuditClosureTests(unittest.TestCase):
    def test_two_process_style_startup_serializes_current_upgrade(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            legacy_dir = tmp / "migrations21"
            copy_migrations(legacy_dir, through=21)
            db_path = tmp / "company.sqlite"

            old = CompanyDB(db_path, migrations_dir=legacy_dir)
            self.assertEqual(old.schema_version, 21)
            old.close()

            barrier = threading.Barrier(2)
            errors: list[Exception] = []
            versions: list[int] = []

            def open_same_db() -> None:
                try:
                    barrier.wait(timeout=5)
                    db = CompanyDB(db_path, migrations_dir=ROOT / "migrations")
                    versions.append(db.schema_version)
                    db.close()
                except Exception as exc:  # captured for assertion in parent thread
                    errors.append(exc)

            threads = [threading.Thread(target=open_same_db) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)

            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            self.assertEqual(sorted(versions), [23, 23])

            final = CompanyDB(db_path, migrations_dir=ROOT / "migrations")
            rows = final.conn.execute(
                "SELECT version, COUNT(*) FROM schema_migrations "
                "GROUP BY version HAVING COUNT(*) != 1"
            ).fetchall()
            self.assertEqual(rows, [])
            self.assertEqual(final.schema_version, 23)
            final.close()

    def test_upgrade_labels_prior_history_backfill_and_new_migration_exact(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            legacy_dir = tmp / "migrations21"
            copy_migrations(legacy_dir, through=21)
            db_path = tmp / "company.sqlite"

            old = CompanyDB(db_path, migrations_dir=legacy_dir)
            old.close()

            db = CompanyDB(db_path, migrations_dir=ROOT / "migrations")
            custody = {
                int(row["version"]): dict(row)
                for row in db.conn.execute(
                    "SELECT * FROM schema_migration_custody ORDER BY version"
                ).fetchall()
            }
            self.assertEqual(custody[1]["custody_source"], "canonical_backfill")
            self.assertEqual(custody[21]["custody_source"], "canonical_backfill")
            self.assertEqual(custody[22]["custody_source"], "applied_exact")
            self.assertEqual(custody[23]["custody_source"], "applied_exact")
            expected = hashlib.sha256(
                (ROOT / "migrations" / "022_stage3_audit_closure.sql").read_bytes()
            ).hexdigest()
            self.assertEqual(custody[22]["sha256"], expected)
            db.close()

    def test_rewritten_applied_migration_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            copied = tmp / "migrations"
            copy_migrations(copied)
            db_path = tmp / "company.sqlite"

            db = CompanyDB(db_path, migrations_dir=copied)
            self.assertEqual(db.schema_version, 22)
            db.close()

            changed = copied / "022_stage3_audit_closure.sql"
            changed.write_text(
                changed.read_text(encoding="utf-8") + "\n-- unauthorized rewrite\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "migration custody mismatch"):
                CompanyDB(db_path, migrations_dir=copied)


if __name__ == "__main__":
    unittest.main()
