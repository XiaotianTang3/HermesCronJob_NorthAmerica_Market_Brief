#!/usr/bin/env python3
"""Bounded North America finance/TMT/macro probe for Hermes cron jobs.

Collects candidate leads only. The agent must still verify and synthesize; output is not
financial advice and should not be treated as trading signal.
"""
from __future__ import annotations
import email.utils, html, json, re, time, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

UA = "Mozilla/5.0 (compatible; Hermes-Finance-Brief-Probe/1.1)"
TIMEOUT = 5
DEADLINE_SEC = 45
LIMIT_PER_SOURCE = 10
MAX_DESC = 520
INVISIBLE = {ord("\u200b"): None, ord("\u200c"): None, ord("\u200d"): None, ord("\ufeff"): None}

SOURCES = [
    {"name":"CNBC Technology","url":"https://www.cnbc.com/id/19854910/device/rss/rss.html","type":"rss"},
    {"name":"CNBC Finance","url":"https://www.cnbc.com/id/10000664/device/rss/rss.html","type":"rss"},
    {"name":"MarketWatch Top Stories","url":"https://feeds.marketwatch.com/marketwatch/topstories/","type":"rss"},
    {"name":"Federal Reserve Press Releases","url":"https://www.federalreserve.gov/feeds/press_all.xml","type":"rss"},
    {"name":"Bank of Canada Press","url":"https://www.bankofcanada.ca/content_type/press/feed/","type":"rss"},
    {"name":"Statistics Canada Daily","url":"https://www150.statcan.gc.ca/n1/dai-quo/ssi/homepage/daily-banner-eng.xml","type":"rss"},
]

SEARCHES = [
    "US stock market today Nasdaq S&P 500 Treasury yields tech stocks when:1d",
    "TMT technology stocks earnings guidance AI capex Nvidia Microsoft Meta Amazon Alphabet when:3d",
    "Canada TSX stocks Bank of Canada inflation jobs GDP CAD oil when:3d",
    "Federal Reserve rates inflation jobs CPI PCE Treasury yields markets when:3d",
]

MARKET_SYMBOLS = {
    "S&P 500 ETF SPY": "SPY.US",
    "Nasdaq 100 ETF QQQ": "QQQ.US",
    "TSX 60 ETF XIU": "XIU.TO",
}

def clean(s: str) -> str:
    s = html.unescape(s or "").translate(INVISIBLE)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def pdate(s: str) -> str:
    if not s: return ""
    try:
        dt=email.utils.parsedate_to_datetime(s)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except Exception:
        return s.strip()

def fetch(url: str) -> bytes:
    req=urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.read(2_000_000)

def parse(data: bytes):
    root=ET.fromstring(data)
    items=[]
    for item in root.findall('.//item')[:LIMIT_PER_SOURCE]:
        title=clean(item.findtext('title') or '')
        link=clean(item.findtext('link') or '')
        pub=pdate(item.findtext('pubDate') or item.findtext('published') or '')
        desc=clean(item.findtext('description') or item.findtext('summary') or '')[:MAX_DESC]
        if title or link: items.append({"title":title,"url":link,"published":pub,"summary":desc})
    ns={'a':'http://www.w3.org/2005/Atom'}
    if not items:
        for entry in root.findall('.//a:entry', ns)[:LIMIT_PER_SOURCE]:
            title=clean(entry.findtext('a:title', default='', namespaces=ns))
            link_el=entry.find('a:link', ns)
            link=link_el.attrib.get('href','') if link_el is not None else ''
            pub=pdate(entry.findtext('a:updated', default='', namespaces=ns) or entry.findtext('a:published', default='', namespaces=ns))
            desc=clean(entry.findtext('a:summary', default='', namespaces=ns) or entry.findtext('a:content', default='', namespaces=ns))[:MAX_DESC]
            if title or link: items.append({"title":title,"url":link,"published":pub,"summary":desc})
    return items

def google_news_url(q: str, gl='US', hl='en-US') -> str:
    return f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&hl={hl}&gl={gl}&ceid={gl}:en"

def stooq_daily(symbol: str):
    # Free daily CSV; not always available for every symbol. Used only for rough market pulse context.
    url=f"https://stooq.com/q/d/l/?s={urllib.parse.quote(symbol.lower())}&i=d"
    try:
        txt=fetch(url).decode('utf-8','ignore').strip().splitlines()
        if len(txt)<3: return None
        rows=[]
        for line in txt[-5:]:
            parts=line.split(',')
            if len(parts)>=5 and parts[0] != 'Date':
                rows.append({"date":parts[0],"open":parts[1],"high":parts[2],"low":parts[3],"close":parts[4]})
        return rows[-3:]
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

def fetch_source(src):
    entry={k:v for k,v in src.items() if k!='url'}; entry['url']=src['url']
    try:
        items=parse(fetch(src['url']))
        entry['items']=items; entry['error']=None
    except Exception as e:
        entry['items']=[]; entry['error']=f"{type(e).__name__}: {e}"
    return entry

def main():
    started=time.time()
    result={"generated_at":datetime.now(timezone.utc).isoformat(),"note":"Finance/TMT/macro candidate leads and rough market context only. Verify before inclusion. Not financial advice.","market_context":{},"sources":[],"stats":{"ok":0,"errors":0,"items":0,"elapsed_sec":0}}
    # Market context is fetched concurrently too; failures are tolerated.
    with ThreadPoolExecutor(max_workers=8) as ex:
        market_futs={ex.submit(stooq_daily, sym): name for name,sym in MARKET_SYMBOLS.items()}
        source_defs=list(SOURCES)+[{"name":f"Google News: {q[:64]}","url":google_news_url(q),"type":"google_news","query":q} for q in SEARCHES]
        source_futs={ex.submit(fetch_source, src): src for src in source_defs}
        for fut in as_completed(market_futs, timeout=DEADLINE_SEC):
            try:
                result['market_context'][market_futs[fut]]=fut.result()
            except Exception as e:
                result['market_context'][market_futs[fut]]={"error":f"{type(e).__name__}: {e}"}
        try:
            for fut in as_completed(source_futs, timeout=DEADLINE_SEC):
                try:
                    entry=fut.result()
                except Exception as e:
                    src=source_futs[fut]
                    entry={k:v for k,v in src.items() if k!='url'}; entry['url']=src['url']; entry['items']=[]; entry['error']=f"{type(e).__name__}: {e}"
                result['sources'].append(entry)
                if entry.get('error'):
                    result['stats']['errors']+=1
                else:
                    result['stats']['ok']+=1; result['stats']['items']+=len(entry.get('items') or [])
        except TimeoutError:
            result['sources'].append({"name":"deadline","type":"guard","items":[],"error":f"Global deadline {DEADLINE_SEC}s reached; remaining sources skipped"})
            result['stats']['errors']+=1
    result['sources'].sort(key=lambda x: x.get('name',''))
    result['stats']['elapsed_sec']=round(time.time()-started,2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__': main()
