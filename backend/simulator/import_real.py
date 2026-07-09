"""Importer for the Department of AI's real Fall 2025 data (real_data/).

Three source documents, all aSc-Timetables / office exports with no machine-
readable structure beyond their PDF table geometry:

  timetables/*.pdf  — one page per section (e.g. "BSAI - 6"), a 5-day x 9-period
                       grid of classes. We only need OCCUPANCY (is a cell
                       empty or not) to compute FR-04's group free-ratio, so
                       course/teacher names inside a cell are not parsed —
                       parsing that reliably would require untangling
                       overlapping text runs the exporter emits per cell,
                       which is unnecessary work for a busy/free signal.
  venues/*.pdf       — same grid, one page per classroom/lab, used as venue
                       availability. Capacities aren't printed anywhere in
                       the export; see CAPACITY_GUESS below.
  events/*.pdf       — the AI Innovation Society's semester plan, a real
                       table (Date / Event / Time / Duration / Audience) that
                       parses cleanly, unlike the two grids above.

Any file matching these roles by folder can be dropped in; multiple PDFs
per folder are all scanned. A CSV with a `venue_id` and `capacity` column in
venues/ overrides the capacity guess.
"""
import csv
import re
from datetime import date, timedelta
from pathlib import Path

import pdfplumber

REAL_DAY_CODES = ["Mo", "Tu", "We", "Th", "Fr"]
REAL_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
REAL_SLOT_LABELS = [
    "08:30-09:25", "09:25-10:20", "10:20-11:15", "11:15-12:10", "12:10-13:05",
    "13:35-14:30", "14:30-15:25", "15:25-16:20", "16:20-17:15",
]
# table column index -> slot index (col 0 = day label, col 6 = the unschedulable lunch/prayer break)
SLOT_COL_MAP = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 7: 5, 8: 6, 9: 7, 10: 8}
PERIOD_MINUTES = 55

DEPARTMENT = "AI"

# No capacity is printed in the export; guessed from the room-name pattern.
# Override any of these by adding a CSV with venue_id,capacity columns to real_data/venues/.
CAPACITY_GUESS = {"lab": 40, "dld": 35, "classroom": 60}

CATEGORY_MAP = {
    "seminar": "seminar", "workshop": "workshop", "visit": "guest_lecture",
    "webinar": "guest_lecture", "competition": "hackathon", "exhibition": "career_fair",
}
# checked in order — most specific phrase first, so "ms" (postgrad) can't
# false-match inside an unrelated word like "teams"
AUDIENCE_GUESS = [
    ("faculty", 150), ("guests", 150),
    ("open", 80), ("teams", 80),
    ("selected batch", 30), ("volunteers", 30),
    ("all students", 60),
    (r"\bms\b", 20), ("postgrad", 20),
]
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _page_label(page) -> str:
    """The bold oversized text on each page — a section or room name."""
    chars = page.chars
    if not chars:
        return ""
    maxsize = max(c["size"] for c in chars)
    raw = "".join(c["text"] for c in chars if c["size"] >= maxsize - 0.5)
    for code in REAL_DAY_CODES:
        raw = raw.replace(code, "", 1) if raw.startswith(code) else raw
    # the prefix is the 5 day codes concatenated; strip them all from the front
    for code in REAL_DAY_CODES:
        if raw.startswith(code):
            raw = raw[len(code):]
    return raw.strip()


def _extract_weekly_grid(page) -> set[tuple[int, int]]:
    """Returns the set of (day_idx, slot_idx) cells that are occupied on this page."""
    tables = page.find_tables()
    if not tables:
        return set()
    rows = tables[0].extract()
    busy: set[tuple[int, int]] = set()
    day_idx = None
    for row in rows:
        label = (row[0] or "").strip()
        if label in REAL_DAY_CODES:
            day_idx = REAL_DAY_CODES.index(label)
        if day_idx is None:
            continue
        for col, slot in SLOT_COL_MAP.items():
            if col < len(row) and row[col] and row[col].strip():
                busy.add((day_idx, slot))
    return busy


def parse_student_timetables(pdf_paths: list[Path]) -> dict[int, list[list[int]]]:
    """Returns {semester_number: busy_cells} for every 'BSAI - N' page found."""
    result: dict[int, list[list[int]]] = {}
    for path in pdf_paths:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                label = _page_label(page)
                m = re.match(r"BSAI\s*-\s*(\d+)", label, re.IGNORECASE)
                if not m:
                    continue
                semester = int(m.group(1))
                busy = _extract_weekly_grid(page)
                result[semester] = [[d, s] for d, s in sorted(busy)]
    return result


def _guess_capacity(venue_id: str) -> int:
    low = venue_id.lower()
    if "dld" in low:
        return CAPACITY_GUESS["dld"]
    if "lab" in low:
        return CAPACITY_GUESS["lab"]
    return CAPACITY_GUESS["classroom"]


