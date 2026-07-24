#!/usr/bin/env python3
"""Build a dependency-light, visual-ready AOI index from a site pack.

This is a feasibility implementation of visual-site-pack/0.1. It deliberately
uses only the Python standard library plus Pillow for the optional preview PNG.
The production design may replace SQLite/JSON with DuckDB, GeoParquet and tiles
without changing the logical tables or result contracts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import re
import sqlite3
import statistics
import time
from collections import Counter, defaultdict
from typing import Any, Iterable


SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE sources (
  source_id TEXT PRIMARY KEY, title TEXT NOT NULL, doi TEXT, url TEXT,
  publisher TEXT, license TEXT, capabilities_json TEXT NOT NULL, content_sha256 TEXT NOT NULL
);
CREATE TABLE entities (
  entity_id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, display_name TEXT NOT NULL,
  hierarchy_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE entity_aliases (
  alias_key TEXT PRIMARY KEY, alias TEXT NOT NULL, entity_id TEXT NOT NULL,
  source_id TEXT NOT NULL, FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);
CREATE TABLE locations (
  location_id TEXT NOT NULL, source_id TEXT NOT NULL, label TEXT NOT NULL,
  latitude REAL, longitude REAL, uncertainty_m REAL, properties_json TEXT NOT NULL,
  PRIMARY KEY(location_id, source_id)
);
CREATE TABLE events (
  event_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_row INTEGER NOT NULL,
  entity_id TEXT, event_type TEXT NOT NULL, evidence_class TEXT NOT NULL, status TEXT NOT NULL,
  event_date TEXT, year INTEGER, month INTEGER, latitude REAL, longitude REAL,
  uncertainty_m REAL, count_value REAL, cell_id TEXT, properties_json TEXT NOT NULL,
  FOREIGN KEY(source_id) REFERENCES sources(source_id),
  FOREIGN KEY(entity_id) REFERENCES entities(entity_id)
);
CREATE TABLE effort (
  effort_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_row INTEGER NOT NULL,
  method TEXT NOT NULL, event_date TEXT, year INTEGER, month INTEGER,
  latitude REAL, longitude REAL, effort_value REAL, effort_unit TEXT,
  cell_id TEXT, properties_json TEXT NOT NULL
);
CREATE TABLE measurements (
  measurement_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_row INTEGER NOT NULL,
  location_id TEXT, metric TEXT NOT NULL, value REAL, unit TEXT NOT NULL,
  event_date TEXT, year INTEGER, month INTEGER, latitude REAL, longitude REAL,
  cell_id TEXT, properties_json TEXT NOT NULL
);
CREATE TABLE cells (
  cell_id TEXT PRIMARY KEY, west REAL NOT NULL, south REAL NOT NULL,
  east REAL NOT NULL, north REAL NOT NULL, center_lat REAL NOT NULL,
  center_lon REAL NOT NULL, target_role TEXT NOT NULL
);
CREATE TABLE event_cell (
  cell_id TEXT NOT NULL, entity_id TEXT, source_id TEXT NOT NULL,
  event_count INTEGER NOT NULL, first_date TEXT, last_date TEXT,
  PRIMARY KEY(cell_id, entity_id, source_id)
);
CREATE TABLE event_time (
  year INTEGER NOT NULL, month INTEGER NOT NULL, entity_id TEXT, source_id TEXT NOT NULL,
  event_count INTEGER NOT NULL, PRIMARY KEY(year, month, entity_id, source_id)
);
CREATE TABLE measurement_time (
  year INTEGER NOT NULL, month INTEGER NOT NULL, metric TEXT NOT NULL,
  source_id TEXT NOT NULL, value REAL, unit TEXT NOT NULL,
  PRIMARY KEY(year, month, metric, source_id)
);
CREATE TABLE visual_views (
  view_id TEXT PRIMARY KEY, visual_type TEXT NOT NULL, title TEXT NOT NULL,
  data_contract TEXT NOT NULL, availability TEXT NOT NULL, reason TEXT
);
CREATE INDEX events_entity_idx ON events(entity_id, year, month);
CREATE INDEX events_cell_idx ON events(cell_id, entity_id);
CREATE INDEX effort_cell_idx ON effort(cell_id, year, month);
CREATE INDEX measurements_metric_idx ON measurements(metric, year, month);
"""


