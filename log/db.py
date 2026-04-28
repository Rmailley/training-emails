import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional, List
import os

DB_PATH = os.getenv("LOG_DB_PATH", "./data/training_log.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS day_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL UNIQUE,
    week_number INTEGER NOT NULL,
    phase INTEGER NOT NULL,
    day_type TEXT NOT NULL DEFAULT 'normal',
    vacation_name TEXT,
    planned_session TEXT NOT NULL,
    adjusted_session TEXT,
    modification_made BOOLEAN DEFAULT 0,
    coaching_note TEXT,
    whoop_recovery INTEGER,
    whoop_hrv REAL,
    whoop_resting_hr INTEGER,
    whoop_sleep_perf INTEGER,
    whoop_yesterday_strain REAL,
    email_sent_at TEXT,
    email_message_id TEXT,
    reply_received_at TEXT,
    reply_raw TEXT,
    reply_parsed TEXT,
    compliance TEXT,
    followup_sent_at TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    week_number INTEGER NOT NULL,
    pullups INTEGER,
    pushups_2min INTEGER,
    situps_2min INTEGER,
    run_1_5mi_seconds INTEGER,
    swim_500m_seconds INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS vacation_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacation_name TEXT NOT NULL,
    date TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    activity_done TEXT,
    whoop_recovery INTEGER,
    feel TEXT,
    notes TEXT
);
"""


def init_db(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def upsert_day_log(d: date, **fields) -> None:
    """Insert or update a day_log row. Pass column names as keyword args."""
    date_str = d.isoformat()
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM day_log WHERE date=?", (date_str,)).fetchone()
        if existing:
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                vals = list(fields.values()) + [date_str]
                conn.execute(f"UPDATE day_log SET {sets} WHERE date=?", vals)
        else:
            fields["date"] = date_str
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            conn.execute(f"INSERT INTO day_log ({cols}) VALUES ({placeholders})", list(fields.values()))


def get_day_log(d: date) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM day_log WHERE date=?", (d.isoformat(),)).fetchone()


def get_recent_logs(as_of_date: date, days: int = 7) -> List[sqlite3.Row]:
    from datetime import timedelta
    start = (as_of_date - timedelta(days=days)).isoformat()
    end = as_of_date.isoformat()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM day_log WHERE date >= ? AND date < ? ORDER BY date ASC",
            (start, end),
        ).fetchall()


def get_consecutive_missed_logs(as_of_date: date) -> int:
    """Count consecutive non-Sunday, non-vacation days before as_of_date with no reply."""
    from datetime import timedelta
    count = 0
    d = as_of_date - timedelta(days=1)
    while True:
        if d < date(2025, 4, 28):
            break
        if d.weekday() == 6:  # Sunday
            d -= timedelta(days=1)
            continue
        row = get_day_log(d)
        if row is None:
            break
        if row["day_type"] in ("vacation", "vacation_exempt"):
            d -= timedelta(days=1)
            continue
        if row["compliance"] is None and row["reply_received_at"] is None:
            count += 1
            d -= timedelta(days=1)
        else:
            break
    return count


def get_weekly_compliance(week_start: date) -> dict:
    """Returns compliance stats for the week starting on `week_start` (Monday)."""
    from datetime import timedelta
    rows = []
    for i in range(7):
        d = week_start + timedelta(days=i)
        row = get_day_log(d)
        if row:
            rows.append(row)

    total = 0
    compliant = 0
    vacation_days = 0
    for row in rows:
        if row["day_type"] in ("rest",):
            continue
        if row["day_type"] in ("vacation",) or row["compliance"] == "vacation_exempt":
            vacation_days += 1
            continue
        total += 1
        if row["compliance"] in ("full", "partial"):
            compliant += 1

    rate = (compliant / total * 100) if total > 0 else None
    return {
        "total_days": total,
        "compliant_days": compliant,
        "vacation_days": vacation_days,
        "rate": rate,
    }


def insert_benchmark(week_number: int, d: date, **fields) -> None:
    fields["date"] = d.isoformat()
    fields["week_number"] = week_number
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" for _ in fields)
    with get_conn() as conn:
        conn.execute(f"INSERT INTO benchmark_log ({cols}) VALUES ({placeholders})", list(fields.values()))


def get_benchmarks() -> List[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM benchmark_log ORDER BY date DESC").fetchall()


def upsert_vacation_log(vacation_name: str, d: date, day_number: int, **fields) -> None:
    date_str = d.isoformat()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM vacation_log WHERE vacation_name=? AND date=?",
            (vacation_name, date_str),
        ).fetchone()
        if existing:
            if fields:
                sets = ", ".join(f"{k}=?" for k in fields)
                vals = list(fields.values()) + [vacation_name, date_str]
                conn.execute(f"UPDATE vacation_log SET {sets} WHERE vacation_name=? AND date=?", vals)
        else:
            fields.update({"vacation_name": vacation_name, "date": date_str, "day_number": day_number})
            cols = ", ".join(fields.keys())
            placeholders = ", ".join("?" for _ in fields)
            conn.execute(f"INSERT INTO vacation_log ({cols}) VALUES ({placeholders})", list(fields.values()))
