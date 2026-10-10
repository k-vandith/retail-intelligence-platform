/* Retail Intel — dependency-free aggregate analytics UI. */
"use strict";

const PAGE_CONFIG = {
  "/": { key: "overview", title: "Store overview" },
  "/traffic": { key: "traffic", title: "Shopper flow" },
  "/queues": { key: "queues", title: "Queue watch" },
  "/inventory": { key: "inventory", title: "Shelf checks" },
  "/sessions": { key: "sessions", title: "Data sessions" },
};

const state = {
  frames: [],
  source: "synthetic-demo",
  rowsRead: 0,
  rowsRemoved: 0,
  queueThreshold: 5,
  shelfThreshold: 0.25,
  metrics: {},
  zones: [],
  activityGrid: [],
  shelves: [],
  busy: false,
  datasetTitle: "Synthetic floor session",
};

const byId = (id) => document.getElementById(id);
const numeric = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
};
const formatNumber = (value, digits = 1) => numeric(value) === null
  ? "—"
  : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 });
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
}[ch]));

function toast(message, type = "ok") {
  const element = byId("toast");
  element.textContent = message;
  element.classList.toggle("error", type === "error");
  element.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => element.classList.remove("show"), 3400);
}

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The local service returned an unreadable response.");
  }
  if (!response.ok) {
    const detail = Array.isArray(payload.detail) ? payload.detail.map((item) => item.msg || String(item)).join("; ") : payload.detail;
    throw new Error(detail || "Request failed with HTTP " + response.status);
  }
  return payload;
}

function setBusy(busy, message = "") {
  state.busy = busy;
  ["load-demo", "analyze-csv", "export-report", "export-inventory", "export-session-csv", "export-session-json"].forEach((id) => {
    const node = byId(id);
    if (node) node.disabled = busy || (id === "analyze-csv" && !byId("csv-file").files?.[0]);
  });
  document.body.classList.toggle("is-busy", busy);
  if (message) toast(message);
}

function computeMetrics(frames) {
  const people = frames.map((item) => Number(item.people_count) || 0);
  const queues = frames.map((item) => Number(item.queue_length) || 0);
  return {
    peak_shoppers: people.length ? Math.max(...people) : 0,
    average_shoppers: people.length ? people.reduce((sum, value) => sum + value, 0) / people.length : 0,
    total_entries: frames.reduce((sum, item) => sum + (Number(item.entries) || 0), 0),
    total_exits: frames.reduce((sum, item) => sum + (Number(item.exits) || 0), 0),
    peak_queue: queues.length ? Math.max(...queues) : 0,
    average_queue: queues.length ? queues.reduce((sum, value) => sum + value, 0) / queues.length : 0,
    queue_alert_count: queues.filter((value) => value >= state.queueThreshold).length,
    peak_wait_minutes: (queues.length ? Math.max(...queues) : 0) / 1.5,
  };
}

function setDataset(payload) {
  state.frames = Array.isArray(payload.frames) ? payload.frames : [];
  state.source = payload.source || "unknown";
  state.rowsRead = payload.rows_read ?? state.frames.length;
  state.rowsRemoved = payload.rows_removed ?? 0;
  state.metrics = payload.metrics || {};
  state.zones = Array.isArray(payload.zones) ? payload.zones : [];
  state.activityGrid = Array.isArray(payload.activity_grid) ? payload.activity_grid : [];
  state.shelves = Array.isArray(payload.shelves) ? payload.shelves : [];
  state.datasetTitle = state.source === "uploaded-aggregate-csv" ? "Imported aggregate session" : "Synthetic floor session";
  renderAll();
}

