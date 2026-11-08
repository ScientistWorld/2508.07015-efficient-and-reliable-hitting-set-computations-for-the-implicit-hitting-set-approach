"""Rank every hardening case against the reference row of scoring/scores_test.json.

rank delta = sum over scored metrics of coefficient * (case value - reference value),
with coefficients from scoring/reference.json and the reference value taken from
the reference method's `sis_sls` row (or the same-named row for baselines).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(__file__).resolve().parent / (sys.argv[1] if len(sys.argv) > 1 else "results")
EXP = "certified_ihs_under_budget"


def main() -> None:
    ref_cfg = json.loads((ROOT / "scoring" / "reference.json").read_text())["experiments"][EXP]
    coefs = {k: v["coefficient"] for k, v in ref_cfg["metrics"].items() if v["coefficient"]}
    weight = ref_cfg["weight"]
    anchor_path = RESULTS / "reference_seed0_test.json"
    anchor = json.loads(anchor_path.read_text())["experiments"][EXP]["results"]

    def delta(row: dict, ref_row: dict) -> float:
        return weight * sum(c * (row[m] - ref_row[m]) for m, c in coefs.items())

    out = {"coefficients": coefs, "weight": weight, "anchor": str(anchor_path.relative_to(ROOT)), "cases": {}}
    for path in sorted(RESULTS.glob("*_test.json")):
        case = path.name[: -len("_test.json")]
        rows = json.loads(path.read_text())["experiments"][EXP]["results"]
        entry = {}
        for name, row in rows.items():
            ref_row = anchor.get(name, anchor["sis_sls"])
            entry[name] = {
                "metrics": row,
                "delta_vs_reference_sis_sls": delta(row, anchor["sis_sls"]),
                "delta_vs_same_named_reference_row": delta(row, ref_row),
            }
        out["cases"][case] = entry
    train = {}
    for path in sorted(RESULTS.glob("*_train.json")):
        case = path.name[: -len("_train.json")]
        train[case] = json.loads(path.read_text())["experiments"][EXP]["results"]
    out["train_cases"] = train
    (RESULTS / "summary.json").write_text(json.dumps(out, indent=2) + "\n")
    for case, entry in out["cases"].items():
        for name, e in entry.items():
            m = e["metrics"]
            print(f"{case:32s} {name:22s} solve={m['certified_solve_rate']:.4f} "
                  f"call_ratio={m['mean_call_ratio']:.4f} hs_share={m['hs_call_share']:.3f} "
                  f"delta={e['delta_vs_reference_sis_sls']:+.4f}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
