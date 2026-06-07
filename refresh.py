"""
refresh.py — Pulls live data from MetricRank Tableau via Playwright + Walmart SSO,
writes data/metrics_raw.txt, then runs parse.py + build.py.

Scheduled daily at 07:30 via Windows Task Scheduler (after MetricRank's ~07:00 refresh).
Run manually anytime: python refresh.py
"""
import asyncio, re, subprocess, sys, logging
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

ROOT     = Path(__file__).parent
RAW      = ROOT / "data" / "metrics_raw.txt"
LOG      = ROOT / "output" / "refresh.log"
PYTHON   = sys.executable

LOG.parent.mkdir(exist_ok=True)
RAW.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    handlers=[
        logging.FileHandler(LOG, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

TABLEAU_URL = (
    "https://tableau-realestate.walmart.com/#/views/TopMetricsFM/MetricRank"
    "/67124dae-54a1-46c9-8963-c4a833f87931/367AGMTech?iid=1"
)
WAIT_MS  = 12_000
HEADLESS = False   # Must be False — SSO requires visible browser

NAME_RE  = re.compile(r'^([A-Z][A-Z ]+[A-Z])$')
FLOAT_RE = re.compile(r'^\d+\.\d+$')
INT_RE   = re.compile(r'^\d+$')


def _parse_table_text(raw_text: str, role: str) -> list[dict]:
    rows, lines = [], [l.strip() for l in raw_text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if NAME_RE.match(line) and len(line.split()) >= 2 and len(line) < 35:
            name, tokens = line.title(), []
            for j in range(i + 1, min(i + 20, len(lines))):
                tok = lines[j].strip()
                if NAME_RE.match(tok) and len(tok.split()) >= 2: break
                tokens.append(tok)

            floats = [t for t in tokens if FLOAT_RE.match(t)]
            ints   = [t for t in tokens if INT_RE.match(t) and int(t) < 200]
            big    = [float(f) for f in floats if float(f) > 50]
            small  = [float(f) for f in floats if float(f) <= 20]

            stores, score, dtc, dtc_hp, self_pf, resp, hp_wos = 1, None, None, None, None, None, 0
            for t in ints:
                v = int(t)
                if 1 <= v <= 9:    stores = v; break
            for t in ints:
                v = int(t)
                if 1 <= v <= 30:   score = v; break
            if small:
                dtc = small[0]
                if len(small) >= 2: dtc_hp = small[1]; hp_wos = 1
            if len(big) >= 2: self_pf, resp = big[0], big[1]

            if dtc is not None and self_pf is not None and resp is not None:
                rows.append({
                    "tech_name": name, "role": role,
                    "dtc": dtc, "dtc_hp": dtc_hp, "hp_wos": hp_wos,
                    "self_perf": self_pf, "response_pct": resp,
                    "score": score, "stores": stores,
                })
        i += 1
    return rows


async def _extract_role(page, list_value: str, role: str) -> list[dict]:
    log.info(f"Switching to: {list_value}")
    await page.wait_for_timeout(3_000)
    try:
        await page.select_option("select", label=list_value, timeout=8_000)
        await page.wait_for_timeout(WAIT_MS)
    except Exception:
        log.warning(f"select_option failed, trying click for {list_value}")
        try:
            await page.click(f"text={list_value}", timeout=5_000)
            await page.wait_for_timeout(WAIT_MS)
        except Exception as e:
            log.error(f"Could not switch list: {e}")

    body_text = await page.evaluate("() => document.body.innerText")
    rows = _parse_table_text(body_text, role)
    log.info(f"  → {len(rows)} technicians found for {role}")
    for r in rows:
        log.info(f"     {r['tech_name']:25s}  DTC={r['dtc']}  HP={r['dtc_hp']}  "
                 f"Self={r['self_perf']}%  RT={r['response_pct']}%  Score={r['score']}")
    return rows


async def run_refresh():
    log.info("=" * 60)
    log.info(f"367-A MetricRank refresh — {datetime.now():%Y-%m-%d %H:%M}")
    log.info("=" * 60)

    async with async_playwright() as p:
        user_data = Path.home() / "AppData/Local/Google/Chrome/User Data"
        browser   = await p.chromium.launch_persistent_context(
            str(user_data), channel="chrome", headless=HEADLESS,
            args=["--profile-directory=Default"], ignore_https_errors=True,
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        log.info(f"Navigating to MetricRank…")
        await page.goto(TABLEAU_URL, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(WAIT_MS)

        gm_rows    = await _extract_role(page, "GM Technician", "GM")
        hvacr_rows = await _extract_role(page, "HVAC/R Technician", "HVACR")
        fe_rows    = await _extract_role(page, "Food Equipment Technician", "FE")
        await browser.close()

    all_rows = gm_rows + hvacr_rows + fe_rows
    if len(all_rows) < 5:
        log.error(f"Only {len(all_rows)} rows — aborting. Check {LOG}")
        sys.exit(1)

    header = "tech_name|role|total_wos|wos_1p|wos_3p|dtc|dtc_hp|hp_wos|self_perf|response_pct|ftf_pct|sla_under|sla_over|sla_missing|recalls|stores"
    lines  = [header]
    for r in all_rows:
        dtc_hp = str(r["dtc_hp"]) if r["dtc_hp"] is not None else "NULL"
        lines.append(
            f"{r['tech_name']}|{r['role']}|0|0|0"
            f"|{r['dtc']}|{dtc_hp}|{r['hp_wos']}"
            f"|{r['self_perf']}|{r['response_pct']}|NULL"
            f"|0|0|0|0|{r['stores']}"
        )
    RAW.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Wrote {len(all_rows)} rows → {RAW}")

    for script in ["parse.py", "build.py"]:
        log.info(f"Running {script}…")
        result = subprocess.run(
            [PYTHON, str(ROOT / script)],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        if result.stdout: log.info(result.stdout.strip())
        if result.returncode != 0:
            log.error(f"{script} failed:\n{result.stderr}"); sys.exit(1)

    log.info(f"✅ Done — {ROOT / 'output' / '367A_Metrics_Final.html'}")


if __name__ == "__main__":
    asyncio.run(run_refresh())
