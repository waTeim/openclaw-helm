#!/usr/bin/env python3
"""Update OpenClaw image tag to the latest GitHub release.

Defaults:
- Updates chart/values.yaml image.tag
- Prints latest tag

Optional:
- --build-config to update build-config.json if present
- --values PATH to update a different values file
- --dry-run to print changes only
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

API_URL = "https://api.github.com/repos/openclaw/openclaw/releases/latest"


def fetch_latest_tag() -> str:
    req = urllib.request.Request(
        API_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "openclaw-kube"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    tag = data.get("tag_name")
    if not tag:
        raise RuntimeError("No tag_name in GitHub release response")
    return tag


def update_values_yaml(path: Path, tag: str, dry_run: bool) -> bool:
    if not path.exists():
        raise FileNotFoundError(f"values file not found: {path}")
    text = path.read_text()
    lines = text.splitlines()
    changed = False
    out = []
    in_image = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("image:"):
            in_image = True
            out.append(line)
            continue
        if in_image:
            if stripped and not line.startswith(" ") and not line.startswith("\t"):
                in_image = False
        if in_image and stripped.startswith("tag:"):
            prefix = line.split("tag:", 1)[0]
            new_line = f"{prefix}tag: \"{tag}\""
            out.append(new_line)
            changed = True
            continue
        out.append(line)
    if not changed:
        raise RuntimeError("Did not find image.tag to update in values file")
    new_text = "\n".join(out) + ("\n" if text.endswith("\n") else "")
    if dry_run:
        sys.stdout.write(new_text)
    else:
        path.write_text(new_text)
    return changed


def update_build_config(path: Path, tag: str, dry_run: bool) -> bool:
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    if data.get("source_tag") == tag:
        return False
    data["source_tag"] = tag
    if dry_run:
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        path.write_text(json.dumps(data, indent=2) + "\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--values", default="chart/values.yaml", help="Path to values.yaml")
    parser.add_argument("--build-config", action="store_true", help="Also update build-config.json")
    parser.add_argument("--dry-run", action="store_true", help="Print changes only")
    args = parser.parse_args()

    tag = fetch_latest_tag()
    print(f"Latest tag: {tag}")

    values_path = Path(args.values)
    update_values_yaml(values_path, tag, args.dry_run)
    print(f"Updated: {values_path}")

    if args.build_config:
        updated = update_build_config(Path("build-config.json"), tag, args.dry_run)
        if updated:
            print("Updated: build-config.json")
        else:
            print("Skipped: build-config.json (missing or already up to date)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
