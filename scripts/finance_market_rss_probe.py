#!/usr/bin/env python3
"""Bounded North America finance/TMT/macro probe for Hermes cron jobs.

Collects candidate leads only. The agent must still verify and synthesize; output is not
financial advice and should not be treated as trading signal.

Free data layers included:
- RSS / Google News RSS for news discovery.
- Yahoo Finance chart endpoint for rough market and watchlist snapshots.
- Stooq daily CSV fallback for selected ETFs.
- Nasdaq earnings calendar API for upcoming earnings discovery.
- FRED CSV endpoint for macro series when reachable; failures are tolerated.
"""
from __future__ import annotations

import csv
import email.utils
import html
import io
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import date, datetime, timedelta, timezone

UA = "Mozilla/5.0 (compatible; Hermes-Finance-Brief-Probe/1.2)"
TIMEOUT = 6
DEADLINE_SEC = 75
LIMIT_PER_SOURCE = 10
MAX_DESC = 520
MAX_WORKERS = 16
INVISIBLE = {ord("\u200b"): None, ord("\u200c"): None, ord("\u200d"): None, ord("\ufeff"): None}

SOURCES = [
    {"name": "CNBC Technology", "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html", "type": "rss"},
    {"name": "CNBC Finance", "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html", "type": "rss"},
    {"name": "MarketWatch Top Stories", "url": "https://feeds.marketwatch.com/marketwatch/topstories/", "type": "rss"},
    {"name": "Federal Reserve Press Releases", "url": "https://www.federalreserve.gov/feeds/press_all.xml", "type": "rss"},
    {"name": "Bank of Canada Press", "url": "https://www.bankofcanada.ca/content_type/press/feed/", "type": "rss"},
]

SEARCHES = [
    "US stock market today Nasdaq S&P 500 Treasury yields tech stocks when:1d",
    "TMT technology stocks earnings guidance AI capex Nvidia Microsoft Meta Amazon Alphabet when:3d",
    "semiconductor stocks Nvidia AMD Broadcom TSM ASML AI capex earnings when:3d",
    "Canada TSX stocks Bank of Canada inflation jobs GDP CAD oil when:3d",
    "Toronto Stock Exchange technology Shopify Constellation Software earnings when:7d",
    "Federal Reserve rates inflation jobs CPI PCE Treasury yields markets when:3d",
    "Bank of Canada rates inflation CAD oil TSX when:7d",
]

# Yahoo Finance symbols. Yahoo's chart endpoint is unofficial but stable enough for lightweight context.
MARKET_SYMBOLS = {
    "S&P 500 ETF SPY": "SPY",
    "Nasdaq 100 ETF QQQ": "QQQ",
    "Dow ETF DIA": "DIA",
    "iShares S&P/TSX 60 ETF XIU.TO": "XIU.TO",
    "USD/CAD": "CAD=X",
    "WTI Crude Oil Futures": "CL=F",
    "Gold Futures": "GC=F",
    "US 10Y Yield (^TNX)": "^TNX",
    "US 2Y Yield (^IRX proxy)": "^IRX",
    "VIX": "^VIX",
}

WATCHLIST_SYMBOLS = {
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "AAPL": "Apple",
    "GOOGL": "Alphabet",
    "AMZN": "Amazon",
    "META": "Meta",
    "TSLA": "Tesla",
    "AVGO": "Broadcom",
    "AMD": "AMD",
    "TSM": "TSMC ADR",
    "ASML": "ASML ADR",
    "ORCL": "Oracle",
    "CRM": "Salesforce",
    "NOW": "ServiceNow",
    "ADBE": "Adobe",
    "NFLX": "Netflix",
    "SHOP.TO": "Shopify Canada",
    "CSU.TO": "Constellation Software",
    "DSG.TO": "Descartes Systems",
    "OTEX.TO": "OpenText",
}

STOOQ_FALLBACK = {
    "SPY": "SPY.US",
    "QQQ": "QQQ.US",
    "XIU.TO": "XIU.TO",
}

FRED_SERIES = {
    "US 10Y Treasury Yield": "DGS10",
    "US 2Y Treasury Yield": "DGS2",
    "WTI Spot Oil": "DCOILWTICO",
    "USD/CAD Exchange Rate": "DEXCAUS",
    "VIX Close": "VIXCLS",
    "5Y Breakeven Inflation": "T5YIE",
}


def clean(s: str) -> str:
    s = html.unescape(s or "").translate(INVISIBLE)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def pdate(s: str) -> str:
    if not s:
        return ""
    try:
        dt = email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return s.strip()


def fetch(url: str, *, accept: str = "application/json,text/csv,application/rss+xml,text/xml,*/*") -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept,
            "Referer": "https://www.google.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(2_500_000)


