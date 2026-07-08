"""Conflict detection for a proposed placement (FR-05).

A placement is (week, day, slot, venue_id) for a given event, checked against
the running schedule. Returns a list of conflict type strings; empty = clean.
"""
LECTURE_OVERLAP_THRESHOLD = 0.5  # below this group-free ratio, most students are in class


def detect_conflicts(event: dict, week: int, day: int, slot: int, venue: dict,
                     free_ratio: float, exam_weeks: set[int],
                     schedule: dict) -> list[str]:
    """schedule maps (week, day, slot, venue_id) -> event dict for placements so far."""
    conflicts = []
    if (week, day, slot, venue["venue_id"]) in schedule:
        conflicts.append("venue_double_booking")
    if [day, slot] not in venue["available_slots"]:
        conflicts.append("venue_unavailable")
    if free_ratio < LECTURE_OVERLAP_THRESHOLD:
        conflicts.append("lecture_overlap")
    if week in exam_weeks:
        conflicts.append("exam_week")
    if venue["capacity"] < 0.5 * event["expected_audience"]:
        conflicts.append("venue_too_small")
    for (w, d, sl, _v), other in schedule.items():
        if w == week and d == day and sl == slot and other["event_id"] != event["event_id"]:
            if other["priority"] >= 2 and event["priority"] >= 2:
                conflicts.append("major_event_clash")
            break
    return conflicts
