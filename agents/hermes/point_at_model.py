#!/usr/bin/env python3
"""Point this box's Hermes Agent install at a given OpenAI-compatible model.

Edits ~/.hermes/config.yaml in place: sets the top-level model.default/provider/base_url,
AND walks every entry in the auxiliary: block (web_extract, compression, vision, etc.) so
nothing is left on provider:auto -- see docs/agents.md for why this matters.

Usage (run with sudo -- ~/.hermes is owned by container uid 10000, not your shell user):
    sudo python3 deploy/hermes/point_at_model.py <model-name> <base-url>

Example:
    sudo python3 deploy/hermes/point_at_model.py deepseek-v4-flash http://172.17.0.1:8000/v1
    sudo python3 deploy/hermes/point_at_model.py nemotron-3-super http://172.17.0.1:8000/v1
    sudo python3 deploy/hermes/point_at_model.py seed-oss-36b http://172.17.0.1:8000/v1
"""
import re
import sys

CONFIG_PATH = "/home/beeps/.hermes/config.yaml"


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    model_name, base_url = sys.argv[1], sys.argv[2]

    with open(CONFIG_PATH) as f:
        lines = f.readlines()

    # Top-level model: block (first 5-6 lines, "model:" then default/provider/base_url).
    for i, line in enumerate(lines):
        if line.rstrip() == "model:":
            lines[i + 1] = f"  default: {model_name}\n"
            lines[i + 2] = "  provider: custom\n"
            lines[i + 3] = f"  base_url: {base_url}\n"
            break

    # auxiliary: block -- pin every sub-task explicitly instead of leaving provider: auto.
    start = next(i for i, l in enumerate(lines) if l.rstrip() == "auxiliary:")
    end = next(i for i, l in enumerate(lines) if l.rstrip() == "display:")
    for i in range(start, end):
        if lines[i].strip() == "provider: auto":
            lines[i] = lines[i].replace("provider: auto", "provider: custom")
        elif re.match(r"^\s*model: .*", lines[i]):
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = f"{indent}model: {model_name}\n"
        elif re.match(r"^\s*base_url: .*", lines[i]):
            indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
            lines[i] = f"{indent}base_url: {base_url}\n"

    with open(CONFIG_PATH, "w") as f:
        f.writelines(lines)
    print(f"Hermes now points at {model_name} @ {base_url} (top-level + all auxiliary tasks)")


if __name__ == "__main__":
    main()
