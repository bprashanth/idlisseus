#!/usr/bin/env python3
"""Generate deterministic, synthetic Idli renderer fixtures.

Every data_ref handle referenced by a fixture envelope gets a matching synthetic
payload file under fixtures/data/<result_id>/<handle>.<geojson|json>, and the
envelope's data_ref.digest is the sha256 of that payload's stable JSON encoding
-- the same convention the companion result service uses
(totalrecall/dss/visual_index/result_service.py: _stable_json / _digest /
_write_result). Payloads are pure-literal or seeded-deterministic (fixed
random.Random seeds derived from the handle name via crc32) so regenerating
fixtures is reproducible. All coordinates and vocabulary are sector-neutral:
a fictional "study area" near lon 7.70, lat 46.60, generic entity/source
labels, and a metric called "index_value" with unit "units".
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import random
import shutil
import zlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "fixtures"
DATA_OUTPUT = OUTPUT / "data"


# ---------------------------------------------------------------------------
# Digests: sha256 of the stable JSON encoding, matching result_service._digest.
# ---------------------------------------------------------------------------


def _stable_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else (
        value.encode() if isinstance(value, str) else _stable_json(value).encode()
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def data_ref(handle: str, payload: Any, media_type: str = "application/json") -> dict[str, Any]:
    return {
        "kind": "result_data",
        "handle": handle,
        "media_type": media_type,
        "digest": digest(payload),
    }


# ---------------------------------------------------------------------------
# Sector-neutral synthetic geography: a fictional study area and cell grid.
#
# Every map fixture's *entire* geometry (all layers combined) is kept within
# about 0.045 deg lon x 0.035 deg lat so it composes as one auto-fit scene
# with no stray far-out features wasting the canvas.
# ---------------------------------------------------------------------------

BASE_LON = 7.700
BASE_LAT = 46.600
CELL_DEG = 0.007
GRID_ROWS = 4
GRID_COLS = 3
AOI_MARGIN = 0.003


def _r(value: float, ndigits: int = 5) -> float:
    return round(value, ndigits)


def _cell_bounds(
    row: int, col: int, cell_deg: float = CELL_DEG,
    west0: float = BASE_LON, south0: float = BASE_LAT,
) -> tuple[float, float, float, float]:
    west = _r(west0 + col * cell_deg)
    south = _r(south0 + row * cell_deg)
    east = _r(west + cell_deg)
    north = _r(south + cell_deg)
    return west, south, east, north


def _cell_role(row: int, col: int) -> str:
    return "target" if col == 1 else "context"


def _polygon_geometry(west: float, south: float, east: float, north: float) -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [west, south], [east, south], [east, north], [west, north], [west, south],
        ]],
    }


def _feature(feature_id: str, geometry: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "Feature", "id": feature_id, "geometry": geometry, "properties": properties}


def _feature_collection(features: list[dict[str, Any]]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": features}


# 01/02/03/09: shared declared-AOI grid (4 rows x 3 cols), ~0.027 x 0.034 deg.
DECLARED_AOI = (
    _r(BASE_LON - AOI_MARGIN), _r(BASE_LAT - AOI_MARGIN),
    _r(BASE_LON + GRID_COLS * CELL_DEG + AOI_MARGIN), _r(BASE_LAT + GRID_ROWS * CELL_DEG + AOI_MARGIN),
)
# The middle column (col 1) is the "target" band; points are sampled strictly
# inside grid cells, so they never fall outside the declared AOI.
TARGET_LON_RANGE = (_r(BASE_LON + CELL_DEG), _r(BASE_LON + 2 * CELL_DEG))
CONTEXT_LON_RANGES = [
    (_r(BASE_LON), _r(BASE_LON + CELL_DEG)),
    (_r(BASE_LON + 2 * CELL_DEG), _r(BASE_LON + 3 * CELL_DEG)),
]
GRID_LAT_RANGE = (_r(BASE_LAT), _r(BASE_LAT + GRID_ROWS * CELL_DEG))

# 04: standalone target AOI (~0.018 x 0.016 deg); surrounding points ring it.
RING_TARGET_AOI = (BASE_LON, BASE_LAT, _r(BASE_LON + 0.018), _r(BASE_LAT + 0.016))

# 05/06: a compact 4x3 modelled/missing cell block, with a donor-point scatter
# immediately west of (touching) its west edge -- one composed scene.
BLOCK_ROWS = 4
BLOCK_COLS = 3
BLOCK_CELL_DEG = 0.007
BLOCK_WEST = _r(BASE_LON + 0.02)
BLOCK_SOUTH = BASE_LAT
BLOCK_HEIGHT = _r(BLOCK_ROWS * BLOCK_CELL_DEG)
SCATTER_WIDTH = 0.02

# 07: a compact 4x3 uncertainty block; candidates sit inside its highest cells.
UBLOCK_WEST = BASE_LON
UBLOCK_SOUTH = BASE_LAT


def _aoi_feature_collection(feature_id: str, label: str, role: str, bounds: tuple[float, float, float, float]) -> dict[str, Any]:
    west, south, east, north = bounds
    return _feature_collection([
        _feature(feature_id, _polygon_geometry(west, south, east, north),
                  {"geometry_role": role, "label": label}),
    ])


# Per-cell density, graded from low at the edges to high near the centre column.
RECORDS_GRID = [
    [2, 5, 3],
    [7, 13, 8],
    [10, 19, 12],
    [3, 7, 4],
]
ENTITIES_GRID = [
    [1, 2, 2],
    [3, 4, 3],
    [4, 6, 4],
    [1, 3, 2],
]


def _density_cells() -> dict[str, Any]:
    features = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            west, south, east, north = _cell_bounds(row, col)
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {
                    "role": _cell_role(row, col),
                    "records": RECORDS_GRID[row][col],
                    "entities": ENTITIES_GRID[row][col],
                },
            ))
    return _feature_collection(features)


def _coverage_cells() -> dict[str, Any]:
    features = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            west, south, east, north = _cell_bounds(row, col)
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {
                    "scope_role": _cell_role(row, col),
                    "records": RECORDS_GRID[row][col],
                },
            ))
    return _feature_collection(features)


# (row, col, effort hours) for the 7 of 12 cells with documented survey effort.
EFFORT_CELLS = [
    (0, 0, 4.5), (0, 1, 6.0), (1, 1, 9.5), (1, 2, 3.0),
    (2, 0, 5.5), (2, 1, 8.0), (3, 1, 2.5),
]


def _effort_lines() -> dict[str, Any]:
    features = []
    inset = _r(CELL_DEG * 0.15)
    for row, col, hours in EFFORT_CELLS:
        west, south, east, north = _cell_bounds(row, col)
        geometry = {
            "type": "LineString",
            "coordinates": [
                [_r(west + inset), _r(south + inset)],
                [_r(east - inset), _r(north - inset)],
            ],
        }
        features.append(_feature(
            f"transect-r{row}-c{col}", geometry,
            {"effort": hours, "unit": "person_hours", "scope_role": _cell_role(row, col)},
        ))
    return _feature_collection(features)


def _coverage_effort_rows() -> list[dict[str, Any]]:
    effort_by_cell = {(row, col): hours for row, col, hours in EFFORT_CELLS}
    rows = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            rows.append({
                "cell_id": f"cell-r{row}-c{col}",
                "scope_role": _cell_role(row, col),
                "records": RECORDS_GRID[row][col],
                "effort": effort_by_cell.get((row, col), 0.0),
                "unit": "person_hours",
            })
    return rows


# ---------------------------------------------------------------------------
# Synthetic point-record generator (observations), seeded per handle.
#
# Positions and metadata are generated separately: a *position* function
# returns (lon, lat, role) triples placed deterministically within a tight
# composition (a grid band, a 3-sided ring, or a jittered scatter block);
# _make_records() then layers seeded-random event metadata onto those fixed
# positions.
# ---------------------------------------------------------------------------


def _grid_band_positions(
    seed_key: str, count: int, target_fraction: float,
) -> list[tuple[float, float, str]]:
    """Sample points inside the shared declared-AOI grid: middle column is
    "target", the two flanking columns are "context". Always inside the AOI."""
    rng = random.Random(zlib.crc32((seed_key + "-pos").encode("utf-8")))
    positions = []
    for _ in range(count):
        is_target = rng.random() < target_fraction
        if is_target:
            lon = rng.uniform(*TARGET_LON_RANGE)
        else:
            lo, hi = rng.choice(CONTEXT_LON_RANGES)
            lon = rng.uniform(lo, hi)
        lat = rng.uniform(*GRID_LAT_RANGE)
        positions.append((lon, lat, "target" if is_target else "context"))
    return positions


def _ring_positions(
    seed_key: str, count: int, bounds: tuple[float, float, float, float],
    buffer_range: tuple[float, float] = (0.002, 0.008), side_extend: float = 0.004,
) -> list[tuple[float, float, str]]:
    """Scatter points just outside 3 sides (west, north, south) of an AOI
    rectangle, within buffer_range degrees of its edge -- never inside it."""
    west, south, east, north = bounds
    rng = random.Random(zlib.crc32((seed_key + "-pos").encode("utf-8")))
    per_side = count // 3
    counts = [per_side, per_side, count - 2 * per_side]
    positions = []
    for _ in range(counts[0]):  # west
        lon = west - rng.uniform(*buffer_range)
        lat = rng.uniform(south - side_extend, north + side_extend)
        positions.append((lon, lat, "context"))
    for _ in range(counts[1]):  # north
        lat = north + rng.uniform(*buffer_range)
        lon = rng.uniform(west - side_extend, east + side_extend)
        positions.append((lon, lat, "context"))
    for _ in range(counts[2]):  # south
        lat = south - rng.uniform(*buffer_range)
        lon = rng.uniform(west - side_extend, east + side_extend)
        positions.append((lon, lat, "context"))
    return positions


def _jittered_block_positions(
    seed_key: str, count: int, cols: int, rows: int,
    west: float, south: float, width: float, height: float,
    role: str, jitter_frac: float = 0.2,
) -> list[tuple[float, float, str]]:
    """A jittered grid scatter inside a rectangle: cols*rows sub-cells, one
    point per sub-cell offset by up to jitter_frac of the sub-cell size. This
    guarantees a minimum spacing of (1 - 2*jitter_frac) * sub-cell-size
    between neighbouring points, so marks never fully overlap."""
    rng = random.Random(zlib.crc32((seed_key + "-pos").encode("utf-8")))
    cell_w = width / cols
    cell_h = height / rows
    jitter_w = cell_w * jitter_frac
    jitter_h = cell_h * jitter_frac
    positions = []
    index = 0
    for row in range(rows):
        for col in range(cols):
            if index >= count:
                return positions
            center_lon = west + (col + 0.5) * cell_w
            center_lat = south + (row + 0.5) * cell_h
            lon = center_lon + rng.uniform(-jitter_w, jitter_w)
            lat = center_lat + rng.uniform(-jitter_h, jitter_h)
            positions.append((lon, lat, role))
            index += 1
    return positions


def _make_records(
    seed_key: str, positioned: list[tuple[float, float, str]], *,
    sources: tuple[str, ...] = ("source-a", "source-b"),
    years: tuple[int, ...] = (2021, 2022, 2023),
) -> list[dict[str, Any]]:
    rng = random.Random(zlib.crc32(seed_key.encode("utf-8")))
    records = []
    for index, (lon, lat, role) in enumerate(positioned):
        year = rng.choice(years)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        records.append({
            "event_id": f"{seed_key}-{index + 1:03d}",
            "source_id": rng.choice(sources),
            "source_row": index + 1,
            "event_date": f"{year:04d}-{month:02d}-{day:02d}",
            "longitude": _r(lon),
            "latitude": _r(lat),
            "uncertainty_m": rng.choice([15, 30, 50, 75, 120, 250]),
            "count_value": rng.randint(1, 6),
            "target_role": role,
        })
    return records


def _records_as_points(records: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for row in records:
        features.append(_feature(
            row["event_id"],
            {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]},
            {
                "source_id": row["source_id"],
                "source_row": row["source_row"],
                "event_date": row["event_date"],
                "coordinate_uncertainty_m": row["uncertainty_m"],
                "count": row["count_value"],
                "scope_role": row["target_role"],
            },
        ))
    return _feature_collection(features)


def _records_as_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "event_id": row["event_id"],
            "source_id": row["source_id"],
            "source_row": row["source_row"],
            "event_date": row["event_date"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "uncertainty_m": row["uncertainty_m"],
            "count_value": row["count_value"],
            "target_role": row["target_role"],
        }
        for row in records
    ]


OUTAGE_FRESHNESS = {"source-a": "current", "source-b": "current", "source-c": "stale"}


def _outage_points(records: list[dict[str, Any]]) -> dict[str, Any]:
    features = []
    for row in records:
        features.append(_feature(
            row["event_id"],
            {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]},
            {
                "source_id": row["source_id"],
                "source_row": row["source_row"],
                "event_date": row["event_date"],
                "coordinate_uncertainty_m": row["uncertainty_m"],
                "count": row["count_value"],
                "scope_role": row["target_role"],
                "freshness": OUTAGE_FRESHNESS.get(row["source_id"], "current"),
            },
        ))
    return _feature_collection(features)


def _outage_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**row, "freshness": OUTAGE_FRESHNESS.get(row["source_id"], "current")}
        for row in _records_as_rows(records)
    ]


# ---------------------------------------------------------------------------
# Modelled surfaces (transfer estimate/uncertainty, failed-gate, value of info).
#
# 05/06 share one compact 4x3 "target area" block (BLOCK_WEST/BLOCK_SOUTH);
# their donor-point scatter sits immediately west of it (see fixtures()).
# ---------------------------------------------------------------------------

ESTIMATE_GRID = [
    [0.55, 0.62, 0.58],
    [0.66, 0.74, 0.69],
    [0.71, 0.81, 0.76],
    [0.52, 0.58, 0.55],
]
MODELLED_UNCERTAINTY_GRID = [
    [0.24, 0.18, 0.22],
    [0.16, 0.12, 0.15],
    [0.13, 0.09, 0.11],
    [0.26, 0.21, 0.25],
]


def _estimate_cells() -> dict[str, Any]:
    features = []
    for row in range(BLOCK_ROWS):
        for col in range(BLOCK_COLS):
            west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, BLOCK_WEST, BLOCK_SOUTH)
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {
                    "estimate": ESTIMATE_GRID[row][col],
                    "uncertainty": MODELLED_UNCERTAINTY_GRID[row][col],
                    "scope_role": "target", "unit": "index_value",
                },
            ))
    return _feature_collection(features)


def _uncertainty_cells_target() -> dict[str, Any]:
    features = []
    for row in range(BLOCK_ROWS):
        for col in range(BLOCK_COLS):
            west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, BLOCK_WEST, BLOCK_SOUTH)
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {"uncertainty": MODELLED_UNCERTAINTY_GRID[row][col], "scope_role": "target"},
            ))
    return _feature_collection(features)


def _unsupported_cells() -> dict[str, Any]:
    features = []
    for row in range(BLOCK_ROWS):
        for col in range(BLOCK_COLS):
            west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, BLOCK_WEST, BLOCK_SOUTH)
            reason = "insufficient-environmental-support" if col == 1 else "boundary-extrapolation"
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {"scope_role": "target", "status": "unsupported", "reason": reason},
            ))
    return _feature_collection(features)


# 07: compact 4x3 uncertainty block (edges high, centre low -- realistically
# under-sampled edges are least certain). Candidate points sit inside the 8
# highest-uncertainty cells: that's the "sample where uncertainty is highest"
# story.
UNCERTAINTY_GRID = [
    [0.72, 0.55, 0.68],
    [0.48, 0.22, 0.44],
    [0.36, 0.15, 0.33],
    [0.70, 0.51, 0.66],
]


def _uncertainty_surface_cells() -> dict[str, Any]:
    features = []
    for row in range(BLOCK_ROWS):
        for col in range(BLOCK_COLS):
            west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, UBLOCK_WEST, UBLOCK_SOUTH)
            features.append(_feature(
                f"cell-r{row}-c{col}", _polygon_geometry(west, south, east, north),
                {"uncertainty": UNCERTAINTY_GRID[row][col], "scope_role": _cell_role(row, col)},
            ))
    return _feature_collection(features)


# (rank, row, col, expected_information_gain, accessible) -- the 8 cells with
# the highest UNCERTAINTY_GRID values, ranked by expected information gain.
CANDIDATE_CELLS = [
    (1, 0, 0, 0.41, True),
    (2, 3, 0, 0.37, True),
    (3, 0, 2, 0.33, True),
    (4, 3, 2, 0.29, True),
    (5, 0, 1, 0.24, True),
    (6, 3, 1, 0.19, True),
    (7, 1, 0, 0.14, False),
    (8, 1, 2, 0.08, False),
]


def _candidate_points() -> dict[str, Any]:
    features = []
    for rank, row, col, gain, accessible in CANDIDATE_CELLS:
        west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, UBLOCK_WEST, UBLOCK_SOUTH)
        lon, lat = _r((west + east) / 2), _r((south + north) / 2)
        features.append(_feature(
            f"candidate-{rank:02d}", {"type": "Point", "coordinates": [lon, lat]},
            {"rank": rank, "expected_information_gain": gain, "accessible": accessible,
             "label": f"Candidate site {rank}"},
        ))
    return _feature_collection(features)


def _candidate_rows() -> list[dict[str, Any]]:
    rows = []
    for rank, row, col, gain, accessible in CANDIDATE_CELLS:
        west, south, east, north = _cell_bounds(row, col, BLOCK_CELL_DEG, UBLOCK_WEST, UBLOCK_SOUTH)
        rows.append({
            "rank": rank, "longitude": _r((west + east) / 2), "latitude": _r((south + north) / 2),
            "expected_information_gain": gain, "accessible": accessible,
        })
    return rows


# ---------------------------------------------------------------------------
# Time series: 60 monthly values (2019-01..2023-12) with 3 missing months.
# ---------------------------------------------------------------------------

GAP_MONTH_INDICES = {8, 29, 51}


def _time_series() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng = random.Random(zlib.crc32(b"metric-time-series"))
    metric_rows = []
    coverage_rows = []
    for index in range(60):
        year = 2019 + index // 12
        month = index % 12 + 1
        noise = round(rng.uniform(-0.6, 0.6), 2)
        value = None if index in GAP_MONTH_INDICES else round(12.0 + 0.35 * index + noise, 2)
        # Deterministic, monotonically widening 80% interval around value: the
        # further into the record, the less certain the estimate.
        width = None if value is None else round(0.5 + 0.05 * index, 2)
        lower = None if value is None else round(value - width, 2)
        upper = None if value is None else round(value + width, 2)
        metric_rows.append({
            "year": year, "month": month, "value": value, "unit": "units", "source_id": "source-a",
            "lower": lower, "upper": upper,
        })
        coverage_rows.append({
            "year": year, "month": month, "present": value is not None, "source_id": "source-a",
        })
    return metric_rows, coverage_rows


def _time_series_drilldown_rows(metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"row_id": index + 1, **row} for index, row in enumerate(metric_rows)]


def _time_series_max_annotation(metric_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Point annotation anchored at the series maximum (highest value row)."""
    best = max((row for row in metric_rows if row["value"] is not None), key=lambda row: row["value"])
    return {
        "anchor": {
            "kind": "point",
            "t": f"{best['year']:04d}-{best['month']:02d}-01",
            "value": best["value"],
        },
        "text": "Highest value in the record",
        "emphasis": "primary",
    }


