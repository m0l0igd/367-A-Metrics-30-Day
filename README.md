# 367-A MetricRank Dashboard

Replicates the **MetricRank Tableau dashboard** for Region 367-A in a fast,
offline-ready HTML file. Data is pulled directly from the live Tableau dashboard
via Playwright + Walmart SSO — no BigQuery queries, no guesswork.

## Quick Start (new machine)

```
git clone <this-repo>
cd 367a-metricrank
setup.bat
```

That's it. `setup.bat` will:
1. Verify Code Puppy is installed (required for Python + Playwright)
2. Register a **daily 07:30 AM scheduled task** to auto-refresh
3. Do an initial build from the last committed data
4. Open the dashboard in your browser

## Manual Refresh

Double-click **`REFRESH.bat`** anytime — pulls live data from Tableau and rebuilds.

## Files

| File | Purpose |
|---|---|
| `setup.bat` | One-time setup on a new machine |
| `REFRESH.bat` | Manual or scheduled refresh runner |
| `refresh.py` | Playwright automation — logs into Tableau via SSO, extracts data |
| `parse.py` | Reads `data/metrics_raw.txt`, ranks technicians, writes `output/payload.json` |
| `build.py` | Reads `output/payload.json`, writes `output/367A_Metrics_Final.html` |
| `data/metrics_raw.txt` | Last committed metric values (pipe-delimited) |
| `output/` | **Gitignored** — generated on every refresh |

## How Ranking Works

Matches MetricRank/Tableau **exactly**:

- **Score** = DTC rank + DTC HP rank + Self Perf rank + Response rank *(4 metrics)*
- **Standard rank** with gaps on ties (e.g. two techs tied at rank 2 → next is rank 4)
- DTC / DTC HP: lower is better (rank 1 = lowest)
- Self Perf / Response: higher is better (rank 1 = highest)
- DTC HP rank = 0 if tech has no high-priority WOs (not penalized)
- **FTF is display-only** — not included in score (confirmed from Tableau DOM)

## Requirements

- [Code Puppy](https://puppy.walmart.com) installed (provides Python + Playwright)
- Walmart VPN or Eagle WiFi (required for Tableau SSO)
- Google Chrome installed
