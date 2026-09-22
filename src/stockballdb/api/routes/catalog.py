"""Catalog HTTP routes — wrap ``stockballdb.app.read.catalog`` only."""

from __future__ import annotations

from fastapi import APIRouter

from stockballdb.app.read import catalog as catalog_app
from stockballdb.api.schemas import DataDomainOut, FieldOut, InstrumentOut

router = APIRouter(tags=["catalog"])


@router.get("/instruments", response_model=list[InstrumentOut])
def list_instruments() -> list[InstrumentOut]:
    return [InstrumentOut.from_app(item) for item in catalog_app.list_instruments()]


@router.get("/domains", response_model=list[DataDomainOut])
def list_domains() -> list[DataDomainOut]:
    return [DataDomainOut.from_app(item) for item in catalog_app.list_data_domains()]


@router.get("/domains/{domain_key}/fields", response_model=list[FieldOut])
def list_fields(domain_key: str) -> list[FieldOut]:
    return [FieldOut.from_app(item) for item in catalog_app.get_fields(domain_key)]
