---
name: finance-market-briefing
description: Daily/periodic North America market briefing for a Canada-based finance professional who follows US equities, Canada macro, TMT/AI/tech stocks, rates, CAD, oil, earnings, and market-moving policy. Produces market intelligence, not investment advice.
type: workflow
---

# Finance Market Briefing Workflow

Use this skill when the user wants a recurring or one-off finance/news briefing about stocks, stock markets, TMT/tech sector, US/Canada macroeconomics, central banks, earnings, listed-company moves, and market-moving policy.

## Core stance

This is **market intelligence**, not financial advice. Do not tell the reader to buy/sell. Focus on what happened, why it moved markets, what to watch next, and confidence/source quality.

Default persona: a Canada-based finance professional who buys/follows US equities and wants a practical North America market read.

## Default scope

Unless customized:
- Time window: last 24 hours for daily brief; extend to 72 hours after weekends/holidays.
- Geography: US 70%, Canada 30%.
- Assets: S&P 500, Nasdaq, TSX, US 2Y/10Y yields, USD/CAD, WTI oil, gold/VIX only when market-moving.
- Stocks/sectors: TMT/AI/tech first — NVDA, MSFT, AAPL, GOOGL, AMZN, META, TSLA, AVGO, AMD, TSM, ASML, ORCL, CRM, NOW, ADBE, NFLX; Canada lens includes SHOP, CSU.TO, DSG.TO, OTEX, banks/energy only when relevant.
- Macro: Fed, Bank of Canada, CPI/PCE/jobs/GDP/retail sales, Treasury yields, CAD, oil.
- Exclude: penny-stock hype, unsourced social posts, generic analyst chatter, crypto unless it materially affects listed equities or macro risk.

## Data layers

The v1.2 probe uses free/public data layers:

- RSS / Google News RSS for candidate market and company leads.
- Yahoo Finance chart endpoint for rough market snapshots and watchlist moves.
- Stooq daily CSV as a fallback for selected ETFs.
- Nasdaq earnings calendar API for upcoming earnings discovery.
- FRED CSV endpoint for macro series such as 2Y/10Y yields, WTI, USD/CAD, VIX and breakevens when reachable.

These data layers are for context and discovery. The final brief must still verify important claims and source URLs.

## Source priority

1. Official/primary sources:
- Company IR/newsroom, SEC/SEDAR+ filings, earnings releases/transcripts.
- Federal Reserve, Bank of Canada, BLS, BEA, Statistics Canada, Treasury, government releases.
- Exchange notices where relevant.

2. Reputable market reporting:
- Reuters, Bloomberg, WSJ, Financial Times, CNBC, AP, MarketWatch, Barron's.
- The Globe and Mail, Financial Post, BNN Bloomberg for Canada.

3. Market data/discovery:
- Nasdaq/Yahoo Finance/Google Finance/Stooq/FRED only for price or macro series context; do not use random SEO sites as final authority.

## Verification rules

For each included item, verify:
- date/time,
- entity/ticker/sector,
- key fact (earnings, guidance, CPI/jobs/rates, policy, deal, lawsuit, product/AI capex, etc.),
- market impact if claimed,
- source URL.

Confidence labels:
- High: official source or Reuters/Bloomberg/WSJ/FT + consistent market context.
- Medium: one reputable report but official filing missing/not yet available.
- Low: social/analyst/rumor-only. Include only if clearly market-moving and label as unconfirmed.

## Daily brief format

```text
📈 North America Market Brief｜YYYY-MM-DD
Scope: US equities + Canada lens + TMT/AI stocks. Not investment advice.

一句话：今天市场最重要的交易主线。

## 1. Market Pulse
- Explain the actual driver: rates, earnings, AI capex, oil/CAD, Fed/BoC, risk-on/off. Mention S&P 500/Nasdaq/TSX/rates/USD-CAD/oil only when useful.

## 2. Macro & Rates｜US / Canada
- [Date] [Indicator/policy] — what changed, why markets cared, and what to watch next. Source: URL. Confidence: High/Medium.

## 3. TMT / AI / Tech Stocks
- [Ticker/company] — event + market implication in 2-3 sentences. Source: URL. Confidence: High/Medium.

## 4. Earnings & Guidance
- Use only when earnings/guidance are active; otherwise merge with TMT.

## 5. Canada Lens
- CAD, TSX, oil, BoC, Canadian tech/banks/energy implications for a Canada-based US-stock investor.

## 6. Watchlist: Next 24-72h
- Specific data releases, Fed/BoC speeches, earnings, company events.

## 7. Bottom Line
- 2-4 bullets: the real regime signal. Avoid generic “markets were mixed.”
```

## Implementation notes

For the validated v1 cron/probe pattern, Canada-based reader assumptions, weekend-market handling, and known gaps, see `references/finance-market-cron-v1.md`.

When building a recurring cron, prefer a bounded concurrent probe script that returns candidate leads and partial results rather than letting the agent perform all discovery live. The final agent pass must still verify facts and source URLs.

## Quality gates

Before finalizing:
- Every main item has at least one URL.
- No trading recommendation or target-price anchoring unless clearly attributed.
- No unsupported price move claims; if price data is unavailable, say “reported market reaction” or omit.
- Separate facts from interpretation.
- Prefer 5-9 strong items over 15 weak items.
- Watchlist must be concrete, not generic.
- Use earnings calendar and macro/market snapshots when available; explicitly say when data is stale or markets are closed.
