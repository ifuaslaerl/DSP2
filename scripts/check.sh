#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

run_target() {
    local target="$1"
    local build_dir="$2"

    echo "==> Configuring ${target}"
    cmake -S "$ROOT_DIR" -B "$build_dir" -DDSP2_TARGET="$target"

    echo "==> Building ${target}"
    cmake --build "$build_dir"

    echo "==> Testing ${target}"
    ctest --test-dir "$build_dir" --output-on-failure
}

run_target "EMBEDDED" "$ROOT_DIR/build-embedded"
run_target "SIMULATION" "$ROOT_DIR/build-sim"

echo "==> All checks passed"