function renderKpis() {
  const metrics = computeMetrics(state.frames);
  const queueAlerts = metrics.queue_alert_count;
  const lowShelves = state.shelves.filter((shelf) => Number(shelf.occupancy) < state.shelfThreshold).length;
  byId("kpi-peak").textContent = formatNumber(metrics.peak_shoppers, 0);
  byId("kpi-average").textContent = formatNumber(metrics.average_shoppers, 1);
  byId("kpi-average-foot").textContent = formatNumber(metrics.total_entries, 0) + " entries · " + formatNumber(metrics.total_exits, 0) + " exits";
  byId("kpi-alerts").textContent = formatNumber(queueAlerts, 0);
  byId("kpi-alerts-foot").textContent = "Threshold: " + state.queueThreshold + " shoppers";
  byId("kpi-low-shelves").textContent = formatNumber(lowShelves, 0);
  byId("kpi-shelf-foot").textContent = "Trigger below " + Math.round(state.shelfThreshold * 100) + "% fill";
  byId("session-count").textContent = formatNumber(state.frames.length, 0);
  byId("dataset-title").textContent = state.datasetTitle;
  byId("dataset-subtitle").textContent = state.source === "uploaded-aggregate-csv"
    ? formatNumber(state.rowsRemoved, 0) + " rows excluded or replaced · aggregate CSV processed locally"
    : "Reproducible synthetic signals · no camera or image input";
  byId("source-label").textContent = state.source === "uploaded-aggregate-csv" ? "Imported CSV" : "Synthetic demo";
  byId("active-session-title").textContent = state.datasetTitle;
  byId("active-session-meta").textContent = formatNumber(state.frames.length, 0) + " valid frame records in the active browser session";
  byId("rows-read").textContent = formatNumber(state.rowsRead, 0);
  byId("rows-removed").textContent = formatNumber(state.rowsRemoved, 0);
  byId("session-source").textContent = state.source === "uploaded-aggregate-csv" ? "CSV" : "Synthetic";
}

function renderPeopleChart() {
  const host = byId("people-chart");
  if (!state.frames.length) {
    host.innerHTML = '<div class="empty-state">No records are available to chart.</div>';
    return;
  }
  const sample = state.frames.length > 240
    ? state.frames.filter((_, index) => index % Math.ceil(state.frames.length / 240) === 0)
    : state.frames;
  const values = sample.map((row) => Number(row.people_count) || 0);
  const maximum = Math.max(1, ...values);
  const left = 48;
  const right = 860;
  const top = 20;
  const bottom = 211;
  const width = right - left;
  const height = bottom - top;
  const coords = values.map((value, index) => ({
    x: left + (values.length < 2 ? width / 2 : (index / (values.length - 1)) * width),
    y: bottom - (value / maximum) * height,
  }));
  const points = coords.map((point) => point.x.toFixed(1) + "," + point.y.toFixed(1)).join(" ");
  const fillPoints = left + "," + bottom + " " + points + " " + right + "," + bottom;
  let grid = "";
  for (let i = 0; i <= 4; i++) {
    const y = top + (height / 4) * i;
    const label = Math.round(maximum * (4 - i) / 4);
    grid += '<line x1="' + left + '" y1="' + y + '" x2="' + right + '" y2="' + y + '" stroke="#403b2e" stroke-dasharray="3 6"/>';
    grid += '<text x="34" y="' + (y + 3) + '" text-anchor="end" fill="#8a806b" font-size="10">' + label + "</text>";
  }
  const lastFrame = state.frames[state.frames.length - 1].frame;
  const firstFrame = state.frames[0].frame;
  host.innerHTML = '<svg viewBox="0 0 900 270" role="img" aria-label="Shopper counts across ' + state.frames.length + ' frames">' +
    grid +
    '<polygon points="' + fillPoints + '" fill="rgba(232,180,91,.10)"/>' +
    '<polyline points="' + points + '" fill="none" stroke="#e8b45b" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>' +
    coords.filter((_, index) => index === coords.length - 1 || (coords.length > 2 && index === Math.floor(coords.length / 2))).map((point) =>
      '<circle cx="' + point.x + '" cy="' + point.y + '" r="4" fill="#ffdc94" stroke="#33291a" stroke-width="2"/>'
    ).join("") +
    '<text x="' + left + '" y="246" fill="#8a806b" font-size="10">Frame ' + firstFrame + "</text>" +
    '<text x="' + right + '" y="246" text-anchor="end" fill="#8a806b" font-size="10">Frame ' + lastFrame + "</text>" +
    "</svg>";
  byId("chart-range").textContent = state.frames.length + " samples · peak " + maximum + " shoppers";
}

