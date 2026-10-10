# Retail Intelligence Platform

<p align="center">
  <img src="web/assets/retail-intel-logo.svg" alt="Retail Intel logo" width="104">
</p>

**A privacy-conscious retail operations dashboard for aggregate shopper flow, queue pressure, and sample shelf availability.** Built with HTML, CSS, vanilla JavaScript, FastAPI, and a deterministic Python demo engine.

> **Demo status:** built-in counts and shelf levels are fictional examples, not measurements from a live store. The web workspace accepts numeric aggregate CSV data only; it does not accept or store photos, video, faces, or biometric identifiers.

## Overview

Retail teams need simple indicators for shopper volume and queue pressure without introducing a facial-recognition or video-retention system. This project provides a local-first workspace for exploring frame-level counts, queue heuristics, optional zone aggregates, and an illustrative shelf-level table. The default workflow uses deterministic synthetic data and runs without a webcam, GPU, paid API, or pretrained-model download.

## Features

- **Focused workspace pages:** Store Overview, Shopper Flow, Queue Watch, Shelf Checks, and Data Sessions each have a dedicated route.
- **Synthetic session generator:** repeatable, seeded frame records with shopper, entry/exit, zone, and queue counts.
- **Aggregate CSV import:** validates required columns, normalizes aliases, skips invalid records, sorts frames, and keeps the last valid record for duplicate frame IDs.
- **Shopper timeline:** native SVG chart with no external charting dependency.
- **Queue review:** configurable threshold, flagged-frame list, and transparent estimate based on an assumed service rate of 1.5 shoppers per minute.
- **Zone rollup and activity projection:** averages optional zone counts and shows a clearly labeled illustrative grid built from frame counts.
- **Sample inventory table:** configurable low-shelf threshold and restock list. Shelf values are independent demo fixtures, not camera estimates.
- **Exports:** active aggregate frame records as CSV, sample inventory as CSV, and a JSON analytics report.
- **Local-first UI:** no CDN, external font, database, authentication token, or external API is required for the demo.

## Architecture

```text
                HTML / CSS / Vanilla JavaScript
                              |
                              v
                 FastAPI local HTTP endpoints
                    /api/demo  /api/analyze/csv
                              |
                              v
                  Python aggregate analytics
                  session / queue / zones
                              |
                              v
                         Counts only

          No image upload, face storage, or live camera path
```

## Tech stack

- Python 3.11+
- FastAPI and Uvicorn
- NumPy for deterministic synthetic samples
- Pandas and Pillow for existing supporting data utilities
- HTML, CSS, and vanilla JavaScript for the user interface
- pytest, Ruff, Bandit, and pip-audit for validation

## Repository structure

```text
retail-intelligence-platform/
├── README.md
├── run.py
├── requirements.txt
├── requirements-dev.txt
├── web/
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── assets/
│       └── retail-intel-logo.svg
├── src/
│   ├── api.py
│   ├── app.py
│   ├── retail.py
│   ├── retail_features.py
│   └── ui_theme.py
├── scripts/
│   ├── setup_env.py
│   ├── setup.sh
│   ├── setup.ps1
│   └── generate_demo_data.py
└── tests/
    ├── test_retail.py
    ├── test_retail_features.py
    ├── test_retail_api.py
    └── test_ui_smoke.py
```

## Quick start

Requirements: Python 3.11 or newer.

### Windows PowerShell

```powershell
git clone https://github.com/k-vandith/retail-intelligence-platform.git
cd retail-intelligence-platform
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

### macOS / Linux

```bash
git clone https://github.com/k-vandith/retail-intelligence-platform.git
cd retail-intelligence-platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:8501**.

The app binds to loopback by default and is designed for local development. Choose another port with:

```bash
python run.py --port 8502
```

The API documentation is at **http://127.0.0.1:8501/docs** and its OpenAPI schema at **http://127.0.0.1:8501/openapi.json**.

### Automated environment setup

The repository also includes a cross-platform environment helper:

```bash
python scripts/setup_env.py
```

Activate the environment it creates, then start the app with **python run.py**. The helper installs runtime dependencies; use **requirements-dev.txt** when developing or running the full test suite.

## Workspace guide

| Page | Route | Purpose |
| --- | --- | --- |
| Store Overview | / | Key session metrics, shopper trend, and attention signals |
| Shopper Flow | /traffic | Available zone rollups and illustrative activity grid |
| Queue Watch | /queues | Change alert threshold and inspect frames above it |
| Shelf Checks | /inventory | Tune low-shelf trigger, review sample inventory, export CSV |
| Data Sessions | /sessions | Generate synthetic data, import aggregate CSV, inspect and export the active session |

### Typical workflow

1. Open **Data Sessions** and generate a reproducible sample, or select a CSV to analyze.
2. Use **Store Overview** to scan peak/average shopper counts and attention signals.
3. Visit **Shopper Flow** to compare zone averages if the uploaded file contains zone columns.
4. Visit **Queue Watch** to change the threshold and inspect flagged frames. The estimated wait is a heuristic based on a fixed 1.5-shoppers-per-minute service rate; it is not a measured queue wait.
5. Use **Shelf Checks** to tune the sample inventory trigger.
6. Export the active session as CSV or JSON. Exports are generated by the browser and are not automatically uploaded or saved to a server database.

