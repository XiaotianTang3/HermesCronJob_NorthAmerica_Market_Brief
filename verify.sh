#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m py_compile "$ROOT/scripts/finance_market_rss_probe.py"
python3 "$ROOT/scripts/finance_market_rss_probe.py" > /tmp/north_america_market_probe_sample.json
python3 - <<'PY'
import json
p='/tmp/north_america_market_probe_sample.json'
d=json.load(open(p))
print('Probe generated_at:', d.get('generated_at'))
print('Stats:', d.get('stats'))
assert isinstance(d.get('sources'), list), 'missing sources list'
assert d.get('stats', {}).get('items', 0) >= 1, 'probe returned no candidate items'
print('OK: probe script compiles and returns JSON. Sample saved to', p)
PY