function renderAttention() {
  const queueFlags = state.frames.filter((row) => Number(row.queue_length) >= state.queueThreshold).length;
  const lowShelves = state.shelves.filter((row) => Number(row.occupancy) < state.shelfThreshold).length;
  const items = [];
  if (queueFlags) {
    items.push({ icon: "!", kind: "", title: queueFlags + " queue-pressure frame(s)", description: "At or above the " + state.queueThreshold + "-shopper threshold. Review Queue Watch.", path: "/queues" });
  } else {
    items.push({ icon: "✓", kind: "ok", title: "No queue threshold breaches", description: "No sampled frame reaches the current trigger. This is not a live store alert.", path: "/queues" });
  }
  items.push({
    icon: lowShelves ? "↗" : "✓",
    kind: lowShelves ? "" : "ok",
    title: lowShelves ? lowShelves + " shelf restock candidate(s)" : "Sample shelf levels above trigger",
    description: "Inventory values are a separate fictional fixture, not inferred from images.",
    path: "/inventory",
  });
  items.push({
    icon: "◇",
    kind: "ok",
    title: "Privacy-first input mode",
    description: "The app accepts aggregate CSV numbers only; it has no image or video upload.",
    path: "/sessions",
  });
  byId("attention-list").innerHTML = items.map((item) =>
    '<a class="attention-item" href="' + item.path + '" data-route-link><span class="attention-icon ' + item.kind + '">' + item.icon + '</span><span><strong>' + escapeHTML(item.title) + '</strong><p>' + escapeHTML(item.description) + "</p></span></a>"
  ).join("");
}

function renderZones() {
  const host = byId("zone-list");
  const valid = state.zones.filter((zone) => numeric(zone.average_people) !== null && Number(zone.sampled_frames) > 0);
  if (!valid.length) {
    host.innerHTML = '<div class="empty-state">No zone-count columns in this dataset.<br>Include zone_entrance, zone_aisle, and zone_checkout to compare zones.</div>';
    return;
  }
  const maxValue = Math.max(1, ...valid.map((zone) => Number(zone.average_people)));
  host.innerHTML = valid.map((zone) => {
    const value = Number(zone.average_people);
    const percent = Math.max(1, (value / maxValue) * 100);
    return '<div class="zone-item"><label>' + escapeHTML(zone.zone) + '</label><div class="zone-track"><span style="width:' + percent.toFixed(1) + '%"></span></div><strong>' + formatNumber(value, 1) + '</strong></div>';
  }).join("");
}

function renderActivityGrid() {
  const host = byId("activity-grid");
  const values = state.activityGrid.flat().map((value) => Number(value) || 0);
  if (!values.length) {
    host.innerHTML = '<div class="empty-state">Activity projection is unavailable.</div>';
    return;
  }
  const max = Math.max(0.001, ...values);
  host.innerHTML = values.map((value) => {
    const level = Math.min(1, value / max);
    const alpha = 0.08 + level * 0.84;
    return '<span class="activity-cell" style="background:rgba(232,180,91,' + alpha.toFixed(3) + ')" title="Illustrative intensity ' + Math.round(level * 100) + '%"></span>';
  }).join("");
}

