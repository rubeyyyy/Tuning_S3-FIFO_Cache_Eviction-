"""Plot only the measured CSV results, using a headless matplotlib backend."""
import csv
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/s3fifo-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

root = Path(__file__).resolve().parents[1]
with (root / "results/baseline.csv").open() as file:
    rows = list(csv.DictReader(file))
fig, ax = plt.subplots(figsize=(7, 4.5))
for algorithm, label in [("fifo", "FIFO"), ("lru", "LRU"), ("sieve", "SIEVE"), ("s3fifo", "S3-FIFO (default)")]:
    points = sorted((int(r["cache_size_objects"]), float(r["miss_ratio"]))
                    for r in rows if r["algorithm"] == algorithm)
    if len(points) != 3:
        raise ValueError(f"Expected three measured points for {algorithm}")
    ax.plot(*zip(*points), marker="o", label=label)
ax.set(xlabel="Cache capacity (objects)", ylabel="Request miss ratio",
       title="libCacheSim baseline — CloudPhysics sample (113,872 requests)",
       xticks=[1000, 5000, 10000], ylim=(0, 1))
ax.yaxis.set_major_formatter(PercentFormatter(1))
ax.grid(alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(root / "results/baseline.png", dpi=160)
plt.close(fig)
print("Saved results/baseline.png")