def _load_capacity_overrides(venues_dir: Path) -> dict[str, int]:
    overrides: dict[str, int] = {}
    for csv_path in venues_dir.glob("*.csv"):
        if "template" in csv_path.stem.lower():
            continue
        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "venue_id" not in reader.fieldnames or "capacity" not in reader.fieldnames:
                continue
            for row in reader:
                if row.get("venue_id") and row.get("capacity"):
                    overrides[row["venue_id"].strip()] = int(row["capacity"])
    return overrides


def parse_classroom_timetable(pdf_paths: list[Path], capacity_overrides: dict[str, int] | None = None) -> list[dict]:
    """Returns a venues list: one entry per classroom/lab page found."""
    capacity_overrides = capacity_overrides or {}
    venues = []
    seen = set()
    for path in pdf_paths:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                venue_id = re.sub(r"\s+", " ", _page_label(page)).strip()
                if not venue_id or venue_id in seen:
                    continue
                seen.add(venue_id)
                busy = _extract_weekly_grid(page)
                available = [[d, s] for d in range(5) for s in range(9) if (d, s) not in busy]
                venues.append({
                    "venue_id": venue_id,
                    "name": venue_id,
                    "capacity": capacity_overrides.get(venue_id, _guess_capacity(venue_id)),
                    "building": "AI Department",
                    "equipment": ["pcs", "projector"] if "lab" in venue_id.lower() else ["projector"],
                    "available_slots": available,
                })
    return venues


# ---------- event plan ----------

def _to_minutes(text: str) -> int | None:
    m = re.search(r"(\d{1,2}):(\d{2})\s*(AM|PM)", text, re.IGNORECASE)
    if not m:
        return None
    h, mnt, ap = int(m.group(1)), int(m.group(2)), m.group(3).upper()
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return h * 60 + mnt


def _parse_time_range(text: str) -> tuple[int | None, int | None]:
    times = re.findall(r"\d{1,2}:\d{2}\s*(?:AM|PM)", text, re.IGNORECASE)
    if len(times) < 2:
        return None, None
    return _to_minutes(times[0]), _to_minutes(times[1])


def _parse_date_range(text: str, year: int) -> tuple[date, date] | None:
    clean = re.sub(r"\s+", " ", text).strip()
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\s*[–-]\s*(\d{1,2})\s+([A-Za-z]{3,})", clean)
    if m:
        d1, mo1, d2, mo2 = m.groups()
        mo1n, mo2n = MONTHS.get(mo1[:3].lower()), MONTHS.get(mo2[:3].lower())
        if mo1n and mo2n:
            return date(year, mo1n, int(d1)), date(year, mo2n, int(d2))
    m = re.search(r"(\d{1,2})\s*[–-]\s*(\d{1,2})\s+([A-Za-z]{3,})", clean)
    if m:
        d1, d2, mo = m.groups()
        mon = MONTHS.get(mo[:3].lower())
        if mon:
            return date(year, mon, int(d1)), date(year, mon, int(d2))
    return None


def _guess_audience(text: str) -> int:
    low = text.lower()
    for pattern, val in AUDIENCE_GUESS:
        if re.search(pattern, low):
            return val
    return 50