function renderQueueReview() {
  const metrics = computeMetrics(state.frames);
  const threshold = state.queueThreshold;
  const flagged = state.frames.filter((row) => Number(row.queue_length) >= threshold).sort((a, b) => Number(b.queue_length) - Number(a.queue_length));
  byId("queue-threshold-out").textContent = threshold + " shoppers";
  byId("queue-peak").textContent = formatNumber(metrics.peak_queue, 0);
  byId("queue-average").textContent = formatNumber(metrics.average_queue, 1);
  byId("queue-wait").textContent = formatNumber(metrics.peak_queue / 1.5, 1) + " min";
  const chip = byId("queue-status-chip");
  chip.textContent = flagged.length ? flagged.length + " FLAGGED" : "NO BREACHES";
  chip.style.color = flagged.length ? "#f0c275" : "#9cceaa";
  byId("queue-status").classList.toggle("warning", flagged.length > 0);
  byId("queue-status").innerHTML = flagged.length
    ? "<strong>" + flagged.length + " sampled frame(s) need queue review</strong><span>Trigger: queue length ≥ " + threshold + "</span>"
    : "<strong>No sampled frame crosses the threshold</strong><span>This applies to the current dataset only.</span>";
  byId("queue-table").innerHTML = flagged.length ? flagged.slice(0, 80).map((row) =>
    '<tr><td>#' + formatNumber(row.frame, 0) + '</td><td>' + formatNumber(row.queue_length, 0) + '</td><td>' + formatNumber(Number(row.queue_length) / 1.5, 1) + ' min</td><td><span class="status-chip warning">Review queue</span></td></tr>'
  ).join("") : '<tr><td colspan="4">No frames meet the configured threshold. Lower the threshold or load another session to explore queue flags.</td></tr>';
  byId("queue-foot").textContent = flagged.length > 80 ? "Showing 80 of " + flagged.length + " flagged frames." : flagged.length + " flagged frame(s) · estimated wait assumes a fixed 1.5 shoppers/minute service rate.";
}

function renderInventory() {
  const threshold = state.shelfThreshold;
  const shelves = state.shelves;
  const low = shelves.filter((row) => Number(row.occupancy) < threshold);
  const average = shelves.length ? shelves.reduce((sum, row) => sum + Number(row.occupancy), 0) / shelves.length : null;
  byId("shelf-threshold-out").textContent = Math.round(threshold * 100) + "%";
  byId("inventory-count").textContent = formatNumber(shelves.length, 0);
  byId("inventory-low-count").textContent = formatNumber(low.length, 0);
  byId("inventory-average").textContent = average === null ? "—" : Math.round(average * 100) + "%";
  byId("inventory-table").innerHTML = shelves.length ? shelves.map((row) => {
    const fill = Math.max(0, Math.min(100, Number(row.occupancy) * 100));
    const alert = Number(row.occupancy) < threshold;
    return '<tr><td>' + escapeHTML(row.sku) + '</td><td><div class="fill-cell"><span class="fill-track"><span style="width:' + fill.toFixed(1) + '%"></span></span><b>' + Math.round(fill) + '%</b></div></td><td><span class="status-chip ' + (alert ? "warning" : "neutral") + '">' + (alert ? "Low shelf" : "In range") + '</span></td><td>' + (alert ? "Restock" : "Monitor") + "</td></tr>";
  }).join("") : '<tr><td colspan="4">The sample inventory fixture is unavailable.</td></tr>';
  byId("kpi-low-shelves").textContent = formatNumber(low.length, 0);
  byId("kpi-shelf-foot").textContent = "Trigger below " + Math.round(threshold * 100) + "% fill";
}

