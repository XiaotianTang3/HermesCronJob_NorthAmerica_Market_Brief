# HermesCronJob North America Market Brief

A reusable Hermes cron kit for a North America market briefing aimed at Canada-based readers who follow US equities, TMT/AI/tech stocks, US/Canada macro, rates, CAD, oil, and TSX.

This is **market intelligence**, not investment advice. The kit is designed to help a Hermes agent produce a daily brief explaining what markets are trading, why it matters, and what to watch next — without giving buy/sell recommendations.

Default output is **Chinese**, matching the original use case. Edit the cron prompt if you want English output.

## What it covers

- US equities: S&P 500, Nasdaq, mega-cap tech, AI/semis/software/cloud.
- Canada lens: TSX, CAD, oil, Bank of Canada, Canadian macro, selected Canadian tech/banks/energy when relevant.
- Macro/rates: Fed, BoC, CPI/PCE/jobs/GDP/retail sales, Treasury yields.
- TMT / AI stocks: NVDA, MSFT, AAPL, GOOGL, AMZN, META, TSLA, AVGO, AMD, TSM, ASML, ORCL, CRM, NOW, ADBE, NFLX; optional Canada names such as SHOP, CSU.TO, DSG.TO, OTEX.

## How it works

```text
finance_market_rss_probe.py
├── public RSS / Google News RSS candidate leads
├── rough public market context when available
└── hard timeouts so bad feeds don't block cron

Hermes cron agent
├── verifies source/date/facts
├── deduplicates and ranks
├── drops weak/old/unverified items
└── writes the final brief with source URLs
```

The probe script is **not the final source of truth**. It only collects candidate leads. The Hermes agent must verify each item before including it.

## Install

```bash
git clone https://github.com/XiaotianTang3/HermesCronJob_NorthAmerica_Market_Brief.git
cd HermesCronJob_NorthAmerica_Market_Brief
./install.sh
./verify.sh
```

This copies:

- `skills/*` → `~/.hermes/skills/`
- `scripts/*.py` → `~/.hermes/scripts/`

If you use a custom Hermes home:

```bash
HERMES_HOME=/path/to/.hermes ./install.sh
```

## Create the cron job

Use `cron-templates/north-america-market-brief.json` as the source of truth.

Recommended fields:

```json
{
  "name": "North America Market Brief",
  "schedule": "0 8 * * 1-5",
  "skills": ["finance-market-briefing"],
  "script": "finance_market_rss_probe.py",
  "enabled_toolsets": ["terminal", "browser", "web", "search", "file", "code_execution"],
  "deliver": "origin"
}
```

Adjust the cron expression to your Hermes host timezone. For a Canada-based reader, a pre-market run around **08:00 local time** is a good starting point.

### Copy-paste instruction for another Hermes agent

```text
Clone https://github.com/XiaotianTang3/HermesCronJob_NorthAmerica_Market_Brief, run ./install.sh and ./verify.sh, then create a recurring cron job using cron-templates/north-america-market-brief.json. Preserve the attached skill, script, enabled_toolsets, source-link rule, Chinese output format, and not-investment-advice constraint.
```

## Quality rules

- Every main item must include at least one clickable URL.
- Official macro/central-bank/company sources are preferred; reputable market media are second-best.
- Do not include stale stories as new.
- Do not give buy/sell recommendations, position sizing, target prices as advice, or portfolio instructions.
- Separate facts from interpretation.
- If market data is not current because markets are closed, explicitly say "latest available trading day".
- Fewer verified items are better than many weak items.

## Replication target

With the same Hermes version, model, tool availability, and network access, another agent should be able to produce a brief with very similar structure and source discipline. Exact article selection may vary because public RSS/search feeds and market conditions change.

Run `docs/replication-checklist.md` before claiming replication success.

## Files

```text
skills/
  finance-market-briefing/
scripts/
  finance_market_rss_probe.py
cron-templates/
  north-america-market-brief.json
docs/
  replication-checklist.md
  public-release-checklist.md
examples/
  output-shape.md
```

## Disclaimer

This repository is for information summarization and market-intelligence workflows. It does not provide financial, investment, tax, or legal advice.