def _result_cards() -> list[dict[str, Any]]:
    return [
        {
            "result_id": "fixture-site-orientation", "title": "Site and observed coverage",
            "visual_type": "map", "view": "site-orientation", "status": "complete",
            "headline": "The site has records in 12 indexed cells.",
        },
        {
            "result_id": "fixture-observed-points", "title": "Where records are available",
            "visual_type": "map", "view": "observed-points", "status": "complete",
            "headline": "Thirty-two source-linked records are available.",
        },
        {
            "result_id": "fixture-time-series", "title": "Metric through time",
            "visual_type": "chart", "view": "metric-time-series", "status": "complete",
            "headline": "The chart contains 60 monthly values with units and coverage.",
        },
        {
            "result_id": "fixture-partial-source-outage", "title": "Available source coverage",
            "visual_type": "map", "view": "source-coverage", "status": "partial",
            "headline": "Most coverage is current; one source refresh failed.",
        },
    ]


# ---------------------------------------------------------------------------
# Envelope helpers.
# ---------------------------------------------------------------------------


def limitation(code: str, message: str, severity: str = "warning",
               affects: list[str] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "message": message,
        "affects": affects or ["answer"],
        "details_ref": None,
    }


def layer(layer_id: str, evidence_class: str, geometry_type: str, label: str,
          payload: Any, media_type: str = "application/geo+json", *,
          uncertainty: dict[str, Any] | None = None,
          denominator_ref: dict[str, Any] | None = None,
          absence_semantics: str | None = None) -> dict[str, Any]:
    result = {
        "layer_id": layer_id,
        "evidence_class": evidence_class,
        "geometry_type": geometry_type,
        "data_ref": data_ref(layer_id, payload, media_type),
        "legend": {"label": label},
        "style_hint": {"palette_role": evidence_class},
    }
    if uncertainty is not None:
        result["uncertainty"] = uncertainty
    if denominator_ref is not None:
        result["denominator_ref"] = denominator_ref
    if absence_semantics is not None:
        result["absence_semantics"] = absence_semantics
    return result


