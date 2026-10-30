# Tuning S3-FIFO Cache Eviction

An Operating Systems project using [libCacheSim](https://github.com/1a1a11a/libCacheSim)
to study cache eviction and investigate workload-aware S3-FIFO parameter tuning.

## Work completed

- Built the existing libCacheSim simulator without modifying its eviction policies.
- Compared FIFO, LRU, SIEVE, and default S3-FIFO at **1,000, 5,000, and 10,000 objects**.
- Used two public samples bundled with libCacheSim: **CloudPhysics** (113,872 requests)
  and **Twitter cluster52** (1,000,000 requests).
- Analyzed unique objects, one-time objects, and reuse frequency distributions.
- Saved measured miss ratios, raw logs, CSV files, and comparison plots.
- Repeated the experiments and obtained identical CSV results.

S3-FIFO parameter tuning and automatic workload-aware selection are the next steps.
They have not been implemented yet.

## Reproduce

Run these commands from the project root. The setup was tested on Ubuntu 26.04.

### 1. Install dependencies

```bash
sudo apt-get update
sudo apt-get install -y build-essential pkg-config cmake libglib2.0-dev libzstd-dev python3-matplotlib
```

For the project-local dependency setup used in this workspace, Ubuntu 26.04 amd64
users can run `bash scripts/install_local_deps.sh` instead. It requires the compiler,
Make, pkg-config, Python, and matplotlib to be available already.

### 2. Get libCacheSim and build

Skip the clone and checkout commands if the pinned source is already present.

```bash
git clone https://github.com/1a1a11a/libCacheSim.git vendor/libCacheSim
git -C vendor/libCacheSim checkout --detach 40fb623af3793fbe5736bda9a35488d0f366ef6e
bash scripts/build.sh
```

Both sample traces are included in `vendor/libCacheSim/data/`.

### 3. Run the experiments and generate plots

```bash
source scripts/env.sh

# CloudPhysics baseline
python3 scripts/run_baseline.py
python3 scripts/plot_baseline.py

# Twitter baseline and analysis of both traces
python3 scripts/run_task2.py
python3 scripts/plot_task2.py
```

All capacities use **objects, not bytes**. Runs start with empty caches, treat each
object as size one, and use the default algorithm parameters. The scripts check
trace checksums and the pinned source revision before running.

## Results

- [CloudPhysics measurements](results/baseline.csv) and [plot](results/baseline.png).
- [Twitter measurements](results/task2/twitter_baseline.csv).
- [Both-trace comparison](results/task2/comparison.png).
- [Workload statistics](results/task2/trace_statistics.csv) and [reuse distribution](results/task2/reuse_frequency.png).

Exact commands, configuration metadata, and raw output are saved under `results/`
and `results/task2/`. See [TASK2.md](TASK2.md) for trace sources and detailed analysis.
