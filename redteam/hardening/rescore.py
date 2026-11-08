"""Rescore saved per-instance details under the final evaluator budgets.

Every solver used in the hardening controls ignores the budget fields of the
instance message, so a session with a lower call cap behaves exactly like the
saved session up to that cap: an instance certified at c <= CALL_CAP calls is
unchanged, any other instance is uncertified at the cap.  Scores are computed
with the hidden-test harness's own `summarize`.  The coefficient-0 diagnostics
of instances that ran past the new cap are split proportionally (approximate).

Usage: python3 redteam/hardening/rescore.py SRC_DIR DST_DIR
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from eval.test import harness as H  # noqa: E402


def cap_row(row: dict) -> dict:
    row = dict(row)
    if row["certified"] and row["calls"] <= H.CALL_CAP:
        return row
    if row["calls"] > H.CALL_CAP:
        frac = H.CALL_CAP / row["calls"]
        row["decide_calls"] = round(row["decide_calls"] * frac)
        row["hs_calls"] = H.CALL_CAP - row["decide_calls"]
        row["calls"] = H.CALL_CAP
    row["certified"] = False
    return row


def main() -> None:
    src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    dst.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.glob("*_details.json")):
        case = path.name[: -len("_details.json")]
        details = json.loads(path.read_text())
        old = json.loads((src / f"{case}_test.json").read_text())
        rows = {v: [cap_row(r) for r in rs] for v, rs in details.items()}
        scores = {
            "slice": "test",
            "solve_budget": H.SOLVE_BUDGET,
            "call_cap": H.CALL_CAP,
            "n_instances": old["n_instances"],
            "seed_offset": old["seed_offset"],
            "rescored_from": str((src / f"{case}_test.json").relative_to(ROOT)),
            "experiments": {H.EXPERIMENT: {"results": {v: H.summarize(rs) for v, rs in rows.items()}}},
        }
        (dst / f"{case}_test.json").write_text(json.dumps(scores, indent=2) + "\n")
        (dst / f"{case}_details.json").write_text(json.dumps(rows, indent=1) + "\n")
        print("rescored", case)


if __name__ == "__main__":
    main()
