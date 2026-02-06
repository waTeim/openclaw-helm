#!/usr/bin/env python3
"""
OpenClaw Kube - Makefile Configuration

Generates build-config.json with the source (FROM) and target image
settings consumed directly by the Makefile.

Usage:
    # Interactive mode
    python bin/configure-make.py

    # From environment variables
    python bin/configure-make.py --from-env

    # Specify values directly
    python bin/configure-make.py \
        --source-registry ghcr.io --source-image openclaw/openclaw --source-tag latest \
        --target-registry ghcr.io/myorg --target-image openclaw-playwright
"""

import json
import os
import sys
import argparse
from pathlib import Path
from typing import Optional

CONFIG_FILE = "build-config.json"


def load_saved_config(output_dir: Path) -> dict:
    """Load previously saved configuration for defaults."""
    path = output_dir / CONFIG_FILE
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(config: dict, output_dir: Path) -> Path:
    """Save configuration to JSON for future defaults."""
    path = output_dir / CONFIG_FILE
    path.write_text(json.dumps(config, indent=2) + "\n")
    print(f"  Saved:   {path}")
    return path


def get_env_or_prompt(
    env_var: str,
    prompt: str,
    required: bool = False,
    default: Optional[str] = None,
) -> Optional[str]:
    """Get value from environment variable or prompt user."""
    value = os.environ.get(env_var)
    if value:
        print(f"  {prompt}: {value} (from {env_var})")
        return value

    if sys.stdin.isatty():
        if default:
            user_input = input(f"  {prompt} [{default}]: ").strip()
            return user_input if user_input else default
        else:
            user_input = input(f"  {prompt}: ").strip()
            if required and not user_input:
                print(f"    Error: {prompt} is required")
                sys.exit(1)
            return user_input if user_input else None
    elif required and not default:
        print(f"Error: {env_var} environment variable required in non-interactive mode")
        sys.exit(1)
    return default


def collect_config(args: argparse.Namespace, saved: dict) -> dict:
    """Collect image configuration values."""
    saved_source = saved.get("source", {})
    saved_target = saved.get("target", {})

    config = {"source": {}, "target": {}}

    # --- Source (FROM) image ---
    print("\n=== Source (FROM) Image ===")

    config["source"]["registry"] = args.source_registry or get_env_or_prompt(
        "SOURCE_REGISTRY",
        "Registry (e.g., ghcr.io, docker.io)",
        required=True,
        default=saved_source.get("registry", "ghcr.io"),
    )

    config["source"]["image"] = args.source_image or get_env_or_prompt(
        "SOURCE_IMAGE",
        "Image name (e.g., openclaw/openclaw)",
        required=True,
        default=saved_source.get("image", "openclaw/openclaw"),
    )

    config["source"]["tag"] = args.source_tag or get_env_or_prompt(
        "SOURCE_TAG",
        "Tag",
        default=saved_source.get("tag", "latest"),
    )

    # --- Target image ---
    print("\n=== Target Image ===")

    config["target"]["registry"] = args.target_registry or get_env_or_prompt(
        "TARGET_REGISTRY",
        "Registry (e.g., ghcr.io/myorg, docker.io/myuser)",
        required=True,
        default=saved_target.get("registry"),
    )

    config["target"]["image"] = args.target_image or get_env_or_prompt(
        "TARGET_IMAGE",
        "Image name",
        default=saved_target.get("image", "openclaw-playwright"),
    )

    config["target"]["tag"] = args.target_tag or get_env_or_prompt(
        "TARGET_TAG",
        "Tag",
        default=saved_target.get("tag", "latest"),
    )

    return config


def main():
    parser = argparse.ArgumentParser(
        description="Configure Makefile for OpenClaw Kube image build",
    )

    parser.add_argument("--from-env", action="store_true",
                        help="Read all values from environment variables (non-interactive)")
    parser.add_argument("--output-dir", type=Path, default=Path("."),
                        help="Directory to write build-config.json (default: .)")

    # Source image
    parser.add_argument("--source-registry", help="Source image registry")
    parser.add_argument("--source-image", help="Source image name")
    parser.add_argument("--source-tag", help="Source image tag")

    # Target image
    parser.add_argument("--target-registry", help="Target image registry")
    parser.add_argument("--target-image", help="Target image name")
    parser.add_argument("--target-tag", help="Target image tag")

    args = parser.parse_args()

    print("=== OpenClaw Kube - Makefile Configuration ===")

    saved = load_saved_config(args.output_dir)
    config = collect_config(args, saved)

    print()
    save_config(config, args.output_dir)

    print("\n=== Next Steps ===")
    print("  make build   # Build the image")
    print("  make push    # Build and push to registry")


if __name__ == "__main__":
    main()
