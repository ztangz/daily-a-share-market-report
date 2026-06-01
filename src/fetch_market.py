from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import (
    A_SHARE_FS,
    CONCEPT_FS,
    EASTMONEY_QUOTE_URL,
    INDEXES,
    INDUSTRY_FS,
    QUOTE_FIELDS,
    SECTOR_FIELDS,
)
from .http_client import fetch_json


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    diff = data.get("diff") or []
    if isinstance(diff, dict):
        return list(diff.values())
    return diff


def _fetch_clist_page(fs: str, fields: str, sort_field: str, page: int, page_size: int) -> dict[str, Any]:
    return fetch_json(
        EASTMONEY_QUOTE_URL,
        {
            "pn": page,
            "pz": page_size,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": sort_field,
            "fs": fs,
            "fields": fields,
        },
    )


def fetch_clist(fs: str, fields: str, sort_field: str = "f3", page_size: int = 100) -> list[dict[str, Any]]:
    payload = _fetch_clist_page(fs, fields, sort_field, 1, page_size)
    return _items(payload)


def fetch_clist_all(fs: str, fields: str, sort_field: str = "f3", page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1

    while True:
        payload = _fetch_clist_page(fs, fields, sort_field, page, page_size)
        page_rows = _items(payload)
        if not page_rows:
            break

        rows.extend(page_rows)
        total = int((payload.get("data") or {}).get("total") or 0)
        if total and len(rows) >= total:
            break
        if len(page_rows) < page_size:
            break
        page += 1

    return rows


def fetch_index_quotes() -> list[dict[str, Any]]:
    secids = ",".join(item["secid"] for item in INDEXES)
    payload = fetch_json(
        "https://push2delay.eastmoney.com/api/qt/ulist.np/get",
        {
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "secids": secids,
            "fields": QUOTE_FIELDS,
        },
    )
    return _items(payload)


def fetch_indices() -> list[dict[str, Any]]:
    rows = fetch_index_quotes()
    names = {item["secid"].split(".", 1)[1]: item["name"] for item in INDEXES}

    for row in rows:
        code = str(row.get("f12", ""))
        row["display_name"] = names.get(code, row.get("f14") or code)
    return rows


def fetch_a_shares() -> list[dict[str, Any]]:
    return fetch_clist_all(A_SHARE_FS, QUOTE_FIELDS, page_size=100)


def fetch_industry_sectors() -> list[dict[str, Any]]:
    return fetch_clist(INDUSTRY_FS, SECTOR_FIELDS, page_size=120)


def fetch_concept_sectors() -> list[dict[str, Any]]:
    return fetch_clist_all(CONCEPT_FS, SECTOR_FIELDS, page_size=100)


def fetch_snapshot(now: datetime) -> dict[str, Any]:
    return {
        "fetched_at": now.isoformat(),
        "source": "eastmoney_push2delay",
        "indices": fetch_indices(),
        "stocks": fetch_a_shares(),
        "industry_sectors": fetch_industry_sectors(),
        "concept_sectors": fetch_concept_sectors(),
    }
