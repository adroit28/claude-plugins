#!/usr/bin/env python3
"""Scaffold for submitting a brief to Higgsfield. Not wired yet.

Usage: generate.py <brief.md> [--dry-run]

Higgsfield exposes generation through a hosted MCP server (OAuth) and a CLI
with long-lived tokens, not an API key. This script assembles the payload
the skill would hand to either. HIGGSFIELD_API_KEY (a CLI token, if one is
ever used) is read from ~/.config/higgsfield-video/.env and never printed.
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from shotcheck import parse  # noqa: E402

ENV_FILE = Path.home() / ".config" / "higgsfield-video" / ".env"


def load_key():
    key = os.environ.get("HIGGSFIELD_API_KEY")
    if key:
        return key
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("HIGGSFIELD_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def build_payload(brief, start_frame=None, resolution="720p", ratio="9:16"):
    shots = parse(brief)
    return {
        "model": "kling-3.0",
        "mode": "multishot-custom",
        "aspect_ratio": ratio,
        "resolution": resolution,
        "audio": True,
        "start_frame": start_frame,
        "shots": [
            {"index": s["n"], "duration": s["secs"], "elements": s["elems"], "prompt": s["text"]}
            for s in shots
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("--start-frame")
    ap.add_argument("--resolution", default="720p", choices=["720p", "1080p", "4K"])
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    payload = build_payload(a.brief, a.start_frame, a.resolution, a.ratio)
    if a.dry_run:
        print(json.dumps(payload, indent=2))
        return

    key = load_key()
    if not key:
        print(f"no HIGGSFIELD_API_KEY in env or {ENV_FILE}; run with --dry-run", file=sys.stderr)
        sys.exit(2)
    print("API submission is not implemented yet. Key found; payload assembled.", file=sys.stderr)
    print("Run with --dry-run to see the payload, or paste shots into the Higgsfield UI.", file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
