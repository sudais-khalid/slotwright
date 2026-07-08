# Real Department Data — upload here

Drop the Department of Artificial Intelligence's real data into these three
folders. Any format works (Excel, CSV, PDF, or a photo/screenshot of the
notice-board sheet) — CSV templates are provided in each folder if you prefer
to type it in directly.

University hours: **Monday–Friday, 8:30 AM – 5:15 PM.**
When writing times use 24-hour `HH:MM` (8:30 AM → `08:30`, 5:15 PM → `17:15`).
Odd class lengths are fine — the importer snaps them to the scheduling grid.

| Folder | What goes in it |
|---|---|
| `timetables/` | Weekly class timetable for each semester (1–8), one file per semester or one combined file |
| `venues/` | The list of venues (capacity, building) and when each venue is NOT available |
| `events/` | The semester event plan: events the societies/department want scheduled |

Once files are here, the importer (`backend/simulator/import_real.py`) parses
them, reseeds MongoDB, and the agent trains against the real department data.
