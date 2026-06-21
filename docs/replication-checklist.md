# Replication checklist

Use this before claiming another Hermes agent has replicated the workflow.

## Installation

- [ ] `./install.sh` completed without error.
- [ ] `./verify.sh` completed without error.
- [ ] `~/.hermes/scripts/finance_market_rss_probe.py` exists and is executable.
- [ ] `~/.hermes/skills/finance-market-briefing/SKILL.md` exists.

## Cron configuration

- [ ] Cron job name is `North America Market Brief` or equivalent.
- [ ] Cron attaches the `finance-market-briefing` skill.
- [ ] Cron script is `finance_market_rss_probe.py`.
- [ ] Toolsets include `terminal`, plus web/search/browser fallback if available.
- [ ] Schedule matches the reader's intended local market time.
- [ ] Delivery target is appropriate for the user (`origin`, email, Telegram, etc.).

## Output quality

- [ ] Every main item has at least one URL.
- [ ] The brief includes US equities/TMT and Canada lens.
- [ ] It explains market drivers, not just headlines.
- [ ] It does not give buy/sell recommendations or personalized investment advice.
- [ ] It distinguishes latest available trading day vs live market data.
- [ ] Watchlist contains concrete upcoming events/data, not generic statements.

## Failure modes

- If probe is slow, reduce source count or per-source timeout.
- If Canada coverage is weak, add Canada-specific feeds/sources and keep verification strict.
- If the brief has no URLs, tighten the cron prompt's source-link rule.
- If it sounds like advice, tighten the not-investment-advice rule.