function csvCell(value) {
  let text = value === null || value === undefined ? "" : String(value);
  return '"' + text.replace(/"/g, '""') + '"';
}
function toCSV(rows) {
  const headers = ["frame", "people_count", "entries", "exits", "queue_length", "zone_entrance", "zone_aisle", "zone_checkout"];
  const body = rows.map((row) => headers.map((header) => {
    if (header.startsWith("zone_")) return csvCell(row.zone_occupancy && row.zone_occupancy[header.slice(5)]);
    return csvCell(row[header]);
  }).join(","));
  return [headers.map(csvCell).join(",")].concat(body).join("\r\n") + "\r\n";
}

function renderFrameTable() {
  const latest = state.frames.slice(-15).reverse();
  byId("frames-table-count").textContent = formatNumber(state.frames.length, 0) + " ROWS";
  byId("frame-table").innerHTML = latest.length ? latest.map((row) => {
    const alerts = Number(row.queue_length) >= state.queueThreshold;
    return '<tr><td>#' + formatNumber(row.frame, 0) + '</td><td>' + formatNumber(row.people_count, 0) + '</td><td>' + formatNumber(row.entries, 0) + '</td><td>' + formatNumber(row.exits, 0) + '</td><td>' + formatNumber(row.queue_length, 0) + '</td><td><span class="status-chip ' + (alerts ? "warning" : "neutral") + '">' + (alerts ? "Queue review" : "Clear") + '</span></td></tr>';
  }).join("") : '<tr><td colspan="6">No records are available.</td></tr>';
}

function renderAll() {
  renderKpis();
  renderPeopleChart();
  renderAttention();
  renderZones();
  renderActivityGrid();
  renderQueueReview();
  renderInventory();
  renderFrameTable();
}

function safeDownload(filename, content, mime) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportSessionCSV() {
  if (!state.frames.length) return toast("There are no frame records to export.", "error");
  safeDownload("retail-session-aggregates.csv", toCSV(state.frames), "text/csv;charset=utf-8");
  toast("Exported " + state.frames.length + " aggregate frame records.");
}

function buildReport() {
  const metrics = computeMetrics(state.frames);
  return {
    generated_at_utc: new Date().toISOString(),
    source: state.source,
    frame_count: state.frames.length,
    rows_read: state.rowsRead,
    rows_removed_or_replaced: state.rowsRemoved,
    queue_threshold: state.queueThreshold,
    shelf_low_threshold_percent: Math.round(state.shelfThreshold * 100),
    metrics: metrics,
    queue_flags: state.frames.filter((row) => Number(row.queue_length) >= state.queueThreshold).map((row) => ({
      frame: row.frame,
      queue_length: row.queue_length,
      estimated_wait_minutes: Number(row.queue_length) / 1.5,
    })),
    inventory_fixture: state.shelves.map((shelf) => ({
      sku: shelf.sku,
      shelf_fill_percent: Math.round(Number(shelf.occupancy) * 100),
      flagged_low: Number(shelf.occupancy) < state.shelfThreshold,
    })),
    privacy: "Aggregate numeric data only. This report does not contain images, faces, or biometric identifiers.",
    limitations: [
      "Synthetic demo values are fictional and are not store measurements.",
      "Queue wait is a simple estimate assuming 1.5 shoppers served per minute.",
      "Activity grid is an illustrative projection of frame counts, not a store floorplan or true dwell measurement.",
      "Shelf-fill values are a separate fictional inventory fixture and are not inferred from images.",
    ],
  };
}

function exportReport() {
  if (!state.frames.length) return toast("There is no active dataset to report.", "error");
  safeDownload("retail-intelligence-report.json", JSON.stringify(buildReport(), null, 2), "application/json");
  toast("Exported the session analytics report.");
}

function exportInventoryCSV() {
  const rows = state.shelves.map((shelf) => ({
    sku: shelf.sku,
    shelf_fill_percent: Math.round(Number(shelf.occupancy) * 100),
    threshold_percent: Math.round(state.shelfThreshold * 100),
    status: Number(shelf.occupancy) < state.shelfThreshold ? "low_shelf" : "in_range",
    action: Number(shelf.occupancy) < state.shelfThreshold ? "restock" : "monitor",
  }));
  const headers = ["sku", "shelf_fill_percent", "threshold_percent", "status", "action"];
  const body = rows.map((row) => headers.map((header) => csvCell(row[header])).join(","));
  safeDownload("retail-shelf-checks-demo.csv", [headers.join(","), ...body].join("\r\n") + "\r\n", "text/csv;charset=utf-8");
  toast("Exported the sample inventory table.");
}

async function loadDemo() {
  if (state.busy) return;
  const frames = Number(byId("demo-frames").value);
  setBusy(true, "Generating synthetic session…");
  try {
    const payload = await fetchJSON("/api/demo?frames=" + encodeURIComponent(frames) + "&queue_threshold=" + encodeURIComponent(state.queueThreshold));
    setDataset(payload);
    toast("Loaded " + payload.frame_count + " synthetic frame records.");
  } catch (error) {
    toast(error.message || "Unable to generate a demo session.", "error");
  } finally {
    setBusy(false);
  }
}

async function analyzeCSV() {
  if (state.busy) return;
  const file = byId("csv-file").files?.[0];
  if (!file) return toast("Choose an aggregate CSV first.", "error");
  if (!file.name.toLowerCase().endsWith(".csv")) return toast("Only CSV files are supported.", "error");
  if (file.size > 5 * 1024 * 1024) return toast("CSV files must be 5 MB or smaller.", "error");
  setBusy(true, "Validating aggregate CSV…");
  try {
    const payload = await fetchJSON("/api/analyze/csv", {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: await file.arrayBuffer(),
    });
    setDataset(payload);
    toast("Analyzed " + payload.frame_count + " valid frame records.");
  } catch (error) {
    toast(error.message || "CSV analysis failed.", "error");
  } finally {
    setBusy(false);
  }
}

function activatePage() {
  const pathname = window.location.pathname.replace(/\/+$/, "") || "/";
  const page = PAGE_CONFIG[pathname] || PAGE_CONFIG["/"];
  document.querySelectorAll("[data-view]").forEach((view) => { view.hidden = view.dataset.view !== page.key; });
  document.querySelectorAll("[data-page-link]").forEach((link) => {
    const active = link.dataset.pageLink === page.key;
    link.classList.toggle("active", active);
    if (active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  byId("page-title").textContent = page.title;
  document.title = page.title + " | Retail Intel";
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("a[data-route-link]");
  if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const destination = new URL(link.href, window.location.href);
  if (destination.origin !== window.location.origin || !Object.prototype.hasOwnProperty.call(PAGE_CONFIG, destination.pathname)) return;
  event.preventDefault();
  if (destination.pathname !== window.location.pathname) history.pushState({}, "", destination.pathname);
  activatePage();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
window.addEventListener("popstate", activatePage);

async function boot() {
  try {
    const health = await fetchJSON("/api/health");
    byId("api-status").textContent = "Local engine connected";
    await loadDemo();
    if (health.status !== "ok") byId("api-status").textContent = "Engine response received";
  } catch (error) {
    byId("api-status").textContent = "Local engine unavailable";
    toast(error.message || "Start the app with python run.py.", "error");
  }
}

byId("load-demo").addEventListener("click", loadDemo);
byId("demo-frames").addEventListener("input", (event) => { byId("demo-frames-out").textContent = formatNumber(event.target.value, 0); });
byId("queue-threshold").addEventListener("input", (event) => {
  state.queueThreshold = Number(event.target.value);
  byId("queue-threshold-out").textContent = state.queueThreshold + " shoppers";
  renderAll();
});
byId("shelf-threshold").addEventListener("input", (event) => {
  state.shelfThreshold = Number(event.target.value) / 100;
  byId("shelf-threshold-out").textContent = Math.round(state.shelfThreshold * 100) + "%";
  renderAll();
});
byId("csv-file").addEventListener("change", (event) => {
  const file = event.target.files?.[0];
  byId("file-name").textContent = file ? file.name + " · " + formatNumber(file.size / 1024, 1) + " KB" : "No file selected";
  byId("analyze-csv").disabled = !file || state.busy;
});
byId("analyze-csv").addEventListener("click", analyzeCSV);
byId("export-report").addEventListener("click", exportReport);
byId("export-inventory").addEventListener("click", exportInventoryCSV);
byId("export-session-csv").addEventListener("click", exportSessionCSV);
byId("export-session-json").addEventListener("click", exportReport);

const drop = byId("file-drop");
["dragenter", "dragover"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
  event.preventDefault();
  drop.classList.add("dragover");
}));
["dragleave", "drop"].forEach((eventName) => drop.addEventListener(eventName, (event) => {
  event.preventDefault();
  drop.classList.remove("dragover");
}));
drop.addEventListener("drop", (event) => {
  const file = event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".csv")) return toast("Only CSV files are supported.", "error");
  const transfer = new DataTransfer();
  transfer.items.add(file);
  byId("csv-file").files = transfer.files;
  byId("csv-file").dispatchEvent(new Event("change", { bubbles: true }));
  analyzeCSV();
});

activatePage();
byId("demo-frames-out").textContent = formatNumber(byId("demo-frames").value, 0);
byId("queue-threshold-out").textContent = state.queueThreshold + " shoppers";
byId("shelf-threshold-out").textContent = Math.round(state.shelfThreshold * 100) + "%";
boot();
