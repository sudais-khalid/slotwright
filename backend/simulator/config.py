"""Shared constants defining the simulated university's time grid and taxonomy."""

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SLOT_LABELS = [
    "09:00-10:00", "10:00-11:00", "11:00-12:00",
    "12:00-13:00", "14:00-15:00", "15:00-16:00",
]
N_DAYS = len(DAYS)
N_SLOTS = len(SLOT_LABELS)
N_WEEKS = 16
EXAM_WEEKS = [8, 16]  # midterm and final weeks

DEPARTMENTS = ["AI", "CS", "SE", "DS"]
SEMESTERS = [2, 4, 6, 8]

# category -> (min_audience, max_audience)
CATEGORIES = {
    "workshop": (30, 80),
    "seminar": (40, 120),
    "hackathon": (50, 150),
    "career_fair": (150, 350),
    "guest_lecture": (60, 200),
    "society_meeting": (10, 40),
}
CATEGORY_LIST = list(CATEGORIES.keys())

VENUES = [
    {"venue_id": "V01", "name": "Seminar Room A", "capacity": 40, "building": "Block A", "equipment": ["projector"]},
    {"venue_id": "V02", "name": "Seminar Room B", "capacity": 60, "building": "Block A", "equipment": ["projector"]},
    {"venue_id": "V03", "name": "Computer Lab 3", "capacity": 50, "building": "Block B", "equipment": ["pcs", "projector"]},
    {"venue_id": "V04", "name": "Lecture Hall 1", "capacity": 120, "building": "Block B", "equipment": ["projector", "audio"]},
    {"venue_id": "V05", "name": "Lecture Hall 2", "capacity": 150, "building": "Block C", "equipment": ["projector", "audio"]},
    {"venue_id": "V06", "name": "Multipurpose Hall", "capacity": 250, "building": "Block C", "equipment": ["stage", "audio"]},
    {"venue_id": "V07", "name": "Main Auditorium", "capacity": 500, "building": "Main", "equipment": ["stage", "audio", "lights"]},
    {"venue_id": "V08", "name": "Outdoor Court", "capacity": 300, "building": "Grounds", "equipment": []},
]
