from __future__ import annotations

import html
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from typing import Any

from .http_client import fetch_json


THS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://data.10jqka.com.cn/",
}


class THSTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.in_row = True
            self.current_row = []
        elif self.in_table and self.in_row and tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            self.in_table = False
        elif self.in_table and tag == "tr":
            if self.current_row:
                self.rows.append(self.current_row)
            self.in_row = False
        elif self.in_table and self.in_row and tag in {"td", "th"}:
            text = " ".join("".join(self.current_cell).split())
            self.current_row.append(text)
            self.in_cell = False

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.current_cell.append(data)


def _fetch_text(url: str, headers: dict[str, str] | None = None, retries: int = 2) -> str:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers=headers or THS_HEADERS)
            with urllib.request.urlopen(request, timeout=18) as response:
                raw = response.read()
            return raw.decode("gbk", errors="replace")
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.8 * attempt)
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


def _parse_float(value: str) -> float | None:
    value = value.replace("%", "").replace(",", "").strip()
    if value in {"", "--", "-"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_fund_table(url: str, category: str) -> list[dict[str, Any]]:
    parser = THSTableParser()
    parser.feed(_fetch_text(url))
    rows = [row for row in parser.rows if len(row) >= 11 and row[0].isdigit()]
    result = []
    for row in rows:
        result.append(
            {
                "rank": int(row[0]),
                "category": category,
                "name": row[1],
                "index_price": _parse_float(row[2]),
                "pct": _parse_float(row[3]),
                "inflow_yi": _parse_float(row[4]),
                "outflow_yi": _parse_float(row[5]),
                "net_inflow_yi": _parse_float(row[6]),
                "stock_count": int(_parse_float(row[7]) or 0),
                "lead_stock": row[8],
                "lead_stock_pct": _parse_float(row[9]),
                "lead_stock_price": _parse_float(row[10]),
            }
        )
    return result


def fetch_ths_fund_flows() -> dict[str, list[dict[str, Any]]]:
    industry = _parse_fund_table("https://data.10jqka.com.cn/funds/hyzjl/", "industry")
    concept = _parse_fund_table("https://data.10jqka.com.cn/funds/gnzjl/", "concept")
    return {"industry": industry, "concept": concept}


def _format_time(value: int | str | None) -> str:
    if value in (None, "", "-"):
        return ""
    digits = str(value).zfill(6)
    return f"{digits[:2]}:{digits[2:4]}:{digits[4:6]}"


def fetch_limit_time_pool(trade_date: str) -> list[dict[str, Any]]:
    payload = fetch_json(
        "https://push2ex.eastmoney.com/getTopicZTPool",
        {
            "ut": "7eea3edcaed734bea9cbfc24409ed989",
            "dpt": "wz.ztzt",
            "Pageindex": 0,
            "pagesize": 500,
            "sort": "fbt:asc",
            "date": trade_date.replace("-", ""),
        },
    )
    rows = ((payload.get("data") or {}).get("pool") or [])
    result = []
    for row in rows:
        result.append(
            {
                "code": str(row.get("c") or ""),
                "name": row.get("n") or "",
                "price": round((row.get("p") or 0) / 1000, 3),
                "pct": row.get("zdp"),
                "amount_yi": round((row.get("amount") or 0) / 100_000_000, 2),
                "turnover": row.get("hs"),
                "first_limit_time": _format_time(row.get("fbt")),
                "last_limit_time": _format_time(row.get("lbt")),
                "open_count": row.get("zbc") or 0,
                "consecutive_boards": row.get("lbc") or 1,
                "eastmoney_industry": row.get("hybk") or "",
                "sealed_fund_yi": round((row.get("fund") or 0) / 100_000_000, 2),
            }
        )
    return result


def _strip_tags(fragment: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", fragment).split())


def fetch_ths_stock_profile(code: str) -> dict[str, Any]:
    text = _fetch_text(f"https://basic.10jqka.com.cn/{code}/", headers={**THS_HEADERS, "Referer": "https://basic.10jqka.com.cn/"})
    industry = ""
    industry_match = re.search(r"所属申万行业.*?<span class=\"tip f14\">(.*?)</span>", text, flags=re.S)
    if industry_match:
        industry = html.unescape(_strip_tags(industry_match.group(1))).strip()

    concepts: list[str] = []
    concept_match = re.search(r"<div class=\"f14\s+newconcept\".*?>(.*?)</div>", text, flags=re.S)
    if concept_match:
        for anchor in re.findall(r"<a\b[^>]*>(.*?)</a>", concept_match.group(1), flags=re.S):
            name = html.unescape(_strip_tags(anchor)).strip(" ，,")
            if name and name not in concepts:
                concepts.append(name)

    return {"ths_industry": industry, "concepts": concepts[:8]}


def enrich_limit_pool_with_ths(limit_pool: list[dict[str, Any]], max_workers: int = 6) -> list[dict[str, Any]]:
    enriched = [dict(row) for row in limit_pool]
    by_code = {row["code"]: row for row in enriched if row.get("code")}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_ths_stock_profile, code): code for code in by_code}
        for future in as_completed(futures):
            code = futures[future]
            try:
                profile = future.result()
            except Exception:
                profile = {"ths_industry": "", "concepts": []}
            by_code[code]["ths_industry"] = profile["ths_industry"] or by_code[code].get("eastmoney_industry", "")
            by_code[code]["concepts"] = profile["concepts"]

    return enriched

