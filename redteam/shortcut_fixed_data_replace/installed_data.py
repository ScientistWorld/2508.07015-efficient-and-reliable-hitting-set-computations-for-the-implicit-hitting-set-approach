"""Small deterministic PBO benchmark instances for scaled PBO-IHS tests."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Iterable


@dataclass(frozen=True)
class PBConstraint:
    terms: tuple[tuple[int, bool, int], ...]
    rhs: int

    def value(self, assignment: tuple[int, ...]) -> int:
        total = 0
        for var, positive, coeff in self.terms:
            lit_value = assignment[var] if positive else 1 - assignment[var]
            total += coeff * lit_value
        return total

    def satisfied(self, assignment: tuple[int, ...]) -> bool:
        return self.value(assignment) >= self.rhs

    def objective_only(self, n_objective: int) -> bool:
        return all(var < n_objective for var, _, _ in self.terms)


@dataclass(frozen=True)
class PBOInstance:
    name: str
    n_objective: int
    n_auxiliary: int
    objective_weights: tuple[int, ...]
    constraints: tuple[PBConstraint, ...]

    @property
    def n_vars(self) -> int:
        return self.n_objective + self.n_auxiliary

    def objective_cost(self, assignment: tuple[int, ...]) -> int:
        return sum(w * assignment[i] for i, w in enumerate(self.objective_weights))


def _c(terms: Iterable[tuple[int, bool, int]], rhs: int) -> PBConstraint:
    return PBConstraint(tuple(terms), rhs)


def _original_benchmark_instances() -> list[PBOInstance]:
    return [
        PBOInstance(
            "warehouse_cover",
            7,
            3,
            (3, 5, 2, 6, 4, 7, 3),
            (
                _c(((0, True, 1), (1, True, 1), (7, True, 1)), 1),
                _c(((2, True, 1), (7, False, 1)), 1),
                _c(((1, True, 1), (3, True, 1), (8, True, 1)), 1),
                _c(((4, True, 1), (8, False, 1)), 1),
                _c(((5, True, 1), (6, True, 1), (9, True, 1)), 1),
                _c(((0, True, 2), (4, True, 1), (9, False, 1)), 2),
                _c(((2, True, 1), (3, True, 1), (6, True, 1)), 1),
                _c(((0, False, 1), (5, False, 1), (8, True, 1)), 1),
            ),
        ),
        PBOInstance(
            "repair_schedule",
            8,
            3,
            (4, 2, 8, 3, 7, 5, 6, 4),
            (
                _c(((0, True, 1), (2, True, 1), (8, True, 1)), 1),
                _c(((1, True, 1), (8, False, 1)), 1),
                _c(((3, True, 1), (4, True, 1), (9, True, 1)), 1),
                _c(((2, True, 1), (9, False, 1)), 1),
                _c(((5, True, 1), (6, True, 1), (10, True, 1)), 1),
                _c(((7, True, 1), (10, False, 1)), 1),
                _c(((0, True, 1), (3, True, 1), (5, True, 1)), 1),
                _c(((1, False, 1), (4, False, 1), (6, True, 1)), 1),
                _c(((2, False, 1), (7, False, 1), (9, True, 1)), 1),
            ),
        ),
        PBOInstance(
            "network_activation",
            9,
            4,
            (6, 4, 5, 3, 9, 2, 8, 5, 7),
            (
                _c(((0, True, 1), (1, True, 1), (9, True, 1)), 1),
                _c(((2, True, 1), (9, False, 1)), 1),
                _c(((3, True, 1), (4, True, 1), (10, True, 1)), 1),
                _c(((5, True, 1), (10, False, 1)), 1),
                _c(((6, True, 1), (7, True, 1), (11, True, 1)), 1),
                _c(((8, True, 1), (11, False, 1)), 1),
                _c(((0, True, 1), (3, True, 1), (6, True, 1), (12, True, 1)), 2),
                _c(((1, True, 1), (5, True, 1), (12, False, 1)), 1),
                _c(((2, False, 1), (4, False, 1), (7, True, 1)), 1),
                _c(((0, False, 1), (8, False, 1), (10, True, 1)), 1),
            ),
        ),
    ]


def all_assignments(n_vars: int):
    for values in product((0, 1), repeat=n_vars):
        yield tuple(values)


def benchmark_instances() -> list[PBOInstance]:
    return [PBOInstance(i.name, i.n_objective, i.n_auxiliary,
                        i.objective_weights, ())
            for i in _original_benchmark_instances()]
