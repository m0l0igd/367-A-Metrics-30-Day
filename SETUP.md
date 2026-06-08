# SETUP.md — Wiring up the daily auto-refresh

## What this does

A GitHub Actions workflow runs every day at 06:00 UTC (1 AM Central).
It queries BigQuery for a fresh rolling 30-day window, rebuilds `index.html`,
and pushes it back to the repo — which GitHub Pages then serves automatically.

You can also trigger it manually from:
**Repo → Actions → "Refresh 367-A Metrics Report" → Run workflow**

---

## One-time setup: GCP Service Account key

The workflow needs a service account that has BigQuery read access to
`re-ods-explorer.us_re_fm_prod.fsai_workorder_activity`.

### 1. Create a service account (if you don't have one)

```bash
gcloud iam service-accounts create 367a-metrics-refresh \
  --project=re-ods-explorer \
  --display-name="367-A Metrics GitHub Actions"
```

### 2. Grant BigQuery Data Viewer

```bash
gcloud projects add-iam-policy-binding re-ods-explorer \
  --member="serviceAccount:367a-metrics-refresh@re-ods-explorer.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding re-ods-explorer \
  --member="serviceAccount:367a-metrics-refresh@re-ods-explorer.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### 3. Create and download a JSON key

```bash
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=367a-metrics-refresh@re-ods-explorer.iam.gserviceaccount.com
```

> ⚠️ Keep `sa-key.json` off your machine after upload. Delete it.

### 4. Add to GitHub repo as a secret

1. Open your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `GCP_SA_KEY`
4. Value: paste the entire contents of `sa-key.json`
5. Save

### 5. Enable GitHub Pages (if not already)

Repo → **Settings → Pages → Source = Deploy from branch → main / (root)**

---

## File layout

| File | Purpose |
|---|---|
| `build_report.py` | Queries BQ, ranks techs, writes `index.html` |
| `template.html` | HTML shell with `%%DATA%%` and `%%PERIOD%%` holes |
| `index.html` | Generated output — served by GitHub Pages |
| `.github/workflows/refresh.yml` | Daily cron + manual dispatch |
| `requirements.txt` | Python dependencies |

---

## Running locally

```bash
pip install -r requirements.txt
gcloud auth application-default login
python build_report.py
```
