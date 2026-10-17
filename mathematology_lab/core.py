"""Validated, provenance-aware NY Lotto storage. No model assumptions are imposed."""
import csv
import hashlib
import io
import json
import sqlite3
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  id TEXT PRIMARY KEY, source TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  row_count INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS draws (
  snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
  draw_date TEXT NOT NULL, raw_numbers TEXT NOT NULL, bonus INTEGER,
  PRIMARY KEY(snapshot_id, draw_date)
);
CREATE TABLE IF NOT EXISTS findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT NOT NULL,
  engine TEXT NOT NULL, algorithm TEXT NOT NULL, version TEXT NOT NULL,
  cutoff_date TEXT NOT NULL, seed INTEGER, payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY(snapshot_id) REFERENCES snapshots(id)
);
"""

def connect(path="mathematology_lab.sqlite3"):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection

def parse_csv(content):
    reader = csv.DictReader(io.StringIO(content))
    if not {"draw_date", "winning_numbers"}.issubset(reader.fieldnames or []):
        raise ValueError("CSV needs draw_date and winning_numbers columns")
    results = []
    seen = set()
    for row in reader:
        day = date.fromisoformat(row["draw_date"].strip()).isoformat()
        numbers = [int(n) for n in row["winning_numbers"].replace(",", " ").split()]
        if len(numbers) != 6 or len(set(numbers)) != 6 or any(n < 1 or n > 59 for n in numbers):
            raise ValueError(f"Invalid six-number draw on {day}")
        raw_bonus = (row.get("bonus") or "").strip()
        bonus = int(raw_bonus) if raw_bonus else None
        if bonus is not None and (bonus < 1 or bonus > 59 or bonus in numbers):
            raise ValueError(f"Invalid bonus on {day}")
        if day in seen:
            raise ValueError(f"Duplicate draw date: {day}")
        seen.add(day)
        results.append((day, numbers, bonus))
    if not results:
        raise ValueError("CSV contains no draws")
    return sorted(results, key=lambda item: item[0])

def import_snapshot(connection, content, source="uploaded_csv"):
    rows = parse_csv(content)
    canonical = json.dumps(rows, separators=(",", ":"))
    snapshot_id = hashlib.sha256(canonical.encode()).hexdigest()
    with connection:
        connection.execute(
            "INSERT OR IGNORE INTO snapshots(id,source,row_count) VALUES(?,?,?)",
            (snapshot_id, source, len(rows)))
        connection.executemany(
            "INSERT OR IGNORE INTO draws(snapshot_id,draw_date,raw_numbers,bonus) VALUES(?,?,?,?)",
            [(snapshot_id, day, json.dumps(numbers), bonus) for day, numbers, bonus in rows])
    return snapshot_id

def list_draws(connection, snapshot_id):
    return [
        {"date": day, "numbers": json.loads(numbers), "bonus": bonus}
        for day, numbers, bonus in connection.execute(
            "SELECT draw_date,raw_numbers,bonus FROM draws WHERE snapshot_id=? ORDER BY draw_date",
            (snapshot_id,))]
