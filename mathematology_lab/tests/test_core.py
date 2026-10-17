import sqlite3
import unittest
from mathematology_lab.core import connect, import_snapshot, list_draws, parse_csv

CSV = "draw_date,winning_numbers,bonus\n2026-10-14,04 06 22 50 53 58,11\n2026-10-10,01 13 47 50 54 59,22\n"

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.db = connect(":memory:")

    def tearDown(self):
        self.db.close()

    def test_preserves_source_number_order_and_chronology(self):
        snapshot = import_snapshot(self.db, CSV)
        draws = list_draws(self.db, snapshot)
        self.assertEqual(draws[0]["numbers"], [1, 13, 47, 50, 54, 59])
        self.assertEqual(draws[1]["numbers"], [4, 6, 22, 50, 53, 58])
        self.assertEqual(draws[1]["bonus"], 11)

    def test_import_is_idempotent(self):
        self.assertEqual(import_snapshot(self.db, CSV), import_snapshot(self.db, CSV))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM draws").fetchone()[0], 2)

    def test_invalid_draw_rejected_without_partial_write(self):
        bad = "draw_date,winning_numbers,bonus\n2026-10-14,01 01 03 04 05 06,11\n"
        with self.assertRaises(ValueError):
            import_snapshot(self.db, bad)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0], 0)

    def test_invalid_bonus_rejected(self):
        with self.assertRaises(ValueError):
            parse_csv("draw_date,winning_numbers,bonus\n2026-10-14,01 02 03 04 05 06,03\n")

if __name__ == "__main__":
    unittest.main()