def parse_event_plan(pdf_paths: list[Path], semester_start: date, year: int) -> tuple[list[dict], list[dict]]:
    """Returns (events, calendar_entries). Events with no resolvable date (TBD) are skipped."""
    events: list[dict] = []
    exam_weeks: set[int] = set()
    holiday_weeks: set[int] = set()
    n = 0

    def week_of(d: date) -> int:
        return max(1, (d - semester_start).days // 7 + 1)

    for path in pdf_paths:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.find_tables():
                    rows = table.extract()
                    if not rows or len(rows[0]) < 13:
                        continue  # not the events table (e.g. a stray fragment table)
                    day_range_re = re.compile(r"\d{1,2}\s*[–-]\s*\d{1,2}|^[A-Z]+$")
                    blocks: list[list[list]] = []
                    for row in rows:
                        # date text sits in col 0 for normal events but shifts to col 1
                        # for the short exam/holiday placeholder rows ("—" duration/audience).
                        # A lone month name on a continuation row (e.g. "May" under "18 – 22")
                        # must NOT be treated as a new block start.
                        col0 = (row[0] or "").strip()
                        col1 = (row[1] or "").strip()
                        starts_block = bool(col0) or bool(day_range_re.match(col1))
                        if starts_block and col0 not in ("Date",) and col1 not in ("Date",):
                            blocks.append([row])
                        elif blocks:
                            blocks[-1].append(row)

                    for block in blocks:
                        head = block[0]
                        # the month sometimes lands on a second row of the same cell
                        # (e.g. "18 – 22" / "May" split across two table rows)
                        date_text = " ".join(
                            (r[0] or r[1] or "") for r in block if (r[0] or r[1] or "").strip()
                        )
                        if date_text.strip() in ("APRIL", "MAY", "JUNE", "JULY", "AUGUST"):
                            continue
                        time_text = head[6] or ""
                        duration_text = head[9] or ""
                        audience_text = head[12] or ""

                        col4_lines = [r[4].strip() for r in block if len(r) > 4 and r[4] and r[4].strip()]
                        if not col4_lines:
                            continue
                        cat_idx = next((i for i, l in enumerate(col4_lines) if l.lower() in CATEGORY_MAP), None)

                        date_range = _parse_date_range(date_text, year)

                        if cat_idx is None:
                            # calendar-only row: no exam/workshop category, just an exam/holiday note
                            label = " ".join(col4_lines).lower()
                            if date_range:
                                w1, w2 = week_of(date_range[0]), week_of(date_range[1])
                                weeks = list(range(w1, w2 + 1))
                                if "exam" in label:
                                    exam_weeks.update(weeks)
                                elif "holiday" in label or "eid" in label:
                                    holiday_weeks.update(weeks)
                            continue

                        if date_range is None:
                            continue  # TBD-dated items (e.g. the online webinar) aren't schedulable

                        name = " ".join(col4_lines[:cat_idx]).strip() or "Untitled Event"
                        category = CATEGORY_MAP[col4_lines[cat_idx].lower()]
                        start_min, end_min = _parse_time_range(time_text)
                        minutes = (end_min - start_min) if start_min is not None and end_min is not None else 60
                        duration_slots = max(1, round(minutes / PERIOD_MINUTES))
                        priority = 3 if "flagship" in name.lower() else (1 if category == "guest_lecture" else 2)
                        audience = _guess_audience(audience_text)

                        n += 1
                        events.append({
                            "event_id": f"REAL{n:03d}",
                            "name": name,
                            "category": category,
                            "expected_audience": audience,
                            "duration": round(minutes / 60, 1),
                            "duration_slots": duration_slots,
                            "priority": priority,
                            "department": DEPARTMENT,
                            "week": week_of(date_range[0]),
                            "organizer": "AI Innovation Society",
                            "_audience_text": audience_text.replace("\n", " ").strip(),
                        })

    calendar = []
    if exam_weeks:
        calendar.append({"type": "exam", "weeks": sorted(exam_weeks), "affected_departments": [DEPARTMENT]})
    if holiday_weeks:
        calendar.append({"type": "holiday", "weeks": sorted(holiday_weeks), "affected_departments": [DEPARTMENT]})
    return events, calendar


# ---------- top-level ----------

def import_real_dataset(real_data_dir: Path, n_students_per_semester: int = 40,
                         semester_start: date = date(2025, 4, 13), year: int = 2025,
                         seed: int = 42) -> dict:
    import random

    tt_dir, venue_dir, event_dir = real_data_dir / "timetables", real_data_dir / "venues", real_data_dir / "events"
    tt_pdfs = [p for p in tt_dir.glob("*.pdf")]
    venue_pdfs = [p for p in venue_dir.glob("*.pdf")]
    event_pdfs = [p for p in event_dir.glob("*.pdf")]
    if not (tt_pdfs and venue_pdfs and event_pdfs):
        raise FileNotFoundError(
            "real_data/ needs at least one PDF each in timetables/, venues/, and events/."
        )

    semester_grids = parse_student_timetables(tt_pdfs)
    if not semester_grids:
        raise ValueError("No 'BSAI - N' pages found in timetables/*.pdf.")
    semesters = sorted(semester_grids)

    capacity_overrides = _load_capacity_overrides(venue_dir)
    venues = parse_classroom_timetable(venue_pdfs, capacity_overrides)

    events, calendar = parse_event_plan(event_pdfs, semester_start, year)
    events_expanded = []
    for ev in events:
        for sem in semesters:  # every real event targets the whole department (all 7 semesters)
            e = dict(ev, semester=sem)
            e["event_id"] = f"{ev['event_id']}-S{sem}"
            events_expanded.append(e)
    events_expanded.sort(key=lambda e: e["week"])

    n_weeks = max([w for e in events_expanded for w in [e["week"]]] +
                  [w for c in calendar for w in c["weeks"]] + [16])

    rng = random.Random(seed)
    students = []
    sid = 0
    for sem in semesters:
        busy = semester_grids[sem]
        for _ in range(n_students_per_semester):
            sid += 1
            students.append({
                "student_id": f"R{sid:04d}",
                "department": DEPARTMENT,
                "semester": sem,
                "weekly_timetable": [list(c) for c in busy],
                # interests aren't in the source documents — synthesized (flagged assumption)
                "interests": rng.sample(list(CATEGORY_MAP.values()), k=rng.randint(1, 3)),
                "attendance_history": round(rng.uniform(0.3, 0.9), 2),
            })

    return {
        "students": students,
        "events": events_expanded,
        "venues": venues,
        "calendar": calendar,
        "seed": seed,
        "source": "real_fall2025",
        "days": REAL_DAYS,
        "slots": REAL_SLOT_LABELS,
        "weeks": n_weeks,
        "departments": [DEPARTMENT],
        "semesters": semesters,
    }
