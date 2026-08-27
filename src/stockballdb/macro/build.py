"""Build macro_conditions from FRED/ALFRED into PostgreSQL."""

from __future__ import annotations

import requests
from sqlalchemy.engine import Engine

from stockballdb.macro.derive import (
    MacroConditionsValidationError,
    assemble_macro_frame,
    load_trading_days,
    upsert_macro_conditions,
)
from stockballdb.macro.pit import (
    build_current_series_on_trading_days,
    build_distinct_inflation_release_yoy,
    build_pit_level_series_on_trading_days,
    parse_alfred_rows,
)
from stockballdb.macro.series import MACRO_SERIES, MACRO_SERIES_BY_FIELD
from stockballdb.providers.fred import (
    FredError,
    fetch_all_vintages,
    fetch_current_observations,
)


def sync_macro_conditions(engine: Engine, api_key: str):
    """
    Fetch FRED/ALFRED, align to trading_days, derive, upsert.

    Returns (frame, inflation_releases).
    """
    trading_days = load_trading_days(engine)
    session = requests.Session()
    series_map: dict = {}
    inflation_releases = []

    try:
        for spec in MACRO_SERIES:
            if spec.pit_vintage:
                rows = fetch_all_vintages(spec.series_id, api_key, session=session)
                vintages = parse_alfred_rows(rows)
                if not vintages:
                    raise MacroConditionsValidationError(
                        f"no ALFRED rows for {spec.series_id}"
                    )
                series_map[spec.field] = build_pit_level_series_on_trading_days(
                    vintages,
                    trading_days,
                    spec.timing,
                    compute_yoy=spec.compute_yoy_pc1,
                )
                if spec.field == "inflation_rate":
                    inflation_releases = build_distinct_inflation_release_yoy(
                        vintages, trading_days, spec.timing
                    )
            else:
                rows = fetch_current_observations(
                    spec.series_id, api_key, session=session
                )
                series_map[spec.field] = build_current_series_on_trading_days(
                    rows,
                    trading_days,
                    spec.timing,
                    forward_fill=spec.forward_fill,
                    walcl_release_lag=(spec.field == "fed_balance_sheet"),
                )
    except FredError as exc:
        raise MacroConditionsValidationError(str(exc)) from exc
    finally:
        session.close()

    missing = set(MACRO_SERIES_BY_FIELD) - set(series_map)
    if missing:
        raise MacroConditionsValidationError(f"missing series fields: {sorted(missing)}")

    frame = assemble_macro_frame(
        trading_days, series_map, inflation_releases=inflation_releases
    )
    upsert_macro_conditions(engine, frame)
    return frame, inflation_releases
