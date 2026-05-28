"""Run all benchmarks and optionally write a JSON summary."""
from __future__ import annotations

import argparse
import platform

from . import e2e, micro
from ._harness import emit_json, print_header, print_row


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--json", help="write summary as JSON to this path")
    args = p.parse_args()

    print_header(f"marrow benchmark suite ({platform.system()} {platform.machine()})")
    results = micro.run_all()
    e2e_result = e2e.run_pipeline(5_000)
    results.append(e2e_result)
    for r in results:
        print_row(r)

    if args.json:
        emit_json(results, args.json)
        print(f"\nwrote summary to {args.json}")


if __name__ == "__main__":
    main()
