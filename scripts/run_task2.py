"""Run the additional public sample and analyze both traces; keep Task 1 intact."""
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shlex
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone

from run_baseline import ALGORITHMS, REVISION, SIZES

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
OUT = Path("results/task2")
TRACE_DIR = Path("vendor/libCacheSim/data")
TRACES = {
    "cloudPhysicsIO.txt": "1b48334535801ae862d53e9d7623467186eeb93054462b38021fef273cab0439",
    "twitter_cluster52.csv": "cf4d37d041569bb30c3bc32b7b54dd40b40438c53ee72e4919acf810063d189a",
}
CSV_PARAMS = "time-col=1,obj-id-col=2,obj-size-col=3,obj-id-is-num=true,has-header=true"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def analyze(name):
    path = TRACE_DIR / name
    counts, last_seen, gaps = Counter(), {}, []
    with path.open() as file:
        if path.suffix == ".csv":
            reader = csv.reader(file)
            if next(reader) != ["# time", " object", " size", " next_access_vtime"]:
                raise ValueError("Unexpected Twitter CSV header")
            ids = (int(row[1]) for row in reader)
        else:
            ids = (int(line) for line in file)
        for position, object_id in enumerate(ids):
            # Python ints preserve all uint64 IDs, without float rounding.
            counts[object_id] += 1
            if object_id in last_seen:
                gaps.append(position - last_seen[object_id])
            last_seen[object_id] = position
    frequency = Counter(counts.values())
    requests, unique = sum(counts.values()), len(counts)
    assert sum(frequency.values()) == unique
    assert sum(k * n for k, n in frequency.items()) == requests
    assert len(gaps) == requests - unique
    exact = [dict(trace=name, requests_per_object=k, reuses_per_object=k - 1,
                  objects=n, object_fraction=n / unique,
                  requests=k * n, request_fraction=k * n / requests)
             for k, n in sorted(frequency.items())]
    bucket_rows = []
    for label, low, high in [("1", 1, 1), ("2", 2, 2), ("3-4", 3, 4),
                             ("5-9", 5, 9), ("10-99", 10, 99),
                             ("100-999", 100, 999), ("1000+", 1000, math.inf)]:
        objects = sum(n for k, n in frequency.items() if low <= k <= high)
        reqs = sum(k * n for k, n in frequency.items() if low <= k <= high)
        bucket_rows.append(dict(trace=name, requests_per_object_bucket=label,
                                objects=objects, object_fraction=objects / unique,
                                requests=reqs, request_fraction=reqs / requests))
    top_count = math.ceil(unique * 0.01)
    summary = dict(
        trace=name, total_requests=requests, unique_objects=unique,
        one_time_objects=frequency[1], one_time_object_fraction=frequency[1] / unique,
        one_time_request_fraction=frequency[1] / requests,
        mean_requests_per_object=requests / unique,
        median_requests_per_object=statistics.median(counts.values()),
        max_requests_per_object=max(counts.values()),
        repeat_requests=requests - unique, compulsory_miss_ratio=unique / requests,
        top_one_percent_object_count=top_count,
        top_one_percent_request_fraction=sum(n for _, n in counts.most_common(top_count)) / requests,
        median_interaccess_gap_requests=statistics.median(gaps),
    )
    return summary, exact, bucket_rows


