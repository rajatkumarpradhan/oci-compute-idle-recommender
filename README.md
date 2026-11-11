# oci-compute-idle-recommender

**Custom portfolio tool (no built-in OCI services wired in).** Offline recommender that reads a synthetic OCI Compute utilization export and answers the money question: which running instances can be stopped, downsized, or at least put on a power schedule.

Problem it solves: fleets accumulate forgotten instances that burn budget at 1% CPU. This tool turns daily CPU/network metric points into a ranked stop/downsize list with an illustrative savings estimate, locally and in CI, without touching a tenancy.

## What it is

- Reads a static JSON fleet export: per-instance OCPU count, lifecycle state, optional tags, and daily metric points (`cpu_pct`, `net_mbps`).
- Four rules (IDLE001-IDLE004) with severity-ranked findings and an exit code suitable for CI gates.
- Runs 100% locally. No OCI SDK, no credentials, no network calls.
- 15 unit tests, all executed locally and in CI on Python 3.10/3.11/3.12.

## What it is NOT (honest limits)

- The cost figures use one **illustrative unit price** ($0.025/OCPU/hour, 730 h/month) purely to rank candidates against each other. It is not OCI pricing; real shapes, burstable pricing and committed-use discounts are not modeled.
- The input schema is a simplified daily-series export, not the OCI Monitoring API response shape; it does not fetch metrics from OCI.
- Recommendations are statistical (averages over the window). A monthly batch spike hidden between daily points is invisible to it; check max values and your workload before stopping anything.
- Stopped instances are skipped entirely; rightsizing stopped instances is out of scope.

## Rules

| Rule | Severity | Finding |
| --- | --- | --- |
| IDLE001 | HIGH | Stop candidate: avg cpu < 5% and avg net < 0.5 Mbps across the window |
| IDLE002 | MEDIUM | Downsize candidate: avg cpu 5-20%; suggests halving OCPUs |
| IDLE003 | LOW | Fewer than 7 metric points; not enough history to recommend |
| IDLE004 | LOW | Stop candidate without a schedule tag; at least put it on a power schedule |

Exit code 2 when any IDLE001 fires; 1 on unreadable or malformed input; 0 otherwise.

## Run

Requires Python 3.10+, no third-party dependencies.

```sh
PYTHONPATH=src python3 -m oci_compute_idle_recommender samples/idle-fleet.json
PYTHONPATH=src python3 -m oci_compute_idle_recommender samples/busy-fleet.json
```

Or the end-to-end demo:

```sh
sh demo.sh
```

Expected demo output: the mixed fleet flags legacy-report-box as a stop candidate (HIGH, ~$73/month illustrative), ci-worker-3 as a downsize candidate 8 -> 4 OCPUs, new-node for insufficient history, plus the missing schedule tag, and exits 2; the busy fleet reports zero findings and exits 0.

## Test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
