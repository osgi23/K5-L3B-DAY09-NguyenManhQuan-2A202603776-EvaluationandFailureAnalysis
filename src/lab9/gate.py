"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    import math
    problems: list[str] = []

    # 1. Any metric value in pr["metrics"] that is NaN or inf
    for k, v in pr.get("metrics", {}).items():
        if isinstance(v, (int, float)):
            if math.isnan(v) or math.isinf(v):
                problems.append(f"metric {k} has invalid value {v}")

    # 2. Manifest items x seeds vs len(pr["rows"])
    manifest = pr.get("manifest", {})
    expected_row_count = manifest.get("items", 0) * len(manifest.get("seeds", []))
    if expected_row_count > 0 and len(pr.get("rows", [])) != expected_row_count:
        problems.append(f"row count {len(pr.get('rows', []))} != expected {expected_row_count}")

    # 3. The (item_id, seed) set of PR differs from the baseline's
    pr_item_seeds = {(r.get("item_id"), r.get("seed")) for r in pr.get("rows", [])}
    base_item_seeds = {(r.get("item_id"), r.get("seed")) for r in base.get("rows", [])}
    if pr_item_seeds != base_item_seeds:
        problems.append("PR (item_id, seed) set differs from baseline")

    # 4. evaluator_failures non-empty, or row whose value for a graded spec metric is None
    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures non-empty: {len(pr['evaluator_failures'])} failure(s)")

    spec_metric_ids = {m["id"] for m in spec.get("metrics", []) if m.get("id")}
    for r in pr.get("rows", []):
        for mid in spec_metric_ids:
            if mid in r and r[mid] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} has None for metric {mid}")
                break

    # 5. Item's slice tags in PR rows differ from baseline's
    pr_slices = {f"{r.get('item_id')}@{r.get('seed')}": tuple(sorted(r.get("slices") or [])) for r in pr.get("rows", [])}
    base_slices = {f"{r.get('item_id')}@{r.get('seed')}": tuple(sorted(r.get("slices") or [])) for r in base.get("rows", [])}
    if pr_slices != base_slices and base_slices:
        problems.append("PR slice tags differ from baseline")

    # 6. Ratchet with base_spec
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        curr_metrics = {m["id"]: m for m in spec.get("metrics", [])}

        for mid, bm in base_metrics.items():
            if mid not in curr_metrics:
                problems.append(f"metric {mid} was removed from spec")
                continue
            cm = curr_metrics[mid]
            if bm.get("blocking") and not cm.get("blocking"):
                problems.append(f"blocking metric {mid} became non-blocking")
            bth = bm.get("threshold", {})
            cth = cm.get("threshold", {})
            if "min" in bth:
                if "min" not in cth or cth["min"] < bth["min"]:
                    problems.append(f"metric {mid} min threshold loosened: {cth.get('min')} < {bth['min']}")
            if "max" in bth:
                if "max" not in cth or cth["max"] > bth["max"]:
                    problems.append(f"metric {mid} max threshold loosened: {cth.get('max')} > {bth['max']}")
            if bth.get("no_significant_drop") and not cth.get("no_significant_drop"):
                problems.append(f"metric {mid} dropped no_significant_drop")

        base_slices_dict = {s["name"]: s for s in base_spec.get("slices", [])}
        curr_slices_dict = {s["name"]: s for s in spec.get("slices", [])}
        for sname, bs_item in base_slices_dict.items():
            if sname not in curr_slices_dict:
                problems.append(f"slice {sname} was removed from spec")
                continue
            cs_item = curr_slices_dict[sname]
            if bs_item.get("blocking") and not cs_item.get("blocking"):
                problems.append(f"blocking slice {sname} became non-blocking")
            if "min" in bs_item:
                if "min" not in cs_item or cs_item["min"] < bs_item["min"]:
                    problems.append(f"slice {sname} min threshold loosened")
            if bs_item.get("no_significant_drop") and not cs_item.get("no_significant_drop"):
                problems.append(f"slice {sname} dropped no_significant_drop")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked: list[str] = []
    lines: list[str] = []
    bs = spec.get("bootstrap", {})
    for s in spec.get("slices", []):
        name = s["name"]
        metric = s["metric"]
        min_val = s.get("min")
        no_drop = s.get("no_significant_drop")
        blocking = s.get("blocking", True)

        a_items = per_item(pr, metric, slice_name=name)
        if not a_items:
            continue
        val = round(sum(a_items.values()) / len(a_items), 4)
        verdict, note = "ok", ""

        if min_val is not None and val < min_val:
            verdict = "fail"

        if no_drop:
            b_items = per_item(base, metric, slice_name=name)
            keys = sorted(set(a_items) & set(b_items))
            if keys:
                d, lo, hi = stats.paired_bootstrap(
                    [a_items[k] for k in keys],
                    [b_items[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000),
                    rng=bs.get("rng", 2027),
                )
                note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                if hi < 0:
                    verdict = "fail"

        tag = f"slice:{name}/{metric}"
        if verdict != "ok" and blocking:
            blocked.append(tag)
        label = {"ok": "ok"}.get(verdict, "BLOCK" if blocking else "warn")
        lines.append(f"  {tag:<22} {val!s:<8} {json.dumps(s):<40} {note:<28} {label}")

    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
