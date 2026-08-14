from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent_reliability_protocol.interchange import check_contract, validate_run_directory


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate an Agent Reliability Protocol JSON contract.")
    parser.add_argument("check", nargs="?", default="check")
    parser.add_argument("--kind", choices=("decision", "event", "manifest", "episode", "evidence", "gate-request"))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--run-directory", type=Path)
    args = parser.parse_args(argv)
    if args.check != "check" and not args.run_directory and not args.kind and not args.input:
        args.run_directory = Path(args.check)
    if args.run_directory:
        errors = validate_run_directory(args.run_directory)
    elif args.kind and args.input:
        errors = check_contract(args.kind, json.loads(args.input.read_text(encoding="utf-8")))
    else:
        parser.error("--run-directory or both --kind and --input are required")
    print(json.dumps({"valid": not errors, "errors": errors}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
