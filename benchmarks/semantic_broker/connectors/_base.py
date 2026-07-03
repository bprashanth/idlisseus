"""Shared helpers for connectors: EE init, point CSV IO with column autodetect.

The point-IO helpers are also the "hardcode the data-finding bit": they guess the
lat/lon (and id) columns so the agent doesn't have to (Q1 wasted turns on this)."""
import csv
import importlib.util
import os
import sys

# Self-heal interpreter: the Hermes terminal tool may run the connector with a
# python whose site-packages lack earthengine-api even though the venv has it
# (the venv's python3 is a symlink to the system binary, so comparing paths is
# unreliable — use an env guard to avoid a re-exec loop). If `ee` isn't
# importable, re-exec with the known-good venv interpreter so the agent can just
# run `python connector.py ...`.
_VENV_PY = "/opt/hermes/.venv/bin/python3"
if (importlib.util.find_spec("ee") is None and os.path.exists(_VENV_PY)
        and not os.environ.get("_CONN_REEXEC")):
    os.execve(_VENV_PY, [_VENV_PY] + sys.argv, {**os.environ, "_CONN_REEXEC": "1"})

_LAT_KEYS = ("lat", "latitude", "decimallatitude", "y", "ycoord", "y_coord")
_LON_KEYS = ("lon", "lng", "long", "longitude", "decimallongitude", "x", "xcoord", "x_coord")
_ID_KEYS = ("id", "site", "name", "plot", "location", "fragment")


def init_ee(project="plantwars"):
    import ee
    ee.Initialize(project=project)
    return ee


def _pick(row_lower, keys):
    for k in keys:
        if k in row_lower and str(row_lower[k]).strip() not in ("", "NA", "NaN"):
            return row_lower[k]
    return None


def read_points(path):
    """Read a CSV into [{'id','lat','lon'}], autodetecting the coordinate columns."""
    pts = []
    with open(path, newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            low = {k.strip().lower(): v for k, v in row.items() if k}
            lat, lon = _pick(low, _LAT_KEYS), _pick(low, _LON_KEYS)
            if lat is None or lon is None:
                continue
            try:
                pts.append({"id": _pick(low, _ID_KEYS) or i,
                            "lat": float(lat), "lon": float(lon)})
            except ValueError:
                continue
    if not pts:
        raise SystemExit("no lat/lon columns found — checked "
                         f"{_LAT_KEYS} / {_LON_KEYS}")
    return pts


def write_points(pts, path=None):
    """Write [{...}] rows as CSV to path or stdout.

    If `path` is not writable (e.g. a read-only mount), fall back to stdout with a
    note on stderr instead of crashing — a write error must never be mistaken for
    a data/auth error by the caller."""
    if not pts:
        return
    cols = list(pts[0].keys())
    out, close = sys.stdout, False
    if path:
        try:
            out, close = open(path, "w", newline=""), True
        except OSError as e:
            print(f"[note] could not write {path} ({e.strerror}); "
                  f"printing to stdout instead", file=sys.stderr)
    w = csv.DictWriter(out, fieldnames=cols)
    w.writeheader()
    w.writerows(pts)
    if close:
        out.close()
