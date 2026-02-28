#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="OpenClaw gateway wrapper")
    parser.add_argument("--bind", required=True)
    parser.add_argument("--port", required=True)
    parser.add_argument("--allow-unconfigured", action="store_true")
    parser.add_argument("extra", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    config_path = Path("/home/node/.openclaw/openclaw.json")
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")

    if token and config_path.exists():
        try:
            data = json.loads(config_path.read_text())
            data.setdefault("gateway", {}).setdefault("auth", {})["token"] = token
            config_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[openclaw-gateway] Warning: failed to update token in config: {e}", file=sys.stderr)

    cmd = ["node", "dist/index.js", "gateway", "--bind", args.bind, "--port", str(args.port)]
    if args.allow_unconfigured:
        cmd.append("--allow-unconfigured")
    if args.extra:
        cmd.extend(args.extra)

    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
