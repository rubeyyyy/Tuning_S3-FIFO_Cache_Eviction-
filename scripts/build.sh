#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/env.sh
mkdir -p results/logs
cmake -S vendor/libCacheSim -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_STANDARD=17 '-DCMAKE_CXX_FLAGS=-include cstdint' -DENABLE_TESTS=OFF 2>&1 | tee results/logs/configure.log
cmake --build build --target cachesim -j 2 2>&1 | tee results/logs/build.log
build/bin/cachesim --help > results/logs/cachesim-help.txt
