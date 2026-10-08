# Retail Intelligence Platform

Privacy-conscious in-store analytics: footfall-style counting from frame sequences, queue estimation, and session metrics — designed to avoid storing identifiable imagery.

## Problem Statement

Retailers want occupancy and queue insights without building invasive surveillance stacks. A local pipeline that works on synthetic frames and aggregate metrics supports pilots and demos.

## Overview

Process image frames or synthetic motion features, estimate counts and queue pressure, and display KPIs in Streamlit. Default mode uses generated data so no camera is required.

## Features

- **Frame / session metrics**
- **Queue estimation heuristics**
- **Privacy-first design** – aggregates over raw face storage
- **Streamlit KPI dashboard**
- **Demo data generator**

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Streamlit  │────▶│   Retail     │────▶│  Metrics +  │
│     UI      │     │   engine     │     │  sessions   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │ Frames / CSV │
                    └──────────────┘
```

## Tech Stack

- Python 3.11+
- NumPy / Pandas
- Pillow
- Streamlit
- pytest

## Repository Structure

```
retail-intelligence-platform/
├── README.md
├── requirements.txt
├── src/
│   └── retail.py
├── tests/
│   └── test_retail.py
├── data/
├── scripts/
│   ├── setup_env.py
│   ├── setup.sh
│   ├── setup.ps1
│   └── generate_demo_data.py
└── docs/
```

## System Requirements

| Mode | CPU | RAM | Disk | GPU |
|------|-----|-----|------|-----|
| Demo | Any | 1 GB | 500 MB | Not needed |

## Installation

### Recommended (all platforms) — automated bootstrap

Handles missing `ensurepip`, symlink restrictions, and installs dependencies into `.venv`:

```bash
git clone https://github.com/k-vandith/retail-intelligence-platform.git
cd retail-intelligence-platform
python3 scripts/setup_env.py    # or:  python scripts/setup_env.py
```

Then activate:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### Manual setup

#### Windows (PowerShell)

```powershell
git clone https://github.com/k-vandith/retail-intelligence-platform.git
cd retail-intelligence-platform
python -m venv .venv --copies
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Linux / macOS

```bash
git clone https://github.com/k-vandith/retail-intelligence-platform.git
cd retail-intelligence-platform
# If venv fails with ensurepip errors:
#   sudo apt install python3-venv python3-pip
python3 -m venv .venv --copies
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Why `--copies`?

Some environments cannot create symlinks inside a venv (`Operation not permitted` on `lib64 → lib`). Using `--copies` avoids that. `scripts/setup_env.py` tries `--copies` first automatically.

## Environment Variables

None required.

## Dataset / Demo Mode

```bash
python scripts/generate_demo_data.py
```

## Running the Application

```bash
streamlit run src/retail.py
```

## API Usage

```python
from src.retail import process_session
print(process_session("data/demo_session/"))
```

## Testing

```bash
pytest -v
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: src` | Run from project root; ensure `PYTHONPATH=.` |
| `venv` / ensurepip fails | Run `python3 scripts/setup_env.py` or install `python3-venv` |
| `Operation not permitted` on lib64 | Use `python3 -m venv .venv --copies` |
| Missing dependency | Activate `.venv` and re-run `pip install -r requirements.txt` |

## Limitations

- Demo counting is heuristic; production CV models are optional extensions.
- Not a loss-prevention or facial-recognition system.
- Camera drivers and edge deployment are out of scope for the base repo.

## Security / Privacy

- Prefer aggregate metrics; avoid retaining identifiable faces.
- Comply with local CCTV / privacy regulations when connecting real cameras.

## Future Improvements

- Optional ONNX person-detector backend
- Multi-store rollups
- Anonymisation filters before storage

## License

MIT
