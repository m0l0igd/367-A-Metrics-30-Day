"""Quick smoke-test: feed the live HTML's known data through rank_group
and verify the output matches the baked-in ranks from the real site."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build_report import rank_group

# ---------- GM group (exact values from live HTML) ----------
gm_raw = [
    dict(name="Stephen Duderstadt", role="GM", wos=19, wos_1p=19, wos_3p=0,
         dtc=2.29, dtc_hp=None, hp_wos=0, response=100.0, self_perf=100.0,
         ftf=89.5, sla_under=19, sla_over=0, sla_missing=0, recalls=0, stores=1),
    dict(name="Thomas Compton", role="GM", wos=30, wos_1p=29, wos_3p=1,
         dtc=2.3, dtc_hp=None, hp_wos=0, response=94.74, self_perf=97.44,
         ftf=79.3, sla_under=28, sla_over=2, sla_missing=0, recalls=0, stores=2),
    dict(name="Jorge Altamirano", role="GM", wos=50, wos_1p=48, wos_3p=2,
         dtc=1.69, dtc_hp=None, hp_wos=0, response=89.47, self_perf=96.3,
         ftf=98.0, sla_under=43, sla_over=5, sla_missing=0, recalls=1, stores=2),
    dict(name="Kody Ewing", role="GM", wos=51, wos_1p=48, wos_3p=3,
         dtc=2.42, dtc_hp=None, hp_wos=0, response=97.22, self_perf=94.64,
         ftf=95.8, sla_under=46, sla_over=2, sla_missing=0, recalls=2, stores=2),
    dict(name="James Bruening", role="GM", wos=29, wos_1p=24, wos_3p=5,
         dtc=3.15, dtc_hp=0.13, hp_wos=1, response=92.31, self_perf=83.87,
         ftf=75.0, sla_under=22, sla_over=2, sla_missing=0, recalls=1, stores=2),
    dict(name="Nicholas Grow", role="GM", wos=53, wos_1p=48, wos_3p=5,
         dtc=4.56, dtc_hp=0.08, hp_wos=1, response=87.8, self_perf=92.42,
         ftf=78.0, sla_under=42, sla_over=7, sla_missing=0, recalls=2, stores=2),
    dict(name="Victor Pino", role="GM", wos=23, wos_1p=21, wos_3p=2,
         dtc=3.77, dtc_hp=0.1, hp_wos=1, response=70.59, self_perf=88.46,
         ftf=52.4, sla_under=17, sla_over=5, sla_missing=0, recalls=1, stores=2),
]

# Expected values from live HTML
EXPECTED_GM = {
    "Stephen Duderstadt":  dict(rank_dtc=2, rank_dtc_hp=0, rank_response=1, rank_self_perf=1, score=4,  rank_overall=1),
    "Thomas Compton":      dict(rank_dtc=3, rank_dtc_hp=0, rank_response=3, rank_self_perf=2, score=8,  rank_overall=2),
    "Jorge Altamirano":    dict(rank_dtc=1, rank_dtc_hp=0, rank_response=5, rank_self_perf=3, score=9,  rank_overall=3),
    "Kody Ewing":          dict(rank_dtc=4, rank_dtc_hp=0, rank_response=2, rank_self_perf=4, score=10, rank_overall=4),
    "James Bruening":      dict(rank_dtc=5, rank_dtc_hp=3, rank_response=4, rank_self_perf=7, score=19, rank_overall=5),
    "Nicholas Grow":       dict(rank_dtc=7, rank_dtc_hp=1, rank_response=6, rank_self_perf=5, score=19, rank_overall=5),
    "Victor Pino":         dict(rank_dtc=6, rank_dtc_hp=2, rank_response=7, rank_self_perf=6, score=21, rank_overall=6),
}

ranked_gm = rank_group(gm_raw)
failures = []
for t in ranked_gm:
    exp = EXPECTED_GM.get(t["name"])
    if exp is None:
        continue
    for field, want in exp.items():
        got = t[field]
        if got != want:
            failures.append(f"  {t['name']}.{field}: got {got}, want {want}")

# ---------- HVACR group ----------
hvacr_raw = [
    dict(name="Eian Palomino", role="HVACR", wos=10, wos_1p=10, wos_3p=0,
         dtc=0.75, dtc_hp=0.13, hp_wos=2, response=100.0, self_perf=100.0,
         ftf=100.0, sla_under=10, sla_over=0, sla_missing=0, recalls=0, stores=2),
    dict(name="Frank Shipp", role="HVACR", wos=20, wos_1p=20, wos_3p=0,
         dtc=1.59, dtc_hp=0.06, hp_wos=4, response=100.0, self_perf=100.0,
         ftf=90.0, sla_under=20, sla_over=0, sla_missing=0, recalls=1, stores=2),
    dict(name="Robert Howard", role="HVACR", wos=12, wos_1p=12, wos_3p=0,
         dtc=1.41, dtc_hp=0.17, hp_wos=2, response=87.5, self_perf=100.0,
         ftf=100.0, sla_under=10, sla_over=2, sla_missing=0, recalls=0, stores=3),
    dict(name="Mario Pelayo", role="HVACR", wos=23, wos_1p=23, wos_3p=0,
         dtc=3.68, dtc_hp=0.65, hp_wos=4, response=78.57, self_perf=100.0,
         ftf=73.9, sla_under=18, sla_over=5, sla_missing=0, recalls=0, stores=3),
    dict(name="Richard Palacios", role="HVACR", wos=16, wos_1p=16, wos_3p=0,
         dtc=4.43, dtc_hp=1.6, hp_wos=2, response=90.0, self_perf=100.0,
         ftf=62.5, sla_under=14, sla_over=2, sla_missing=0, recalls=0, stores=3),
]

EXPECTED_HVACR = {
    "Eian Palomino":   dict(rank_dtc=1, rank_dtc_hp=2, rank_response=1, rank_self_perf=1, score=5,  rank_overall=1),
    "Frank Shipp":     dict(rank_dtc=3, rank_dtc_hp=1, rank_response=1, rank_self_perf=1, score=6,  rank_overall=2),
    "Robert Howard":   dict(rank_dtc=2, rank_dtc_hp=3, rank_response=4, rank_self_perf=1, score=10, rank_overall=3),
    "Mario Pelayo":    dict(rank_dtc=4, rank_dtc_hp=4, rank_response=5, rank_self_perf=1, score=14, rank_overall=4),
    "Richard Palacios":dict(rank_dtc=5, rank_dtc_hp=5, rank_response=3, rank_self_perf=1, score=14, rank_overall=4),
}

ranked_hvacr = rank_group(hvacr_raw)
for t in ranked_hvacr:
    exp = EXPECTED_HVACR.get(t["name"])
    if exp is None:
        continue
    for field, want in exp.items():
        got = t[field]
        if got != want:
            failures.append(f"  {t['name']}.{field}: got {got}, want {want}")

# ---------- Report ----------
if failures:
    print("FAIL — ranking mismatches:")
    for f in failures:
        print(f)
    sys.exit(1)
else:
    print("PASS — all GM + HVACR ranks match live HTML exactly!")
