"""Rule-based possible-leak screening from paired pipeline boundary readings.

This is a screening tool, not a calibrated field leak detector. It only evaluates
rows where the user confirms a stable, full-pipe window and all known taps/storage
changes between the meters are accounted for.
"""
from collections import defaultdict
from math import hypot, isfinite

REQUIRED = {
    "branch_id", "cycle_id", "q_up_l_s", "q_down_l_s",
    "meter_up_sigma_l_s", "meter_down_sigma_l_s",
    "full_pipe_flag", "stable_window_verified",
}


def _bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _number(row, key, default=0.0):
    value = float(row.get(key, default) or default)
    if not isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    return value


def analyze_rows(rows):
    if not rows:
        raise ValueError("Upload at least one measurement row.")
    missing = REQUIRED - set(rows[0])
    if missing:
        raise ValueError("Missing required CSV columns: " + ", ".join(sorted(missing)))

    checked = []
    groups = defaultdict(list)
    for index, row in enumerate(rows, start=2):
        branch = str(row.get("branch_id", "")).strip()
        cycle = str(row.get("cycle_id", "")).strip()
        if not branch or not cycle:
            raise ValueError(f"CSV row {index}: branch_id and cycle_id are required")
        q_up = _number(row, "q_up_l_s")
        q_down = _number(row, "q_down_l_s")
        up_sigma = _number(row, "meter_up_sigma_l_s")
        down_sigma = _number(row, "meter_down_sigma_l_s")
        if min(q_up, q_down, up_sigma, down_sigma) < 0 or up_sigma == 0 or down_sigma == 0:
            raise ValueError(f"CSV row {index}: flows must be non-negative and meter uncertainties must be positive")
        storage = _number(row, "pipe_storage_change_l_s")
        taps = _number(row, "branch_tap_l_s")
        residual = q_up - q_down - storage - taps
        sigma = hypot(up_sigma, down_sigma)
        z_score = residual / sigma
        eligible = _bool(row.get("full_pipe_flag", False)) and _bool(row.get("stable_window_verified", False))
        # Positive unexplained upstream flow is consistent with water leaving the measured segment.
        candidate = eligible and z_score > 1.0
        result = {
            "csv_row": index, "branch_id": branch, "cycle_id": cycle,
            "q_up_l_s": q_up, "q_down_l_s": q_down,
            "accounted_storage_l_s": storage, "accounted_taps_l_s": taps,
            "unexplained_flow_l_s": round(residual, 5),
            "combined_meter_sigma_l_s": round(sigma, 5),
            "z_score": round(z_score, 3), "eligible": eligible,
            "possible_leak_signal": bool(candidate),
            "reason": ("Unexplained positive flow exceeds 3× combined meter uncertainty" if candidate else
                       "Not eligible: stable full-pipe window not verified" if not eligible else
                       "No 3-sigma positive flow imbalance in this window"),
        }
        checked.append(result)
        if eligible:
            groups[branch].append(result)

    branch_summary = []
    for branch, items in sorted(groups.items()):
        flagged = [x for x in items if x["possible_leak_signal"]]
        cycles = len({x["cycle_id"] for x in flagged})
        branch_summary.append({
            "branch_id": branch,
            "eligible_windows": len(items),
            "flagged_windows": len(flagged),
            "distinct_flagged_cycles": cycles,
            "status": ("POSSIBLE LEAK — inspect this segment" if cycles >= 2 else
                       "SINGLE-WINDOW ANOMALY — repeat measurement" if cycles == 1 else
                       "NO LEAK SIGNAL ABOVE SCREENING THRESHOLD"),
            "mean_flagged_unexplained_flow_l_s": round(sum(x["unexplained_flow_l_s"] for x in flagged) / len(flagged), 5) if flagged else None,
        })

    return {
        "overall_status": ("POSSIBLE LEAK SIGNAL FOUND" if any(x["distinct_flagged_cycles"] >= 2 for x in branch_summary) else
                           "ANOMALY NEEDS RECHECK" if any(x["flagged_windows"] for x in branch_summary) else
                           "NO QUALIFYING LEAK SIGNAL FOUND"),
        "rows_analyzed": len(checked),
        "eligible_rows": sum(1 for x in checked if x["eligible"]),
        "screening_rule": "positive flow residual > 3 × combined independent meter standard uncertainty; repeated in at least 2 distinct cycles for branch-level possible-leak status",
        "branches": branch_summary,
        "row_results": checked,
        "limitations": [
            "A positive flow imbalance is a possible leak signal, not proof of leakage.",
            "Unmetered taps, tank filling, bypasses, meter bias, air, changing pipe storage or incorrect boundaries can mimic leakage.",
            "Only use stable, full-pipe windows with all known withdrawals and storage changes accounted for.",
            "A branch identifier localizes only to the supplied segment; this tool does not estimate an exact leak position.",
            "No detection accuracy or win rate can be calculated without independent verified leak/normal labels.",
        ],
    }
