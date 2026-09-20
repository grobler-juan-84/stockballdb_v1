"""Catalog application service — discover instruments and data domains.

P1 wraps the certified V1 universe constants and Explorer table registry.
Does not implement portable universe sync (P10) or Explore queries (P5).
"""

from __future__ import annotations

from sqlalchemy import inspect as sa_inspect

from stockballdb.app.errors import AppNotFoundError
from stockballdb.app.results import DataDomainInfo, FieldInfo, InstrumentInfo
from stockballdb.explorer.definitions import definition_for
from stockballdb.explorer.registry import TABLE_REGISTRY, ExplorerQueryError, get_table_spec
from stockballdb.market_data.universe import (
    V1_MARKET_SYMBOLS,
    asset_type_for_symbol,
    is_close_only_symbol,
)


def list_instruments() -> tuple[InstrumentInfo, ...]:
    """Return the current V1 market universe as application-level instruments."""
    return tuple(
        InstrumentInfo(
            symbol=symbol,
            asset_type=asset_type_for_symbol(symbol),
            close_only=is_close_only_symbol(symbol),
        )
        for symbol in V1_MARKET_SYMBOLS
    )


def list_data_domains() -> tuple[DataDomainInfo, ...]:
    """Return inspectable canonical data domains (Explorer tables) without models."""
    domains: list[DataDomainInfo] = []
    for key, spec in TABLE_REGISTRY.items():
        domains.append(
            DataDomainInfo(
                key=key,
                display_name=spec.display_name,
                date_column=spec.date_column,
                symbol_column=spec.symbol_column,
                sortable_columns=tuple(sorted(spec.sortable_columns)),
                boolean_filter_columns=tuple(sorted(spec.boolean_filter_columns)),
                supports_event_type_filter=spec.event_type_filter,
            )
        )
    return tuple(domains)


def get_fields(domain_key: str) -> tuple[FieldInfo, ...]:
    """Return fields for a data domain (column names + allowlist flags + definitions)."""
    try:
        spec = get_table_spec(domain_key)
    except ExplorerQueryError as exc:
        raise AppNotFoundError(f"unknown data domain: {domain_key!r}") from exc

    column_names = [c.key for c in sa_inspect(spec.model).columns]
    sortable = set(spec.sortable_columns)
    boolean_filters = set(spec.boolean_filter_columns)
    return tuple(
        FieldInfo(
            name=name,
            sortable=name in sortable,
            boolean_filterable=name in boolean_filters,
            definition=definition_for(name),
        )
        for name in column_names
    )
