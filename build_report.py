"""
build_report.py — Refreshes 367-A Metrics GitHub Pages report.

Queries BigQuery with a rolling 30-day window, computes rankings,
then writes index.html from template.html.

Usage:
    python build_report.py

Expects GOOGLE_APPLICATION_CREDENTIALS env var (or ADC) to be set.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import bigquery

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BQ_PROJECT = "re-ods-explorer"
REGION = "367-A"
MANAGER = "Michael Leanox"
TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.html")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "index.html")

GOALS = {"dtc": 4.0, "dtc_hp": 1.9, "response": 85.0, "self_perf": 72.0, "ftf": 85.0}
ROLE_ORDER = ["GM", "HVACR", "FE"]

# ---------------------------------------------------------------------------
# SQL — rolling 30-day window; mirrors metricrank_v8.sql logic exactly
# ---------------------------------------------------------------------------
SQL = """
WITH raw AS (
  SELECT *,
    ROW_NUMBER() OVER (
      PARTITION BY tracking_nbr ORDER BY update_ts DESC
    ) AS rn
  FROM `re-ods-explorer.us_re_fm_prod.fsai_workorder_activity`
  WHERE fm_sub_region = '367-A'
    AND package7 = 'Yes'
    AND in_scope = 'Yes'
    AND UPPER(category_name) IN ('REPAIR - REACTIVE', 'INTERNAL TECH', 'RESERVE')
    AND UPPER(status_name) = 'COMPLETED'
    AND (
      status_extended_name IS NULL
      OR status_extended_name = ''
      OR UPPER(status_extended_name) IN (
        'PENDING CONFIRMATION','CONFIRMED','GMT COMPLETE','HVAC/R TECH COMPLETE')
    )
    AND UPPER(provider_name) NOT IN ('SDI INC','CROSSBID LLC')
    AND completion_date >= DATETIME_SUB(CURRENT_DATETIME(), INTERVAL 30 DAY)
    AND completion_date <= CURRENT_DATETIME()
),
deduped AS (SELECT * FROM raw WHERE rn = 1),

gm AS (
  SELECT
    aligned_gm_tech AS tech_name, 'GM' AS role, tracking_nbr,
    DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0 AS dtc_calc,
    CASE WHEN high_priority = 'Yes'
      THEN DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0
    END AS dtc_hp_calc,
    high_priority, third_party_assigned,
    sla_response_compliance, first_time_fix_compliance,
    recall_tracking_nbr, store_nbr
  FROM deduped
  WHERE aligned_gm_tech IS NOT NULL
    AND UPPER(trade_group_name) NOT IN (
      'REFRIGERATION','HVAC','KITCHEN EQUIPMENT','SECURITY',
      'GLASS & MIRRORS','GENERAL REPAIRS & MAINTENANCE',
      'STRUCTURAL REPAIRS','FLOORING','COIL CLEANING',
      'FIRE PROTECTION & SAFETY','LANDSCAPING','PARKING LOT SWEEPING',
      'POWER WASHING','SHOPPING CARTS','SHOPPING CART RETRIEVAL',
      'STORM WATER SYSTEMS','ENVIRONMENTAL SERVICES',
      'GREASE CLEANING & DISPOSAL','EXCLUDE',
      'GENERAL REPAIRS','AUDIO & VIDEO','EVENT RENTALS',
      'DOCK DOORS & EQUIPMENT','VERTICAL TRANSPORTATION','PNEUMATIC SYSTEMS')
),
hvacr AS (
  SELECT
    aligned_hvacr_tech AS tech_name, 'HVACR' AS role, tracking_nbr,
    DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0 AS dtc_calc,
    CASE WHEN high_priority = 'Yes'
      THEN DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0
    END AS dtc_hp_calc,
    high_priority, third_party_assigned,
    sla_response_compliance, first_time_fix_compliance,
    recall_tracking_nbr, store_nbr
  FROM deduped
  WHERE aligned_hvacr_tech IS NOT NULL
    AND UPPER(trade_group_name) IN (
      'REFRIGERATION','HVAC','COIL CLEANING','GENERAL REPAIRS & MAINTENANCE')
    AND UPPER(priority_name) NOT IN (
      'SCHEDULED SERVICE','TECH INITIATED','P5-ONSITE W/I 5 DAYS')
),
fe AS (
  SELECT
    aligned_food_equipment_tech AS tech_name, 'FE' AS role, tracking_nbr,
    DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0 AS dtc_calc,
    CASE WHEN high_priority = 'Yes'
      THEN DATETIME_DIFF(completion_date, call_date, MINUTE) / 1440.0
    END AS dtc_hp_calc,
    high_priority, third_party_assigned,
    sla_response_compliance, first_time_fix_compliance,
    recall_tracking_nbr, store_nbr
  FROM deduped
  WHERE aligned_food_equipment_tech IS NOT NULL
    AND UPPER(trade_group_name) IN ('KITCHEN EQUIPMENT')
    AND UPPER(priority_name) NOT IN (
      'SCHEDULED SERVICE','TECH INITIATED','P7-ONSITE W/I 7 DAYS')
),
combined AS (
  SELECT * FROM gm UNION ALL SELECT * FROM hvacr UNION ALL SELECT * FROM fe
)

