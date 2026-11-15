import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.environ.get("ASTROHEALTH_DATABASE", os.path.join(BASE_DIR, "astrohealth.db"))


@contextmanager
def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database():
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS astronauts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                call_sign TEXT NOT NULL,
                mission TEXT NOT NULL,
                role TEXT NOT NULL,
                mission_day INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'On mission'
            );
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                source TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_measurements_astronaut_metric
                ON measurements(astronaut_id, metric, recorded_at);
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                acknowledged_at TEXT
            );
            CREATE TABLE IF NOT EXISTS check_ins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                astronaut_id INTEGER NOT NULL REFERENCES astronauts(id),
                mood INTEGER NOT NULL,
                stress INTEGER NOT NULL,
                sleep_hours REAL NOT NULL,
                notes TEXT DEFAULT '',
                recorded_at TEXT NOT NULL
            );
            """
        )
        if db.execute("SELECT COUNT(*) FROM astronauts").fetchone()[0] == 0:
            cursor = db.execute(
                """INSERT INTO astronauts
                   (name, call_sign, mission, role, mission_day)
                   VALUES (?, ?, ?, ?, ?)""",
                ("Dr. Maya Chen", "ASTRA-01", "AURORA-7", "Mission Specialist", 142),
            )
            astronaut_id = cursor.lastrowid
            now = datetime.now(timezone.utc)
            samples = [
                ("heart_rate", 64, "bpm"), ("heart_rate", 67, "bpm"),
                ("heart_rate", 66, "bpm"), ("heart_rate", 70, "bpm"),
                ("heart_rate", 68, "bpm"), ("heart_rate", 72, "bpm"),
                ("heart_rate", 69, "bpm"), ("temperature", 36.7, "°C"),
                ("temperature", 36.8, "°C"), ("temperature", 36.6, "°C"),
                ("temperature", 36.9, "°C"), ("temperature", 36.7, "°C"),
                ("systolic", 116, "mmHg"), ("diastolic", 76, "mmHg"),
                ("oxygen", 98, "%"), ("sleep", 7.2, "h"),
            ]
            for index, (metric, value, unit) in enumerate(samples):
                db.execute(
                    """INSERT INTO measurements
                       (astronaut_id, metric, value, unit, source, recorded_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (astronaut_id, metric, value, unit, "Synthetic demo", (now - timedelta(hours=len(samples) - index)).isoformat()),
                )
            db.execute(
                """INSERT INTO check_ins
                   (astronaut_id, mood, stress, sleep_hours, notes, recorded_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (astronaut_id, 4, 2, 7.2, "Feeling focused after scheduled exercise.", now.isoformat()),
            )
            db.execute(
                """INSERT INTO alerts
                   (astronaut_id, severity, title, message, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (astronaut_id, "Info", "Daily check-in complete",
                 "Synthetic demo activity logged. This is not a medical assessment.",
                 "Open", now.isoformat()),
            )


def utc_now():
    return datetime.now(timezone.utc).isoformat()