def parse_feed(data: bytes):
    root = ET.fromstring(data)
    items = []
    for item in root.findall(".//item")[:LIMIT_PER_SOURCE]:
        title = clean(item.findtext("title") or "")
        link = clean(item.findtext("link") or "")
        pub = pdate(item.findtext("pubDate") or item.findtext("published") or "")
        desc = clean(item.findtext("description") or item.findtext("summary") or "")[:MAX_DESC]
        if title or link:
            items.append({"title": title, "url": link, "published": pub, "summary": desc})
    ns = {"a": "http://www.w3.org/2005/Atom"}
    if not items:
        for entry in root.findall(".//a:entry", ns)[:LIMIT_PER_SOURCE]:
            title = clean(entry.findtext("a:title", default="", namespaces=ns))
            link_el = entry.find("a:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            pub = pdate(
                entry.findtext("a:updated", default="", namespaces=ns)
                or entry.findtext("a:published", default="", namespaces=ns)
            )
            desc = clean(
                entry.findtext("a:summary", default="", namespaces=ns)
                or entry.findtext("a:content", default="", namespaces=ns)
            )[:MAX_DESC]
            if title or link:
                items.append({"title": title, "url": link, "published": pub, "summary": desc})
    return items


def google_news_url(q: str, gl="US", hl="en-US") -> str:
    return f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl={hl}&gl={gl}&ceid={gl}:en"


def fetch_source(src):
    entry = {k: v for k, v in src.items() if k != "url"}
    entry["url"] = src["url"]
    try:
        items = parse_feed(fetch(src["url"], accept="application/rss+xml,text/xml,*/*"))
        entry["items"] = items
        entry["error"] = None
    except Exception as e:
        entry["items"] = []
        entry["error"] = f"{type(e).__name__}: {e}"
    return entry


def pct_change(latest: float, previous: float):
    if previous in (0, None) or latest is None:
        return None
    return round((latest - previous) / previous * 100, 3)


def yahoo_chart(symbol: str, label: str | None = None):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range=10d&interval=1d"
    try:
        obj = json.loads(fetch(url).decode("utf-8", "ignore"))
        res = (obj.get("chart", {}).get("result") or [None])[0]
        if not res:
            return {"symbol": symbol, "label": label or symbol, "url": url, "error": "no result"}
        meta = res.get("meta", {})
        timestamps = res.get("timestamp") or []
        quote = (res.get("indicators", {}).get("quote") or [{}])[0]
        closes = quote.get("close") or []
        rows = []
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            rows.append({
                "date": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(),
                "close": round(float(close), 4),
            })
        rows = rows[-5:]
        latest = rows[-1]["close"] if rows else meta.get("regularMarketPrice")
        previous = rows[-2]["close"] if len(rows) >= 2 else meta.get("previousClose")
        return {
            "symbol": symbol,
            "label": label or symbol,
            "currency": meta.get("currency"),
            "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
            "timezone": meta.get("exchangeTimezoneName"),
            "latest_close": latest,
            "previous_close": previous,
            "pct_change": pct_change(float(latest), float(previous)) if latest is not None and previous is not None else None,
            "history": rows,
            "url": url,
            "error": None,
        }
    except Exception as e:
        return {"symbol": symbol, "label": label or symbol, "url": url, "error": f"{type(e).__name__}: {e}"}


def stooq_daily(symbol: str):
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(symbol.lower())}&i=d"
    try:
        txt = fetch(url, accept="text/csv,*/*").decode("utf-8", "ignore").strip().splitlines()
        if len(txt) < 3:
            return {"symbol": symbol, "url": url, "error": "not enough rows"}
        rows = []
        for line in txt[-5:]:
            parts = line.split(",")
            if len(parts) >= 5 and parts[0] != "Date":
                rows.append({"date": parts[0], "open": parts[1], "high": parts[2], "low": parts[3], "close": parts[4]})
        return {"symbol": symbol, "history": rows[-3:], "url": url, "error": None}
    except Exception as e:
        return {"symbol": symbol, "url": url, "error": f"{type(e).__name__}: {e}"}


def fred_series(series_id: str, label: str):
    start = (date.today() - timedelta(days=45)).isoformat()
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}&cosd={start}"
    try:
        text = fetch(url, accept="text/csv,*/*").decode("utf-8", "ignore")
        rows = []
        for row in csv.DictReader(io.StringIO(text)):
            value = row.get(series_id) or row.get("VALUE") or ""
            if value and value != ".":
                rows.append({"date": row.get("observation_date") or row.get("DATE"), "value": value})
        return {"series_id": series_id, "label": label, "latest": rows[-1] if rows else None, "history": rows[-5:], "url": url, "error": None}
    except Exception as e:
        return {"series_id": series_id, "label": label, "url": url, "error": f"{type(e).__name__}: {e}"}


