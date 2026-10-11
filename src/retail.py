"""Privacy-conscious retail analytics: counting, zones, queues (no facial recognition)."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

SERVICE_RATE_PER_MIN = 1.5


@dataclass
class FrameAnalytics:
    people_count: int
    entries: int
    exits: int
    zone_occupancy: dict[str, int]
    queue_length: int
    est_wait_sec: float
    low_stock_alerts: list[str] = field(default_factory=list)


def _require_positive_integer(value: object, name: str, *, maximum: int = 100_000) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > maximum:
        raise ValueError(f"{name} must be a positive integer no greater than {maximum}")
    return value


def analyze_synthetic_frame(seed: int = 0, queue_threshold: int = 5) -> FrameAnalytics:
    _require_positive_integer(queue_threshold, "queue_threshold", maximum=10_000)
    rng = np.random.default_rng(seed)
    people = int(rng.integers(0, 25))
    entries = int(rng.integers(0, 5))
    exits = int(rng.integers(0, 5))
    zones = {f"zone_{zone}": int(rng.integers(0, 10)) for zone in ("entrance", "aisle", "checkout")}
    queue = int(rng.integers(0, 12))
    wait = queue / SERVICE_RATE_PER_MIN * 60.0
    alerts = []
    if queue >= queue_threshold:
        alerts.append(f"Queue length {queue} meets or exceeds threshold {queue_threshold}")
    stock = {"sku_milk": int(rng.integers(0, 30)), "sku_bread": int(rng.integers(0, 20))}
    for sku, qty in stock.items():
        if qty < 5:
            alerts.append(f"Low stock: {sku}={qty}")
    return FrameAnalytics(people, entries, exits, zones, queue, wait, alerts)


def run_demo_session(frames: int = 20, queue_threshold: int = 5) -> list[dict]:
    _require_positive_integer(frames, "frames", maximum=100_000)
    _require_positive_integer(queue_threshold, "queue_threshold", maximum=10_000)
    results = []
    for index in range(frames):
        analysis = analyze_synthetic_frame(seed=index, queue_threshold=queue_threshold)
        results.append({
            "frame": index,
            "people_count": analysis.people_count,
            "entries": analysis.entries,
            "exits": analysis.exits,
            "zone_occupancy": analysis.zone_occupancy,
            "queue_length": analysis.queue_length,
            "est_wait_sec": analysis.est_wait_sec,
            "alerts": analysis.low_stock_alerts,
        })
    return results
