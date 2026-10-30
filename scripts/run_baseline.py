"""Replay the upstream simulator; never compute results with a substitute policy."""
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
REVISION = "40fb623af3793fbe5736bda9a35488d0f366ef6e"
TRACE = Path("vendor/libCacheSim/data/cloudPhysicsIO.txt")
TRACE_SHA256 = "1b48334535801ae862d53e9d7623467186eeb93054462b38021fef273cab0439"
ALGORITHMS = {"fifo": "FIFO", "lru": "LRU", "sieve": "Sieve", "s3fifo": "S3FIFO-0.1000-2"}
SIZES = (1000, 5000, 10000)


def output(*cmd):
    return subprocess.check_output(cmd, text=True).strip()


def main():
    revision = output("git", "-C", "vendor/libCacheSim", "rev-parse", "HEAD")
    if revision != REVISION:
        raise RuntimeError(f"Expected upstream revision {REVISION}, got {revision}")
    if output("git", "-C", "vendor/libCacheSim", "status", "--porcelain"):
        raise RuntimeError("Upstream checkout has changes; baseline requires unmodified source")
    trace_bytes = TRACE.read_bytes()
    if hashlib.sha256(trace_bytes).hexdigest() != TRACE_SHA256:
        raise RuntimeError("Trace checksum mismatch")
    requests = len(trace_bytes.splitlines())
    Path("results/logs").mkdir(parents=True, exist_ok=True)
    rows, commands = [], []
    for algorithm, cache_name in ALGORITHMS.items():
        for size in SIZES:
            stem = f"results/logs/{algorithm}_{size}"
            # cachesim appends, so reset only this run's summary file.
            summary_path = Path(stem + ".txt")
            summary_path.write_text("")
            command = [
                "build/bin/cachesim", str(TRACE), "txt", algorithm, str(size),
                "--ignore-obj-size", "1", "--num-thread", "1",
                "--warmup-sec", "-1", "--consider-obj-metadata", "0",
                "--print-head-req", "0", "--output", str(summary_path),
            ]
            commands.append(shlex.join(command))
            with open(stem + ".log", "w") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            summary = summary_path.read_text()
            pattern = (re.escape(str(TRACE)) + r" " + re.escape(cache_name)
                       + r" cache size\s+(\d+),\s+(\d+) req, miss ratio (\d+\.\d{4}), throughput [\d.]+ MQPS\n")
            match = re.fullmatch(pattern, summary)
            if not match:
                raise RuntimeError(f"Unexpected simulator output: {summary!r}")
            actual_size, actual_requests, ratio = match.groups()
            if int(actual_size) != size or int(actual_requests) != requests or not 0 <= float(ratio) <= 1:
                raise RuntimeError(f"Invalid simulator result: {summary!r}")
            rows.append(dict(trace=TRACE.name, algorithm=algorithm,
                             cache_size_objects=size, requests=requests,
                             miss_ratio=ratio, raw_output=str(summary_path)))
            print(f"{algorithm:6s} {size:5d} objects: miss ratio {ratio}")
    with open("results/baseline.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    Path("results/commands.txt").write_text("\n".join(commands) + "\n")
    metadata = dict(
        measured_at_utc=datetime.now(timezone.utc).isoformat(),
        upstream_url="https://github.com/1a1a11a/libCacheSim.git",
        upstream_commit=revision, trace=str(TRACE), trace_sha256=TRACE_SHA256,
        trace_bytes=len(trace_bytes), requests=requests,
        unique_objects=len(set(trace_bytes.splitlines())),
        cache_sizes_objects=SIZES, miss_ratio_decimal_places=4,
        cold_start=True, warmup=False, object_size=1, consider_object_metadata=False,
        eviction_parameters="upstream defaults; no --eviction-params passed",
        s3fifo_defaults="small-size-ratio=0.10,ghost-size-ratio=0.90,move-to-main-threshold=2",
        simulator_sha256=hashlib.sha256(Path("build/bin/cachesim").read_bytes()).hexdigest(),
        platform=platform.platform(), python=platform.python_version(),
        gcc=output("gcc", "--version").splitlines()[0],
        cmake=output("cmake", "--version").splitlines()[0],
        glib=output("pkg-config", "--modversion", "glib-2.0"),
        zstd=output("pkg-config", "--modversion", "libzstd"),
        build_command="bash scripts/build.sh",
        commands=commands,
    )
    Path("results/metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