def next_weekdays(n=7):
    days = []
    d = date.today()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def nasdaq_earnings(day: date):
    url = f"https://api.nasdaq.com/api/calendar/earnings?date={day.isoformat()}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": UA,
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": "https://www.nasdaq.com/market-activity/earnings",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            obj = json.loads(r.read(2_500_000).decode("utf-8", "ignore"))
        rows = ((obj.get("data") or {}).get("rows") or [])
        wanted = set(WATCHLIST_SYMBOLS.keys()) | {s.replace(".TO", "") for s in WATCHLIST_SYMBOLS if s.endswith(".TO")}
        filtered = []
        for row in rows:
            sym = clean(row.get("symbol") or "")
            if sym in wanted or len(filtered) < 20:
                filtered.append({
                    "date": day.isoformat(),
                    "time": clean(row.get("time") or ""),
                    "symbol": sym,
                    "name": clean(row.get("name") or ""),
                    "marketCap": clean(row.get("marketCap") or ""),
                    "fiscalQuarterEnding": clean(row.get("fiscalQuarterEnding") or ""),
                    "epsForecast": clean(row.get("epsForecast") or ""),
                    "noOfEsts": clean(row.get("noOfEsts") or ""),
                })
        return {"date": day.isoformat(), "url": url, "items": filtered[:30], "error": None}
    except Exception as e:
        return {"date": day.isoformat(), "url": url, "items": [], "error": f"{type(e).__name__}: {e}"}


def main():
    started = time.time()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Finance/TMT/macro candidate leads, market snapshots, earnings calendar, and macro series. Verify before inclusion. Not financial advice.",
        "market_context": {},
        "watchlist_snapshot": {},
        "macro_series": {},
        "earnings_calendar": [],
        "stooq_fallback": {},
        "sources": [],
        "stats": {"ok": 0, "errors": 0, "items": 0, "elapsed_sec": 0},
    }

    source_defs = list(SOURCES) + [
        {"name": f"Google News: {q[:64]}", "url": google_news_url(q), "type": "google_news", "query": q}
        for q in SEARCHES
    ]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures = {}
        for label, symbol in MARKET_SYMBOLS.items():
            futures[ex.submit(yahoo_chart, symbol, label)] = ("market", label)
        for symbol, label in WATCHLIST_SYMBOLS.items():
            futures[ex.submit(yahoo_chart, symbol, label)] = ("watchlist", symbol)
        for label, symbol in STOOQ_FALLBACK.items():
            futures[ex.submit(stooq_daily, symbol)] = ("stooq", label)
        for label, series_id in FRED_SERIES.items():
            futures[ex.submit(fred_series, series_id, label)] = ("fred", label)
        for day in next_weekdays(7):
            futures[ex.submit(nasdaq_earnings, day)] = ("earnings", day.isoformat())
        for src in source_defs:
            futures[ex.submit(fetch_source, src)] = ("source", src.get("name"))

        try:
            for fut in as_completed(futures, timeout=DEADLINE_SEC):
                kind, key = futures[fut]
                try:
                    data = fut.result()
                except Exception as e:
                    data = {"error": f"{type(e).__name__}: {e}"}
                if kind == "market":
                    result["market_context"][key] = data
                    result["stats"]["errors" if data.get("error") else "ok"] += 1
                elif kind == "watchlist":
                    result["watchlist_snapshot"][key] = data
                    result["stats"]["errors" if data.get("error") else "ok"] += 1
                elif kind == "stooq":
                    result["stooq_fallback"][key] = data
                elif kind == "fred":
                    result["macro_series"][key] = data
                elif kind == "earnings":
                    result["earnings_calendar"].append(data)
                    result["stats"]["items"] += len(data.get("items") or [])
                    if data.get("error"):
                        result["stats"]["errors"] += 1
                    else:
                        result["stats"]["ok"] += 1
                elif kind == "source":
                    result["sources"].append(data)
                    result["stats"]["items"] += len(data.get("items") or [])
                    if data.get("error"):
                        result["stats"]["errors"] += 1
                    else:
                        result["stats"]["ok"] += 1
        except TimeoutError:
            result["sources"].append({"name": "deadline", "type": "guard", "items": [], "error": f"Global deadline {DEADLINE_SEC}s reached; remaining tasks skipped"})
            result["stats"]["errors"] += 1

    result["sources"].sort(key=lambda x: x.get("name", ""))
    result["earnings_calendar"].sort(key=lambda x: x.get("date", ""))
    result["stats"]["elapsed_sec"] = round(time.time() - started, 2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