## Aggregate CSV format

Required columns:

| Canonical field | Accepted aliases | Meaning |
| --- | --- | --- |
| <code>frame</code> | <code>frame_id</code>, <code>frame_index</code>, <code>sample</code> | Frame or sample identifier |
| <code>people_count</code> | <code>person_count</code>, <code>persons</code>, <code>shoppers</code>, <code>shopper_count</code> | Aggregate shopper count for that sample |
| <code>queue_length</code> | <code>queue</code>, <code>queue_count</code>, <code>line_length</code> | Aggregate queue length |

Optional columns:

| Canonical field | Accepted aliases | Meaning |
| --- | --- | --- |
| <code>entries</code> | <code>entry_count</code>, <code>entrants</code> | Entry count |
| <code>exits</code> | <code>exit_count</code>, <code>leavers</code> | Exit count |
| <code>zone_entrance</code> | <code>entrance_count</code>, <code>entrance</code> | Aggregate entrance-zone count |
| <code>zone_aisle</code> | <code>aisle_count</code>, <code>aisle</code> | Aggregate aisle-zone count |
| <code>zone_checkout</code> | <code>checkout_count</code>, <code>checkout</code> | Aggregate checkout-zone count |

Example:

```csv
frame,people_count,entries,exits,queue_length,zone_entrance,zone_aisle,zone_checkout
0,4,1,0,2,1,2,1
1,6,2,0,4,2,3,1
2,8,1,1,6,2,4,2
```

Column names are normalized case-insensitively. Counts must be non-negative whole numbers. Invalid rows are skipped; duplicate frame identifiers keep the last valid record, and valid rows are sorted by frame ID. At least one valid record must remain. The upload limit is **5 MB** and **50,000 non-empty records**.

Only aggregate counts are supported. The CSV importer intentionally does not accept a path to images or video, and it does not store raw visual material. Zone statistics are unavailable when the corresponding zone columns are not supplied.

Download a starter CSV from the app or use **GET /api/template.csv**.

## HTTP API

All endpoints run on the same local origin as the interface.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | / | Serve the overview page |
| GET | /traffic, /queues, /inventory, /sessions | Serve direct-linkable workspace pages |
| GET | /styles.css, /app.js | Serve local frontend assets |
| GET | /assets/retail-intel-logo.svg | Serve logo and favicon asset |
| GET | /api/health | Health status and operating mode |
| GET | /api/demo?frames=40&queue_threshold=5 | Generate synthetic frame data (10–120 frames; threshold 2–12) |
| GET | /api/template.csv | Download the aggregate CSV template |
| POST | /api/analyze/csv | Validate and normalize a raw CSV request body |

CSV request example:

```bash
curl -X POST "http://127.0.0.1:8501/api/analyze/csv" \
  -H "Content-Type: text/csv" \
  --data-binary "@retail-session.csv"
```

The analysis endpoint returns normalized frame records, counts read/removed, summary metrics, zone coverage, an illustrative activity grid, and the independent sample inventory fixture. Validation failures return HTTP 422. Requests above 5 MB or CSVs above 50,000 non-empty records return HTTP 413.

## Python usage

Generate a deterministic demo session:

```python
from src.retail import run_demo_session

session = run_demo_session(frames=30, queue_threshold=5)
print(session[0])
```

The existing supporting module **src/retail_features.py** contains optional person-detection and derived-metric helpers for future experiments. The default web workspace does **not** invoke the optional YOLO detector; it runs synthetic data by default, preventing surprise model download or image inference during startup.

To generate the sample JSON artifact with the helper script:

```bash
python scripts/generate_demo_data.py
```

## Development and testing

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run checks from the repository root:

```bash
ruff check src run.py tests
node --check web/app.js
bandit -q -r src run.py -ll
pip-audit -r requirements.txt --progress-spinner off
pytest -v
```

GitHub Actions runs the linter, JavaScript syntax check, Bandit, dependency audit, and pytest.

## Privacy, security, and limitations

- The default data is deterministic synthetic data and must not be represented as observed store activity.
- The shelf levels are a separate fictional inventory fixture. They are not computed from camera frames or imported shopper counts.
- The activity grid visualizes a deterministic projection of frame counts, not a floorplan, actual location, or true dwell time.
- Queue waits are rough estimates under a constant service-rate assumption. They are not measured predictions.
- The browser session is in memory. Data is not written to a persistent database by the dashboard.
- Bind to loopback for local use. The development API has no authentication and should not be exposed directly to the public internet.
- Real deployments that connect cameras or third-party detectors need a separate privacy, consent, security, and jurisdictional review. The current web UI does not implement a live camera or video-ingestion path.

## License

MIT. See LICENSE.
