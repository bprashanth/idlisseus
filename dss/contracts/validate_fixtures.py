#!/usr/bin/env python3
"""Validate checked-in Idli result and activity fixtures."""

from __future__ import annotations

import json
import pathlib
import sys

import jsonschema


ROOT = pathlib.Path(__file__).resolve().parent


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    for path in paths:
        instance = load(path)
        schema = (
            activity_schema
            if instance.get("schema_version") == "idli-activity/1"
            else result_schema
        )
        try:
            jsonschema.Draft202012Validator(schema).validate(instance)
            print(f"ok {path.name}")
        except jsonschema.ValidationError as exc:
            errors += 1
            location = "/".join(str(item) for item in exc.absolute_path)
            print(f"FAIL {path.name}:{location}: {exc.message}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