def main():
    revision = subprocess.check_output(
        ["git", "-C", "vendor/libCacheSim", "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise RuntimeError("Unexpected libCacheSim revision")
    if subprocess.check_output(["git", "-C", "vendor/libCacheSim", "status", "--porcelain"]):
        raise RuntimeError("Baseline requires a clean upstream checkout")
    for name, expected_hash in TRACES.items():
        if sha256(TRACE_DIR / name) != expected_hash:
            raise RuntimeError(f"Trace checksum mismatch: {name}")
    (OUT / "logs").mkdir(parents=True, exist_ok=True)
    summaries, exact_rows, buckets = [], [], []
    for name in TRACES:
        summary, exact, bucket_rows = analyze(name)
        summaries.append(summary)
        exact_rows.extend(exact)
        buckets.extend(bucket_rows)
        print(json.dumps(summary), flush=True)
    write_csv(OUT / "trace_statistics.csv", summaries)
    write_csv(OUT / "reuse_frequency.csv", exact_rows)
    write_csv(OUT / "frequency_buckets.csv", buckets)

    name = "twitter_cluster52.csv"
    trace_path = TRACE_DIR / name
    expected_requests = summaries[1]["total_requests"]
    rows, commands = [], []
    for algorithm, cache_name in ALGORITHMS.items():
        for size in SIZES:
            stem = OUT / "logs" / f"{algorithm}_{size}"
            summary_path = stem.with_suffix(".txt")
            summary_path.write_text("")  # cachesim appends summaries.
            command = ["build/bin/cachesim", str(trace_path), "csv", algorithm, str(size),
                       "-t", CSV_PARAMS, "--ignore-obj-size", "1", "--num-thread", "1",
                       "--warmup-sec", "-1", "--consider-obj-metadata", "0",
                       "--print-head-req", "0", "--output", str(summary_path)]
            commands.append(shlex.join(command))
            with stem.with_suffix(".log").open("w") as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
            raw = summary_path.read_text()
            pattern = (re.escape(str(trace_path)) + " " + re.escape(cache_name)
                       + r" cache size\s+(\d+),\s+(\d+) req, miss ratio (\d+\.\d{4}), throughput [\d.]+ MQPS\n")
            match = re.fullmatch(pattern, raw)
            if match is None:
                raise RuntimeError(f"Unexpected simulator summary: {raw!r}")
            actual_size, requests, ratio = match.groups()
            if int(actual_size) != size or int(requests) != expected_requests or not 0 <= float(ratio) <= 1:
                raise RuntimeError(f"Invalid simulator measurement: {raw!r}")
            rows.append(dict(trace=name, algorithm=algorithm, cache_size_objects=size,
                             requests=int(requests), miss_ratio=ratio, raw_output=str(summary_path)))
            print(f"{algorithm:6s} {size:5d} objects: {ratio}", flush=True)
    write_csv(OUT / "twitter_baseline.csv", rows)

    # Reuse Task 1's actual measurements, after checking provenance and raw logs.
    original_metadata = json.loads(Path("results/metadata.json").read_text())
    if original_metadata["upstream_commit"] != revision or original_metadata["trace_sha256"] != TRACES["cloudPhysicsIO.txt"]:
        raise RuntimeError("Task 1 provenance does not match")
    with Path("results/baseline.csv").open() as file:
        original = list(csv.DictReader(file))
    expected_pairs = {(a, s) for a in ALGORITHMS for s in SIZES}
    if len(original) != 12 or {(r["algorithm"], int(r["cache_size_objects"])) for r in original} != expected_pairs:
        raise RuntimeError("Task 1 is missing expected measurements")
    for row in original:
        if row["trace"] != "cloudPhysicsIO.txt" or int(row["requests"]) != summaries[0]["total_requests"]:
            raise RuntimeError("Task 1 request count or trace mismatch")
        raw = Path(row["raw_output"]).read_text()
        if f"miss ratio {row['miss_ratio']}," not in raw:
            raise RuntimeError("Task 1 CSV differs from raw output")
    write_csv(OUT / "comparison.csv", original + rows)
    (OUT / "commands.txt").write_text("\n".join(commands) + "\n")
    metadata = dict(
        measured_at_utc=datetime.now(timezone.utc).isoformat(), upstream_commit=revision,
        simulator_sha256=sha256(Path("build/bin/cachesim")),
        trace_sources={name: dict(
            source_url=f"https://raw.githubusercontent.com/1a1a11a/libCacheSim/{revision}/data/{name}",
            local_path=str(TRACE_DIR / name), sha256=digest,
            bytes=(TRACE_DIR / name).stat().st_size) for name, digest in TRACES.items()},
        acquisition="Both files obtained unmodified in the official pinned Git clone; no separate download required",
        twitter_trace_format="CSV: time, numeric uint64 object ID, size, next_access_vtime; header present",
        csv_params=CSV_PARAMS, capacity_unit="objects", cache_sizes_objects=SIZES,
        ignore_object_size=True, warmup=False, metadata_charge=False, threads=1,
        eviction_parameters="upstream defaults; no eviction parameters passed",
        miss_ratio_decimal_places=4, python=platform.python_version(),
        original_baseline_csv_sha256=sha256(Path("results/baseline.csv")),
        original_metadata_sha256=sha256(Path("results/metadata.json")), commands=commands,
        analysis_definitions=dict(
            one_time_object="Object with exactly one request within the supplied sample",
            reuse_frequency="For an object with k total requests, reuses = k-1; exact histogram contains both",
            interaccess_gap="Request-index difference between consecutive accesses to the same ID; not distinct-object stack distance",
            top_one_percent="Most frequently requested ceil(0.01 * unique_objects) IDs, divided by all requests"),
    )
    (OUT / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
