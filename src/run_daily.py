from __future__ import annotations

import argparse
from datetime import datetime

from .config import CN_TZ, PROCESSED_DIR, RAW_DIR
from .fetch_market import fetch_snapshot
from .render_report import render_report
from .storage import save_processed_to_db, write_json
from .transform import process_snapshot


def validate_processed(processed: dict) -> None:
    summary = processed["summary"]
    problems = []
    if summary["stock_count"] < 1000:
        problems.append(f"stock_count too small: {summary['stock_count']}")
    if summary["index_count"] < 6:
        problems.append(f"index_count too small: {summary['index_count']}")
    if not processed["industry_top"]:
        problems.append("industry sector data is empty")
    if not processed["concept_top"]:
        problems.append("concept sector data is empty")
    if problems:
        raise RuntimeError("Data validation failed: " + "; ".join(problems))


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch A-share market data and render a static daily report.")
    parser.add_argument("--date", help="Trade date in YYYY-MM-DD. Defaults to today in Asia/Shanghai.")
    args = parser.parse_args()

    now = datetime.now(CN_TZ)
    trade_date = args.date or now.date().isoformat()

    raw = fetch_snapshot(now)
    processed = process_snapshot(raw, trade_date, now)
    validate_processed(processed)

    raw_dir = RAW_DIR / trade_date
    processed_dir = PROCESSED_DIR / trade_date
    write_json(raw_dir / "snapshot.json", raw)
    write_json(processed_dir / "market.json", processed)
    save_processed_to_db(processed)
    report_path = render_report(processed)

    summary = processed["summary"]
    print(
        f"Generated {report_path} | "
        f"stocks={summary['stock_count']} advancers={summary['advancers']} "
        f"limit_up={summary['limit_up_count']} emotion={summary['emotion_score']}"
    )


if __name__ == "__main__":
    main()
