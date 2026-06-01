from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
DAILY_REPORTS_DIR = REPORTS_DIR / "daily"
SITE_DIR = PROJECT_ROOT / "site"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
DB_PATH = DATA_DIR / "market.db"
CN_TZ = ZoneInfo("Asia/Shanghai")

EASTMONEY_QUOTE_URL = "https://push2delay.eastmoney.com/api/qt/clist/get"

INDEXES = [
    {"name": "上证指数", "secid": "1.000001"},
    {"name": "深证成指", "secid": "0.399001"},
    {"name": "沪深300", "secid": "1.000300"},
    {"name": "创业板指", "secid": "0.399006"},
    {"name": "科创50", "secid": "1.000688"},
    {"name": "中证500", "secid": "1.000905"},
    {"name": "中证1000", "secid": "1.000852"},
    {"name": "北证50", "secid": "0.899050"},
]

A_SHARE_FS = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
INDUSTRY_FS = "m:90+t:2"
CONCEPT_FS = "m:90+t:3"

QUOTE_FIELDS = ",".join(
    [
        "f1",
        "f2",   # latest
        "f3",   # pct change
        "f4",   # change
        "f5",   # volume
        "f6",   # amount
        "f8",   # turnover
        "f10",  # volume ratio
        "f12",  # code
        "f14",  # name
        "f15",  # high
        "f16",  # low
        "f17",  # open
        "f18",  # previous close
        "f20",  # total market cap
        "f21",  # float market cap
        "f23",  # pb
        "f115", # pe ttm
    ]
)

SECTOR_FIELDS = ",".join(
    [
        "f2",
        "f3",
        "f4",
        "f6",
        "f8",
        "f12",
        "f14",
        "f20",
        "f62",
        "f104",
        "f105",
        "f128",
        "f136",
        "f140",
    ]
)

CN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
}

