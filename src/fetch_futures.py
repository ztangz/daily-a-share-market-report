from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .config import EASTMONEY_QUOTE_URL
from .http_client import fetch_json


FUTURES_FIELDS = ",".join(
    [
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f12",
        "f13",
        "f14",
        "f15",
        "f16",
        "f17",
        "f18",
    ]
)
FUTURES_FS = ["m:113", "m:114", "m:115", "m:142", "m:8"]
SINA_KLINE_URL = "https://stock2.finance.sina.com.cn/futures/api/json.php/IndexService.getInnerFuturesDailyKLine"


def _items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data") or {}
    diff = data.get("diff") or []
    if isinstance(diff, dict):
        return list(diff.values())
    return diff


def _fetch_clist_all(fs: str, fields: str, page_size: int = 100) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = fetch_json(
            EASTMONEY_QUOTE_URL,
            {
                "pn": page,
                "pz": page_size,
                "po": 1,
                "np": 1,
                "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": fs,
                "fields": fields,
            },
        )
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


def _as_float(value: Any) -> float | None:
    if value in (None, "", "-", "null"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sina_symbol(code: str) -> str | None:
    if code.isdigit():
        return None
    if code.endswith("m") and len(code) > 1:
        return f"{code[:-1].upper()}0"
    if code.endswith("M") and len(code) > 1:
        return f"{code[:-1].upper()}0"
    match = re.match(r"([A-Za-z]+)", code)
    if match:
        return f"{match.group(1).upper()}0"
    return None


def _fetch_sina_kline(symbol: str) -> list[list[Any]]:
    url = f"{SINA_KLINE_URL}?symbol={symbol}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.sina.com.cn/",
        },
    )
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                text = response.read().decode("utf-8", errors="replace")
            if text.strip() == "null":
                return []
            rows = json.loads(text)
            if not isinstance(rows, list):
                return []
            return rows
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            time.sleep(0.5 * (attempt + 1))
    return []


def _period_pct(rows: list[list[Any]], days: int) -> float | None:
    valid = [row for row in rows if len(row) >= 5 and _as_float(row[4]) is not None]
    if len(valid) <= days:
        return None
    latest = _as_float(valid[-1][4])
    base = _as_float(valid[-days - 1][4])
    if not latest or not base:
        return None
    return round((latest / base - 1) * 100, 2)


def _clean_future(row: dict[str, Any]) -> dict[str, Any]:
    code = str(row.get("f12") or "")
    name = row.get("f14") or code
    return {
        "code": code,
        "market": row.get("f13"),
        "name": name,
        "price": _as_float(row.get("f2")),
        "pct_today": _as_float(row.get("f3")),
        "change": _as_float(row.get("f4")),
        "amount_yi": round((_as_float(row.get("f6")) or 0) / 100_000_000, 2),
        "high": _as_float(row.get("f15")),
        "low": _as_float(row.get("f16")),
        "open": _as_float(row.get("f17")),
        "prev_close": _as_float(row.get("f18")),
        "sina_symbol": _sina_symbol(code),
    }


def _is_primary_contract(row: dict[str, Any]) -> bool:
    name = row["name"]
    code = row["code"]
    if "次主" in name:
        return False
    return "主连" in name or "主力" in name or "连续" in name or code.lower().endswith("m")


def fetch_futures_rankings() -> dict[str, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for fs in FUTURES_FS:
        rows.extend(_fetch_clist_all(fs, FUTURES_FIELDS, page_size=100))

    cleaned = [_clean_future(row) for row in rows if row.get("f12") and row.get("f14")]
    primary = [row for row in cleaned if _is_primary_contract(row)]
    if not primary:
        primary = cleaned

    by_key: dict[str, dict[str, Any]] = {}
    for row in primary:
        symbol = row["sina_symbol"] or row["code"]
        current = by_key.get(symbol)
        if current is None or (row.get("pct_today") or -999) > (current.get("pct_today") or -999):
            by_key[symbol] = row

    contracts = [row for row in by_key.values() if row.get("price") is not None]

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_fetch_sina_kline, row["sina_symbol"]): row
            for row in contracts
            if row.get("sina_symbol")
        }
        for future in as_completed(futures):
            row = futures[future]
            history = future.result()
            row["pct_3d"] = _period_pct(history, 3)
            row["pct_7d"] = _period_pct(history, 7)

    for row in contracts:
        row.setdefault("pct_3d", None)
        row.setdefault("pct_7d", None)

    three_day = [row for row in contracts if row.get("pct_3d") is not None]
    seven_day = [row for row in contracts if row.get("pct_7d") is not None]

    return {
        "today": sorted(contracts, key=lambda item: item["pct_today"] if item["pct_today"] is not None else -999, reverse=True)[:20],
        "three_day": sorted(three_day, key=lambda item: item["pct_3d"], reverse=True)[:20],
        "seven_day": sorted(seven_day, key=lambda item: item["pct_7d"], reverse=True)[:20],
    }
