"""Diagnose trading_days vs macro_conditions spine mismatch."""
from __future__ import annotations

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from stockballdb.db import get_engine, reset_engine

reset_engine()
eng = get_engine()
with eng.connect() as conn:
    for t in ("trading_days", "macro_conditions", "calendar_context"):
        r = conn.execute(
            text(f"SELECT COUNT(*), MIN(date), MAX(date) FROM {t}")
        ).one()
        print(f"{t}: count={r[0]} min={r[1]} max={r[2]}")
    for label, sql in [
        ("trading_days tail", "SELECT date FROM trading_days WHERE date >= '2026-08-25' ORDER BY date"),
        ("macro tail", "SELECT date FROM macro_conditions WHERE date >= '2026-08-25' ORDER BY date"),
        ("calendar tail", "SELECT date FROM calendar_context WHERE date >= '2026-08-25' ORDER BY date"),
    ]:
        rows = conn.execute(text(sql)).all()
        print(f"{label}:", [x[0] for x in rows])
    orphan = conn.execute(
        text(
            """
            SELECT td.date FROM trading_days td
            LEFT JOIN macro_conditions mc ON mc.date = td.date
            WHERE mc.date IS NULL
            ORDER BY td.date DESC LIMIT 5
            """
        )
    ).all()
    print("trading_days without macro_conditions:", [x[0] for x in orphan])
