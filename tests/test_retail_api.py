from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.api import app


def request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    content: bytes | str | None = None,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, json=payload, content=content, headers=headers)

    return asyncio.run(send())


def test_static_workspace_routes_and_assets() -> None:
    root = request("GET", "/")
    assert root.status_code == 200
    assert "RETAIL INTEL" in root.text
    assert 'href="/styles.css"' in root.text

    for route in ("/traffic", "/queues", "/inventory", "/sessions"):
        response = request("GET", route)
        assert response.status_code == 200
        assert "data-view=" in response.text

    css = request("GET", "/styles.css")
    js = request("GET", "/app.js")
    logo = request("GET", "/assets/retail-intel-logo.svg")
    assert css.status_code == 200
    assert "--gold: #e8b45b" in css.text
    assert js.status_code == 200
    assert "async function analyzeCSV()" in js.text
    assert "exportInventoryCSV" in js.text
    assert logo.status_code == 200
    assert "image/svg+xml" in logo.headers["content-type"]
    assert "<svg" in logo.text


def test_frontend_referenced_ids_exist_in_html() -> None:
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    script = (root / "web" / "app.js").read_text(encoding="utf-8")
    import re

    html_ids = set(re.findall(r'id="([^"]+)"', html))
    script_ids = set(re.findall(r'byId\("([^"]+)"\)', script))
    assert script_ids - html_ids == set()


def test_health_and_demo_session_are_valid() -> None:
    health = request("GET", "/api/health")
    assert health.status_code == 200
    assert health.json()["mode"] == "aggregate-only"

    response = request("GET", "/api/demo?frames=30&queue_threshold=4")
    assert response.status_code == 200
    payload = response.json()
    assert payload["frame_count"] == 30
    assert len(payload["frames"]) == 30
    assert payload["metrics"]["peak_shoppers"] >= payload["metrics"]["average_shoppers"]
    assert payload["queue_threshold"] == 4
    assert len(payload["activity_grid"]) == 8
    assert all(len(row) == 8 for row in payload["activity_grid"])
    assert all("entrance" in frame["zone_occupancy"] for frame in payload["frames"])
    assert payload["source"] == "synthetic-demo"
    assert payload["shelves"]
    assert len(payload["activity_grid"]) == 8

    invalid = request("GET", "/api/demo?frames=2")
    assert invalid.status_code == 422


def test_csv_template_has_required_aggregate_columns() -> None:
    response = request("GET", "/api/template.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    header = response.text.splitlines()[0]
    assert "frame" in header
    assert "people_count" in header
    assert "queue_length" in header


def test_csv_analysis_normalizes_aliases_skips_invalid_and_deduplicates() -> None:
    csv = (
        "frame_index,shoppers,queue,entry_count,exit_count,entrance_count,aisle_count,checkout_count\n"
        "0,3,1,1,0,1,2,0\n"
        "1,5,6,2,0,2,3,0\n"
        "1,7,6,1,1,3,3,1\n"
        "not-a-frame,8,2,0,0,2,4,2\n"
        "3,not-a-count,2,0,0,1,1,0\n"
    )
    response = request(
        "POST",
        "/api/analyze/csv",
        content=csv,
        headers={"Content-Type": "text/csv"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "uploaded-aggregate-csv"
    assert payload["rows_read"] == 5
    assert payload["rows_removed"] == 3
    assert payload["frame_count"] == 2
    row_one = next(row for row in payload["frames"] if row["frame"] == 1)
    assert row_one["people_count"] == 7
    assert row_one["queue_length"] == 6
    assert row_one["zone_occupancy"]["entrance"] == 3
    assert payload["metrics"]["queue_alert_count"] == 1
    assert payload["zones"][0]["sampled_frames"] == 2


@pytest.mark.parametrize(
    "content, expected_detail",
    [
        (b"", "non-empty"),
        (b"frame,people_count\n0,4\n", "Missing required"),
        (b"frame,people_count,queue_length\n0,not-a-count,2\n", "No valid frame"),
    ],
)
def test_csv_analysis_returns_clear_validation_errors(content: bytes, expected_detail: str) -> None:
    response = request("POST", "/api/analyze/csv", content=content, headers={"Content-Type": "text/csv"})
    assert response.status_code == 422
    assert expected_detail.lower() in response.json()["detail"].lower()



def test_csv_analysis_rejects_ambiguous_headers_after_normalization() -> None:
    csv = (
        "frame,people_count,people-count,queue_length\n"
        "0,5,8,2\n"
    )

    response = request(
        "POST",
        "/api/analyze/csv",
        content=csv,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 422
    assert "ambiguous duplicate csv headers" in response.json()["detail"].lower()


def test_api_queue_wait_matches_the_documented_service_rate() -> None:
    response = request("GET", "/api/demo?frames=10")

    assert response.status_code == 200
    for frame in response.json()["frames"]:
        assert frame["est_wait_sec"] == pytest.approx(frame["queue_length"] / 1.5 * 60)


def test_uploaded_queue_wait_is_unavailable_without_measured_service_rate() -> None:
    csv = "frame,people_count,queue_length\n0,3,3\n"
    response = request(
        "POST",
        "/api/analyze/csv",
        content=csv,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 200
    assert response.json()["frames"][0]["est_wait_sec"] is None
    assert response.json()["metrics"]["peak_wait_minutes"] is None
    assert response.json()["metrics"]["peak_wait_alert"] is None
    assert any("no measured service rate" in item for item in response.json()["limitations"])



@pytest.mark.parametrize(
    "header, row, canonical",
    [
        ("frame,people_count,shoppers,queue_length", "0,3,9,2", "people_count"),
        ("frame,people_count,queue_length,queue_count", "0,3,2,9", "queue_length"),
        ("frame,people_count,queue_length,zone_entrance,entrance_count", "0,3,2,1,7", "zone_entrance"),
    ],
)
def test_csv_analysis_rejects_distinct_aliases_for_same_field(header, row, canonical) -> None:
    response = request(
        "POST",
        "/api/analyze/csv",
        content=f"{header}\n{row}\n",
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"].lower()
    assert f"ambiguous csv columns for {canonical}" in detail



def test_uploaded_aggregate_csv_does_not_receive_demo_inventory_or_floorplan_values() -> None:
    csv = "frame,people_count,queue_length\n0,3,2\n1,5,4\n"
    response = request(
        "POST",
        "/api/analyze/csv",
        content=csv,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "uploaded-aggregate-csv"
    assert payload["shelves"] == []
    assert payload["activity_grid"] == []
    assert any("No shelf inventory measurement" in item for item in payload["limitations"])
