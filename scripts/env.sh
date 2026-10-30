#!/usr/bin/env bash
# Source from the project root. Prefer project-local Ubuntu dependencies if present.
if [[ -d "$PWD/.deps/root/usr" ]]; then
  export PATH="$PWD/.deps/root/usr/bin:$PATH"
  export LD_LIBRARY_PATH="$PWD/.deps/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  export PKG_CONFIG_LIBDIR="$PWD/.deps/root/usr/lib/x86_64-linux-gnu/pkgconfig:$PWD/.deps/root/usr/share/pkgconfig"
  export PKG_CONFIG_SYSROOT_DIR="$PWD/.deps/root"
  export CMAKE_PREFIX_PATH="$PWD/.deps/root/usr${CMAKE_PREFIX_PATH:+:$CMAKE_PREFIX_PATH}"
fi
export MPLCONFIGDIR="${TMPDIR:-/tmp}/s3fifo-matplotlib"
export MPLBACKEND=Agg
