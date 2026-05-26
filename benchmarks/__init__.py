"""agentcore benchmark suite.

Run the full suite:

    python -m benchmarks.run

Run a single benchmark:

    python -m benchmarks.micro
    python -m benchmarks.e2e
    python -m benchmarks.compare_langgraph   # needs `pip install '.[bench]'`

Results print to stdout in a stable format intended for diffing
across commits. Re-run on a quiet machine for reliable numbers.
"""
