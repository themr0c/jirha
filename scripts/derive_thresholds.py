#!/usr/bin/env python3
"""Re-derive SP tier thresholds from empirical PR data.

Reads both CSVs, aggregates PRs per Jira key, segments by task type
(doc/tooling/mixed), computes percentile boundaries, and outputs
updated threshold constants.

Output is for human review — does NOT auto-patch api.py.

Usage: python scripts/derive_thresholds.py
"""
import csv
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CSV_FILES = [
    REPO_ROOT / "docs" / "superpowers" / "pr_sp_data.csv",
    REPO_ROOT / "docs" / "superpowers" / "pr_sp_data_2025.csv",
]

SP_VALUES = [0, 1, 2, 3, 5, 8, 13]

# Current thresholds (for comparison)
CURRENT_ADOC = [5, 30, 60, 120, 300, 550, 1200]
CURRENT_TOTAL = [20, 100, 250, 600, 1500, 5000, 15000]


def load_data():
    """Load and merge both CSVs. Returns list of dicts."""
    rows = []
    for path in CSV_FILES:
        if not path.exists():
            print(f"Warning: {path} not found, skipping")
            continue
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def aggregate_by_jira(rows):
    """Group PRs by Jira key and aggregate metrics.

    Returns dict: jira_key → {sp, adoc_total, total_lines, pr_type, n_prs}.
    """
    jiras = defaultdict(lambda: {"prs": []})
    for row in rows:
        key = row.get("jira_key", "").strip()
        if not key:
            continue
        sp_raw = row.get("sp", "").strip()
        if not sp_raw:
            continue
        try:
            sp = int(float(sp_raw))
        except ValueError:
            continue
        try:
            adoc_total = int(row.get("adoc_total", 0) or 0)
            total_lines = int(row.get("total_lines", 0) or 0)
            n_adoc_files = int(row.get("adoc_files", 0) or 0)
        except ValueError:
            continue
        jiras[key]["sp"] = sp
        jiras[key]["prs"].append({
            "adoc_total": adoc_total,
            "total_lines": total_lines,
            "n_adoc_files": n_adoc_files,
        })

    # Aggregate per Jira
    result = {}
    for key, data in jiras.items():
        sp = data["sp"]
        if sp not in SP_VALUES:
            continue
        agg_adoc = sum(pr["adoc_total"] for pr in data["prs"])
        agg_total = sum(pr["total_lines"] for pr in data["prs"])
        agg_n_adoc = sum(pr["n_adoc_files"] for pr in data["prs"])

        if agg_n_adoc == 0:
            pr_type = "tooling"
        elif agg_total > 0 and agg_adoc > agg_total * 0.5:
            pr_type = "doc"
        else:
            pr_type = "mixed"

        result[key] = {
            "sp": sp,
            "adoc_total": agg_adoc,
            "total_lines": agg_total,
            "pr_type": pr_type,
            "n_prs": len(data["prs"]),
        }
    return result


def segment(jiras):
    """Split Jiras into doc/tooling/mixed segments."""
    segments = {"doc": [], "tooling": [], "mixed": []}
    for data in jiras.values():
        segments[data["pr_type"]].append(data)
    return segments


def percentile(values, p):
    """Compute p-th percentile (0-100) of a sorted list."""
    if not values:
        return 0
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(values):
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)


def derive_thresholds(segment_data, signal_key):
    """Derive tier thresholds from data for a given signal.

    For each adjacent SP pair, threshold = midpoint between p75 of lower
    and p25 of upper. Rounded to clean numbers.
    """
    by_sp = defaultdict(list)
    for item in segment_data:
        by_sp[item["sp"]].append(item[signal_key])

    thresholds = []
    for i in range(len(SP_VALUES) - 1):
        lower_sp = SP_VALUES[i]
        upper_sp = SP_VALUES[i + 1]
        lower_vals = by_sp.get(lower_sp, [])
        upper_vals = by_sp.get(upper_sp, [])

        if not lower_vals or not upper_vals:
            thresholds.append(None)
            continue

        p75_lower = percentile(lower_vals, 75)
        p25_upper = percentile(upper_vals, 25)
        mid = (p75_lower + p25_upper) / 2

        # Round to clean numbers
        if mid < 50:
            mid = round(mid / 5) * 5
        elif mid < 500:
            mid = round(mid / 10) * 10
        elif mid < 5000:
            mid = round(mid / 50) * 50
        else:
            mid = round(mid / 500) * 500

        thresholds.append(max(int(mid), 1))

    return thresholds


def accuracy(segment_data, signal_key, thresholds):
    """Compute % of Jiras landing within 1 tier of correct."""
    correct = 0
    total = 0
    for item in segment_data:
        total += 1
        val = item[signal_key]
        tier = len(thresholds)
        for i, t in enumerate(thresholds):
            if t is not None and val < t:
                tier = i
                break
        sp = item["sp"]
        sp_idx = SP_VALUES.index(sp) if sp in SP_VALUES else -1
        if sp_idx >= 0 and abs(tier - sp_idx) <= 1:
            correct += 1
    return correct / total * 100 if total else 0


def main():
    rows = load_data()
    if not rows:
        print("No data loaded.")
        return

    jiras = aggregate_by_jira(rows)
    print(f"Loaded {len(rows)} PR rows → {len(jiras)} unique Jiras\n")

    segs = segment(jiras)

    for seg_name in ("doc", "tooling", "mixed"):
        data = segs[seg_name]
        n = len(data)
        print(f"=== {seg_name} segment (N={n} Jiras) ===")
        if n < 5:
            print("  Too few data points, skipping.\n")
            continue
        if n < 30:
            print("  Warning: N<30, treat as directional only")

        # SP distribution
        sp_dist = defaultdict(int)
        for item in data:
            sp_dist[item["sp"]] += 1
        dist_str = ", ".join(f"{sp}:{sp_dist[sp]}" for sp in SP_VALUES if sp_dist[sp])
        print(f"  SP distribution: {dist_str}")

        if seg_name in ("doc", "mixed"):
            new_adoc = derive_thresholds(data, "adoc_total")
            acc_old = accuracy(data, "adoc_total", CURRENT_ADOC)
            acc_new = accuracy(data, "adoc_total", [t if t else c for t, c in zip(new_adoc, CURRENT_ADOC)])
            print(f"  adoc_total thresholds: {CURRENT_ADOC}  (current)")
            print(f"                         {new_adoc}  (re-derived)")
            print(f"  Accuracy: {acc_new:.0f}% within 1 tier (was {acc_old:.0f}%)")

        new_total = derive_thresholds(data, "total_lines")
        acc_old_t = accuracy(data, "total_lines", CURRENT_TOTAL)
        acc_new_t = accuracy(data, "total_lines", [t if t else c for t, c in zip(new_total, CURRENT_TOTAL)])
        print(f"  total_lines thresholds: {CURRENT_TOTAL}  (current)")
        print(f"                          {new_total}  (re-derived)")
        print(f"  Accuracy: {acc_new_t:.0f}% within 1 tier (was {acc_old_t:.0f}%)")
        print()


if __name__ == "__main__":
    main()
