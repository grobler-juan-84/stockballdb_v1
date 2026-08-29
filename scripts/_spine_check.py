"""Quick spine alignment check."""
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import os

load_dotenv()
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    for t in ("trading_days", "macro_conditions", "calendar_context"):
        r = c.execute(
            text(
                f"""
                SELECT COUNT(*) AS n, MIN(date) AS d0, MAX(date) AS d1,
                       COUNT(*) - COUNT(DISTINCT date) AS dups
                FROM {t}
                """
            )
        ).mappings().one()
        orphan = c.execute(
            text(
                f"""
                SELECT COUNT(*) FROM {t} x
                LEFT JOIN trading_days td ON td.date = x.date
                WHERE td.date IS NULL
                """
            )
        ).scalar()
        missing = c.execute(
            text(
                f"""
                SELECT COUNT(*) FROM trading_days td
                LEFT JOIN {t} x ON x.date = td.date
                WHERE x.date IS NULL
                """
            )
        ).scalar()
        print(
            f"{t}: rows={r['n']} first={r['d0']} last={r['d1']} "
            f"dups={r['dups']} orphan={orphan} missing_from_td={missing}"
        )
