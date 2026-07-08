# Venues and their availability

Two things go here:

## 1. Venue list (`venues_template.csv`)

| column | meaning | example |
|---|---|---|
| venue_id | short code | AUD-1 |
| name | full name | Main Auditorium |
| capacity | seats | 400 |
| building | block/building | Academic Block |
| equipment | comma-free list separated by `;` | projector;audio;stage |

## 2. Busy slots (`venue_busy_template.csv`)

Only the times a venue is **NOT** available for events (classes held there,
maintenance, reserved). Anything not listed counts as free within university
hours (Mon–Fri 08:30–17:15). One row per recurring weekly block:

| column | meaning | example |
|---|---|---|
| venue_id | matches the list above | Lab-3 |
| day | Mon / Tue / Wed / Thu / Fri | Mon |
| start | 24h | 08:30 |
| end | 24h | 11:30 |
| reason | optional | BSAI-6 classes |

An Excel sheet or a photo of the venue booking register works too.
