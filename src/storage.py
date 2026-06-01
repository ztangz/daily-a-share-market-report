from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import DB_PATH


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(
            """
            create table if not exists daily_summary (
                trade_date text primary key,
                generated_at text not null,
                stock_count integer,
                advancers integer,
                decliners integer,
                flat integer,
                limit_up_count integer,
                limit_down_count integer,
                broken_limit_count integer,
                total_amount_yi real,
                emotion_score integer,
                payload text not null
            );

            create table if not exists index_quotes (
                trade_date text not null,
                code text not null,
                name text not null,
                price real,
                pct real,
                amount_yi real,
                primary key (trade_date, code)
            );
            """
        )


def save_processed_to_db(processed: dict[str, Any]) -> None:
    init_db()
    summary = processed["summary"]
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            insert or replace into daily_summary (
                trade_date, generated_at, stock_count, advancers, decliners, flat,
                limit_up_count, limit_down_count, broken_limit_count, total_amount_yi,
                emotion_score, payload
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary["trade_date"],
                summary["generated_at"],
                summary["stock_count"],
                summary["advancers"],
                summary["decliners"],
                summary["flat"],
                summary["limit_up_count"],
                summary["limit_down_count"],
                summary["broken_limit_count"],
                summary["total_amount_yi"],
                summary["emotion_score"],
                json.dumps(processed, ensure_ascii=False),
            ),
        )
        conn.executemany(
            """
            insert or replace into index_quotes (
                trade_date, code, name, price, pct, amount_yi
            ) values (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    summary["trade_date"],
                    item["code"],
                    item["name"],
                    item["price"],
                    item["pct"],
                    item["amount_yi"],
                )
                for item in processed["indices"]
            ],
        )

