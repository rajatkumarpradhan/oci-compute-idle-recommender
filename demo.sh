#!/bin/sh
# Recommends on the mixed fleet (one stop candidate -> exit 2), then the busy fleet (exit 0).
set -u
export PYTHONPATH="$(dirname "$0")/src"

echo "=== Analyzing samples/idle-fleet.json ==="
python3 -m oci_compute_idle_recommender samples/idle-fleet.json
echo "exit code: $? (2 = stop candidate found, expected for the mixed fleet)"
echo
echo "=== Analyzing samples/busy-fleet.json ==="
python3 -m oci_compute_idle_recommender samples/busy-fleet.json
echo "exit code: $? (0 = no stop candidates, expected for the busy fleet)"
