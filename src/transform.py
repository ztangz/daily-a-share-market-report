from __future__ import annotations

import statistics
from datetime import datetime
from typing import Any


def as_float(value: Any, default: float | None = None) -> float | None:
    if value in (None, "-", ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    number = as_float(value)
    if number is None:
        return default
    return int(number)


def amount_yi(value: Any) -> float:
    number = as_float(value, 0.0) or 0.0
    return round(number / 100_000_000, 2)


def clean_quote(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(row.get("f12", "")),
        "name": row.get("display_name") or row.get("f14") or "",
        "price": as_float(row.get("f2")),
        "pct": as_float(row.get("f3")),
        "change": as_float(row.get("f4")),
        "volume": as_int(row.get("f5")),
        "amount": as_float(row.get("f6"), 0.0) or 0.0,
        "amount_yi": amount_yi(row.get("f6")),
        "turnover": as_float(row.get("f8")),
        "volume_ratio": as_float(row.get("f10")),
        "high": as_float(row.get("f15")),
        "low": as_float(row.get("f16")),
        "open": as_float(row.get("f17")),
        "prev_close": as_float(row.get("f18")),
        "total_market_cap": as_float(row.get("f20"), 0.0) or 0.0,
        "float_market_cap": as_float(row.get("f21"), 0.0) or 0.0,
        "pb": as_float(row.get("f23")),
        "pe_ttm": as_float(row.get("f115")),
    }


def clean_sector(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(row.get("f12", "")),
        "name": row.get("f14") or "",
        "price": as_float(row.get("f2")),
        "pct": as_float(row.get("f3")),
        "change": as_float(row.get("f4")),
        "amount_yi": amount_yi(row.get("f6")),
        "turnover": as_float(row.get("f8")),
        "net_inflow_yi": amount_yi(row.get("f62")),
        "up_count": as_int(row.get("f104")),
        "down_count": as_int(row.get("f105")),
        "lead_stock": row.get("f128") or "",
        "lead_stock_pct": as_float(row.get("f136")),
        "lead_stock_code": str(row.get("f140", "")),
    }


def limit_threshold(stock: dict[str, Any]) -> float:
    code = stock["code"]
    name = stock["name"].upper()
    if "ST" in name:
        return 4.8
    if code.startswith(("300", "301", "688")):
        return 19.7
    if code.startswith(("8", "4", "92")):
        return 29.7
    return 9.7


def board_name(code: str) -> str:
    if code.startswith(("600", "601", "603", "605")):
        return "沪市主板"
    if code.startswith(("000", "001", "002", "003")):
        return "深市主板"
    if code.startswith(("300", "301")):
        return "创业板"
    if code.startswith("688"):
        return "科创板"
    if code.startswith(("8", "4", "92")):
        return "北交所"
    return "其他"


def hit_upper_limit(stock: dict[str, Any]) -> bool:
    pct = stock.get("pct")
    return pct is not None and pct >= limit_threshold(stock)


def hit_lower_limit(stock: dict[str, Any]) -> bool:
    pct = stock.get("pct")
    return pct is not None and pct <= -limit_threshold(stock)


def touched_upper_then_fell(stock: dict[str, Any]) -> bool:
    high = stock.get("high")
    prev = stock.get("prev_close")
    if not high or not prev:
        return False
    high_pct = (high / prev - 1) * 100
    return high_pct >= limit_threshold(stock) and not hit_upper_limit(stock)


def percentile_proxy(stocks: list[dict[str, Any]], size: int = 400) -> dict[str, Any]:
    candidates = [
        stock
        for stock in stocks
        if stock["pct"] is not None and stock["float_market_cap"] and stock["float_market_cap"] > 0
    ]
    candidates.sort(key=lambda item: item["float_market_cap"])
    sample = candidates[:size]
    pcts = [stock["pct"] for stock in sample if stock["pct"] is not None]
    return {
        "name": "微盘股代理",
        "sample_size": len(sample),
        "median_pct": round(statistics.median(pcts), 2) if pcts else None,
        "avg_pct": round(sum(pcts) / len(pcts), 2) if pcts else None,
        "advancers": sum(1 for pct in pcts if pct > 0),
        "decliners": sum(1 for pct in pcts if pct < 0),
    }


def emotion_score(summary: dict[str, Any]) -> int:
    total = max(summary["stock_count"], 1)
    up_ratio = summary["advancers"] / total
    limit_balance = summary["limit_up_count"] / max(summary["limit_up_count"] + summary["limit_down_count"], 1)
    blast_penalty = summary["broken_limit_count"] / max(summary["limit_up_count"] + summary["broken_limit_count"], 1)
    index_bias = summary["positive_index_count"] / max(summary["index_count"], 1)
    raw = 100 * (0.35 * up_ratio + 0.25 * limit_balance + 0.25 * index_bias + 0.15 * (1 - blast_penalty))
    return max(0, min(100, round(raw)))


def process_snapshot(raw: dict[str, Any], trade_date: str, now: datetime) -> dict[str, Any]:
    indices = [clean_quote(row) for row in raw["indices"]]
    stocks = [clean_quote(row) for row in raw["stocks"] if row.get("f12") and row.get("f14")]
    industries = [clean_sector(row) for row in raw["industry_sectors"] if row.get("f12")]
    concepts = [clean_sector(row) for row in raw["concept_sectors"] if row.get("f12")]

    advancers = sum(1 for stock in stocks if (stock["pct"] or 0) > 0)
    decliners = sum(1 for stock in stocks if (stock["pct"] or 0) < 0)
    flat = len(stocks) - advancers - decliners
    limit_ups = [stock for stock in stocks if hit_upper_limit(stock)]
    limit_downs = [stock for stock in stocks if hit_lower_limit(stock)]
    broken_limits = [stock for stock in stocks if touched_upper_then_fell(stock)]
    total_amount_yi = round(sum(stock["amount"] for stock in stocks) / 100_000_000, 2)

    board_stats: dict[str, dict[str, Any]] = {}
    for stock in stocks:
        board = board_name(stock["code"])
        stats = board_stats.setdefault(board, {"name": board, "count": 0, "advancers": 0, "decliners": 0, "limit_ups": 0})
        stats["count"] += 1
        stats["advancers"] += 1 if (stock["pct"] or 0) > 0 else 0
        stats["decliners"] += 1 if (stock["pct"] or 0) < 0 else 0
        stats["limit_ups"] += 1 if hit_upper_limit(stock) else 0

    for stats in board_stats.values():
        stats["advance_ratio"] = round(stats["advancers"] / max(stats["count"], 1) * 100, 1)

    summary = {
        "trade_date": trade_date,
        "generated_at": now.isoformat(),
        "source": raw.get("source", ""),
        "stock_count": len(stocks),
        "advancers": advancers,
        "decliners": decliners,
        "flat": flat,
        "limit_up_count": len(limit_ups),
        "limit_down_count": len(limit_downs),
        "broken_limit_count": len(broken_limits),
        "total_amount_yi": total_amount_yi,
        "index_count": len(indices),
        "positive_index_count": sum(1 for item in indices if (item["pct"] or 0) > 0),
    }
    summary["emotion_score"] = emotion_score(summary)
    ths_fund_flows = raw.get("ths_fund_flows") or {"industry": [], "concept": []}
    ths_industries = ths_fund_flows.get("industry", [])
    limit_time_pool = raw.get("limit_time_pool") or []
    futures_rankings = raw.get("futures_rankings") or {"today": [], "three_day": [], "seven_day": []}

    return {
        "summary": summary,
        "indices": indices,
        "microcap_proxy": percentile_proxy(stocks),
        "board_stats": sorted(board_stats.values(), key=lambda item: item["advance_ratio"], reverse=True),
        "ths_fund_flows": {
            "industry_inflow": sorted(ths_fund_flows.get("industry", []), key=lambda item: item["net_inflow_yi"] if item["net_inflow_yi"] is not None else -999, reverse=True)[:20],
            "concept_inflow": sorted(ths_fund_flows.get("concept", []), key=lambda item: item["net_inflow_yi"] if item["net_inflow_yi"] is not None else -999, reverse=True)[:20],
            "industry_outflow": sorted(ths_fund_flows.get("industry", []), key=lambda item: item["net_inflow_yi"] if item["net_inflow_yi"] is not None else 999)[:10],
            "concept_outflow": sorted(ths_fund_flows.get("concept", []), key=lambda item: item["net_inflow_yi"] if item["net_inflow_yi"] is not None else 999)[:10],
        },
        "industry_top": sorted(ths_industries, key=lambda item: item["pct"] if item["pct"] is not None else -999, reverse=True)[:15],
        "industry_bottom": sorted(ths_industries, key=lambda item: item["pct"] if item["pct"] is not None else 999)[:10],
        "concept_top": sorted(concepts, key=lambda item: item["pct"] if item["pct"] is not None else -999, reverse=True)[:20],
        "limit_time_pool": sorted(limit_time_pool, key=lambda item: item.get("first_limit_time") or "99:99:99")[:80],
        "futures_rankings": futures_rankings,
        "limit_ups": sorted(limit_ups, key=lambda item: item["pct"] or 0, reverse=True)[:80],
        "limit_downs": sorted(limit_downs, key=lambda item: item["pct"] or 0)[:50],
        "broken_limits": sorted(broken_limits, key=lambda item: item["pct"] or 0, reverse=True)[:50],
    }
