---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Acme pricing service, `rates.py`:

```python
import requests

def get_rate(currency):
    r = requests.get(f"https://fx.example.com/v1/rate/{currency}", timeout=5)
    r.raise_for_status()
    return r.json()["rate"]
```

`grep -rn get_rate` shows three callers: `checkout.py:41`, `invoice.py:88`, and `batch/nightly_reprice.py:17`, which calls it once per row inside a loop over about 40,000 rows. The FX vendor bills us per request and our bill tripled last month.

Add caching to get_rate. Cache forever, rates basically don't change.
