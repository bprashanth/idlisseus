#!/usr/bin/env python3
"""Validate checked-in Idli result and activity fixtures.

Beyond schema validation, this also confirms that every data_ref handle in
every result fixture has a matching payload file under
fixtures/data/<result_id>/<handle>.<geojson|json>, that the file's sha256
digest matches the data_ref.digest recorded in the envelope, and that no
orphan payload files are left behind under fixtures/data/.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parent
DATA_ROOT = ROOT / "fixtures" / "data"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_digest(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _payload_path(result_id: str, handle: str, media_type: str) -> pathlib.Path:
    suffix = ".geojson" if media_type == "application/geo+json" else ".json"
    return DATA_ROOT / result_id / f"{handle}{suffix}"


def _iter_data_refs(instance: dict) -> list[dict]:
    refs = []
    for visual in instance.get("visuals", []):
        for layer in visual.get("layers", []):
            refs.append(layer["data_ref"])
            uncertainty = layer.get("uncertainty")
            if uncertainty:
                for key in ("lower_ref", "upper_ref"):
                    ref = uncertainty.get(key)
                    if ref:
                        refs.append(ref)
            denominator_ref = layer.get("denominator_ref")
            if denominator_ref:
                refs.append(denominator_ref)
        for drilldown in visual.get("drilldowns", []):
            refs.append(drilldown["data_ref"])
    return refs


def _modelled_layers_without_uncertainty(instance: dict) -> list[str]:
    """Layer ids with evidence_class "modelled" that carry no uncertainty
    block. Per VISUAL_BACKEND_DECISION.md roadmap item 1: "Modelled layers
    should not validate without one" -- enforced here as a warning, not a
    schema failure, since the field is additive/optional in idli-result/1."""
    missing = []
    for visual in instance.get("visuals", []):
        for layer in visual.get("layers", []):
            if layer.get("evidence_class") == "modelled" and not layer.get("uncertainty"):
                missing.append(f"{visual.get('visual_id')}/{layer.get('layer_id')}")
    return missing


def _check_payloads(instance: dict, seen: set[pathlib.Path]) -> list[str]:
    errors = []
    result_id = instance.get("result_id")
    for ref in _iter_data_refs(instance):
        if ref.get("kind") != "result_data" or not ref.get("handle"):
            continue
        handle = ref["handle"]
        media_type = ref.get("media_type", "")
        digest = ref.get("digest")
        path = _payload_path(result_id, handle, media_type)
        if not path.is_file():
            errors.append(f"missing payload file for handle {handle!r}: {path}")
            continue
        seen.add(path.resolve())
        actual = _file_digest(path)
        if digest != actual:
            errors.append(
                f"digest mismatch for handle {handle!r}: envelope={digest} file={actual}"
            )
    return errors


def main() -> int:
    result_schema = load(ROOT / "idli-result.schema.json")
    activity_schema = load(ROOT / "idli-activity.schema.json")
    jsonschema.Draft202012Validator.check_schema(result_schema)
    jsonschema.Draft202012Validator.check_schema(activity_schema)
    paths = sorted((ROOT / "fixtures").glob("*.json"))
    if not paths:
        print("No fixtures found", file=sys.stderr)
        return 1
    errors = 0
    warnings = 0
    seen_payload_files: set[pathlib.Path] = set()
    for path in paths:
        instance = load(path)
        is_activity = instance.get("schema_version") == "idli-activity/1"
        schema = activity_schema if is_activity else result_schema
        try:
            jsonschema.Draft202012Validator(schema).validate(instance)
            print(f"ok {path.name}")
        except jsonschema.ValidationError as exc:
            errors += 1
            location = "/".join(str(item) for item in exc.absolute_path)
            print(f"FAIL {path.name}:{location}: {exc.message}", file=sys.stderr)
            continue
        if not is_activity:
            payload_errors = _check_payloads(instance, seen_payload_files)
            for message in payload_errors:
                errors += 1
                print(f"FAIL {path.name}: {message}", file=sys.stderr)
            if not payload_errors:
                handle_count = sum(
                    1 for ref in _iter_data_refs(instance)
                    if ref.get("kind") == "result_data" and ref.get("handle")
                )
                print(f"ok {path.name}: {handle_count} data_ref payload(s) verified")
            missing_uncertainty = _modelled_layers_without_uncertainty(instance)
            if missing_uncertainty:
                warnings += 1
                print(
                    f"WARN {path.name}: modelled layer(s) without an uncertainty block: "
                    + ", ".join(missing_uncertainty),
                    file=sys.stderr,
                )

    if DATA_ROOT.is_dir():
        all_payload_files = {p.resolve() for p in DATA_ROOT.rglob("*") if p.is_file()}
        orphans = sorted(all_payload_files - seen_payload_files)
        for orphan in orphans:
            errors += 1
            print(f"FAIL orphan payload file: {orphan}", file=sys.stderr)

    if warnings:
        print(f"{warnings} warning(s)", file=sys.stderr)

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
