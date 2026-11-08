"""Hidden-test harness: certified implicit-hitting-set solving under an oracle-call budget.

The harness owns every instance.  A solver never sees the feasibility
constraints of an instance: it receives only the objective, the constraints
that mention objective variables only, a call budget and a seed.  Everything
else about the instance is reachable only through two counted oracles that the
harness answers over a JSON-lines pipe:

* ``decide``      -- decision oracle over the full instance under assumptions on
                     objective variables.  Returns a feasible assignment or a core
                     (a constraint over objective literals that every feasible
                     assignment satisfies and that the assumptions violate).
* ``hs_improve``  -- exact pseudo-Boolean decision procedure over the hitting-set
                     problem (all seed constraints plus every core this harness has
                     returned so far): find an assignment of cost < bound or prove
                     that none exists.

The harness keeps its own log.  The upper bound is the cheapest feasible
assignment it has returned; the lower bound is the largest bound for which it
proved the hitting-set problem has no cheaper solution.  An instance counts as
solved only when the harness itself has lower bound >= upper bound within
SOLVE_BUDGET oracle calls; sessions continue up to CALL_CAP calls so that the
efficiency metric sees every instance.  Nothing the solver writes is trusted: the scores are computed
from this log alone.

This file is the test-slice copy.  It scores the held-out instances in
``eval/test/instances_test.json`` and shares no code with ``eval/train/``.  It
never writes per-instance costs or bounds outside ``eval/test/``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import select
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SLICE = "test"
INSTANCE_FILE = Path(__file__).resolve().parent / "instances_test.json"
DEFAULT_OUTPUT = ROOT / "scoring" / "scores_test.json"
DETAILS_OUTPUT = ""  # no per-instance file unless requested
EXPERIMENT = "certified_ihs_under_budget"
SOLVER_CMD = ["bash", "scripts/solver.sh"]

SOLVE_BUDGET = 180         # an instance is solved if certified within this many oracle calls
CALL_CAP = 720             # hard cap on decide + hs_improve calls per instance (4 x SOLVE_BUDGET)
SOLVER_TIME_LIMIT_SEC = 300.0  # safety guard on time spent waiting for the solver per instance
                               # (harness oracle time is excluded; the reference needs < 60 s)
LIST_TIMEOUT_SEC = 120.0
HS_NODE_LIMIT = 2_000_000      # deterministic cap on search nodes for one hs_improve call
HS_SESSION_NODE_LIMIT = 20_000_000  # deterministic cap on hs_improve search nodes per instance
MAX_LINE_BYTES = 1 << 20
BASE_SEED = 1009
# per-instance fields written to an explicitly requested details file: no
# instance names, costs or bounds, so test answers never leave eval/test/
DETAIL_FIELDS = ("index", "certified", "calls", "decide_calls", "hs_calls", "end_reason")
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$")


class ProtocolError(Exception):
    pass


class OracleLimit(Exception):
    pass


# --------------------------------------------------------------------------
# Instance oracles
# --------------------------------------------------------------------------


class Instance:
    def __init__(self, payload: dict):
        self.name = str(payload["name"])
        self.n = int(payload["n_objective"])
        self.weights = [int(w) for w in payload["weights"]]
        if len(self.weights) != self.n or any(w <= 0 for w in self.weights):
            raise ValueError(f"bad weights in {self.name}")
        self.demands = [[tuple(int(v) for v in route) for route in demand] for demand in payload["demands"]]
        self.seeds = [(tuple(int(v) for v in s["vars"]), int(s["k"])) for s in payload["seed_constraints"]]
        self.optimum = int(payload["optimum"])
        for demand in self.demands:
            for route in demand:
                if not route or any(v < 0 or v >= self.n for v in route):
                    raise ValueError(f"bad route in {self.name}")

    def cost(self, x: list[int]) -> int:
        return sum(w for w, xi in zip(self.weights, x) if xi)

    def feasible(self, x: list[int]) -> bool:
        for demand in self.demands:
            if not any(all(x[v] for v in route) for route in demand):
                return False
        return all(sum(x[v] for v in vs) >= k for vs, k in self.seeds)

    def decide(self, assumptions: dict[int, int]):
        """Decision oracle over the full instance.

        Every route constraint is monotone in the objective variables, so the
        assumptions are consistent with a feasible assignment iff setting every
        unassumed objective variable to 1 is feasible.  On a conflict the core
        is the clause over the variables assumed 0 that block the first
        unsatisfiable requirement.
        """
        zeros = {v for v, val in assumptions.items() if val == 0}
        for demand in self.demands:
            if all(any(v in zeros for v in route) for route in demand):
                blocked = sorted({v for route in demand for v in route if v in zeros})
                return False, (blocked, 1)
        for vs, k in self.seeds:
            blocked = [v for v in vs if v in zeros]
            available = len(vs) - len(blocked)
            if available < k:
                return False, (sorted(blocked), k - available)
        x = [0] * self.n
        for v, val in assumptions.items():
            x[v] = val
        for demand in self.demands:
            if any(all(x[v] for v in route) for route in demand):
                continue
            best = None
            for route in demand:
                if any(v in zeros for v in route):
                    continue
                add = sum(self.weights[v] for v in route if not x[v])
                if best is None or add < best[0]:
                    best = (add, route)
            for v in best[1]:
                x[v] = 1
        for vs, k in self.seeds:
            have = sum(x[v] for v in vs)
            if have >= k:
                continue
            cand = sorted((self.weights[v], v) for v in vs if not x[v] and v not in assumptions)
            for _, v in cand[: k - have]:
                x[v] = 1
        if not self.feasible(x):  # defensive: the completion above is exact for this family
            raise RuntimeError(f"decision oracle produced an infeasible completion on {self.name}")
        return True, x


def hs_improve(n: int, weights: list[int], cons: list[tuple[tuple[int, ...], int]], bound: int,
               phase: list[int] | None, node_limit: int):
    """Exact search for x with sum_i w_i x_i <= bound - 1 satisfying all covering constraints.

    ``cons`` holds unit-coefficient covering constraints (vars, k): sum_{v in vars} x_v >= k.
    Returns (assignment or None, nodes).  Depth-first branch and bound with
    unit propagation, cost-based fixing and an LP-dual lower bound.
    """
    limit = bound - 1
    if limit < 0:
        return None, 0
    m = len(cons)
    occ: list[list[int]] = [[] for _ in range(n)]
    for ci, (vs, _) in enumerate(cons):
        for v in vs:
            occ[v].append(ci)
    need = [k for _, k in cons]
    freec = [len(vs) for vs, _ in cons]
    x = [-1] * n
    pref = phase if phase is not None else [0] * n
    cost = [0]
    nodes = [0]
    trail: list[int] = []

    def assign(v: int, val: int) -> None:
        x[v] = val
        trail.append(v)
        for ci in occ[v]:
            freec[ci] -= 1
            if val:
                need[ci] -= 1
        if val:
            cost[0] += weights[v]

    def undo(to: int) -> None:
        while len(trail) > to:
            v = trail.pop()
            val = x[v]
            for ci in occ[v]:
                freec[ci] += 1
                if val:
                    need[ci] += 1
            if val:
                cost[0] -= weights[v]
            x[v] = -1

    def propagate() -> bool:
        changed = True
        while changed:
            changed = False
            slack = limit - cost[0]
            if slack < 0:
                return False
            for v in range(n):
                if x[v] == -1 and weights[v] > slack:
                    assign(v, 0)
                    changed = True
            for ci in range(m):
                if need[ci] <= 0:
                    continue
                if freec[ci] < need[ci]:
                    return False
                if freec[ci] == need[ci]:
                    for v in cons[ci][0]:
                        if x[v] == -1:
                            assign(v, 1)
                    changed = True
                    if cost[0] > limit:
                        return False
        return True

    def lower_bound(open_c: list[int]) -> int:
        residual: dict[int, int] = {}
        lb = 0
        for ci in sorted(open_c, key=lambda c: freec[c]):
            free_vars = [v for v in cons[ci][0] if x[v] == -1]
            y = min(residual.get(v, weights[v]) for v in free_vars)
            if y <= 0:
                continue
            lb += need[ci] * y
            for v in free_vars:
                residual[v] = residual.get(v, weights[v]) - y
        return lb

    def dfs():
        nodes[0] += 1
        if nodes[0] > node_limit:
            raise OracleLimit("hs_improve node limit")
        mark = len(trail)
        if not propagate():
            undo(mark)
            return None
        open_c = [ci for ci in range(m) if need[ci] > 0]
        if not open_c:
            sol = [1 if val == 1 else 0 for val in x]
            undo(mark)
            return sol
        if cost[0] + lower_bound(open_c) > limit:
            undo(mark)
            return None
        ci = min(open_c, key=lambda c: (freec[c] - need[c], freec[c], c))
        free_vars = [v for v in cons[ci][0] if x[v] == -1]
        v = min(free_vars, key=lambda u: (-pref[u], weights[u], u))
        for val in (1, 0):
            mark2 = len(trail)
            assign(v, val)
            found = dfs()
            undo(mark2)
            if found is not None:
                undo(mark)
                return found
        undo(mark)
        return None

    sys.setrecursionlimit(max(10000, 4 * n + 1000))
    return dfs(), nodes[0]


# --------------------------------------------------------------------------
# Solver session
# --------------------------------------------------------------------------


def _constraint_payload(vs, k) -> dict:
    return {"terms": [[1, int(v), 1] for v in vs], "rhs": int(k)}


class Session:
    """One solver process working on one instance."""

    def __init__(self, inst: Instance, variant: str, seed: int, budget: int, stderr_handle):
        self.inst = inst
        self.variant = variant
        self.seed = seed
        self.budget = budget
        self.stderr_handle = stderr_handle
        self.cores: list[tuple[tuple[int, ...], int]] = list(inst.seeds)
        self.decide_calls = 0
        self.hs_calls = 0
        self.ub: int | None = None
        self.lb = 0
        self.end_reason = "unknown"
        self.buffer = b""
        self.nodes = 0

    @property
    def calls(self) -> int:
        return self.decide_calls + self.hs_calls

    @property
    def certified(self) -> bool:
        return self.ub is not None and self.lb >= self.ub

    # ---- request handling -------------------------------------------------
    def _status(self) -> dict:
        return {
            "lb": self.lb,
            "ub": self.ub,
            "calls_left": self.budget - self.calls,
            "certified": self.certified,
        }

    def _handle(self, req) -> dict:
        if not isinstance(req, dict):
            raise ProtocolError("request must be a JSON object")
        op = req.get("op")
        if op not in ("decide", "hs_improve"):
            raise ProtocolError(f"unknown op {op!r}")
        if self.calls >= self.budget:
            self.end_reason = "budget_exhausted"
            return {"error": "budget_exhausted", **self._status()}
        n = self.inst.n
        if op == "decide":
            raw = req.get("assumptions", [])
            if not isinstance(raw, list) or len(raw) > n:
                raise ProtocolError("assumptions must be a list of [var, value] pairs")
            assumptions: dict[int, int] = {}
            for item in raw:
                if (not isinstance(item, list) or len(item) != 2
                        or any(isinstance(z, bool) or not isinstance(z, int) for z in item)):
                    raise ProtocolError("each assumption must be [var, value] with integers")
                v, val = item
                if not 0 <= v < n or val not in (0, 1) or v in assumptions:
                    raise ProtocolError("assumption variable out of range, value not 0/1, or repeated")
                assumptions[v] = val
            self.decide_calls += 1
            sat, payload = self.inst.decide(assumptions)
            if sat:
                c = self.inst.cost(payload)
                if self.ub is None or c < self.ub:
                    self.ub = c
                return {"sat": True, "assignment": payload, "cost": c, **self._status()}
            vs, k = payload
            self.cores.append((tuple(vs), k))
            return {"sat": False, "core": _constraint_payload(vs, k), **self._status()}
        bound = req.get("bound")
        if isinstance(bound, bool) or not isinstance(bound, int):
            raise ProtocolError("hs_improve needs an integer bound")
        phase = req.get("phase")
        if phase is not None:
            if (not isinstance(phase, list) or len(phase) != n
                    or any(isinstance(z, bool) or z not in (0, 1) for z in phase)):
                raise ProtocolError("phase must be a list of n values in {0,1}")
        self.hs_calls += 1
        node_limit = min(HS_NODE_LIMIT, HS_SESSION_NODE_LIMIT - self.nodes)
        sol, nodes = hs_improve(n, self.inst.weights, self.cores, bound, phase, node_limit)
        self.nodes += nodes
        if sol is None:
            if bound > self.lb:
                self.lb = bound
            return {"sat": False, **self._status()}
        return {"sat": True, "assignment": sol, "cost": self.inst.cost(sol), **self._status()}

    # ---- process I/O ------------------------------------------------------
    def _readline(self, proc, selector, deadline: float):
        while b"\n" not in self.buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            events = selector.select(timeout=min(remaining, 1.0))
            if not events:
                continue
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                return None
            self.buffer += chunk
            if len(self.buffer) > MAX_LINE_BYTES and b"\n" not in self.buffer:
                raise ProtocolError("request line too long")
        line, self.buffer = self.buffer.split(b"\n", 1)
        return line

    def run(self) -> dict:
        start = time.monotonic()
        # The guard counts only time spent waiting on the solver: the deadline is
        # pushed back by however long the harness itself spends answering.
        deadline = start + SOLVER_TIME_LIMIT_SEC
        proc = subprocess.Popen(
            SOLVER_CMD + ["run", self.variant],
            cwd=str(ROOT),
            bufsize=0,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self.stderr_handle,
            start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        hello = {
            "type": "instance",
            "n_objective": self.inst.n,
            "weights": self.inst.weights,
            "seed_constraints": [_constraint_payload(vs, k) for vs, k in self.inst.seeds],
            "budget": self.budget,
            "solve_budget": SOLVE_BUDGET,
            "seed": self.seed,
        }
        try:
            self._send(proc, hello, deadline)
            while True:
                if self.certified:
                    self.end_reason = "certified"
                    break
                line = self._readline(proc, selector, deadline)
                if line is None:
                    self.end_reason = "solver_exit"
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    req = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ProtocolError(f"invalid JSON: {exc}") from exc
                if isinstance(req, dict) and req.get("op") == "done":
                    self.end_reason = "solver_done"
                    break
                handle_start = time.monotonic()
                resp = self._handle(req)
                deadline += time.monotonic() - handle_start
                self._send(proc, resp, deadline)
                if resp.get("error") == "budget_exhausted":
                    break
        except TimeoutError:
            self.end_reason = "solver_time_limit"
        except ProtocolError as exc:
            self.end_reason = f"protocol_error: {exc}"
            try:
                self._send(proc, {"error": "protocol_error", "detail": str(exc)}, time.monotonic() + 1.0)
            except (TimeoutError, OSError):
                pass
        except OracleLimit:
            self.end_reason = "oracle_limit"
        except OSError:
            self.end_reason = "solver_pipe_closed"
        finally:
            selector.close()
            self._terminate(proc)
        if self.certified and self.ub != self.inst.optimum:
            raise RuntimeError(
                f"harness inconsistency on {self.inst.name}: certified {self.ub} but optimum {self.inst.optimum}"
            )
        return {
            "instance": self.inst.name,
            "certified": self.certified,
            "calls": self.calls,
            "decide_calls": self.decide_calls,
            "hs_calls": self.hs_calls,
            "lb": self.lb,
            "ub": self.ub,
            "end_reason": self.end_reason,
            "hs_nodes": self.nodes,
            "wall_sec": round(time.monotonic() - start, 3),
        }

    @staticmethod
    def _send(proc, payload: dict, deadline: float) -> None:
        """Write one JSON line; never blocks past the deadline (TimeoutError)."""
        view = memoryview((json.dumps(payload) + "\n").encode())
        fd = proc.stdin.fileno()
        while view:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            _, writable, _ = select.select([], [fd], [], min(remaining, 1.0))
            if writable:
                written = os.write(fd, view[:4096])
                view = view[written:]

    @staticmethod
    def _terminate(proc) -> None:
        try:
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            proc.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            pass
        for stream in (proc.stdout,):
            try:
                stream.close()
            except OSError:
                pass


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def discover_variants() -> list[str]:
    try:
        out = subprocess.run(
            SOLVER_CMD + ["list"], cwd=str(ROOT), capture_output=True, timeout=LIST_TIMEOUT_SEC, check=True
        ).stdout.decode()
    except (subprocess.SubprocessError, OSError) as exc:
        raise SystemExit(f"could not list solver variants: {exc}")
    text = out.strip()
    try:
        names = json.loads(text)
        if not isinstance(names, list):
            raise ValueError
    except ValueError:
        names = text.split()
    variants = []
    for name in names:
        if isinstance(name, str) and NAME_RE.match(name) and name not in variants:
            variants.append(name)
    if not variants:
        raise SystemExit("solver listed no valid variants")
    return variants


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    solved = sum(1 for r in rows if r["certified"] and r["calls"] <= SOLVE_BUDGET)
    call_ratio = sum((r["calls"] if r["certified"] else CALL_CAP) / SOLVE_BUDGET for r in rows) / n
    total_decide = sum(r["decide_calls"] for r in rows)
    total_hs = sum(r["hs_calls"] for r in rows)
    total = total_decide + total_hs
    return {
        "certified_solve_rate": solved / n,
        "mean_call_ratio": call_ratio,
        "mean_decide_calls": total_decide / n,
        "mean_hs_calls": total_hs / n,
        "hs_call_share": (total_hs / total) if total else 0.0,
    }


def load_instances() -> list[Instance]:
    payload = json.loads(INSTANCE_FILE.read_text(encoding="utf-8"))
    return [Instance(item) for item in payload["instances"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--details", default=str(DETAILS_OUTPUT))
    parser.add_argument("--seed-offset", type=int, default=0,
                        help="shift every per-instance seed (seed-noise studies only)")
    parser.add_argument("--limit", type=int, default=0, help="score only the first N instances (smoke tests)")
    args = parser.parse_args()

    instances = load_instances()
    if args.limit > 0:
        instances = instances[: args.limit]
    variants = discover_variants()
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    results = {}
    details = {}
    for variant in variants:
        rows = []
        with open(log_dir / f"solver_{SLICE}_{variant}.stderr", "wb") as err:
            for idx, inst in enumerate(instances):
                seed = BASE_SEED + 7919 * idx + 104729 * args.seed_offset
                row = Session(inst, variant, seed, CALL_CAP, err).run()
                row["index"] = idx
                rows.append(row)
                print(f"[{SLICE}] {variant} {inst.name}: certified={row['certified']} calls={row['calls']} "
                      f"(decide {row['decide_calls']}, hs {row['hs_calls']}) end={row['end_reason']}",
                      file=sys.stderr, flush=True)
        results[variant] = summarize(rows)
        details[variant] = [{k: row[k] for k in DETAIL_FIELDS} for row in rows]
    scores = {
        "slice": SLICE,
        "solve_budget": SOLVE_BUDGET,
        "call_cap": CALL_CAP,
        "n_instances": len(instances),
        "seed_offset": args.seed_offset,
        "experiments": {EXPERIMENT: {"results": results}},
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2) + "\n", encoding="utf-8")
    if args.details:
        Path(args.details).write_text(json.dumps(details, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
