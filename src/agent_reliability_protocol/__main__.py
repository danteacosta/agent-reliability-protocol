from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_reliability_protocol.interchange import check_contract


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Agent Reliability Protocol JSON contract.")
    parser.add_argument("check", nargs="?", default="check")
    parser.add_argument("--kind", choices=("decision", "event", "manifest"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args(argv)
    errors = check_contract(args.kind, json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps({"valid": not errors, "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
