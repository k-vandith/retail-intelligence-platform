"""Retail intelligence: YOLO optional person detect, queues, dwell, shelf occupancy."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd

def download_sample_video(path: Path) -> Path:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image, ImageDraw
        frames_dir = path.with_suffix(""); frames_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            img = Image.new("RGB", (320, 240), (30, 30, 40))
            d = ImageDraw.Draw(img)
            for p in range(3):
                x = 20 + i*5 + p*40; d.rectangle([x, 80, x+20, 160], fill=(200, 180, 150))
            img.save(frames_dir / f"frame_{i:03d}.jpg")
        path.write_text(str(frames_dir), encoding="utf-8"); return path
    except Exception:
        path.write_text("synthetic", encoding="utf-8"); return path

def detect_persons_yolo(source: Path | None = None) -> dict[str, Any]:
    try:
        from ultralytics import YOLO
        model = YOLO("yolov8n.pt")
        results = model.predict(source=str(source) if source else "bus.jpg", verbose=False)
        counts = [sum(1 for c in r.boxes.cls.tolist() if int(c)==0) if r.boxes is not None else 0 for r in results]
        return {"backend": "yolo", "frame_counts": counts, "total_detections": int(sum(counts))}
    except Exception as exc:
        counts = [2,3,4,3,5,4,3,2,2,1]
        return {"backend": "synthetic", "frame_counts": counts, "total_detections": int(sum(counts)), "error": str(exc)}

def shopper_count_series(frame_counts: list[int]) -> pd.DataFrame:
    return pd.DataFrame({"frame": list(range(len(frame_counts))), "persons": frame_counts})

def dwell_heatmap(frame_counts: list[int], grid: int = 8) -> np.ndarray:
    heat = np.zeros((grid, grid), dtype=float)
    for i, c in enumerate(frame_counts):
        r, col = (i*3)%grid, (i*5)%grid; heat[r, col] += c
    if heat.max() > 0: heat /= heat.max()
    return heat

def queue_wait_estimate(queue_length: int, service_rate_per_min: float = 1.5) -> dict[str, Any]:
    wait = queue_length / max(service_rate_per_min, 0.1)
    alert = wait >= 5.0
    return {"queue_length": queue_length, "est_wait_minutes": round(wait, 2), "alert": alert, "message": "Open another till" if alert else "Queue OK"}

def shelf_occupancy(stock_levels: dict[str, float], threshold: float = 0.25) -> list[dict[str, Any]]:
    return [{"sku": sku, "occupancy": level, "low_stock": level < threshold, "action": "restock" if level < threshold else "ok"} for sku, level in stock_levels.items()]
