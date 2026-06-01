from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from .config import DAILY_REPORTS_DIR, REPORTS_DIR, SITE_DIR, TEMPLATE_DIR


def _json_for_script(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render_report(processed: dict[str, Any]) -> Path:
    template_path = TEMPLATE_DIR / "report.html"
    template = template_path.read_text(encoding="utf-8")
    trade_date = processed["summary"]["trade_date"]
    title = f"A股每日复盘 {trade_date}"
    html_text = (
        template.replace("{{ title }}", html.escape(title))
        .replace("{{ trade_date }}", html.escape(trade_date))
        .replace("{{ report_json }}", _json_for_script(processed))
    )

    DAILY_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    daily_path = DAILY_REPORTS_DIR / f"{trade_date}.html"
    latest_path = REPORTS_DIR / "latest.html"
    site_index = SITE_DIR / "index.html"
    daily_path.write_text(html_text, encoding="utf-8")
    latest_path.write_text(html_text, encoding="utf-8")
    site_index.write_text(html_text, encoding="utf-8")

    site_daily = SITE_DIR / "daily"
    site_daily.mkdir(parents=True, exist_ok=True)
    shutil.copy2(daily_path, site_daily / daily_path.name)
    return daily_path

