#!/usr/bin/env bash
# Ubuntu 26.04 amd64 fallback when sudo installation is unavailable.
set -euo pipefail
cd "$(dirname "$0")/.."
project_root="$PWD"
mkdir -p .deps/packages .deps/root
mapfile -t packages < scripts/ubuntu-deps.lock
cd .deps/packages
apt-get download "${packages[@]}"
cd "$project_root"
sha256sum -c results/dependency-packages.sha256
for package in .deps/packages/*.deb; do
  dpkg-deb -x "$package" .deps/root
done
