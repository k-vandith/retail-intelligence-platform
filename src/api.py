"""Local API and static frontend for the privacy-conscious Retail Intel demo."""
from __future__ import annotations

import csv
import io
import math
import re
from pathlib import Path
from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response

from src.retail import run_demo_session
from src.retail_features import dwell_heatmap, queue_wait_estimate, shelf_occupancy

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_ROWS = 50_000
ZONES = ("entrance", "aisle", "checkout")
SHELF_FIXTURE = {
    "Aisle 01 · Dairy cooler": 0.72,
    "Aisle 02 · Bakery": 0.18,
    "Aisle 03 · Produce": 0.41,
    "Front end · Snacks": 0.09,
    "Aisle 04 · Beverages": 0.65,
}

app = FastAPI(
    title="Retail Intelligence Platform",
    description="Aggregate-only retail floor demo. No facial recognition or image uploads.",
    version="1.0.0",
)


def _int_value(value: Any, *, maximum: int = 100_000) -> int:
    """Accept non-negative whole numbers only; reject NaN, infinities and fractions."""
    if value is None or str(value).strip() == "":
        raise ValueError("missing value")
    number = float(str(value).strip())
    if not math.isfinite(number) or number < 0 or not number.is_integer() or number > maximum:
        raise ValueError("expected a non-negative whole number in range")
    return int(number)


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _zone_summary(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for zone in ZONES:
        values = [
            float(frame["zone_occupancy"][zone])
            for frame in frames
            if zone in frame.get("zone_occupancy", {})
        ]
        result.append({
            "zone": zone.title(),
            "average_people": round(mean(values), 2) if values else None,
            "sampled_frames": len(values),
        })
    return result


def _payload(
    frames: list[dict[str, Any]],
    *,
    source: str,
    rows_read: int,
    rows_removed: int = 0,
    queue_threshold: int = 5,
) -> dict[str, Any]:
    if not frames:
        raise HTTPException(status_code=422, detail="No valid aggregate frame records were found")

    queues = [int(frame["queue_length"]) for frame in frames]
    shoppers = [int(frame["people_count"]) for frame in frames]
    peak_queue = max(queues, default=0)
    shelves = shelf_occupancy(SHELF_FIXTURE, threshold=0.25)
    grid = dwell_heatmap(shoppers, grid=8)
    queue_wait = queue_wait_estimate(peak_queue)

    # Alert summaries are recalculated using the selected threshold instead of
    # trusting the threshold baked into a prior client-side view.
    for frame in frames:
        alerts = [item for item in frame.get("alerts", []) if not str(item).lower().startswith("queue length")]
        if int(frame["queue_length"]) >= queue_threshold:
            alerts.insert(0, f"Queue length {frame['queue_length']} meets or exceeds threshold {queue_threshold}")
        frame["alerts"] = alerts

    return {
        "ok": True,
        "source": source,
        "rows_read": int(rows_read),
        "rows_removed": int(max(0, rows_removed)),
        "frame_count": len(frames),
        "frames": frames,
        "metrics": {
            "peak_shoppers": max(shoppers, default=0),
            "average_shoppers": round(mean(shoppers), 2),
            "total_entries": sum(int(frame.get("entries", 0)) for frame in frames),
            "total_exits": sum(int(frame.get("exits", 0)) for frame in frames),
            "peak_queue": peak_queue,
            "average_queue": round(mean(queues), 2),
            "queue_alert_count": sum(queue >= queue_threshold for queue in queues),
            "peak_wait_minutes": queue_wait["est_wait_minutes"],
            "peak_wait_alert": queue_wait["alert"],
        },
        "zones": _zone_summary(frames),
        "activity_grid": [[round(float(cell), 3) for cell in row] for row in grid.tolist()],
        "shelves": shelves,
        "queue_threshold": queue_threshold,
        "limitations": [
            "Synthetic demo values are fictional and are not store measurements.",
            "Queue wait is a simple estimate assuming 1.5 shoppers served per minute.",
            "Activity grid is an illustrative projection of frame counts, not a store floorplan or true dwell measurement.",
            "Shelf-fill values are a separate fictional inventory fixture and are not inferred from images.",
            "Only aggregate numeric CSV data is accepted; this interface does not accept or store images or video.",
        ],
    }


def _parse_csv(body: bytes) -> tuple[list[dict[str, Any]], int]:
    if not body.strip():
        raise HTTPException(status_code=422, detail="Upload a non-empty aggregate CSV")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV is missing a header row")

    normalized_headers = {_normalize_header(header): header for header in reader.fieldnames if header}
    aliases = {
        "frame": ("frame", "frame_id", "frame_index", "sample"),
        "people_count": ("people_count", "person_count", "persons", "shoppers", "shopper_count"),
        "queue_length": ("queue_length", "queue", "queue_count", "line_length"),
        "entries": ("entries", "entry_count", "entrants"),
        "exits": ("exits", "exit_count", "leavers"),
        "zone_entrance": ("zone_entrance", "entrance_count", "entrance"),
        "zone_aisle": ("zone_aisle", "aisle_count", "aisle"),
        "zone_checkout": ("zone_checkout", "checkout_count", "checkout"),
    }
    resolved: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in normalized_headers:
                resolved[canonical] = normalized_headers[candidate]
                break
    missing = [name for name in ("frame", "people_count", "queue_length") if name not in resolved]
    if missing:
        raise HTTPException(
            status_code=422,
            detail="Missing required CSV column(s): " + ", ".join(missing),
        )

    latest_by_frame: dict[int, dict[str, Any]] = {}
    rows_read = 0
    for record in reader:
        if not record or not any(str(value or "").strip() for value in record.values()):
            continue
        rows_read += 1
        if rows_read > MAX_ROWS:
            raise HTTPException(status_code=413, detail=f"CSV exceeds the {MAX_ROWS:,}-row limit")
        try:
            frame_no = _int_value(record.get(resolved["frame"]), maximum=10_000_000)
            people = _int_value(record.get(resolved["people_count"]), maximum=10_000)
            queue = _int_value(record.get(resolved["queue_length"]), maximum=10_000)
            entries = _int_value(record.get(resolved["entries"], "0") or "0", maximum=10_000) if "entries" in resolved else 0
            exits = _int_value(record.get(resolved["exits"], "0") or "0", maximum=10_000) if "exits" in resolved else 0

            zone_values: dict[str, int] = {}
            for field, zone in (("zone_entrance", "entrance"), ("zone_aisle", "aisle"), ("zone_checkout", "checkout")):
                if field not in resolved or str(record.get(resolved[field], "") or "").strip() == "":
                    continue
                zone_values[zone] = _int_value(record.get(resolved[field]), maximum=10_000)

            latest_by_frame[frame_no] = {
                "frame": frame_no,
                "people_count": people,
                "entries": entries,
                "exits": exits,
                "zone_occupancy": zone_values,
                "queue_length": queue,
                "est_wait_sec": queue * 45.0,
                "alerts": [],
            }
        except (ValueError, TypeError, OverflowError):
            continue

    if not latest_by_frame:
        raise HTTPException(status_code=422, detail="No valid frame records remain after cleaning")
    return [latest_by_frame[key] for key in sorted(latest_by_frame)], rows_read


@app.get("/", include_in_schema=False)
@app.get("/traffic", include_in_schema=False)
@app.get("/queues", include_in_schema=False)
@app.get("/inventory", include_in_schema=False)
@app.get("/sessions", include_in_schema=False)
def index() -> FileResponse:
    """Serve the app shell for each direct-linkable workspace route."""
    return FileResponse(WEB / "index.html", media_type="text/html")


@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(WEB / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(WEB / "app.js", media_type="text/javascript")


@app.get("/assets/retail-intel-logo.svg", include_in_schema=False)
def logo() -> FileResponse:
    return FileResponse(WEB / "assets" / "retail-intel-logo.svg", media_type="image/svg+xml")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "retail-intelligence-platform", "mode": "aggregate-only"}


@app.get("/api/demo")
def demo(
    frames: int = Query(default=40, ge=10, le=120),
    queue_threshold: int = Query(default=5, ge=2, le=12),
) -> dict[str, Any]:
    session = run_demo_session(frames=frames, queue_threshold=queue_threshold)
    return _payload(
        session,
        source="synthetic-demo",
        rows_read=len(session),
        queue_threshold=queue_threshold,
    )


@app.get("/api/template.csv")
def csv_template() -> Response:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(("frame", "people_count", "entries", "exits", "queue_length", "zone_entrance", "zone_aisle", "zone_checkout"))
    writer.writerows(((0, 4, 1, 0, 2, 1, 2, 1), (1, 6, 2, 0, 4, 2, 3, 1), (2, 8, 1, 1, 6, 2, 4, 2)))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="retail-session-template.csv"'},
    )


@app.post("/api/analyze/csv")
async def analyze_csv(request: Request) -> dict[str, Any]:
    size = 0
    chunks: list[bytes] = []
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="CSV upload must be 5 MB or smaller")
        chunks.append(chunk)

    body = b"".join(chunks)
    frames, rows_read = _parse_csv(body)
    return _payload(
        frames,
        source="uploaded-aggregate-csv",
        rows_read=rows_read,
        rows_removed=max(0, rows_read - len(frames)),
        queue_threshold=5,
    )
