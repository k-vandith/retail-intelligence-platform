"""Retail intelligence: optional person detection, queues, dwell, and shelf occupancy."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.retail import SERVICE_RATE_PER_MIN


def download_sample_video(path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw

        frames_dir = path.with_suffix("")
        frames_dir.mkdir(parents=True, exist_ok=True)
        for index in range(10):
            img = Image.new("RGB", (320, 240), (30, 30, 40))
            draw = ImageDraw.Draw(img)
            for person in range(3):
                x = 20 + index * 5 + person * 40
                draw.rectangle([x, 80, x + 20, 160], fill=(200, 180, 150))
            img.save(frames_dir / f"frame_{index:03d}.jpg")
        path.write_text(str(frames_dir), encoding="utf-8")
        return path
    except Exception:
        path.write_text("synthetic", encoding="utf-8")
        return path


def detect_persons_yolo(source: Path | None = None) -> dict[str, Any]:
    """Count persons only when a concrete input and the detector are available."""
    if source is None:
        return {
            "backend": "unavailable",
            "frame_counts": [],
            "total_detections": None,
            "error": "Provide a local image or video source. No measurements were generated.",
        }
    source = Path(source).expanduser()
    if not source.is_file():
        return {
            "backend": "unavailable",
            "frame_counts": [],
            "total_detections": None,
            "error": "The selected media file is not available. No measurements were generated.",
        }
    try:
        from ultralytics import YOLO

        model = YOLO("yolov8n.pt")
        results = model.predict(source=str(source), verbose=False)
        counts = [
            sum(1 for category in result.boxes.cls.tolist() if int(category) == 0)
            if result.boxes is not None else 0
            for result in results
        ]
        return {"backend": "yolo", "frame_counts": counts, "total_detections": int(sum(counts))}
    except Exception:
        return {
            "backend": "unavailable",
            "frame_counts": [],
            "total_detections": None,
            "error": "The detector could not complete inference. No synthetic measurements were substituted.",
        }


def shopper_count_series(frame_counts: list[int]) -> pd.DataFrame:
    values = np.asarray(frame_counts)
    if values.ndim != 1 or not np.isfinite(values.astype(float)).all():
        raise ValueError("frame_counts must be a one-dimensional list of finite counts")
    if (values < 0).any() or not np.equal(values, np.floor(values)).all():
        raise ValueError("frame_counts must contain non-negative whole numbers")
    return pd.DataFrame({"frame": list(range(len(values))), "persons": values.astype(int)})


def dwell_heatmap(frame_counts: list[int], grid: int = 8) -> np.ndarray:
    if not isinstance(grid, int) or isinstance(grid, bool) or grid < 1 or grid > 256:
        raise ValueError("grid must be a positive integer no greater than 256")
    values = np.asarray(frame_counts, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("frame_counts must contain finite non-negative values")
    heat = np.zeros((grid, grid), dtype=float)
    for index, count in enumerate(values):
        row, column = (index * 3) % grid, (index * 5) % grid
        heat[row, column] += count
    if heat.max() > 0:
        heat /= heat.max()
    return heat


def queue_wait_estimate(
    queue_length: int,
    service_rate_per_min: float = SERVICE_RATE_PER_MIN,
) -> dict[str, Any]:
    if not isinstance(queue_length, int) or isinstance(queue_length, bool) or not 0 <= queue_length <= 10_000:
        raise ValueError("queue_length must be a non-negative integer no greater than 10000")
    if (
        not isinstance(service_rate_per_min, (int, float))
        or isinstance(service_rate_per_min, bool)
        or not math.isfinite(float(service_rate_per_min))
        or service_rate_per_min <= 0
    ):
        raise ValueError("service_rate_per_min must be a positive finite number")
    wait = queue_length / float(service_rate_per_min)
    alert = wait >= 5.0
    return {
        "queue_length": queue_length,
        "est_wait_minutes": round(wait, 2),
        "alert": alert,
        "message": "Open another till" if alert else "Queue OK",
    }


def shelf_occupancy(stock_levels: dict[str, float], threshold: float = 0.25) -> list[dict[str, Any]]:
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not math.isfinite(float(threshold)) or not 0 <= threshold <= 1:
        raise ValueError("threshold must be a finite ratio between 0 and 1")
    result = []
    for sku, raw_level in stock_levels.items():
        if (
            not isinstance(raw_level, (int, float))
            or isinstance(raw_level, bool)
            or not math.isfinite(float(raw_level))
            or not 0 <= raw_level <= 1
        ):
            raise ValueError(f"occupancy for {sku!r} must be a finite ratio between 0 and 1")
        low = raw_level < threshold
        result.append({
            "sku": sku,
            "occupancy": float(raw_level),
            "low_stock": low,
            "action": "restock" if low else "ok",
        })
    return result
