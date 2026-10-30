"""Plot actual per-trace results and object/request weighted frequency bins."""
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3fifo-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

OUT = Path(__file__).resolve().parents[1] / "results/task2"
with (OUT / "comparison.csv").open() as file:
    rows = list(csv.DictReader(file))
traces = [("cloudPhysicsIO.txt", "CloudPhysics (113,872 requests)"),
          ("twitter_cluster52.csv", "Twitter cluster52 (1,000,000 requests)")]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
for ax, (trace, title) in zip(axes, traces):
    for algorithm, label in [("fifo", "FIFO"), ("lru", "LRU"), ("sieve", "SIEVE"), ("s3fifo", "S3-FIFO (default)")]:
        points = sorted((int(r["cache_size_objects"]), float(r["miss_ratio"]))
                        for r in rows if r["trace"] == trace and r["algorithm"] == algorithm)
        if len(points) != 3:
            raise ValueError(f"Missing measured points for {trace}/{algorithm}")
        ax.plot(*zip(*points), marker="o", label=label)
    ax.set(title=title, xlabel="Cache capacity (objects)", xticks=[1000, 5000, 10000], ylim=(0, 1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(alpha=0.3)
axes[0].set_ylabel("Request miss ratio")
axes[1].legend()
fig.tight_layout()
fig.savefig(OUT / "comparison.png", dpi=160)
plt.close(fig)

with (OUT / "frequency_buckets.csv").open() as file:
    buckets = list(csv.DictReader(file))
labels = ["1", "2", "3-4", "5-9", "10-99", "100-999", "1000+"]
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, field, title in zip(axes, ["object_fraction", "request_fraction"],
                           ["Share of distinct objects", "Share of all requests"]):
    for i, (trace, name) in enumerate(traces):
        by_bin = {r["requests_per_object_bucket"]: float(r[field]) for r in buckets if r["trace"] == trace}
        ax.bar([x + (i - 0.5) * 0.38 for x in range(len(labels))],
               [by_bin[label] for label in labels], width=0.38, label=name.split(" (")[0])
    ax.set(title=title, xlabel="Total requests per object (reuses = requests − 1)",
           xticks=range(len(labels)), xticklabels=labels)
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=0.3)
axes[0].legend()
fig.tight_layout()
fig.savefig(OUT / "reuse_frequency.png", dpi=160)
plt.close(fig)
print("Saved results/task2/comparison.png and reuse_frequency.png")
