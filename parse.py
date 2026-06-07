"""
parse.py — Reads data/metrics_raw.txt, ranks technicians, writes output/payload.json
Ranking matches Tableau MetricRank exactly:
  Score = DTC rank + DTC HP rank + Self Perf rank + Response rank  (4 metrics)
  Standard rank with gaps on ties (confirmed via Tableau scores).
  FTF is display-only — not scored.
"""
import json, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT    = Path(__file__).parent
RAW     = ROOT / "data" / "metrics_raw.txt"
PAYLOAD = ROOT / "output" / "payload.json"
PAYLOAD.parent.mkdir(exist_ok=True)

def n(v, default=None):
    if v in ('NULL', '', None): return default
    try: return float(v)
    except: return default

lines = RAW.read_text(encoding='utf-8-sig').splitlines()
data  = [l for l in lines if '|' in l]
if not data:
    print("ERROR: No data in data/metrics_raw.txt"); sys.exit(1)

cols = data[0].split('|')
techs_raw = []
for line in data[1:]:
    if not line.strip(): continue
    vals = line.split('|')
    techs_raw.append({cols[i]: vals[i].strip() if i < len(vals) else '' for i in range(len(cols))})

ROLE_MAP = {
    'GM': 'GM', 'HVACR': 'HVACR', 'FE': 'FE',
    'GM Technician': 'GM', 'HVACR Technician': 'HVACR',
    'Food Equipment Technician': 'FE',
}

techs = []
for r in techs_raw:
    role = ROLE_MAP.get(r.get('role', '').strip(), r.get('role', '').strip())
    techs.append({
        'name':        r.get('tech_name', '').strip().title(),
        'role':        role,
        'wos':         int(n(r.get('total_wos'), 0)),
        'wos_1p':      int(n(r.get('wos_1p'), 0)),
        'wos_3p':      int(n(r.get('wos_3p'), 0)),
        'dtc':         n(r.get('dtc')),
        'dtc_hp':      n(r.get('dtc_hp')),
        'hp_wos':      int(n(r.get('hp_wos'), 0)),
        'response':    n(r.get('response_pct')),
        'self_perf':   n(r.get('self_perf')),
        'ftf':         n(r.get('ftf_pct')),   # display only
        'sla_under':   int(n(r.get('sla_under'), 0)),
        'sla_over':    int(n(r.get('sla_over'), 0)),
        'sla_missing': int(n(r.get('sla_missing'), 0)),
        'recalls':     int(n(r.get('recalls'), 0)),
        'stores':      int(n(r.get('stores'), 0)),
    })

# ── Ranking ───────────────────────────────────────────────────────────────────
def std_rank_asc(val, vals):
    return 1 + sum(1 for v in vals if v < val)

def std_rank_desc(val, vals):
    return 1 + sum(1 for v in vals if v > val)

for role in ['GM', 'HVACR', 'FE']:
    grp = [t for t in techs if t['role'] == role]
    if not grp: continue

    dtc_all  = [t['dtc']       for t in grp if t['dtc']       is not None]
    hp_all   = [t['dtc_hp']    for t in grp if t['dtc_hp']    is not None and t['hp_wos'] > 0]
    resp_all = [t['response']  for t in grp if t['response']  is not None]
    sp_all   = [t['self_perf'] for t in grp if t['self_perf'] is not None]
    ftf_all  = [t['ftf']       for t in grp if t['ftf']       is not None]

    for t in grp:
        t['rank_dtc']       = std_rank_asc(t['dtc'],        dtc_all)  if t['dtc']       is not None else len(grp)+1
        t['rank_dtc_hp']    = std_rank_asc(t['dtc_hp'],     hp_all)   if t['hp_wos'] > 0 and t['dtc_hp'] is not None else 0
        t['rank_response']  = std_rank_desc(t['response'],  resp_all) if t['response']  is not None else len(grp)+1
        t['rank_self_perf'] = std_rank_desc(t['self_perf'], sp_all)   if t['self_perf'] is not None else len(grp)+1
        t['rank_ftf']       = std_rank_desc(t['ftf'],       ftf_all)  if t['ftf']       is not None else len(grp)+1
        t['score'] = t['rank_dtc'] + t['rank_dtc_hp'] + t['rank_self_perf'] + t['rank_response']

    score_vals = sorted(set(t['score'] for t in grp))
    rm = {v: i+1 for i, v in enumerate(score_vals)}
    for t in grp:
        t['rank_overall'] = rm[t['score']]

# ── Period ────────────────────────────────────────────────────────────────────
now      = datetime.now()
start_dt = now - timedelta(days=30)
period   = f"{start_dt.strftime('%b %d')}–{now.strftime('%b %d, %Y')}"

payload = {
    "techs": techs,
    "goals": {"dtc": 4.0, "dtc_hp": 1.9, "response": 85.0, "self_perf": 72.0, "ftf": 85.0},
    "meta":  {
        "manager":   "Michael Leanox",
        "region":    "367-A",
        "period":    period,
        "refresh":   now.strftime('%B %d, %Y'),
        "total_wos": sum(t['wos'] for t in techs),
        "total_1p":  sum(t['wos_1p'] for t in techs),
        "total_3p":  sum(t['wos_3p'] for t in techs),
        "n_techs":   len(techs),
    }
}

PAYLOAD.write_text(json.dumps(payload, separators=(',', ':')), encoding='utf-8')

print(f"Parsed {len(techs)} technicians  |  Period: {period}")
print(f"\n{'Role':<8} {'Tech':<24} {'DTC':>5} {'r':>2} {'DTC_HP':>7} {'r':>2} {'SP%':>6} {'r':>2} {'RT%':>6} {'r':>2} {'Score':>6} {'Overall':>7}")
print("-" * 95)
for role in ['GM', 'HVACR', 'FE']:
    for t in sorted([t for t in techs if t['role'] == role], key=lambda x: x['rank_overall']):
        hp = f"{t['dtc_hp']:.2f}" if t['dtc_hp'] is not None else "  --"
        print(f"{t['role']:<8} {t['name']:<24} "
              f"{t['dtc'] or 0:>5.2f} {t['rank_dtc']:>2} "
              f"{hp:>7} {t['rank_dtc_hp']:>2} "
              f"{t['self_perf'] or 0:>6.2f} {t['rank_self_perf']:>2} "
              f"{t['response'] or 0:>6.2f} {t['rank_response']:>2} "
              f"{t['score']:>6} #{t['rank_overall']:>2}")
print(f"\nSaved: {PAYLOAD}")
