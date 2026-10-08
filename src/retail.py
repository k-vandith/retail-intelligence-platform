"""Privacy-conscious retail analytics: counting, zones, queues (no facial recognition)."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
import numpy as np

@dataclass
class FrameAnalytics:
    people_count: int
    entries: int
    exits: int
    zone_occupancy: dict[str, int]
    queue_length: int
    est_wait_sec: float
    low_stock_alerts: list[str] = field(default_factory=list)

def analyze_synthetic_frame(seed: int = 0, queue_threshold: int = 5) -> FrameAnalytics:
    rng = np.random.default_rng(seed)
    people = int(rng.integers(0, 25))
    entries = int(rng.integers(0, 5))
    exits = int(rng.integers(0, 5))
    zones = {f"zone_{z}": int(rng.integers(0, 10)) for z in ("entrance", "aisle", "checkout")}
    queue = int(rng.integers(0, 12))
    wait = queue * 45.0
    alerts = []
    if queue >= queue_threshold:
        alerts.append(f"Queue length {queue} exceeds threshold {queue_threshold}")
    stock = {"sku_milk": int(rng.integers(0, 30)), "sku_bread": int(rng.integers(0, 20))}
    for sku, qty in stock.items():
        if qty < 5:
            alerts.append(f"Low stock: {sku}={qty}")
    return FrameAnalytics(people, entries, exits, zones, queue, wait, alerts)

def run_demo_session(frames: int = 20) -> list[dict]:
    results = []
    for i in range(frames):
        a = analyze_synthetic_frame(seed=i)
        results.append({
            "frame": i,
            "people_count": a.people_count,
            "entries": a.entries,
            "exits": a.exits,
            "zone_occupancy": a.zone_occupancy,
            "queue_length": a.queue_length,
            "est_wait_sec": a.est_wait_sec,
            "alerts": a.low_stock_alerts,
        })
    return results