SELECT
  tech_name, role,
  COUNT(*)                                                         AS total_wos,
  COUNTIF(third_party_assigned = 'No')                            AS wos_1p,
  COUNTIF(third_party_assigned = 'Yes')                           AS wos_3p,
  ROUND(AVG(CASE WHEN third_party_assigned='No'
                 THEN dtc_calc END), 2)                           AS dtc,
  ROUND(AVG(CASE WHEN third_party_assigned='No' AND high_priority='Yes'
                 THEN dtc_hp_calc END), 2)                        AS dtc_hp,
  COUNTIF(third_party_assigned='No' AND high_priority='Yes')      AS hp_wos,
  ROUND(SAFE_DIVIDE(
    COUNTIF(third_party_assigned='No'), COUNT(*)) * 100, 2)       AS self_perf,
  ROUND(SAFE_DIVIDE(
    COUNTIF(third_party_assigned='No'
            AND sla_response_compliance='Under SLA Response'),
    NULLIF(COUNTIF(third_party_assigned='No'
                   AND sla_response_compliance != 'Missing Time'), 0)
  ) * 100, 2)                                                     AS response_pct,
  ROUND(SAFE_DIVIDE(
    COUNTIF(third_party_assigned='No'
            AND first_time_fix_compliance = 'Yes First Time Fix'),
    NULLIF(COUNTIF(third_party_assigned='No'), 0)
  ) * 100, 2)                                                     AS ftf_pct,
  COUNTIF(third_party_assigned='No'
          AND sla_response_compliance='Under SLA Response')        AS sla_under,
  COUNTIF(third_party_assigned='No'
          AND sla_response_compliance='Over SLA Response')         AS sla_over,
  COUNTIF(third_party_assigned='No'
          AND sla_response_compliance='Missing Time')              AS sla_missing,
  COUNTIF(third_party_assigned='No'
          AND recall_tracking_nbr IS NOT NULL)                     AS recalls,
  COUNT(DISTINCT store_nbr)                                        AS stores
FROM combined
GROUP BY tech_name, role
ORDER BY role, dtc
"""


# ---------------------------------------------------------------------------
# Ranking helpers
# ---------------------------------------------------------------------------

def std_rank(values: list[float | None], ascending: bool = True) -> list[int]:
    """Standard competition ranking — ties share rank, next rank skips.
    None values (or excluded entries) receive rank 0.
    """
    indexed = [(v, i) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda x: x[0] if ascending else -x[0])
    ranks = [0] * len(values)
    pos = 0
    while pos < len(indexed):
        end = pos
        while end < len(indexed) - 1 and indexed[end + 1][0] == indexed[pos][0]:
            end += 1
        for k in range(pos, end + 1):
            ranks[indexed[k][1]] = pos + 1
        pos = end + 1
    return ranks


def dense_rank(values: list[float | None], ascending: bool = True) -> list[int]:
    """Dense ranking — ties share rank, no gaps after ties.
    None values receive rank 0.
    """
    unique_vals = sorted({v for v in values if v is not None},
                         reverse=not ascending)
    val_map = {v: i + 1 for i, v in enumerate(unique_vals)}
    return [val_map.get(v, 0) for v in values]


def rank_group(group: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute all per-metric ranks + composite score for one role group.

    Individual metrics: standard competition ranking.
    Overall rank: dense ranking on score (lower = better).
    DTC HP: only techs with hp_wos > 0 participate.
    FTF: ranked for display only — NOT included in score.
    """
    dtc_ranks = std_rank([t["dtc"] for t in group], ascending=True)
    dtc_hp_ranks = std_rank(
        [t["dtc_hp"] if t["hp_wos"] > 0 else None for t in group],
        ascending=True,
    )
    resp_ranks = std_rank([t["response"] for t in group], ascending=False)
    sp_ranks = std_rank([t["self_perf"] for t in group], ascending=False)
    ftf_ranks = std_rank([t["ftf"] for t in group], ascending=False)

    for i, t in enumerate(group):
        t["rank_dtc"] = dtc_ranks[i]
        t["rank_dtc_hp"] = dtc_hp_ranks[i]
        t["rank_response"] = resp_ranks[i]
        t["rank_self_perf"] = sp_ranks[i]
        t["rank_ftf"] = ftf_ranks[i]
        t["score"] = (
            dtc_ranks[i] + dtc_hp_ranks[i] + resp_ranks[i] + sp_ranks[i]
        )

    overall = dense_rank([t["score"] for t in group], ascending=True)
    for i, t in enumerate(group):
        t["rank_overall"] = overall[i]

    group.sort(key=lambda t: (t["rank_overall"], t["score"]))
    return group