def _json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256_files(paths: Iterable[pathlib.Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(set(paths), key=str):
        digest.update(str(path.name).encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _stable(prefix: str, *parts: Any) -> str:
    material = "\x1f".join(str(part or "") for part in parts)
    return f"{prefix}-{hashlib.sha256(material.encode()).hexdigest()[:16]}"


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").replace("_", " ").lower()).strip()


def _float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or text.lower() in {"na", "nan", "none", "null"}:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _coord(value: Any, *, latitude: bool) -> float | None:
    number = _float(value)
    if number is None:
        return None
    limit = 90 if latitude else 180
    return number if -limit <= number <= limit else None


def _date_parts(raw: Any) -> tuple[str | None, int | None, int | None]:
    text = str(raw or "").strip()
    if not text or text.lower() == "na":
        return None, None, None
    match = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", text)
    if not match:
        return text, None, None
    year = int(match.group(1))
    month = int(match.group(2) or 1)
    normal = f"{year:04d}-{month:02d}"
    if match.group(3):
        normal += f"-{int(match.group(3)):02d}"
    return normal, year, month


def _cell(lat: float | None, lon: float | None, resolution: float = 0.01) -> str | None:
    if lat is None or lon is None:
        return None
    south = math.floor(lat / resolution) * resolution
    west = math.floor(lon / resolution) * resolution
    return f"g{resolution:.3f}:{south:.4f}:{west:.4f}"


def _row_id(row: dict[str, str], spec: str | list[str] | None, row_number: int) -> str:
    if isinstance(spec, list):
        return "|".join(str(row.get(name) or "") for name in spec)
    if isinstance(spec, str):
        return str(row.get(spec) or row_number)
    return str(row_number)


def _properties(row: dict[str, str], names: list[str] | None) -> str:
    return json.dumps(
        {name: row.get(name) for name in names or [] if row.get(name) not in (None, "", "NA")},
        ensure_ascii=False,
        sort_keys=True,
    )


class Builder:
    def __init__(self, site_pack: pathlib.Path, output: pathlib.Path):
        self.site_pack = site_pack.resolve()
        self.output = output.resolve()
        self.site = _json(self.site_pack / "site.json")
        self.registry = _json(self.site_pack / "sources.json")
        self.questions = _json(self.site_pack / "questions.json")
        self.db_path = self.output / "site_index.sqlite"
        self.conn: sqlite3.Connection | None = None
        self.aliases: dict[str, str] = {}
        self.entity_names: dict[str, tuple[str, str]] = {}
        self.stats: Counter[str] = Counter()

    def path(self, relative: str) -> pathlib.Path:
        path = (self.site_pack / relative).resolve()
        if self.site_pack not in path.parents:
            raise ValueError(f"path escapes site pack: {relative}")
        if not path.is_file():
            raise FileNotFoundError(path)
        return path

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        self.output.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript(SCHEMA)
        self._register_sources()
        self._load_crosswalks()
        self._load_hierarchies()
        self._load_named_points()
        for source in self.registry["sources"]:
            for adapter in source.get("adapters", []):
                getattr(self, f"_ingest_{adapter['kind']}")(source, adapter)
        self._materialize()
        bundle = self._bundle()
        (self.output / "visual_bundle.json").write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        self._render_preview(bundle)
        self.conn.commit()
        integrity = self.conn.execute("PRAGMA integrity_check").fetchone()[0]
        bundle["build"]["integrity"] = integrity
        bundle["build"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        (self.output / "build_report.json").write_text(
            json.dumps(bundle["build"], indent=2) + "\n", encoding="utf-8"
        )
        self.conn.close()
        return bundle

    @property
    def sql(self) -> sqlite3.Connection:
        assert self.conn is not None
        return self.conn

    def _register_sources(self) -> None:
        for source in self.registry["sources"]:
            files = [self.path(source["local_metadata"])]
            for crosswalk in source.get("crosswalks", []):
                files.append(self.path(crosswalk["path"]))
            if source.get("hierarchy"):
                files.append(self.path(source["hierarchy"]["path"]))
            for adapter in source.get("adapters", []):
                files.append(self.path(adapter["path"]))
                for lookup_name in ("location_lookup", "entity_lookup"):
                    if adapter.get(lookup_name):
                        files.append(self.path(adapter[lookup_name]["path"]))
            self.sql.execute(
                "INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
                (
                    source["source_id"], source["title"], source.get("doi"), source.get("url"),
                    source.get("publisher"), source.get("license"),
                    json.dumps(sorted(source.get("capabilities", []))),
                    _sha256_files(files),
                ),
            )

    def _ensure_entity(
        self, canonical: str, label: str | None, source_id: str, hierarchy: dict | None = None
    ) -> str | None:
        canonical = str(canonical or "").strip()
        if not canonical or canonical.lower() in {"na", "unknown"}:
            return None
        canonical_key = _key(canonical)
        entity_id = self.aliases.get(canonical_key) or _stable("ent", canonical_key)
        display = str(label or canonical).replace("_", " ").strip()
        existing = self.sql.execute(
            "SELECT hierarchy_json FROM entities WHERE entity_id=?", (entity_id,)
        ).fetchone()
        old_hierarchy = json.loads(existing[0]) if existing else {}
        merged = {**old_hierarchy, **(hierarchy or {})}
        self.sql.execute(
            """INSERT INTO entities(entity_id,canonical_name,display_name,hierarchy_json)
               VALUES(?,?,?,?)
               ON CONFLICT(entity_id) DO UPDATE SET
                 hierarchy_json=excluded.hierarchy_json""",
            (entity_id, canonical, display, json.dumps(merged, sort_keys=True)),
        )
        self._alias(canonical, entity_id, source_id)
        if label:
            self._alias(label, entity_id, source_id)
        return entity_id

    def _alias(self, alias: str, entity_id: str, source_id: str) -> None:
        alias_key = _key(alias)
        if not alias_key:
            return
        previous = self.aliases.get(alias_key)
        if previous and previous != entity_id:
            return
        self.aliases[alias_key] = entity_id
        self.sql.execute(
            """INSERT OR IGNORE INTO entity_aliases(alias_key,alias,entity_id,source_id)
               VALUES(?,?,?,?)""",
            (alias_key, str(alias).strip(), entity_id, source_id),
        )

    def _load_crosswalks(self) -> None:
        for source in self.registry["sources"]:
            source_id = source["source_id"]
            for spec in source.get("crosswalks", []):
                for row in _rows(self.path(spec["path"])):
                    canonical = row.get(spec["canonical"]) or ""
                    label = row.get(spec.get("label", "")) or canonical
                    entity_id = self._ensure_entity(canonical, label, source_id)
                    if entity_id:
                        self._alias(row.get(spec["alias"]) or "", entity_id, source_id)

    def _load_hierarchies(self) -> None:
        for source in self.registry["sources"]:
            spec = source.get("hierarchy")
            if not spec:
                continue
            source_id = source["source_id"]
            for row in _rows(self.path(spec["path"])):
                hierarchy = {
                    name: row.get(name) for name in spec.get("levels", [])
                    if row.get(name) not in (None, "", "NA")
                }
                canonical = row.get(spec["canonical"]) or row.get(spec["key"]) or ""
                label = row.get(spec.get("label", "")) or canonical
                entity_id = self._ensure_entity(canonical, label, source_id, hierarchy)
                if entity_id:
                    self._alias(row.get(spec["key"]) or "", entity_id, source_id)

    def _load_named_points(self) -> None:
        for point in self.site.get("named_points", []):
            self.sql.execute(
                "INSERT OR REPLACE INTO locations VALUES (?,?,?,?,?,?,?)",
                (
                    point["location_id"], point.get("source_id", "site-profile"), point["label"],
                    point.get("latitude"), point.get("longitude"), point.get("uncertainty_m"),
                    json.dumps({"role": "named_point"}, sort_keys=True),
                ),
            )

    def _lookup(
        self, spec: dict[str, Any] | None
    ) -> dict[str, dict[str, Any]]:
        if not spec:
            return {}
        groups: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in _rows(self.path(spec["path"])):
            groups[_key(row.get(spec["lookup_key"]))].append(row)
        result: dict[str, dict[str, Any]] = {}
        for key, rows in groups.items():
            if spec.get("aggregate") == "mean":
                lats = [_coord(row.get(spec["latitude"]), latitude=True) for row in rows]
                lons = [_coord(row.get(spec["longitude"]), latitude=False) for row in rows]
                lats = [value for value in lats if value is not None]
                lons = [value for value in lons if value is not None]
                result[key] = {
                    "latitude": statistics.fmean(lats) if lats else None,
                    "longitude": statistics.fmean(lons) if lons else None,
                    "uncertainty_m": None,
                }
            else:
                row = rows[0]
                result[key] = {
                    "latitude": _coord(row.get(spec.get("latitude", "")), latitude=True),
                    "longitude": _coord(row.get(spec.get("longitude", "")), latitude=False),
                    "uncertainty_m": _float(row.get(spec.get("uncertainty_m", ""))),
                    "canonical": row.get(spec.get("canonical", "")),
                    "label": row.get(spec.get("label", "")),
                }
        return result

    def _ingest_location(self, source: dict, spec: dict) -> None:
        for row_number, row in enumerate(_rows(self.path(spec["path"])), 1):
            lat = _coord(row.get(spec["latitude"]), latitude=True)
            lon = _coord(row.get(spec["longitude"]), latitude=False)
            location_id = str(row.get(spec["location_id"]) or row_number)
            self.sql.execute(
                "INSERT OR REPLACE INTO locations VALUES (?,?,?,?,?,?,?)",
                (
                    location_id, source["source_id"], row.get(spec["label"]) or location_id,
                    lat, lon, _float(row.get(spec.get("uncertainty_m", ""))),
                    _properties(row, spec.get("properties")),
                ),
            )
            self.stats["locations"] += 1

    def _ingest_event(self, source: dict, spec: dict) -> None:
        location_lookup = self._lookup(spec.get("location_lookup"))
        entity_lookup = self._lookup(spec.get("entity_lookup"))
        source_id = source["source_id"]
        for row_number, row in enumerate(_rows(self.path(spec["path"])), 1):
            location = location_lookup.get(
                _key(row.get((spec.get("location_lookup") or {}).get("event_key", ""))), {}
            )
            lat = _coord(row.get(spec.get("latitude", "")), latitude=True)
            lon = _coord(row.get(spec.get("longitude", "")), latitude=False)
            lat = lat if lat is not None else location.get("latitude")
            lon = lon if lon is not None else location.get("longitude")
            uncertainty = _float(row.get(spec.get("uncertainty_m", "")))
            if uncertainty is None:
                uncertainty = location.get("uncertainty_m")
            entity_raw = row.get(spec.get("entity", "")) or ""
            entity_match = entity_lookup.get(
                _key(row.get((spec.get("entity_lookup") or {}).get("event_key", ""))), {}
            )
            canonical = entity_match.get("canonical") or entity_raw
            label = entity_match.get("label") or row.get(spec.get("entity_alias", "")) or canonical
            entity_id = self.aliases.get(_key(canonical)) or self.aliases.get(_key(entity_raw))
            if not entity_id:
                entity_id = self._ensure_entity(canonical, label, source_id)
            elif label:
                self._alias(label, entity_id, source_id)
            date_value = row.get(spec.get("date", "")) or spec.get("date_value")
            event_date, year, month = _date_parts(date_value)
            original_id = _row_id(row, spec.get("record_id"), row_number)
            # Upstream "unique" keys are not always unique. Retain the immutable source-row
            # locator so duplicate natural keys never silently replace evidence.
            event_id = _stable("evt", source_id, original_id, row_number)
            event_type = str(row.get(spec.get("event_type", "")) or spec.get("event_type_value") or "event")
            status = str(row.get(spec.get("status", "")) or "present").lower()
            self.sql.execute(
                "INSERT OR REPLACE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    event_id, source_id, row_number, entity_id, event_type,
                    spec.get("evidence_class", "observed"), status,
                    event_date, year, month, lat, lon, uncertainty,
                    _float(row.get(spec.get("count", ""))), _cell(lat, lon),
                    _properties(row, spec.get("properties")),
                ),
            )
            self.stats["events"] += 1
            if lat is not None and lon is not None:
                self.stats["georeferenced_events"] += 1

    def _ingest_effort(self, source: dict, spec: dict) -> None:
        location_lookup = self._lookup(spec.get("location_lookup"))
        for row_number, row in enumerate(_rows(self.path(spec["path"])), 1):
            location = location_lookup.get(
                _key(row.get((spec.get("location_lookup") or {}).get("event_key", ""))), {}
            )
            lat, lon = location.get("latitude"), location.get("longitude")
            event_date, year, month = _date_parts(row.get(spec.get("date", "")))
            original_id = _row_id(row, spec.get("record_id"), row_number)
            self.sql.execute(
                "INSERT OR REPLACE INTO effort VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    _stable("eff", source["source_id"], original_id), source["source_id"], row_number,
                    spec.get("method_value", "survey"), event_date, year, month, lat, lon,
                    _float(row.get(spec.get("effort_value", ""))), spec.get("effort_unit"),
                    _cell(lat, lon), _properties(row, spec.get("properties")),
                ),
            )
            self.stats["effort_rows"] += 1

    def _ingest_measurement(self, source: dict, spec: dict) -> None:
        for row_number, row in enumerate(_rows(self.path(spec["path"])), 1):
            if spec.get("date_parts"):
                year = int(row.get(spec["date_parts"][0]) or 0) or None
                month = int(row.get(spec["date_parts"][1]) or 1) if year else None
                event_date = f"{year:04d}-{month:02d}" if year and month else None
            else:
                event_date, year, month = _date_parts(row.get(spec.get("date", "")))
            lat = _coord(spec.get("latitude_value"), latitude=True)
            lon = _coord(spec.get("longitude_value"), latitude=False)
            original_id = _row_id(row, spec.get("record_id"), row_number)
            for metric, unit in spec.get("metrics", {}).items():
                self.sql.execute(
                    "INSERT OR REPLACE INTO measurements VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        _stable("mea", source["source_id"], original_id, metric),
                        source["source_id"], row_number, spec.get("location_id_value"),
                        metric, _float(row.get(metric)), unit, event_date, year, month,
                        lat, lon, _cell(lat, lon), "{}",
                    ),
                )
                self.stats["measurements"] += 1

    def _inside_target(self, lat: float, lon: float) -> bool:
        polygon = self.site["target_aoi"]["geometry"]["coordinates"][0]
        west = min(point[0] for point in polygon)
        east = max(point[0] for point in polygon)
        south = min(point[1] for point in polygon)
        north = max(point[1] for point in polygon)
        return west <= lon <= east and south <= lat <= north

    def _materialize(self) -> None:
        cell_ids = {
            row[0] for row in self.sql.execute(
                "SELECT cell_id FROM events WHERE cell_id IS NOT NULL UNION "
                "SELECT cell_id FROM effort WHERE cell_id IS NOT NULL UNION "
                "SELECT cell_id FROM measurements WHERE cell_id IS NOT NULL"
            )
        }
        for cell_id in sorted(cell_ids):
            _, south_text, west_text = cell_id.split(":")
            south, west = float(south_text), float(west_text)
            resolution = 0.01
            center_lat, center_lon = south + resolution / 2, west + resolution / 2
            self.sql.execute(
                "INSERT INTO cells VALUES (?,?,?,?,?,?,?,?)",
                (
                    cell_id, west, south, west + resolution, south + resolution,
                    center_lat, center_lon,
                    "target" if self._inside_target(center_lat, center_lon) else "context_or_donor",
                ),
            )
        self.sql.execute(
            """INSERT INTO event_cell
               SELECT cell_id,entity_id,source_id,COUNT(*),MIN(event_date),MAX(event_date)
               FROM events WHERE cell_id IS NOT NULL
               GROUP BY cell_id,entity_id,source_id"""
        )
        self.sql.execute(
            """INSERT INTO event_time
               SELECT year,month,entity_id,source_id,COUNT(*)
               FROM events WHERE year IS NOT NULL AND month IS NOT NULL
               GROUP BY year,month,entity_id,source_id"""
        )
        self.sql.execute(
            """INSERT INTO measurement_time
               SELECT year,month,metric,source_id,AVG(value),MIN(unit)
               FROM measurements WHERE year IS NOT NULL AND month IS NOT NULL AND value IS NOT NULL
               GROUP BY year,month,metric,source_id"""
        )
        views = [
            ("site_overview_map", "map", "AOI, named places and event-density cells", "ready", None),
            ("named_location_map", "map", "Named place with nearby events and measurements", "ready", None),
            ("observed_points_map", "map", "Entity-filtered observed points", "ready", None),
            ("entity_richness_map", "map", "Distinct entities by spatial cell", "ready", None),
            ("coverage_and_effort_map", "map", "Observed records and survey effort", "ready", None),
            ("seasonal_effort_normalised_chart", "chart", "Events with explicit effort denominator", "ready", None),
            ("metric_time_series", "chart", "Unit-aware measurement time series", "ready", None),
            ("hierarchy_sunburst", "hierarchy", "Entity hierarchy", "ready", None),
            (
                "donor_coverage_and_gate_map", "map", "Donor coverage, target and gate result",
                "partial", "Feature cube and versioned gate result are not yet onboarded",
            ),
            (
                "value_of_information_map", "map", "Expected information gain by cell",
                "blocked", "Requires a versioned model run, uncertainty surface and action-cost layer",
            ),
        ]
        self.sql.executemany(
            "INSERT INTO visual_views VALUES (?,?,?,?,?,?)",
            [(view_id, kind, title, view_id, status, reason) for view_id, kind, title, status, reason in views],
        )

    def _bundle(self) -> dict[str, Any]:
        context = self.site["context_aoi"]["bbox"]
        west, south, east, north = context
        cells = [
            {
                "cell_id": row[0], "west": row[1], "south": row[2], "east": row[3],
                "north": row[4], "role": row[5], "events": row[6], "entities": row[7],
                "effort": row[8],
            }
            for row in self.sql.execute(
                """SELECT c.cell_id,c.west,c.south,c.east,c.north,c.target_role,
                          COUNT(e.event_id),COUNT(DISTINCT e.entity_id),
                          COALESCE((SELECT SUM(x.effort_value) FROM effort x
                                    WHERE x.cell_id=c.cell_id),0)
                   FROM cells c LEFT JOIN events e ON e.cell_id=c.cell_id
                   WHERE c.center_lon BETWEEN ? AND ? AND c.center_lat BETWEEN ? AND ?
                   GROUP BY c.cell_id ORDER BY COUNT(e.event_id) DESC""",
                (west, east, south, north),
            )
        ]
        entity_counts = [
            {"entity_id": row[0], "name": row[1], "count": row[2]}
            for row in self.sql.execute(
                """SELECT e.entity_id,e.display_name,COUNT(v.event_id)
                   FROM entities e JOIN events v ON v.entity_id=e.entity_id
                   GROUP BY e.entity_id ORDER BY COUNT(v.event_id) DESC LIMIT 15"""
            )
        ]
        annual = [
            {"year": row[0], "events": row[1], "entities": row[2]}
            for row in self.sql.execute(
                """SELECT year,COUNT(*),COUNT(DISTINCT entity_id) FROM events
                   WHERE year IS NOT NULL GROUP BY year ORDER BY year"""
            )
        ]
        rainfall = [
            {"year": row[0], "value": round(row[1], 2), "unit": row[2]}
            for row in self.sql.execute(
                """SELECT year,SUM(value),MIN(unit) FROM measurement_time
                   WHERE metric='rainfall' GROUP BY year ORDER BY year"""
            )
        ]
        source_coverage = [
            {
                "source_id": row[0], "title": row[1], "capabilities": json.loads(row[2]),
                "events": row[3], "georeferenced": row[4],
                "first_date": row[5], "last_date": row[6],
            }
            for row in self.sql.execute(
                """SELECT s.source_id,s.title,s.capabilities_json,COUNT(e.event_id),
                          SUM(CASE WHEN e.cell_id IS NOT NULL THEN 1 ELSE 0 END),
                          MIN(e.event_date),MAX(e.event_date)
                   FROM sources s LEFT JOIN events e ON e.source_id=s.source_id
                   GROUP BY s.source_id ORDER BY COUNT(e.event_id) DESC"""
            )
        ]
        effort_by_season = [
            {"season": row[0], "visits": row[1], "km": round(row[2] or 0, 1)}
            for row in self.sql.execute(
                """SELECT json_extract(properties_json,'$.season'),COUNT(*),SUM(effort_value)
                   FROM effort GROUP BY json_extract(properties_json,'$.season')"""
            )
        ]
        hierarchy = [
            {"name": row[0], "hierarchy": json.loads(row[1]), "events": row[2]}
            for row in self.sql.execute(
                """SELECT e.display_name,e.hierarchy_json,COUNT(v.event_id)
                   FROM entities e JOIN events v ON v.entity_id=e.entity_id
                   WHERE e.hierarchy_json <> '{}'
                   GROUP BY e.entity_id ORDER BY COUNT(v.event_id) DESC LIMIT 100"""
            )
        ]
        views = [
            {
                "view_id": row[0], "visual_type": row[1], "title": row[2],
                "availability": row[3], "reason": row[4],
            }
            for row in self.sql.execute(
                "SELECT view_id,visual_type,title,availability,reason FROM visual_views ORDER BY view_id"
            )
        ]
        return {
            "schema_version": "visual-bundle/0.1",
            "site": self.site,
            "site_overview": {"cells": cells, "named_points": self.site.get("named_points", [])},
            "entity_counts": entity_counts,
            "annual_events": annual,
            "annual_rainfall": rainfall,
            "effort_by_season": effort_by_season,
            "source_coverage": source_coverage,
            "hierarchy_sample": hierarchy,
            "views": views,
            "build": {
                "site_id": self.site["site_id"],
                "sources": self.sql.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
                "events": self.sql.execute("SELECT COUNT(*) FROM events").fetchone()[0],
                "georeferenced_events": self.sql.execute(
                    "SELECT COUNT(*) FROM events WHERE cell_id IS NOT NULL"
                ).fetchone()[0],
                "entities": self.sql.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
                "aliases": self.sql.execute("SELECT COUNT(*) FROM entity_aliases").fetchone()[0],
                "locations": self.sql.execute("SELECT COUNT(*) FROM locations").fetchone()[0],
                "effort_rows": self.sql.execute("SELECT COUNT(*) FROM effort").fetchone()[0],
                "measurements": self.sql.execute("SELECT COUNT(*) FROM measurements").fetchone()[0],
                "cells": self.sql.execute("SELECT COUNT(*) FROM cells").fetchone()[0],
                "ready_views": self.sql.execute(
                    "SELECT COUNT(*) FROM visual_views WHERE availability='ready'"
                ).fetchone()[0],
            },
        }

    def _render_preview(self, bundle: dict[str, Any]) -> None:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return
        width, height = 1500, 980
        image = Image.new("RGB", (width, height), "#f5f1e8")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()
        bold = font
        ink, muted, coral, teal, gold, blue = (
            "#1f2933", "#69757d", "#e56b5d", "#287f7a", "#e2a93b", "#4b71b5"
        )
        draw.text((42, 28), "Valparai visual-index feasibility preview", fill=ink, font=bold)
        summary = bundle["build"]
        draw.text(
            (42, 55),
            f"{summary['events']:,} events  •  {summary['entities']:,} resolved entities  •  "
            f"{summary['effort_rows']:,} effort rows  •  {summary['measurements']:,} measurements",
            fill=muted, font=font,
        )
        # AOI and density map.
        map_box = (42, 95, 860, 585)
        draw.rounded_rectangle(map_box, 18, fill="#fffdf8", outline="#d9d3c6", width=2)
        draw.text((65, 115), "Where records and effort are concentrated", fill=ink, font=bold)
        west, south, east, north = self.site["context_aoi"]["bbox"]
        px0, py0, px1, py1 = 70, 150, 835, 555

        def xy(lon: float, lat: float) -> tuple[float, float]:
            return (
                px0 + (lon - west) / (east - west) * (px1 - px0),
                py1 - (lat - south) / (north - south) * (py1 - py0),
            )

        max_count = max([cell["events"] for cell in bundle["site_overview"]["cells"]] or [1])
        for cell in bundle["site_overview"]["cells"]:
            x0, y1 = xy(cell["west"], cell["south"])
            x1, y0 = xy(cell["east"], cell["north"])
            alpha = min(1, math.log1p(cell["events"]) / math.log1p(max_count))
            colour = (
                int(252 - 45 * alpha), int(239 - 114 * alpha), int(222 - 125 * alpha)
            )
            draw.rectangle((x0, y0, x1, y1), fill=colour, outline="#f3ddd4")
            if cell["effort"]:
                draw.ellipse((x0 + 2, y0 + 2, x0 + 7, y0 + 7), fill=teal)
        target = self.site["target_aoi"]["geometry"]["coordinates"][0]
        draw.line([xy(lon, lat) for lon, lat in target], fill=ink, width=3)
        for point in self.site.get("named_points", []):
            x, y = xy(point["longitude"], point["latitude"])
            draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=blue, outline="white")
            draw.text((x + 8, y - 6), point["label"], fill=ink, font=font)
        draw.text((70, 564), "coral = event density    teal dot = explicit effort    outline = target AOI", fill=muted)

        # Top entities.
        box = (885, 95, 1458, 585)
        draw.rounded_rectangle(box, 18, fill="#fffdf8", outline="#d9d3c6", width=2)
        draw.text((910, 115), "Most represented resolved entities", fill=ink, font=bold)
        entities = bundle["entity_counts"][:10]
        maximum = max([item["count"] for item in entities] or [1])
        for index, item in enumerate(entities):
            y = 155 + index * 39
            label = item["name"][:27]
            draw.text((910, y), label, fill=ink, font=font)
            length = 230 * item["count"] / maximum
            draw.rounded_rectangle((1115, y - 2, 1115 + length, y + 14), 6, fill=coral)
            draw.text((1355, y), f"{item['count']:,}", fill=muted, font=font)

        # Annual records.
        chart = (42, 615, 710, 935)
        draw.rounded_rectangle(chart, 18, fill="#fffdf8", outline="#d9d3c6", width=2)
        draw.text((65, 637), "Records by year (coverage, not population trend)", fill=ink, font=bold)
        annual = bundle["annual_events"]
        years = [item["year"] for item in annual]
        values = [item["events"] for item in annual]
        if years:
            max_value = max(values)
            for index, item in enumerate(annual):
                x = 80 + index * (590 / max(1, len(annual)))
                bar_height = 220 * item["events"] / max_value
                draw.rectangle((x, 885 - bar_height, x + 28, 885), fill=blue)
                draw.text((x, 891), str(item["year"])[-2:], fill=muted, font=font)

        # Rainfall.
        chart = (735, 615, 1090, 935)
        draw.rounded_rectangle(chart, 18, fill="#fffdf8", outline="#d9d3c6", width=2)
        draw.text((758, 637), "Annual rainfall", fill=ink, font=bold)
        rain = [item for item in bundle["annual_rainfall"] if item["year"] < 2026]
        if rain:
            maximum = max(item["value"] for item in rain)
            points = []
            for index, item in enumerate(rain):
                x = 765 + index * (285 / max(1, len(rain) - 1))
                y = 890 - 205 * item["value"] / maximum
                points.append((x, y))
            draw.line(points, fill=teal, width=4)
            for x, y in points:
                draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=teal)
            draw.text((765, 895), str(rain[0]["year"]), fill=muted)
            draw.text((1015, 895), str(rain[-1]["year"]), fill=muted)

        # View readiness.
        chart = (1115, 615, 1458, 935)
        draw.rounded_rectangle(chart, 18, fill="#fffdf8", outline="#d9d3c6", width=2)
        draw.text((1138, 637), "Visual question readiness", fill=ink, font=bold)
        for index, view in enumerate(bundle["views"]):
            y = 674 + index * 24
            colour = {"ready": teal, "partial": gold, "blocked": coral}[view["availability"]]
            draw.ellipse((1138, y, 1148, y + 10), fill=colour)
            draw.text((1158, y - 2), view["view_id"][:34], fill=ink, font=font)
        image.save(self.output / "preview.png")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = Builder(args.site_pack, args.output).run()
    print(json.dumps(result["build"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