def visual(visual_id: str, visual_type: str, view: str, title: str,
           layers: list[dict[str, Any]], headline: str,
           denominators: dict[str, Any], *,
           status: str = "ready", priority: str = "primary",
           limitations: list[dict[str, Any]] | None = None,
           drilldown: bool = True, rows_payload: Any = None,
           annotations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    drilldowns: list[dict[str, Any]] = []
    if drilldown:
        if rows_payload is None:
            raise ValueError(f"rows_payload is required for drilldown visual {visual_id!r}")
        drilldowns = [{
            "action_id": f"inspect-{visual_id}",
            "label": "Inspect source rows",
            "data_ref": data_ref(f"{visual_id}-rows", rows_payload, "application/json"),
        }]
    result = {
        "visual_id": visual_id,
        "visual_type": visual_type,
        "view": view,
        "title": title,
        "priority": priority,
        "status": status,
        "scope": {
            "aoi_ids": ["target", "context"],
            "time": {"start": None, "end": None},
        },
        "layers": layers,
        "summary": {"headline": headline, "denominators": denominators},
        "drilldowns": drilldowns,
        "limitations": limitations or [],
    }
    if annotations:
        result["annotations"] = annotations
    return result


def action(action_id: str, kind: str, label: str, capability_id: str,
           arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "kind": kind,
        "label": label,
        "capability_id": capability_id,
        "arguments": arguments,
        "requires_confirmation": True,
    }


def result(key: str, original: str, resolved: str, headline: str,
           evidence_classes: list[str], visuals: list[dict[str, Any]], *,
           status: str = "complete",
           limitations: list[dict[str, Any]] | None = None,
           actions: list[dict[str, Any]] | None = None,
           capability: str = "fixture-capability") -> dict[str, Any]:
    return {
        "schema_version": "idli-result/1",
        "result_id": f"fixture-{key}",
        "request_id": f"fixture-request-{key}",
        "revision": 1,
        "status": status,
        "site": {
            "site_id": "synthetic-fixture-site",
            "label": "Synthetic fixture site",
            "pack_digest": digest("synthetic-fixture-pack"),
            "synthetic": True,
        },
        "question": {
            "original": original,
            "resolved": resolved,
            "bindings": {"aoi_ids": ["target"], "fixture": True},
        },
        "answer": {
            "headline": headline,
            "detail": "Synthetic renderer fixture; not evidence about a real place.",
            "evidence_classes": evidence_classes,
        },
        "visuals": visuals,
        "limitations": [
            limitation(
                "synthetic-data",
                "This result uses synthetic test data and is not evidence about a real place.",
                severity="info",
            ),
            *(limitations or []),
        ],
        "actions": actions or [],
        "audit": {
            "audit_id": f"fixture-audit-{key}",
            "source_versions": [{
                "source_id": "synthetic-fixture-source",
                "version": "1",
                "digest": digest("synthetic-fixture-source"),
                "synthetic": True,
            }],
            "capability_runs": [{
                "capability_id": capability,
                "version": "1.0.0",
                "status": "partial" if status == "partial" else (
                    "blocked" if status == "blocked" else "complete"
                ),
            }],
            "query_hash": digest(f"fixture-query-{key}"),
        },
    }


def fixtures() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, tuple[str, Any]]]]:
    # payload_registry: key -> {handle: (media_type, payload)}, written to
    # fixtures/data/fixture-<key>/<handle>.<ext> by main().
    payload_registry: dict[str, dict[str, tuple[str, Any]]] = {}

    def reg(key: str, handle: str, media_type: str, payload: Any) -> Any:
        payload_registry.setdefault(key, {})[handle] = (media_type, payload)
        return payload

    key = "site-orientation"
    orientation_records = _make_records(f"{key}-rows", _grid_band_positions(f"{key}-rows", 18, 0.4))
    orientation = visual(
        "orientation-map", "map", "site-orientation", "Site and observed coverage",
        [
            layer("declared-aoi", "reported", "polygon", "Declared analysis area",
                  reg(key, "declared-aoi", "application/geo+json",
                      _aoi_feature_collection("study-area", "Synthetic study area", "declared", DECLARED_AOI))),
            layer("event-density", "derived", "cell", "Indexed record density",
                  reg(key, "event-density", "application/geo+json", _density_cells())),
        ],
        "The declared area contains records in 12 indexed cells.",
        {"indexed_cells": 12, "records": 148},
        rows_payload=reg(key, "orientation-map-rows", "application/json", _records_as_rows(orientation_records)),
    )

    key = "observed-points"
    observed_records = _make_records(key, _grid_band_positions(key, 32, 0.28))
    observed = visual(
        "observed-map", "map", "observed-points", "Where records are available",
        [layer("observations", "observed", "point", "Observed records",
               reg(key, "observations", "application/geo+json", _records_as_points(observed_records)))],
        "Thirty-two source-linked records are available.",
        {"records": 32, "sources": 2, "surveyed_cells": 9},
        rows_payload=reg(key, "observed-map-rows", "application/json", _records_as_rows(observed_records)),
    )

    key = "coverage-effort"
    effort_payload = reg(key, "effort", "application/geo+json", _effort_lines())
    coverage = visual(
        "coverage-effort-map", "map", "coverage-and-effort",
        "Records and documented effort",
        [
            layer("coverage", "derived", "cell", "Record coverage",
                  reg(key, "coverage", "application/geo+json", _coverage_cells()),
                  denominator_ref=data_ref("effort", effort_payload, "application/geo+json"),
                  absence_semantics="non_detection"),
            layer("effort", "observed", "line", "Documented survey effort",
                  effort_payload),
        ],
        "Effort is documented in 7 of the 12 cells containing records.",
        {"record_cells": 12, "effort_cells": 7},
        rows_payload=reg(key, "coverage-effort-map-rows", "application/json", _coverage_effort_rows()),
    )

    empty_limit = limitation(
        "no-target-records",
        "No admitted records fall inside the target area; this is not evidence of absence.",
        affects=["surrounding-map", "answer"],
    )
    key = "empty-target-surrounding"
    surrounding_records = _make_records(key, _ring_positions(key, 27, RING_TARGET_AOI))
    surrounding = visual(
        "surrounding-map", "map", "surrounding-data",
        "Where data exists around the target",
        [
            layer("target-aoi", "reported", "polygon", "Target area",
                  reg(key, "target-aoi", "application/geo+json",
                      _aoi_feature_collection("target-area", "Target area", "target", RING_TARGET_AOI))),
            layer("surrounding-records", "observed", "point", "Surrounding records",
                  reg(key, "surrounding-records", "application/geo+json", _records_as_points(surrounding_records)),
                  absence_semantics="unknown"),
        ],
        "No target records were returned; 27 records are available in the context area.",
        {"target_records": 0, "context_records": 27},
        status="partial", limitations=[empty_limit],
        rows_payload=reg(key, "surrounding-map-rows", "application/json", _records_as_rows(surrounding_records)),
    )

    key = "modelled-passing-gates"
    donor_records = _make_records(key, _jittered_block_positions(
        key, 24, cols=6, rows=4,
        west=_r(BLOCK_WEST - SCATTER_WIDTH), south=BLOCK_SOUTH,
        width=SCATTER_WIDTH, height=BLOCK_HEIGHT, role="donor",
    ))
    modelled = visual(
        "transfer-map", "map", "donor-target-gates", "Transferred estimate and uncertainty",
        [
            layer("donor-records", "observed", "point", "Donor observations",
                  reg(key, "donor-records", "application/geo+json", _records_as_points(donor_records))),
            layer("estimate", "modelled", "raster", "Modelled estimate",
                  reg(key, "estimate", "application/geo+json", _estimate_cells()),
                  uncertainty={
                      "kind": "agreement",
                      "agreement": {"fraction": 0.85, "signal_to_noise": 1.6},
                  }),
            layer("uncertainty", "modelled", "raster", "Model uncertainty",
                  reg(key, "uncertainty", "application/geo+json", _uncertainty_cells_target())),
        ],
        "The registered transfer gate passed for 68 target cells.",
        {"donor_records": 84, "target_cells": 68, "holdout_rows": 21},
        rows_payload=reg(key, "transfer-map-rows", "application/json", _records_as_rows(donor_records)),
    )

    gate_limit = limitation(
        "transfer-gate-failed",
        "Environmental support did not cover enough of the target; no estimate is shown.",
        severity="error", affects=["failed-gate-map", "answer"],
    )
    key = "failed-gate"
    failed_donor_records = _make_records(key, _jittered_block_positions(
        key, 18, cols=6, rows=3,
        west=_r(BLOCK_WEST - SCATTER_WIDTH), south=BLOCK_SOUTH,
        width=SCATTER_WIDTH, height=BLOCK_HEIGHT, role="donor",
    ))
    failed_gate = visual(
        "failed-gate-map", "map", "donor-target-gates",
        "Donor coverage and failed transfer gate",
        [
            layer("failed-donor-records", "observed", "point", "Donor observations",
                  reg(key, "failed-donor-records", "application/geo+json", _records_as_points(failed_donor_records))),
            layer("unsupported-target", "missing", "cell", "Unsupported target cells",
                  reg(key, "unsupported-target", "application/geo+json", _unsupported_cells())),
        ],
        "Observed donor records remain visible, but the estimate was blocked.",
        {"donor_records": 19, "supported_target_fraction": 0.31},
        status="partial", limitations=[gate_limit],
        rows_payload=reg(key, "failed-gate-map-rows", "application/json", _records_as_rows(failed_donor_records)),
    )

    key = "data-request"
    request_map = visual(
        "data-request-map", "map", "value-of-information",
        "Where another measurement would help most",
        [
            layer("uncertainty-surface", "modelled", "raster", "Current uncertainty",
                  reg(key, "uncertainty-surface", "application/geo+json", _uncertainty_surface_cells())),
            layer("candidate-actions", "designed", "point", "Candidate collection locations",
                  reg(key, "candidate-actions", "application/geo+json", _candidate_points())),
        ],
        "Eight candidate locations are ranked by expected information gain.",
        {"candidate_locations": 8, "accessible_locations": 6},
        rows_payload=reg(key, "data-request-map-rows", "application/json", _candidate_rows()),
    )

    key = "time-series"
    metric_rows, coverage_rows = _time_series()
    time_series = visual(
        "time-series", "chart", "metric-time-series", "Metric through time",
        [
            layer("metric-series", "observed", "series", "Monthly measurements",
                  reg(key, "metric-series", "application/json", metric_rows), "application/json",
                  uncertainty={"kind": "interval", "level": 0.8, "inline": True}),
            layer("coverage-strip", "derived", "series", "Monthly coverage",
                  reg(key, "coverage-strip", "application/json", coverage_rows), "application/json"),
        ],
        "The chart contains 60 monthly values with units and coverage.",
        {"months": 60, "missing_months": 3, "sources": 1},
        rows_payload=reg(key, "time-series-rows", "application/json", _time_series_drilldown_rows(metric_rows)),
        annotations=[_time_series_max_annotation(metric_rows)],
    )

    outage_limit = limitation(
        "source-refresh-failed",
        "One source refresh failed; last-known-good records remain visible.",
        affects=["outage-map", "answer"],
    )
    key = "partial-source-outage"
    outage_records = _make_records(
        key, _grid_band_positions(key, 24, 0.3), sources=("source-a", "source-b", "source-c"),
    )
    outage = visual(
        "outage-map", "map", "source-coverage", "Available source coverage",
        [layer("last-known-good", "observed", "point", "Last-known-good records",
               reg(key, "last-known-good", "application/geo+json", _outage_points(outage_records)))],
        "Two sources are current and one is serving its last-known-good version.",
        {"current_sources": 2, "stale_sources": 1},
        status="partial", limitations=[outage_limit],
        rows_payload=reg(key, "outage-map-rows", "application/json", _outage_rows(outage_records)),
    )

    key = "dashboard"
    dashboard = visual(
        "dashboard", "dashboard", "composed-results", "Investigation dashboard",
        [
            layer("result-cards", "derived", "none", "Immutable prior results",
                  reg(key, "result-cards", "application/json", _result_cards()), "application/json"),
        ],
        "The dashboard composes four immutable prior results.",
        {"results": 4, "maps": 2, "charts": 1, "gaps": 1},
        drilldown=False,
    )

    results = {
        "01-site-orientation.json": result(
            "site-orientation", "Tell me about this site.",
            "Orient the user to the declared AOI and indexed source coverage.",
            "The site has records in 12 indexed cells.",
            ["reported", "derived"], [orientation],
            capability="site-orientation",
            actions=[action(
                "inspect-coverage", "drilldown", "Inspect source coverage",
                "source-coverage", {},
            )],
        ),
        "02-observed-points.json": result(
            "observed-points", "Where has this entity been recorded?",
            "Map admitted observations for the resolved entity.",
            "Thirty-two source-linked records are available.",
            ["observed"], [observed], capability="entity-record-map",
        ),
        "03-coverage-effort.json": result(
            "coverage-effort", "Where are there records and survey effort?",
            "Compare record coverage with explicit effort denominators.",
            "Documented effort covers 7 of 12 record cells.",
            ["observed", "derived"], [coverage], capability="coverage-versus-effort",
        ),
        "04-empty-target-surrounding.json": result(
            "empty-target-surrounding", "Is this entity present at the site?",
            "Check the target first, then show admitted data in the context area.",
            "No target records were returned; surrounding data is available.",
            ["observed", "missing"], [surrounding], status="partial",
            limitations=[empty_limit], capability="entity-record-map",
            actions=[action(
                "test-transfer", "run_capability", "Test transfer to the target",
                "gated-transfer", {"donor_scope": "context", "target_scope": "target"},
            )],
        ),
        "05-modelled-passing-gates.json": result(
            "modelled-passing-gates", "Can surrounding data be transferred here?",
            "Run the registered transfer model and disclose all gates.",
            "The transfer gate passed; estimate and uncertainty are available.",
            ["observed", "modelled"], [modelled], capability="gated-transfer",
        ),
        "06-failed-gate.json": result(
            "failed-gate", "Can surrounding data be transferred here?",
            "Run the registered transfer model and retain valid donor evidence if a gate fails.",
            "The transfer gate failed; observed donor coverage remains available.",
            ["observed", "missing"], [failed_gate], status="partial",
            limitations=[gate_limit], capability="gated-transfer",
            actions=[action(
                "request-model", "request_model", "Request a model for this target",
                "request-model", {"failed_gate": "environmental-support"},
            )],
        ),
        "07-data-request.json": result(
            "data-request", "Where should the next survey happen?",
            "Rank feasible collection locations using a versioned uncertainty surface.",
            "Eight candidate locations are ranked for additional collection.",
            ["modelled", "designed"], [request_map], capability="value-of-information",
            actions=[action(
                "submit-data-request", "request_data", "Submit this data request",
                "request-data", {"candidate_layer": "candidate-actions"},
            )],
        ),
        "08-time-series.json": result(
            "time-series", "How has this metric changed through time?",
            "Plot unit-compatible measurements with an explicit coverage strip.",
            "Sixty monthly values are available; three months are missing.",
            ["observed", "derived"], [time_series], capability="metric-time-series",
        ),
        "09-partial-source-outage.json": result(
            "partial-source-outage", "Show current source coverage.",
            "Show last-known-good evidence and disclose failed source refreshes.",
            "Most coverage is current; one source refresh failed.",
            ["observed"], [outage], status="partial", limitations=[outage_limit],
            capability="source-coverage",
        ),
        "10-dashboard.json": result(
            "dashboard", "Summarise this investigation as a dashboard.",
            "Compose immutable prior results without recomputing their evidence.",
            "Four audited results are ready in one dashboard.",
            ["derived"], [dashboard], capability="compose-dashboard",
            actions=[action(
                "export-report", "export_report", "Export an audited report",
                "export-report", {"result_ids": ["fixture-a", "fixture-b"]},
            )],
        ),
    }
    return results, payload_registry


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in OUTPUT.glob("*.json"):
        path.unlink()
    if DATA_OUTPUT.exists():
        shutil.rmtree(DATA_OUTPUT)
    DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

    values, payload_registry = fixtures()
    values.update({
        "activity-01-query.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-observed-points",
            "phase": "query",
            "label": "Finding admitted records",
            "capability_id": "entity-record-map",
            "state": "running",
            "sequence": 1,
        },
        "activity-02-compute.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-modelled-passing-gates",
            "phase": "compute",
            "label": "Testing transfer gates",
            "capability_id": "gated-transfer",
            "state": "running",
            "sequence": 2,
        },
        "activity-03-complete.json": {
            "schema_version": "idli-activity/1",
            "request_id": "fixture-request-modelled-passing-gates",
            "phase": "publish",
            "label": "Visual result ready",
            "capability_id": "gated-transfer",
            "state": "complete",
            "sequence": 3,
        },
    })
    for name, value in values.items():
        (OUTPUT / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # Write payload files under fixtures/data/<result_id>/<handle>.<ext>, using
    # the exact stable-JSON bytes the digest was computed from (matching
    # result_service._write_result's on-disk convention).
    for name, envelope in values.items():
        if envelope.get("schema_version") != "idli-result/1":
            continue
        result_id = envelope["result_id"]
        key = result_id[len("fixture-"):]
        handles = payload_registry.get(key, {})
        if not handles:
            continue
        result_dir = DATA_OUTPUT / result_id
        result_dir.mkdir(parents=True, exist_ok=True)
        for handle, (media_type, payload) in handles.items():
            suffix = ".geojson" if media_type == "application/geo+json" else ".json"
            (result_dir / f"{handle}{suffix}").write_bytes(_stable_json(payload).encode("utf-8"))


if __name__ == "__main__":
    main()
