"""Bounded sequential local workflow benchmark; not a sustained queue-capacity claim."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=3, choices=range(1, 11))
    args = parser.parse_args()
    latencies = []
    started = time.perf_counter()
    for _ in range(args.samples):
        result = subprocess.run(
            [sys.executable, str(Path(__file__).with_name("http_workflow.py"))],
            capture_output=True,
            text=True,
            timeout=180,
            check=True,
        )
        record = json.loads(result.stdout.strip().splitlines()[-1])
        assert record["async_job"] == "succeeded"
        latencies.append(record["queue_completion_seconds"])
    elapsed = time.perf_counter() - started
    print(
        json.dumps(
            {
                "successful_jobs": len(latencies),
                "queue_completion_seconds": latencies,
                "whole_workflows_seconds": round(elapsed, 3),
                "observed_jobs_per_minute_including_workflow_overhead": round(
                    len(latencies) * 60 / elapsed, 2
                ),
                "scope": "sequential synthetic local workflows; not saturated queue throughput",
            }
        )
    )


if __name__ == "__main__":
    main()
