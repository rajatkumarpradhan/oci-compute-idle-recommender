"""Find idle and oversized compute instances from utilization series.

OCI Monitoring exposes per-instance CPU and network utilization; the money
question is which instances can be stopped or downsized. This module reads a
static JSON fleet export (daily metric points per instance) and recommends
stop / downsize / schedule actions with an illustrative cost estimate.
All analysis is offline; no OCI calls.
"""

from dataclasses import dataclass

SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

# Illustrative unit price used ONLY to rank savings between candidates.
# Not a real OCI price; see README.
OCPU_HOURLY_USD = 0.025
HOURS_PER_MONTH = 730

MIN_POINTS = 7
STOP_CPU_PCT = 5.0
STOP_NET_MBPS = 0.5
DOWNSIZE_CPU_PCT = 20.0


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    subject: str
    message: str


def _series_stats(points):
    cpu = [p["cpu_pct"] for p in points]
    net = [p["net_mbps"] for p in points]
    return {
        "n": len(points),
        "avg_cpu": sum(cpu) / len(cpu),
        "max_cpu": max(cpu),
        "avg_net": sum(net) / len(net),
    }


def _monthly_cost(ocpus):
    return round(ocpus * OCPU_HOURLY_USD * HOURS_PER_MONTH, 2)


def analyze_fleet(document):
    instances = document.get("instances")
    if not isinstance(instances, list):
        raise ValueError("document must contain a top-level 'instances' list")
    findings = []
    for inst in instances:
        name = inst.get("name")
        if not name:
            raise ValueError("instance entry missing 'name'")
        if inst.get("lifecycle_state", "RUNNING").upper() != "RUNNING":
            continue
        points = inst.get("metrics") or []
        if len(points) < MIN_POINTS:
            findings.append(Finding("IDLE003", "LOW", name,
                                    f"only {len(points)} metric point(s); at least {MIN_POINTS} days needed for a recommendation"))
            continue
        ocpus = float(inst.get("ocpus", 1))
        stats = _series_stats(points)
        cost = _monthly_cost(ocpus)
        detail = f"avg cpu {stats['avg_cpu']:.1f}%, max {stats['max_cpu']:.1f}%, avg net {stats['avg_net']:.2f} Mbps over {stats['n']} days"
        if stats["avg_cpu"] < STOP_CPU_PCT and stats["avg_net"] < STOP_NET_MBPS:
            findings.append(Finding("IDLE001", "HIGH", name,
                f"stop candidate: {detail}; illustrative monthly cost ${cost:.2f} for {ocpus:g} OCPU(s)"))
            if not (inst.get("tags") or {}).get("schedule"):
                findings.append(Finding("IDLE004", "LOW", name,
                    "no schedule tag; an instance this idle should at least run on a power schedule"))
        elif stats["avg_cpu"] < DOWNSIZE_CPU_PCT:
            suggested = max(1, ocpus // 2)
            findings.append(Finding("IDLE002", "MEDIUM", name,
                f"downsize candidate: {detail}; {ocpus:g} -> {suggested:g} OCPU(s) would save ~${cost - _monthly_cost(suggested):.2f}/month (illustrative)"))
    return sorted(findings, key=lambda f: (SEVERITY_ORDER[f.severity], f.rule_id, f.subject))