# ---------------------------------------------------------------------------
# Row → tech dict
# ---------------------------------------------------------------------------

def row_to_tech(row: Any) -> dict[str, Any]:
    def _f(v: Any) -> float | None:
        return round(float(v), 2) if v is not None else None

    return {
        "name": row.tech_name,
        "role": row.role,
        "wos": int(row.total_wos),
        "wos_1p": int(row.wos_1p),
        "wos_3p": int(row.wos_3p),
        "dtc": _f(row.dtc),
        "dtc_hp": _f(row.dtc_hp),
        "hp_wos": int(row.hp_wos),
        "response": _f(row.response_pct),
        "self_perf": _f(row.self_perf),
        "ftf": _f(row.ftf_pct),
        "sla_under": int(row.sla_under),
        "sla_over": int(row.sla_over),
        "sla_missing": int(row.sla_missing),
        "recalls": int(row.recalls),
        "stores": int(row.stores),
    }


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def _fmt_date(d: datetime) -> str:
    """Jun 8, 2026 style (no leading zero on day)."""
    return d.strftime("%b %-d, %Y") if sys.platform != "win32" else d.strftime("%b %#d, %Y")


def build_meta(techs: list[dict[str, Any]]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    period = f"{_fmt_date(start)}\u2013{_fmt_date(now)}"
    return {
        "manager": MANAGER,
        "region": REGION,
        "period": period,
        "refresh": _fmt_date(now),
        "total_wos": sum(t["wos"] for t in techs),
        "total_1p": sum(t["wos_1p"] for t in techs),
        "total_3p": sum(t["wos_3p"] for t in techs),
        "n_techs": len(techs),
    }


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def build_html(techs: list[dict[str, Any]]) -> str:
    meta = build_meta(techs)
    payload = {"techs": techs, "goals": GOALS, "meta": meta}
    data_json = json.dumps(payload, separators=(",", ":"))

    with open(TEMPLATE_PATH, encoding="utf-8") as fh:
        html = fh.read()

    html = html.replace("%%DATA%%", data_json)
    html = html.replace("%%PERIOD%%", meta["period"])
    return html


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import google.auth

    creds, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    # Strip quota project so billing hits re-ods-explorer directly
    if hasattr(creds, "_quota_project_id"):
        creds._quota_project_id = None

    client = bigquery.Client(project=BQ_PROJECT, credentials=creds)
    print(f"Querying BigQuery ({BQ_PROJECT}) — rolling 30-day window...")

    job = client.query(SQL)
    rows = list(job.result())

    if not rows:
        print("ERROR: BigQuery returned 0 rows.", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(rows)} tech rows returned | "
          f"{job.total_bytes_billed / 1e6:.1f} MB billed")

    # Group by role, rank each group
    by_role: dict[str, list[dict]] = {r: [] for r in ROLE_ORDER}
    for row in rows:
        if row.role in by_role:
            by_role[row.role].append(row_to_tech(row))

    ranked: list[dict] = []
    for role in ROLE_ORDER:
        group = by_role.get(role, [])
        if group:
            ranked.extend(rank_group(group))

    html = build_html(ranked)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        fh.write(html)

    meta = build_meta(ranked)
    print(f"  index.html written — {meta['n_techs']} techs | "
          f"{meta['total_1p']} 1P WOs | {meta['period']}")


if __name__ == "__main__":
    main()
