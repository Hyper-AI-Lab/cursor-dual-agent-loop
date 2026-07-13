#!/usr/bin/env python3
"""List Cursor model IDs available to this account (for config.yaml).

Usage:
  export CURSOR_API_KEY=cursor_...
  python auto/orchestrator/list_models.py
  python auto/orchestrator/list_models.py --verbose
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List Cursor SDK model IDs for model / developer_model / master_model"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show display names, variants, and parameter IDs when available",
    )
    args = parser.parse_args()

    if not os.environ.get("CURSOR_API_KEY"):
        print(
            "CURSOR_API_KEY is required.\n"
            "  export CURSOR_API_KEY=cursor_...\n"
            "Then re-run this script.",
            file=sys.stderr,
        )
        return 1

    try:
        from cursor_sdk import Cursor
    except ImportError:
        print("cursor-sdk is not installed. pip install cursor-sdk", file=sys.stderr)
        return 1

    try:
        models = Cursor.models.list()
    except Exception as exc:
        print(f"Failed to list models: {exc}", file=sys.stderr)
        return 1

    if not models:
        print("No models returned for this account.")
        return 0

    print(f"# {len(models)} model(s) available for this CURSOR_API_KEY")
    print("# Copy an id exactly into config.yaml (model / developer_model / master_model)\n")

    for m in models:
        mid = getattr(m, "id", None) or str(m)
        if not args.verbose:
            print(mid)
            continue

        disp = (
            getattr(m, "display_name", None)
            or getattr(m, "name", None)
            or getattr(m, "title", None)
        )
        line = mid if not disp else f"{mid}  # {disp}"
        print(line)

        params = getattr(m, "parameters", None) or getattr(m, "params", None) or []
        if params:
            for p in params:
                pid = getattr(p, "id", None) or p
                print(f"    param: {pid}")

        variants = getattr(m, "variants", None) or getattr(m, "presets", None) or []
        if variants:
            for v in variants:
                vid = getattr(v, "id", None) or getattr(v, "name", None) or v
                print(f"    variant: {vid}")

    print(
        "\n# Tip: ids are case-sensitive slugs (e.g. auto, composer-2.5).\n"
        "# Do not use UI display names with spaces."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
