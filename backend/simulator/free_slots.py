"""Common free-slot computation for a target student group (FR-04).

The free ratio for a (day, slot) cell is the share of students in the
(department, semester) group whose weekly timetable has no lecture/lab there.
Computed at scheduling time from student documents, per Section 12 of the
requirements document — never stored as its own collection.
"""
import numpy as np

from .config import N_DAYS, N_SLOTS


def group_free_ratio(students: list[dict], department: str, semester: int,
                      n_days: int = N_DAYS, n_slots: int = N_SLOTS) -> np.ndarray:
    """(n_days, n_slots) array of free ratios in [0, 1] for the group.

    n_days/n_slots default to the synthetic grid but must be passed explicitly
    for any dataset with a different grid shape (e.g. real timetables use 9
    real class periods instead of the synthetic 6)."""
    group = [s for s in students if s["department"] == department and s["semester"] == semester]
    grid = np.zeros((n_days, n_slots))
    if not group:
        return grid
    for s in group:
        busy = {(d, sl) for d, sl in s["weekly_timetable"]}
        for d in range(n_days):
            for sl in range(n_slots):
                if (d, sl) not in busy:
                    grid[d, sl] += 1
    return grid / len(group)


def group_interest_share(students: list[dict], department: str, semester: int, category: str) -> float:
    """Share of the target group whose interests include the event category."""
    group = [s for s in students if s["department"] == department and s["semester"] == semester]
    if not group:
        return 0.0
    return sum(1 for s in group if category in s["interests"]) / len(group)
