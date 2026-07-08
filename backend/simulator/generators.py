"""Synthetic data generators (FR-01).

Students in the same (department, semester) group share a base timetable —
they attend the same lectures — plus 1–2 individual elective slots, which is
what makes the group free-slot intersection meaningful rather than trivial.
"""
import random

from .config import (
    CATEGORIES, CATEGORY_LIST, DEPARTMENTS, EXAM_WEEKS, N_DAYS, N_SLOTS,
    N_WEEKS, SEMESTERS, VENUES,
)


def _group_base_timetable(rng: random.Random) -> list[list[int]]:
    """~14 of the 30 weekly (day, slot) cells are lectures/labs for the group."""
    cells = [[d, s] for d in range(N_DAYS) for s in range(N_SLOTS)]
    return rng.sample(cells, k=rng.randint(12, 16))


def generate_students(rng: random.Random, n_students: int = 480) -> list[dict]:
    students = []
    groups = [(d, s) for d in DEPARTMENTS for s in SEMESTERS]
    base = {g: _group_base_timetable(rng) for g in groups}
    per_group = max(1, n_students // len(groups))
    sid = 0
    for dept, sem in groups:
        for _ in range(per_group):
            sid += 1
            timetable = [list(c) for c in base[(dept, sem)]]
            free = [[d, s] for d in range(N_DAYS) for s in range(N_SLOTS) if [d, s] not in timetable]
            for cell in rng.sample(free, k=rng.randint(1, 2)):  # electives
                timetable.append(cell)
            students.append({
                "student_id": f"S{sid:04d}",
                "department": dept,
                "semester": sem,
                "weekly_timetable": timetable,
                "interests": rng.sample(CATEGORY_LIST, k=rng.randint(1, 3)),
                "attendance_history": round(rng.uniform(0.3, 0.9), 2),
            })
    return students


def generate_events(rng: random.Random, n_events: int = 40) -> list[dict]:
    events = []
    for i in range(1, n_events + 1):
        category = rng.choice(CATEGORY_LIST)
        lo, hi = CATEGORIES[category]
        events.append({
            "event_id": f"E{i:03d}",
            "category": category,
            "expected_audience": rng.randint(lo, hi),
            "duration": 1,
            "priority": rng.randint(1, 3),
            "department": rng.choice(DEPARTMENTS),
            "semester": rng.choice(SEMESTERS),
            "week": rng.randint(1, N_WEEKS),
            "preferred_venue": rng.choice(VENUES)["venue_id"],
            "organizer": f"Society-{rng.randint(1, 8)}",
        })
    events.sort(key=lambda e: e["week"])
    return events


def generate_venues(rng: random.Random) -> list[dict]:
    """Each venue is blocked (maintenance/classes) in a few weekly cells."""
    venues = []
    for v in VENUES:
        cells = [[d, s] for d in range(N_DAYS) for s in range(N_SLOTS)]
        blocked = rng.sample(cells, k=rng.randint(2, 5))
        available = [c for c in cells if c not in blocked]
        venues.append({**v, "available_slots": available})
    return venues


def generate_calendar() -> list[dict]:
    entries = [
        {"type": "exam", "weeks": EXAM_WEEKS, "affected_departments": DEPARTMENTS},
        {"type": "holiday", "weeks": [12], "affected_departments": DEPARTMENTS},
    ]
    return entries


def generate_dataset(seed: int = 42, n_students: int = 480, n_events: int = 40) -> dict:
    rng = random.Random(seed)
    return {
        "students": generate_students(rng, n_students),
        "events": generate_events(rng, n_events),
        "venues": generate_venues(rng),
        "calendar": generate_calendar(),
        "seed": seed,
    }
